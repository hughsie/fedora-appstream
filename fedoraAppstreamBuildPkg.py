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

import ConfigParser
import glob
from PIL import Image
import os
import shutil
import subprocess
import sys
import tarfile
import fnmatch
import re
from gi.repository import GdkPixbuf, Gdk, GLib, Rsvg

import cairo

import fedoraAppstreamData
import fedoraAppstreamPkg

# NOTE; we could use escape() from xml.sax.saxutils import escape but that seems
# like a big dep for such trivial functionality
def sanitise_xml(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

def resize_icon(icon, filename):

    # get ending
    ext = icon.rsplit('.', 1)[1]

    # use GDK to process XPM files
    gdk_exts = [ 'xpm', 'ico' ]
    if ext in gdk_exts:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon)
        if pixbuf.get_width() < 32 and pixbuf.get_height() < 32:
            raise StandardError('Icon too small to process')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon, 64, 64)
        pixbuf.savev(filename, "png", [], [])
        return

    # use PIL to resize PNG files
    pil_exts = [ 'png', 'gif' ]
    if ext in pil_exts:
        im = Image.open(icon)
        width, height = im.size
        if width < 32 and height < 32:
            raise StandardError('Icon too small to process (' + str(width) + 'px)')
        im = im.resize((64, 64), Image.ANTIALIAS)
        im.save(filename, 'png')
        return

    # use RSVG to write PNG file
    rsvg_exts = [ 'svg' ]
    if ext in rsvg_exts:
        img = cairo.ImageSurface(cairo.FORMAT_ARGB32, 64, 64)
        ctx = cairo.Context(img)
        handler = Rsvg.Handle.new_from_file(icon)
        ctx.scale(float(64) / handler.props.width, float(64) / handler.props.height)
        handler.render_cairo(ctx)
        img.write_to_png(filename)
        return
    return

def write_appstream_icon(icon, filename):

    # we can handle these sorts of files
    supported_ext = [ '.png', '.svg', '.xpm' ]

    # remove any extension we recognise
    if not icon.startswith('/'):
        icon_split = icon.rsplit('.', 1)
        if len(icon_split) == 2:
            if '.' + icon_split[1] in supported_ext:
                icon = icon_split[0]

    # fully qualified path
    icon_fullpath = './tmp/' + icon
    if os.path.exists(icon_fullpath):
        resize_icon(icon_fullpath, filename)
        return

    # hicolor apps
    icon_sizes = [ '64x64', '128x128', '96x96', '256x256', 'scalable', '48x48', '32x32', '24x24', '16x16' ]
    for s in icon_sizes:
        for ext in supported_ext:
            icon_fullpath = './tmp/usr/share/icons/hicolor/' + s + '/apps/' + icon + ext
            if os.path.isfile(icon_fullpath):
                resize_icon(icon_fullpath, filename)
                return

    # pixmap
    for location in [ 'pixmaps', 'icons' ]:
        for ext in supported_ext:
            icon_fullpath = './tmp/usr/share/' + location + '/' + icon + ext
            if os.path.isfile(icon_fullpath):
                resize_icon(icon_fullpath, filename)
                return

    return

def _to_utf8(txt, errors='replace'):
    if isinstance(txt, str):
        return txt
    if isinstance(txt, unicode):
        return txt.encode('utf-8', errors=errors)
    return str(txt)

