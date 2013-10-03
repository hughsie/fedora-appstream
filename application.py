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
        self.app_id = None
        self.app_id_full = None
        self.names = {}
        self.categories = None
        self.descriptions = {}
        self.comments = {}
        self.mimetypes = None
        self.homepage_url = pkg.homepage_url
        self.icon = None
        self.keywords = None
        self.pkgname = pkg.name
        self.cached_icon = False
        self.cfg = cfg
        self.screenshots = []
        self.type_id = None
        self.project_group = None
        self.requires_appdata = False

    def add_screenshot_url(self, url):

        # download image and add it
        cache_filename = './screenshot-cache/' + self.app_id
        cache_filename += '-' + os.path.basename(url)
        if not os.path.exists(cache_filename):
            urllib.urlretrieve (url, cache_filename)
        img = Image.open(cache_filename)
        self.screenshots.append(Screenshot(self.app_id, img))

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
                    print 'WARNING\t', self.app_id, ' has AudioVideo but not Audio or Video'
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
        if self.keywords:
            f.write("    <keywords>\n")
            for keyword in self.keywords:
                f.write("      <keyword>%s</keyword>\n" % quote(keyword))
            f.write("    </keywords>\n")
        if self.mimetypes:
            f.write("    <mimetypes>\n")
            for mimetype in self.mimetypes:
                f.write("      <mimetype>%s</mimetype>\n" % quote(mimetype))
            f.write("    </mimetypes>\n")
        if self.homepage_url:
            f.write("    <url type=\"homepage\">%s</url>\n" % quote(self.homepage_url))
        if self.project_group:
            f.write("    <project_group>%s</project_group>\n" % quote(self.project_group))
        if self.descriptions and 'C' in self.descriptions:
            f.write("    <description>%s</description>\n" % quote(self.descriptions['C']))
            for lang in self.descriptions:
                if lang != 'C':
                    f.write("    <description xml:lang=\"%s\">%s</description>\n" %
                            (quote(lang), quote(self.descriptions[lang])))

        # any screenshots
        if len(self.screenshots) > 0:
            f.write("    <screenshots>\n")
            mirror_url = self.cfg.get_screenshot_mirror_url()
            for s in self.screenshots:
                f.write("      <screenshot>\n")

                # write the full size source image
                url = mirror_url + 'source/' + s.basename
                f.write("        <image type=\"source\" width=\"%s\" "
                        "height=\"%s\">%s</image>\n" %
                        (s.width, s.height, url))

                # write all the thumbnail sizes too
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

        f.write("  </application>\n")

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
