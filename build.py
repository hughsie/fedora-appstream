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
import time
import tarfile
import fnmatch
import xml.etree.ElementTree as ET
from gi.repository import Gio

# internal
from application import Release
from logger import LoggerItem
from package import Package
from config import Config
from desktop_file import DesktopFile
from font_file import FontFile, FontFileFilter
from input_method import InputMethodTable, InputMethodComponent
from codec import Codec

def package_decompress(pkg):
    if os.path.exists('../extract-package'):
        p = subprocess.Popen(['../extract-package', pkg.filename, 'tmp'],
                             cwd='.', stdout=subprocess.PIPE)
        p.wait()
        if p.returncode:
            raise StandardError('Cannot extract package: ' + p.stdout)

def check_for_symbol(filename, symbol_name):
    p = subprocess.Popen(['/usr/bin/nm', '-D', filename],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    p.wait()
    if p.returncode != 0:
        return False
    for line in out.split('\n'):
        if line.find(symbol_name) >= 0:
            return True
    return False

class Build:

    def __init__(self):
        self.cfg = Config()
        self.application_ids = []
        self.has_valid_content = False
        self.completed = {}

    def add_application(self, app):

        # application is blacklisted
        blacklisted = False
        for b in self.cfg.get_id_blacklist():
            if fnmatch.fnmatch(app.app_id, b):
                app.log.write(LoggerItem.INFO, "application is blacklisted")
                blacklisted = True
                break
        if blacklisted:
            return False

        # packages that ship .desktop files in /usr/share/applications
        # *and* /usr/share/applications/kde4 do not need multiple entries
        if app.app_id in self.application_ids:
            app.log.write(LoggerItem.INFO, "duplicate ID in package %s" % app.pkgnames[0])
            return False
        self.application_ids.append(app.app_id)

        # add AppData
        if not app.add_appdata_file() and app.requires_appdata:
            app.log.write(LoggerItem.INFO, "%s requires AppData" % app.app_id_full)
            return False

        # use the homepage to filter out same more generic apps
        homepage_url = None
        if app.urls.has_key('homepage'):
            homepage_url = app.urls['homepage']
        if homepage_url and not app.project_group:

            # GNOME
            project_urls = [ 'http*://*.gnome.org*',
                             'http://gnome-*.sourceforge.net/']
            for m in project_urls:
                if fnmatch.fnmatch(homepage_url, m):
                    app.project_group = u'GNOME'

            # KDE
            project_urls = [ 'http*://*.kde.org*',
                            'http://*kde-apps.org/*' ]
            for m in project_urls:
                if fnmatch.fnmatch(homepage_url, m):
                    app.project_group = u'KDE'

            # XFCE
            project_urls = [ 'http://*xfce.org*' ]
            for m in project_urls:
                if fnmatch.fnmatch(homepage_url, m):
                    app.project_group = u'XFCE'

            # LXDE
            project_urls = [ 'http://lxde.org*',
                             'http://lxde.sourceforge.net/*' ]
            for m in project_urls:
                if fnmatch.fnmatch(homepage_url, m):
                    app.project_group = u'LXDE'

            # MATE
            project_urls = [ 'http://*mate-desktop.org*' ]
            for m in project_urls:
                if fnmatch.fnmatch(homepage_url, m):
                    app.project_group = u'MATE'

            # log that we auto-added it
            if app.project_group:
                app.log.write(LoggerItem.INFO, "assigned %s" % app.project_group)

        # Do not include apps without a name
        if not 'C' in app.names:
            app.log.write(LoggerItem.INFO, "ignored as no Name")
            return False

        # Do not include apps without a summary
        if not 'C' in app.comments:
            app.log.write(LoggerItem.INFO, "ignored as no Comment")
            return False

        # Do not include apps without an icon
        if not app.icon:
            app.log.write(LoggerItem.INFO, "ignored as no Icon")
            return False

        # do we have screeshot overrides?
        extra_screenshots = os.path.join('../screenshots-extra', app.app_id)
        if os.path.exists(extra_screenshots):
            app.screenshots = []
            overrides = glob.glob(extra_screenshots + "/*.png")
            app.log.write(LoggerItem.INFO, "adding %i screenshot overrides" % len(overrides))
            overrides.sort()
            for f in overrides:
                app.add_screenshot_filename(f)

        # we got something useful
        if not self.has_valid_content:
            self.has_valid_content = True

        return True

    def add_completed(self, pkg, app):
        key = pkg.sourcerpm.replace('.src.rpm', '')
        if key in self.completed:
            self.completed[key].append(app)
        else:
            self.completed[key] = [app]

    def build(self, filename):

        # check the package has .desktop files
        pkg = Package(filename)

        for b in self.cfg.get_package_blacklist():
            if fnmatch.fnmatch(pkg.name, b):
                pkg.log.write(LoggerItem.INFO, "package is blacklisted")
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
                if c[1] != pkg.name:
                    extra_files = glob.glob("./packages/%s*.rpm" % c[1])
                    for f in extra_files:
                        extra_pkg = Package(f)
                        pkg.log.write(LoggerItem.INFO, "adding extra package %s" % extra_pkg.name)
                        package_decompress(extra_pkg)

        # check for duplicate apps in the package
        self.has_valid_content = False

        # check for codecs
        if pkg.name.startswith('gstreamer'):
            app = Codec(pkg, self.cfg)
            if app.parse_files(files):
                if self.add_application(app):
                    self.add_completed(pkg, app)
        else:
            # process each desktop file in the original package
            for f in files:

                pkg.log.write(LoggerItem.INFO, "reading %s" % f)
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
                    pkg.log.write(LoggerItem.INFO, "content type %s not supported" % content_type)
                    continue

                # the ID is the filename
                app_id = os.path.basename(f).decode('utf-8')
                app.set_id(app_id)

                # parse file
                if not app.parse_file(f):
                    continue

                # get the locale info
                if os.path.exists('../extract-gettext'):
                    p = subprocess.Popen(['../extract-gettext', './tmp'],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    p.wait()
                    out, err = p.communicate()
                    if p.returncode == 0:
                        for locale in out.split('\n'):
                            data = locale.split('\t')
                            if len(data) != 2:
                                continue
                            app.languages[data[0]] = data[1]

                # add the last three releases
                if not len(app.releases):
                    for b in pkg.builds[:3]:
                        release = Release()
                        release.version = b.version
                        release.timestamp = b.timestamp
                        app.releases.append(release)

                # get any additional kudos
                for f in pkg.filelist:
                    if f.startswith('/usr/share/gnome-shell/search-providers/'):
                        app.metadata['X-Kudo-SearchProvider'] = ''
                        break
                for f in pkg.filelist:
                    if f.startswith('/usr/share/help/'):
                        app.metadata['X-Kudo-InstallsUserDocs'] = ''
                        break
                for f in pkg.filelist:
                    if f.startswith('/usr/bin/') and check_for_symbol('./tmp' + f, 'gtk_application_set_app_menu'):
                        app.metadata['X-Kudo-UsesAppMenu'] = ''
                        break
                for d in pkg.deps:
                    if d == 'libgtk-3.so.0':
                        app.metadata['X-Kudo-GTK3'] = ''
                for r in app.releases:
                    days = (time.time() - int(r.timestamp)) / (60 * 60 * 24)
                    if days < 365:
                        app.metadata['X-Kudo-RecentRelease'] = ''
                        break

                # write the application
                if self.add_application(app):
                    self.add_completed(pkg, app)

    def write_appstream(self):

        valid_apps = []
        for key in self.completed:
            log = LoggerItem(key)
            valid_apps = self.completed[key]

            # group fonts of the same family
            fltr = FontFileFilter()
            valid_apps = fltr.merge(valid_apps)

            # create AppStream XML and icons
            filename = './appstream/' + key + '.xml'
            filename_icons = "./appstream/%s-icons.tar" % key
            root = ET.Element("applications")
            root.set("version", "0.1")
            for app in valid_apps:
                try:
                    app.build_xml(root)
                    #app.write_status()
                except UnicodeEncodeError, e:
                    log.write(LoggerItem.WARNING,
                              "Failed to build %s: %s" % (app.app_id, str(e)))
                    continue
                except TypeError, e:
                    log.write(LoggerItem.WARNING,
                              "Failed to build %s: %s" % (app.app_id, str(e)))
                    continue
            log.write(LoggerItem.INFO,
                      "writing %s and %s" % (filename, filename_icons))
            try:
                ET.ElementTree(root).write(filename,
                                           encoding='UTF-8',
                                           xml_declaration=True)
            except UnicodeDecodeError, e:
                log.write(LoggerItem.WARNING,
                          "Failed to write %s: %s" % (filename, str(e)))
            else:
                # create AppStream icon tar
                tar = tarfile.open(filename_icons, "w")
                for app in valid_apps:
                    filename = app.app_id + '.png'
                    if os.path.exists('./icons/' + filename):
                        tar.add('./icons/' + filename, arcname=filename)
                tar.close()

        # remove tmp
        if not os.getenv('APPSTREAM_DEBUG'):
            shutil.rmtree('./tmp')
            shutil.rmtree('./icons')

def main():
    job = Build()
    for fn in sys.argv[1:]:
        job.build(fn)
    job.write_appstream()
    sys.exit(0)

if __name__ == "__main__":
    main()
