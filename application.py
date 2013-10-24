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
import urllib

from PIL import Image

# internal
from logger import LoggerItem
from package import Package
from screenshot import Screenshot

def _to_utf8(txt, errors='replace'):
    if isinstance(txt, str):
        return txt
    if isinstance(txt, unicode):
        return txt.encode('utf-8', errors=errors)
    return str(txt)

# NOTE; we could use escape() from xml.sax.saxutils import escape but that seems
# like a big dep for such trivial functionality
def quote(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\"", "&#34;")
    text = text.replace("\'", "&#39;")
    return _to_utf8(text)

class Application:

    def __init__(self, pkg, cfg):
        self.log = LoggerItem()
        self.app_id = None
        self.app_id_full = None
        self.names = {}
        self.categories = None
        self.descriptions = {}
        self.comments = {}
        self.mimetypes = None
        self.urls = {}
        self.metadata = {}
        if pkg.homepage_url:
            self.urls['homepage'] = pkg.homepage_url
        self.licence = pkg.licence
        self.icon = None
        self.keywords = []
        self.pkgname = pkg.name
        self.cached_icon = False
        self.cfg = cfg
        self.screenshots = []
        self.compulsory_for_desktop = []
        self.type_id = None
        self.project_group = None
        self.requires_appdata = False
        self.thumbnail_screenshots = True
        self.status_html = None

    def add_screenshot_filename(self, filename, caption=None):

        # just add it
        try:
            img = Image.open(filename)
        except IOError as e:
            self.log.write(LoggerItem.WARNING,
                           "Failed to open %s: %s" % (filename, str(e)))
        else:
            self.screenshots.append(Screenshot(self.app_id, img, caption))

    def add_screenshot_url(self, url, caption=None):

        # download image and add it
        cache_filename = './screenshot-cache/' + self.app_id
        cache_filename += '-' + os.path.basename(url)
        if not os.path.exists(cache_filename):
            urllib.urlretrieve (url, cache_filename)
        self.add_screenshot_filename(cache_filename, caption)

    def set_id(self, app_id):

        # we use the full AppID when writing to AppStream XML
        self.app_id_full = app_id
        self.app_id_full = self.app_id_full.replace('&', '-')
        self.app_id_full = self.app_id_full.replace('<', '-')
        self.app_id_full = self.app_id_full.replace('>', '-')

        # we use the short version (without the extension) internally when
        # refering to things like icon names
        self.app_id = self.app_id_full
        split = self.app_id_full.rsplit('.', 1)
        if len(split) > 1:
            self.app_id = split[0]

        # update the log name
        self.log.update_key(self.app_id_full)

        # is this app compulsory for any specific desktop?
        desktops = self.cfg.get_compulsory_for_desktop_for_id(self.app_id)
        if desktops:
            self.compulsory_for_desktop.extend(desktops)

    def write(self, f):
        f.write("  <application>\n")
        f.write("    <id type=\"%s\">%s</id>\n" % (self.type_id, self.app_id_full))
        f.write("    <pkgname>%s</pkgname>\n" % self.pkgname)
        f.write("    <name>%s</name>\n" % quote(self.names['C']))
        for lang in self.names:
            if lang != 'C':
                f.write("    <name xml:lang=\"%s\">%s</name>\n" %
                        (quote(lang), quote(self.names[lang])))
        f.write("    <summary>%s</summary>\n" % quote(self.comments['C']))
        for lang in self.comments:
            if lang != 'C':
                f.write("    <summary xml:lang=\"%s\">%s</summary>\n" %
                        (quote(lang), quote(self.comments[lang])))
        if self.icon:
            if self.cached_icon:
                f.write("    <icon type=\"cached\">%s.png</icon>\n" % self.app_id)
            else:
                f.write("    <icon type=\"stock\">%s</icon>\n" % self.icon)
        if self.categories:
            f.write("    <appcategories>\n")
            # check for a common problem
            if 'AudioVideo' in self.categories:
                if not 'Audio' in self.categories and not 'Video' in self.categories:
                    self.log.write(LoggerItem.WARNING,
                                   "has AudioVideo but not Audio or Video")
                    self.categories.extend(['Audio', 'Video'])
            for cat in self.categories:
                if cat in self.cfg.get_category_ignore_list():
                    continue
                if cat.startswith('X-'):
                    continue
                # simple substitution
                if cat == 'Feed':
                    cat = 'News'
                f.write("      <appcategory>%s</appcategory>\n" % cat)
            f.write("    </appcategories>\n")
        if len(self.keywords) > 0:
            f.write("    <keywords>\n")
            for keyword in self.keywords:
                f.write("      <keyword>%s</keyword>\n" % quote(keyword))
            f.write("    </keywords>\n")
        if self.mimetypes:
            f.write("    <mimetypes>\n")
            for mimetype in self.mimetypes:
                f.write("      <mimetype>%s</mimetype>\n" % quote(mimetype))
            f.write("    </mimetypes>\n")
        if self.licence:
            f.write("    <licence>%s</licence>\n" % quote(self.licence))
        for key in self.urls:
            f.write("    <url type=\"%s\">%s</url>\n" % (key, quote(self.urls[key])))
        if self.project_group:
            f.write("    <project_group>%s</project_group>\n" % quote(self.project_group))
        if self.descriptions and 'C' in self.descriptions:
            f.write("    <description>%s</description>\n" % quote(self.descriptions['C']))
            for lang in self.descriptions:
                if lang != 'C':
                    f.write("    <description xml:lang=\"%s\">%s</description>\n" %
                            (quote(lang), quote(self.descriptions[lang])))

        # compulsory for any specific desktop?
        if len(self.compulsory_for_desktop) > 0:
            for c in self.compulsory_for_desktop:
                f.write("    <compulsory_for_desktop>%s</compulsory_for_desktop>\n"% c)

        # any screenshots
        mirror_url = self.cfg.get_screenshot_mirror_url()
        if mirror_url and len(self.screenshots) > 0:
            f.write("    <screenshots>\n")
            for s in self.screenshots:
                if s == self.screenshots[0]:
                    f.write("      <screenshot type=\"default\">\n")
                else:
                    f.write("      <screenshot type=\"normal\">\n")

                # write caption
                if s.caption:
                    f.write("        <caption>%s</caption>\n" % s.caption)

                # write the full size source image
                url = mirror_url + 'source/' + s.basename
                f.write("        <image type=\"source\" width=\"%s\" "
                        "height=\"%s\">%s</image>\n" %
                        (s.width, s.height, url))

                # write all the thumbnail sizes too
                if self.thumbnail_screenshots:
                    for size in self.cfg.get_screenshot_thumbnail_sizes():
                        size_str = str(size[0]) + 'x' + str(size[1])
                        url = mirror_url + size_str + '/' + s.basename
                        s.dump_to_file('./screenshots/' + size_str, size)
                        f.write("        <image type=\"thumbnail\" width=\"%s\" "
                                "height=\"%s\">%s</image>\n" %
                                (size[0], size[1], url))
                f.write("      </screenshot>\n")
                s.dump_to_file('./screenshots/source')
            f.write("    </screenshots>\n")

        # any metadata
        for m in self.metadata:
            f.write("    <X-%s>%s</X-%s>\n" % (m, self.metadata[m], m))

        f.write("  </application>\n")

        # write to the status file
        if self.status_html and self.type_id != 'font':
            self.status_html.write("<h2>%s</h2>\n" % self.app_id)
            if mirror_url and len(self.screenshots) > 0:
                for s in self.screenshots:
                    url = mirror_url + '624x351/' + s.basename
                    thumb_url = mirror_url + '112x63/' + s.basename
                    self.status_html.write("<a href=\"%s\"><img src=\"%s\" alt=\"%s\"/></a>\n" %
                                           (url, thumb_url, s.caption))
            self.status_html.write("<table>\n")
            self.status_html.write("<tr><td>%s</td><td><code>%s</code></td></tr>\n" %
                                   ("Type", self.type_id))
            self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                   ("Name", self.names['C']))
            self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                   ("Comment", self.comments['C']))
            if self.descriptions and 'C' in self.descriptions:
                self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                       ("Description", self.descriptions['C']))
            self.status_html.write("<tr><td>%s</td><td><code>%s</code></td></tr>\n" %
                                   ("Package", self.pkgname))
            if self.categories:
                self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                       ("Categories", ', '.join(self.categories)))
            if len(self.keywords):
                self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                       ("Keywords", ', '.join(self.keywords)))
            if 'homepage' in self.urls:
                self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                       ("Homepage", self.urls['homepage']))
            if self.project_group:
                self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                       ("Project", self.project_group))
            if len(self.compulsory_for_desktop):
                self.status_html.write("<tr><td>%s</td><td>%s</td></tr>\n" %
                                       ("Compulsory", ', '.join(self.compulsory_for_desktop)))
            self.status_html.write("</table>\n")
            self.status_html.flush()

def main():
    pkg = Package(sys.argv[1])
    app = Application(pkg, None)
    app.app_id = 'test'
    app.names['C'] = 'test'
    app.comments['C'] = 'Test package'
    f = open('/tmp/test.xml', 'w')
    app.write(f)
    f.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
