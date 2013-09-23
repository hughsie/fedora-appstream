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
from input_method import InputMethod

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
        if not os.path.exists('./screenshots'):
            os.makedirs('./screenshots')
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
        application_ids = []
        has_valid_content = False

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
                app = InputMethod(pkg, self.cfg)
            else:
                print 'IGNORE\t', f, '\t', "content type " + content_type + " not supported"
                continue

            # the ID is the filename
            app.set_id(f.split('/')[-1])

            # application is blacklisted
            blacklisted = False
            for b in self.cfg.get_id_blacklist():
                if fnmatch.fnmatch(app.app_id, b):
                    print 'IGNORE\t', f, '\t', "application is blacklisted:", app.app_id
                    blacklisted = True
                    break
            if blacklisted:
                continue

            # packages that ship .desktop files in /usr/share/applications
            # *and* /usr/share/applications/kde4 do not need multiple entries
            if app.app_id in application_ids:
                print 'IGNORE\t', f, '\t', app.app_id, 'duplicate ID in package'
                continue
            application_ids.append(app.app_id)

            # parse desktop file
            if not app.parse_file(f):
                continue

            # do we have an AppData file?
            appdata_file = './tmp/usr/share/appdata/' + app.app_id + '.appdata.xml'
            appdata_extra_file = './appdata-extra/' + app.app_id + '.appdata.xml'
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
                    env['RELAX'] = '1'
                    p = subprocess.Popen(['/usr/bin/appdata-validate', appdata_file],
                                         cwd='.', env=env, stdout=subprocess.PIPE)
                    p.wait()
                    if p.returncode:
                        for line in p.stdout:
                            line = line.replace('\n', '')
                            print 'WARNING\tAppData did not validate: ' + line

                # check the id matches
                if data.get_id() != app.app_id:
                    raise StandardError('The AppData id does not match: ' + app.app_id)

                # check the licence is okay
                if data.get_licence() not in self.cfg.get_content_licences():
                    raise StandardError('The AppData licence is not okay for ' +
                                        app.app_id + ': \'' +
                                        data.get_licence() + '\'')

                # if we have an override, use it for all languages
                tmp = data.get_name()
                if tmp:
                    app.names = {}
                    app.names['C'] = tmp

                # if we have an override, use it for all languages
                tmp = data.get_summary()
                if tmp:
                    app.comments = {}
                    app.comments['C'] = tmp

                # get optional bits
                tmp = data.get_url()
                if tmp:
                    app.homepage_url = tmp
                app.descriptions = data.get_descriptions()

            # we got something useful
            if not has_valid_content:
                has_valid_content = True

            # write content
            app.write(xml)

        # create AppStream XML
        xml.write("</applications>\n")
        xml.close()
        if not has_valid_content:
            os.remove(xml_output_file)

        # create AppStream icon tar
        if has_valid_content:
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
