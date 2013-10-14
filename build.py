#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Licensed under the GNU General Public License Version 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

# Copyright (C) 2009-2013
#    Richard Hughes <richard@hughsie.com>
#
# Copyright (C) 2013
#    Florian Festi <ffesti@redhat.com>
#

import glob
import os
import shutil
import subprocess
import sys
import tarfile
import fnmatch
from gi.repository import Gio

# internal
from package import Package
from appdata import AppData
from config import Config
from desktop_file import DesktopFile
from font_file import FontFile
from input_method import InputMethodTable, InputMethodComponent
from codec import Codec

def package_decompress(pkg):
    if os.path.exists('./extract-package'):
        p = subprocess.Popen(['./extract-package', pkg.filename, 'tmp'],
                             cwd='.', stdout=subprocess.PIPE)
        p.wait()
        if p.returncode:
            raise StandardError('Cannot extract package: ' + p.stdout)
    else:
        wildcards = []
        if not os.getenv('APPSTREAM_DEBUG'):
            wildcards.append('./usr/share/applications/*.desktop')
            wildcards.append('./usr/share/applications/kde4/*.desktop')
            wildcards.append('./usr/share/appdata/*.xml')
            wildcards.append('./usr/share/icons/hicolor/*/apps/*')
            wildcards.append('./usr/share/pixmaps/*.*')
            wildcards.append('./usr/share/icons/*.*')
            wildcards.append('./usr/share/*/images/*')
            pkg.extract('./tmp', wildcards)
        else:
            wildcards.append('./*/*.*')
            pkg.extract('./tmp', wildcards)