class AppstreamBuild:

    def __init__(self):
        #to do something
        self.cat_blacklist = ['GTK', 'Qt', 'KDE', 'GNOME']

        # get the list of stock icons
        f = open('./data/stock-icon-names.txt', 'r')
        self.stock_icons = f.read().rstrip().split('\n')
        f.close()

        # get blacklisted applications
        f = open('./data/blacklist-id.txt', 'r')
        self.blacklisted_ids = f.read().rstrip().split('\n')
        f.close()

        # get blacklisted applications
        f = open('./data/blacklist-packages.txt', 'r')
        self.blacklisted_packages = f.read().rstrip().split('\n')
        f.close()

        # get blacklisted categories
        f = open('./data/blacklist-category.txt', 'r')
        self.blacklisted_categories = f.read().rstrip().split('\n')
        f.close()

        # get extra categories to add for apps
        self.categories_add = {}
        f = open('./data/category-add.txt', 'r')
        for line in f.read().rstrip().split('\n'):
            entry = line.split('\t', 1)
            self.categories_add[entry[0]] = entry[1].split(',')
        f.close()

        # get extra packages needed for some applications
        f = open('./data/common-packages.txt', 'r')
        entries = common_packages = f.read().rstrip().split('\n')
        self.common_packages = []
        for e in entries:
            self.common_packages.append(e.split('\t', 2))
        f.close()

    def decompress(self, pkg):
        if os.path.exists('./extract-package'):
            cmd = "'./extract-package' %s %s" % (pkg.filename, 'tmp')
            p = subprocess.Popen(cmd, cwd='.', shell=True, stdout=subprocess.PIPE)
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

    def build(self, filename):

        # check the package has .desktop files
        print 'SOURCE\t', filename
        pkg = fedoraAppstreamPkg.AppstreamPkg(filename)
        if not pkg.contains_desktop_file:
            print 'IGNORE\t', filename, '\t', "no desktop files"
            return

        for b in self.blacklisted_packages:
            if fnmatch.fnmatch(pkg.name, b):
                print 'IGNORE\t', filename, '\t', "package is blacklisted:", pkg.name
                return

        # set up state
        if not os.path.exists('./appstream'):
            os.makedirs('./appstream')
        if not os.path.exists('./icons'):
            os.makedirs('./icons')
        # remove tmp
        if os.path.exists('./tmp'):
            shutil.rmtree('./tmp')
        os.makedirs('./tmp')

        # decompress main file and search for desktop files
        self.decompress(pkg)
        files = []
        files.extend(glob.glob("./tmp/usr/share/applications/*.desktop"))
        files.extend(glob.glob("./tmp/usr/share/applications/kde4/*.desktop"))
        files.sort()

        # we only need to install additional files if we're not running on
        # the builders
        decompress_files = [ filename ]
        for c in self.common_packages:
            if fnmatch.fnmatch(pkg.name, c[0]):
                extra_files = glob.glob("./packages/%s*.rpm" % c[1])
                for f in extra_files:
                    extra_pkg = fedoraAppstreamPkg.AppstreamPkg(f)
                    print "INFO\tAdding extra package %s for %s" % (extra_pkg.name, pkg.name)
                    self.decompress(extra_pkg)

        # open the AppStream file for writing
        has_header = False
        xml_output_file = './appstream/' + pkg.name + '.xml'
        xml = open(xml_output_file, 'w')

        # check for duplicate apps in the package
        application_ids = []

        # process each desktop file in the original package
        for f in files:
            config = GLib.KeyFile()
            config.load_from_file(f, GLib.KeyFileFlags.KEEP_TRANSLATIONS)

            # optional
            names = {}
            categories = None
            descriptions = {}
            comments = {}
            mimetypes = None
            homepage_url = pkg.homepage_url
            icon = None
            keywords = None
            icon_fullpath = None
            skip = False
            DG = GLib.KEY_FILE_DESKTOP_GROUP
            keys, _ = config.get_keys(DG)
            for k in keys:
                if k == GLib.KEY_FILE_DESKTOP_KEY_NO_DISPLAY and config.get_boolean(DG, k):
                    print 'IGNORE\t', f, '\t', "not included in the menu"
                    skip = True
                    break
                elif k == GLib.KEY_FILE_DESKTOP_KEY_TYPE and \
                     config.get_string(DG, k) != GLib.KEY_FILE_DESKTOP_TYPE_APPLICATION:
                    print 'IGNORE\t', f, '\t', "not an application"
                    skip = True
                    break
                elif k.startswith(GLib.KEY_FILE_DESKTOP_KEY_NAME):
                    m = re.match(GLib.KEY_FILE_DESKTOP_KEY_NAME + '\[([^\]]+)\]', k)
                    if m:
                        names[m.group(1)] = config.get_string(DG, k)
                    else:
                        names['C'] = config.get_string(DG, k)
                elif k.startswith(GLib.KEY_FILE_DESKTOP_KEY_COMMENT):
                    m = re.match(GLib.KEY_FILE_DESKTOP_KEY_COMMENT + '\[([^\]]+)\]', k)
                    if m:
                        comments[m.group(1)] = config.get_string(DG, k)
                    else:
                        comments['C'] = config.get_string(DG, k)
                elif k == GLib.KEY_FILE_DESKTOP_KEY_ICON:
                    icon = config.get_string(DG, k)
                elif k == GLib.KEY_FILE_DESKTOP_KEY_CATEGORIES:
                    categories = config.get_string_list(DG, k)
                elif k == 'Keywords':
                    keywords = config.get_string_list(DG, k)
                elif k == 'MimeType':
                    mimetypes = config.get_string_list(DG, k)

            if skip:
                continue

            # Do not include apps without a Name
            if not 'C' in names:
                print 'IGNORE\t', f, '\t', "no Name"
                continue

            # Do not include apps without a Comment
            if not 'C' in comments:
                print 'IGNORE\t', f, '\t', "no Comment"
                continue

            if not icon:
                print 'IGNORE\t', f, '\t', "Icon unspecified"
                continue

            # We blacklist some apps by categories
            blacklisted = False
            if categories:
                for c in categories:
                    for b in self.blacklisted_categories:
                        if fnmatch.fnmatch(c, b):
                            print 'IGNORE\t', f, '\tcategory is blacklisted:', c
                            blacklisted = True
                            break
            if blacklisted:
                continue;

            basename = f.split("/")[-1]
            app_id = basename.replace('.desktop', '')

            # check icon exists
            if icon not in self.stock_icons:
                icon_fullpath = './icons/' + app_id + '.png'
                try:
                    write_appstream_icon(icon, icon_fullpath)
                except Exception as e:
                    print 'IGNORE\t', f, '\t', "icon is corrupt:", icon, str(e)
                    continue
                if not os.path.exists(icon_fullpath):
                    print 'IGNORE\t', f, '\t', "icon does not exist:", icon
                    continue

            print 'PROCESS\t', f

            # packages that ship .desktop files in /usr/share/applications
            # *and* /usr/share/applications/kde4 do not need multiple entries
            if app_id in application_ids:
                print 'IGNORE\t', f, '\t', app_id, 'duplicate ID in package'
                continue
            application_ids.append(app_id)

            # do we have to add any categories
            if categories:
                if self.categories_add.has_key(app_id):
                    cats_to_add = self.categories_add[app_id]
                    if cats_to_add:
                        # check it's not been added upstream
                        for cat in cats_to_add:
                            if cat in categories:
                                print 'WARNING\t' + app_id + ' now includes category ' + cat
                            else:
                                print 'INFO\tFor ' + app_id + ' manually adding category', cat
                        categories.extend(cats_to_add)

            # application is blacklisted
            for b in self.blacklisted_ids:
                if fnmatch.fnmatch(app_id, b):
                    print 'IGNORE\t', f, '\t', "application is blacklisted:", app_id
                    blacklisted = True
                    break
            if blacklisted:
                continue;

            # do we have an AppData file?
            appdata_file = './tmp/usr/share/appdata/' + app_id + '.appdata.xml'
            appdata_extra_file = './appdata-extra/' + app_id + '.appdata.xml'
            if os.path.exists(appdata_file) and os.path.exists(appdata_extra_file):
                print 'DELETE\t', appdata_extra_file, 'as upstream AppData file exists'
                os.remove(appdata_extra_file)

            # just use the extra file in places of the missing upstream one
            if os.path.exists(appdata_extra_file):
                appdata_file = appdata_extra_file

            # need to extract details
            if os.path.exists(appdata_file):
                data = fedoraAppstreamData.AppstreamData()
                data.extract(appdata_file)

                # check the id matches
                if data.get_id() != app_id:
                    raise StandardError('The AppData id does not match: ' + app_id)

                # check the licence is okay
                if data.get_licence() != 'CC0':
                    raise StandardError('The AppData licence is not okay: ' + app_id)

                # get optional bits
                tmp = data.get_url()
                if tmp:
                    homepage_url = tmp
                descriptions = data.get_descriptions()

            # write header
            if not has_header:
                print 'WRITING\t', xml_output_file
                xml.write("<?xml version=\"1.0\"?>\n")
                xml.write("<applications version=\"0.1\">\n")
                has_header = True

            # write content
            xml.write("  <application>\n")
            xml.write("    <id type=\"desktop\">%s</id>\n" % basename)
            xml.write("    <pkgname>%s</pkgname>\n" % pkg.name)
            xml.write("    <name>%s</name>\n" % sanitise_xml(names['C']))
            for lang in names:
                if lang != 'C':
                    xml.write("    <name xml:lang=\"%s\">%s</name>\n" % (sanitise_xml(lang), sanitise_xml(names[lang])))
            xml.write("    <summary>%s</summary>\n" % sanitise_xml(comments['C']))
            for lang in comments:
                if lang != 'C':
                    xml.write("    <summary xml:lang=\"%s\">%s</summary>\n" % (sanitise_xml(lang), sanitise_xml(comments[lang])))
            if icon_fullpath:
                xml.write("    <icon type=\"cached\">%s</icon>\n" % app_id)
            else:
                xml.write("    <icon type=\"stock\">%s</icon>\n" % icon)
            if categories:
                xml.write("    <appcategories>\n")
                # check for a common problem
                if 'AudioVideo' in categories:
                    if not 'Audio' in categories and not 'Video' in categories:
                        print 'WARNING\t', f, '\tHas AudioVideo but not Audio or Video'
                        categories.extend(['Audio', 'Video'])
                for cat in categories:
                    if cat in self.cat_blacklist:
                        continue
                    if cat.startswith('X-'):
                        continue
                    xml.write("      <appcategory>%s</appcategory>\n" % cat)
                xml.write("    </appcategories>\n")
            if keywords:
                xml.write("    <keywords>\n")
                for keyword in keywords:
                    xml.write("      <keyword>%s</keyword>\n" % sanitise_xml(keyword))
                xml.write("    </keywords>\n")
            if mimetypes:
                xml.write("    <mimetypes>\n")
                for mimetype in mimetypes:
                    xml.write("      <mimetype>%s</mimetype>\n" % sanitise_xml(mimetype))
                xml.write("    </mimetypes>\n")
            if homepage_url:
                xml.write("    <url type=\"homepage\">%s</url>\n" % sanitise_xml(homepage_url))
            if 'C' in descriptions:
                xml.write("    <description>%s</description>\n" % sanitise_xml(descriptions['C']))
                for lang in descriptions:
                    if lang != 'C':
                        xml.write("    <description xml:lang=\"%s\">%s</description>\n" % (sanitise_xml(lang), sanitise_xml(descriptions[lang])))
            xml.write("  </application>\n")

        # create AppStream XML
        xml.write("</applications>\n")
        xml.close()
        if not has_header:
            os.remove(xml_output_file)

        # create AppStream icon tar
        if has_header:
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
    job = AppstreamBuild()
    for fn in sys.argv[1:]:
        job.build(fn)
    sys.exit(0)

if __name__ == "__main__":
    main()
