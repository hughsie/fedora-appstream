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

import os
import sys
import re
import fnmatch
import cairo
import subprocess

from PIL import Image, ImageOps
from gi.repository import GdkPixbuf, GLib, Rsvg

# internal
from logger import LoggerItem
from application import Application
from package import Package

def get_string_unicode(config, group, key):
    tmp = config.get_string(group, key).decode('utf-8')
    tmp = tmp.strip()
    if len(tmp) == 0:
        return None
    return tmp

def get_string_list_unicode(config, group, key):
    tmp = config.get_string_list(group, key)
    values = []
    for t in tmp:
        values.append(t.decode('utf-8'))
    if len(values) == 0:
        return None
    return values

class AppdataException(Exception):
    pass

class DesktopFile(Application):

    def __init__(self, pkg, cfg):
        Application.__init__(self, pkg, cfg)
        self.type_id = u'desktop'

    def _repair_icon(self, filename):
        #try to run optipng -fix on the file
        self.log.write(LoggerItem.INFO,
                       "trying to repear icon using optipng")
        env = os.environ
        p = subprocess.Popen(['/usr/bin/optipng',
                              '-quiet', '-fix', filename],
                             cwd='.', env=env, stdout=subprocess.PIPE)
        p.wait()
        if p.returncode:
            for line in p.stdout:
                line = line.replace('\n', '').decode('utf-8')
                self.log.write(LoggerItem.WARNING,
                               "optipng could not repair: %s" % line)

    def resize_icon(self, icon, filename):

        # get ending
        ext = icon.rsplit('.', 1)[1]
        size = self.cfg.icon_size
        min_size = self.cfg.min_icon_size

        # use GDK to process XPM files
        gdk_exts = [ 'xpm', 'ico' ]
        if ext in gdk_exts:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon)
            if pixbuf.get_width() < min_size or pixbuf.get_height() < min_size:
                raise AppdataException('Icon too small to process')
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon, size, size)
            pixbuf.savev(filename, "png", [], [])
            return

        # use PIL to resize PNG files
        pil_exts = [ 'png', 'gif' ]
        if ext in pil_exts:
            try:
                im = Image.open(icon)
            except IOError, e:
                if ext == 'png':
                    try:
                        self._repair_icon(icon)
                        im = Image.open(icon)
                    except IOError, e:
                        raise AppdataException("Failed to repair icon: %s" % e)
                else:
                    raise AppdataException("Failed to open icon: %s" % e)
            width, height = im.size
            if width < min_size or height < min_size:
                raise AppdataException('Icon too small to process (' +
                                       str(width) + 'px)')

            # do not resize, just add a transparent border
            if width <= size and height <= size:
                bwidth = (size - width) / 2
                im = ImageOps.expand(im, border=bwidth)
                im.save(filename, 'png')
                return

            im = im.resize((size, size), Image.ANTIALIAS)
            im.save(filename, 'png')
            return

        # use RSVG to write PNG file
        rsvg_exts = [ 'svg' ]
        if ext in rsvg_exts:
            img = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
            ctx = cairo.Context(img)
            handler = Rsvg.Handle.new_from_file(icon)
            ctx.scale(float(64) / handler.props.width,
                      float(size) / handler.props.height)
            handler.render_cairo(ctx)
            img.write_to_png(filename.encode('utf-8'))
            return
        return

    def write_appstream_icon(self, icon, filename):

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
            self.resize_icon(icon_fullpath, filename)
            return

        # hicolor apps
        icon_sizes = self.cfg.get_preferred_icon_sizes()
        for s in icon_sizes:
            for ext in supported_ext:
                icon_fullpath = './tmp/usr/share/icons/hicolor/' + s + '/apps/' + icon + ext
                if os.path.isfile(icon_fullpath):
                    self.resize_icon(icon_fullpath, filename)
                    return

        # pixmap
        for location in [ 'pixmaps', 'icons' ]:
            for ext in supported_ext:
                icon_fullpath = './tmp/usr/share/' + location + '/' + icon + ext
                if os.path.isfile(icon_fullpath):
                    self.resize_icon(icon_fullpath, filename)
                    return

        return

    def parse_file(self, f):

        config = GLib.KeyFile()
        config.load_from_file(f, GLib.KeyFileFlags.KEEP_TRANSLATIONS)

        icon_fullpath = None
        is_application = False
        no_display = False
        DG = GLib.KEY_FILE_DESKTOP_GROUP
        keys, _ = config.get_keys(DG)
        for k in keys:
            if k == GLib.KEY_FILE_DESKTOP_KEY_NO_DISPLAY and config.get_boolean(DG, k):
                no_display = True
            elif k == GLib.KEY_FILE_DESKTOP_KEY_TYPE:
                if config.get_string(DG, k) != GLib.KEY_FILE_DESKTOP_TYPE_APPLICATION:
                    break
                is_application = True
            elif k.startswith(GLib.KEY_FILE_DESKTOP_KEY_NAME):
                m = re.match(GLib.KEY_FILE_DESKTOP_KEY_NAME + '\[([^\]]+)\]', k)
                tmp = get_string_unicode(config, DG, k)
                if not tmp:
                    continue
                if m:
                    self.names[m.group(1)] = tmp
                else:
                    self.names['C'] = tmp
            elif k.startswith(GLib.KEY_FILE_DESKTOP_KEY_COMMENT):
                m = re.match(GLib.KEY_FILE_DESKTOP_KEY_COMMENT + '\[([^\]]+)\]', k)
                tmp = get_string_unicode(config, DG, k)
                if not tmp:
                    continue
                if m:
                    self.comments[m.group(1)] = tmp
                else:
                    self.comments['C'] = tmp
            elif k == GLib.KEY_FILE_DESKTOP_KEY_ICON:
                value = get_string_unicode(config, DG, k)
                if value:
                    self.icon = value
            elif k == GLib.KEY_FILE_DESKTOP_KEY_CATEGORIES:
                self.categories = get_string_list_unicode(config, DG, k)
            elif k == 'Keywords':
                self.keywords = get_string_list_unicode(config, DG, k)
            elif k == 'MimeType':
                self.mimetypes = get_string_list_unicode(config, DG, k)
            elif k == 'X-GNOME-Bugzilla-Product':
                self.project_group = u'GNOME'
            elif k == 'X-MATE-Bugzilla-Product':
                self.project_group = u'MATE'
            elif k == 'X-KDE-StartupNotify':
                self.project_group = u'KDE'
            elif k == 'X-DocPath':
                tmp = get_string_unicode(config, DG, k)
                if tmp.startswith(u'http://userbase.kde.org/'):
                    self.project_group = u'KDE'
                self.project_group = u'KDE'
            elif k == GLib.KEY_FILE_DESKTOP_KEY_EXEC:
                tmp = config.get_string(DG, k)
                if tmp.startswith('xfce4-'):
                    self.project_group = u'XFCE'
            elif k == GLib.KEY_FILE_DESKTOP_KEY_ONLY_SHOW_IN:
                # if an app has only one entry, it's tied to that desktop
                tmp = get_string_list_unicode(config, DG, k)
                if len(tmp) == 1:
                    self.project_group = tmp[0]
        if not is_application:
            self.log.write(LoggerItem.INFO, "not an application")
            return False

        # if we're not showing in the menu, we'd need an AppData file
        if no_display:
            self.log.write(LoggerItem.INFO, "NoDisplay=True")
            self.requires_appdata = True

        # are we overriding the project_group value?
        project_group_override = self.cfg.get_project_group_for_id(self.app_id)
        if project_group_override:
            self.project_group = project_group_override

        # We blacklist some apps by categories
        blacklisted = False
        if self.categories:
            for c in self.categories:
                for b in self.cfg.get_category_blacklist():
                    if fnmatch.fnmatch(c, b):
                        self.log.write(LoggerItem.INFO, "category %s is blacklisted" % c)
                        blacklisted = True
                        break
        if blacklisted:
            return False

        # do we have to add any categories
        if self.categories:
            cats_to_add = self.cfg.get_category_extra_for_id(self.app_id)
            if cats_to_add:
                # check it's not been added upstream
                for cat in cats_to_add:
                    if cat in self.categories:
                        self.log.write(LoggerItem.WARNING, "self includes category %s" % cat)
                    else:
                        self.log.write(LoggerItem.INFO, "manually adding category %s" % cat)
                self.categories.extend(cats_to_add)

        # check icon exists
        if self.icon and self.icon not in self.cfg.get_stock_icons():
            icon_fullpath = u'./icons/' + self.app_id + u'.png'
            try:
                self.write_appstream_icon(self.icon, icon_fullpath)
            except AppdataException as e:
                self.log.write(LoggerItem.INFO, "failed to load icon %s: %s" % (icon_fullpath, str(e)))
                return False
            if not os.path.exists(icon_fullpath):
                self.log.write(LoggerItem.INFO, "icon %s does not exist" % icon_fullpath)
                return False
            self.cached_icon = True

        return True

def main():
    pkg = Package(sys.argv[1])
    app = DesktopFile(pkg, None)
    app.app_id = 'test'
    app.names['C'] = 'test'
    app.comments['C'] = 'Test package'
    f = open('/tmp/test.xml', 'w')
    app.write(f)
    f.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