class Build:

    def __init__(self):
        self.cfg = Config()
        self.application_ids = []

    def add_application(self, app):

        # application is blacklisted
        blacklisted = False
        for b in self.cfg.get_id_blacklist():
            if fnmatch.fnmatch(app.app_id, b):
                print 'IGNORE\t', "application is blacklisted:", app.app_id
                blacklisted = True
                break
        if blacklisted:
            return False

        # packages that ship .desktop files in /usr/share/applications
        # *and* /usr/share/applications/kde4 do not need multiple entries
        if app.app_id in self.application_ids:
            print 'IGNORE\t', app.pkgname, '\t', app.app_id, 'duplicate ID in package'
            return False
        self.application_ids.append(app.app_id)

        # do we have an AppData file?
        appdata_file = './tmp/usr/share/appdata/' + app.app_id + '.appdata.xml'
        appdata_extra_file = './appdata-extra/' + app.type_id + '/' + app.app_id + '.appdata.xml'
        if os.path.exists(appdata_file) and os.path.exists(appdata_extra_file):
            print 'DELETE\t', appdata_extra_file, 'as upstream AppData file exists'
            os.remove(appdata_extra_file)

        # just use the extra file in places of the missing upstream one
        if os.path.exists(appdata_extra_file):
            appdata_file = appdata_extra_file

        # need to extract details
        if os.path.exists(appdata_file):
            data = AppData()
            data.extract(appdata_file)

            # check AppData file validates
            if os.path.exists('/usr/bin/appdata-validate'):
                env = os.environ
                p = subprocess.Popen(['/usr/bin/appdata-validate',
                                      '--relax', appdata_file],
                                     cwd='.', env=env, stdout=subprocess.PIPE)
                p.wait()
                if p.returncode:
                    for line in p.stdout:
                        line = line.replace('\n', '')
                        print 'WARNING\tAppData did not validate: ' + line

            # check the id matches
            if data.get_id() != app.app_id and data.get_id() != app.app_id_full:
                raise StandardError('The AppData id does not match: ' + app.app_id)

            # check the licence is okay
            if data.get_licence() not in self.cfg.get_content_licences():
                raise StandardError('The AppData licence is not okay for ' +
                                    app.app_id + ': \'' +
                                    data.get_licence() + '\'')

            # if we have an override, use it for all languages
            tmp = data.get_names()
            if tmp:
                app.names = tmp

            # if we have an override, use it for all languages
            tmp = data.get_summaries()
            if tmp:
                app.comments = tmp

            # get optional bits
            tmp = data.get_url()
            if tmp:
                app.homepage_url = tmp
            tmp = data.get_project_group()
            if tmp:
                app.project_group = tmp
            app.descriptions = data.get_descriptions()

            # get screenshots
            tmp = data.get_screenshots()
            for image in tmp:
                print 'DOWNLOADING\t', image
                app.add_screenshot_url(image)

        elif app.requires_appdata:
            print 'IGNORE\t', app.pkgname, '\t', app.app_id_full, 'requires AppData to be included'
            return False

        # use the homepage to filter out same more generic apps
        if not app.project_group:

            # GNOME
            project_urls = [ 'http*://*.gnome.org*',
                             'http://gnome-*.sourceforge.net/']
            for m in project_urls:
                if fnmatch.fnmatch(app.homepage_url, m):
                    app.project_group = "GNOME"

            # KDE
            project_urls = [ 'http*://*.kde.org*',
                            'http://*kde-apps.org/*' ]
            for m in project_urls:
                if fnmatch.fnmatch(app.homepage_url, m):
                    app.project_group = "KDE"

            # XFCE
            project_urls = [ 'http://*xfce.org*' ]
            for m in project_urls:
                if fnmatch.fnmatch(app.homepage_url, m):
                    app.project_group = "XFCE"

            # LXDE
            project_urls = [ 'http://lxde.org*',
                             'http://lxde.sourceforge.net/*' ]
            for m in project_urls:
                if fnmatch.fnmatch(app.homepage_url, m):
                    app.project_group = "LXDE"

            # MATE
            project_urls = [ 'http://*mate-desktop.org*' ]
            for m in project_urls:
                if fnmatch.fnmatch(app.homepage_url, m):
                    app.project_group = "MATE"

            # print that we auto-added it
            if app.project_group:
                print 'INFO\t', app.pkgname, '\t', app.app_id, 'assigned', app.project_group

        # we got something useful
        if not self.has_valid_content:
            self.has_valid_content = True

        # Do not include apps without a name
        if not 'C' in app.names:
            print 'IGNORE\t', app.pkgname, '\t', "no Name"
            return False

        # Do not include apps without a summary
        if not 'C' in app.comments:
            print 'IGNORE\t', app.pkgname, '\t', "no Comment"
            return False

        # Do not include apps without an icon
        if not app.icon:
            print 'IGNORE\t', app.pkgname, '\t', "Icon unspecified"
            return False

        # do we have screeshot overrides?
        extra_screenshots = os.path.join('./screenshots-extra', app.app_id)
        if os.path.exists(extra_screenshots):
            app.screenshots = []
            overrides = glob.glob(extra_screenshots + "/*.png")
            print 'INFO\tAdding', len(overrides), 'screenshot overrides'
            overrides.sort()
            for f in overrides:
                app.add_screenshot_filename(f)
        return True

    def build(self, filename):

        # check the package has .desktop files
        print 'SOURCE\t', filename
        pkg = Package(filename)

        for b in self.cfg.get_package_blacklist():
            if fnmatch.fnmatch(pkg.name, b):
                print 'IGNORE\t', filename, '\t', "package is blacklisted:", pkg.name
                return

        # set up state
        if not os.path.exists('./appstream'):
            os.makedirs('./appstream')
        if not os.path.exists('./icons'):
            os.makedirs('./icons')
        if not os.path.exists('./screenshot-cache'):
            os.makedirs('./screenshot-cache')
        if not os.path.exists('./screenshots'):
            os.makedirs('./screenshots')
        if not os.path.exists('./screenshots/source'):
            os.makedirs('./screenshots/source')
        for size in self.cfg.get_screenshot_thumbnail_sizes():
            path = './screenshots/' + str(size[0]) + 'x' + str(size[1])
            if not os.path.exists(path):
                os.makedirs(path)

        # remove tmp
        if os.path.exists('./tmp'):
            shutil.rmtree('./tmp')
        os.makedirs('./tmp')

        # decompress main file and search for desktop files
        package_decompress(pkg)
        files = []
        for f in self.cfg.get_interesting_installed_files():
            files.extend(glob.glob("./tmp" + f))
        files.sort()

        # we only need to install additional files if we're not running on
        # the builders
        for c in self.cfg.get_package_data_list():
            if fnmatch.fnmatch(pkg.name, c[0]):
                extra_files = glob.glob("./packages/%s*.rpm" % c[1])
                for f in extra_files:
                    extra_pkg = Package(f)
                    print "INFO\tAdding extra package %s for %s" % (extra_pkg.name, pkg.name)
                    package_decompress(extra_pkg)

        # open the AppStream file for writing
        xml_output_file = './appstream/' + pkg.name + '.xml'
        xml = open(xml_output_file, 'w')
        xml.write("<?xml version=\"1.0\"?>\n")
        xml.write("<applications version=\"0.1\">\n")

        # check for duplicate apps in the package
        self.has_valid_content = False

        # check for codecs
        if pkg.name.startswith('gstreamer'):
            app = Codec(pkg, self.cfg)
            if app.parse_files(files):
                if self.add_application(app):
                    app.write(xml)
        else:
            # process each desktop file in the original package
            for f in files:

                print 'PROCESS\t', f

                fi = Gio.file_new_for_path(f)
                info = fi.query_info('standard::content-type', 0, None)

                # create the right object depending on the content type
                content_type = info.get_content_type()
                if content_type == 'inode/symlink':
                    continue
                if content_type == 'application/x-font-ttf':
                    app = FontFile(pkg, self.cfg)
                elif content_type == 'application/x-font-otf':
                    app = FontFile(pkg, self.cfg)
                elif content_type == 'application/x-desktop':
                    app = DesktopFile(pkg, self.cfg)
                elif content_type == 'application/xml':
                    app = InputMethodComponent(pkg, self.cfg)
                elif content_type == 'application/x-sqlite3':
                    app = InputMethodTable(pkg, self.cfg)
                else:
                    print 'IGNORE\t', f, '\t', "content type " + content_type + " not supported"
                    continue

                # the ID is the filename
                app.set_id(f.split('/')[-1])

                # parse file
                if not app.parse_file(f):
                    continue

                # write the application
                if self.add_application(app):
                    app.write(xml)

        # create AppStream XML
        xml.write("</applications>\n")
        xml.close()
        if not self.has_valid_content:
            os.remove(xml_output_file)

        # create AppStream icon tar
        if self.has_valid_content:
            output_file = "./appstream/%s-icons.tar" % pkg.name
            print 'WRITING\t', output_file
            tar = tarfile.open(output_file, "w")
            files = glob.glob("./icons/*.png")
            for f in files:
                tar.add(f, arcname=f.split('/')[-1])
            tar.close()

        # remove tmp
        if not os.getenv('APPSTREAM_DEBUG'):
            shutil.rmtree('./tmp')
            shutil.rmtree('./icons')

def main():
    job = Build()
    for fn in sys.argv[1:]:
        job.build(fn)
    sys.exit(0)

if __name__ == "__main__":
    main()
