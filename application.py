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

import sys
from package import Package

# NOTE; we could use escape() from xml.sax.saxutils import escape but that seems
# like a big dep for such trivial functionality
def sanitise_xml(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

class Application:

    def __init__(self, pkg, cfg):
        self.app_id = None
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

    def write(self, f):
        f.write("  <application>\n")
        f.write("    <id type=\"desktop\">%s.desktop</id>\n" % self.app_id)
        f.write("    <pkgname>%s</pkgname>\n" % self.pkgname)
        f.write("    <name>%s</name>\n" % sanitise_xml(self.names['C']))
        for lang in self.names:
            if lang != 'C':
                f.write("    <name xml:lang=\"%s\">%s</name>\n" % (sanitise_xml(lang), sanitise_xml(self.names[lang])))
        f.write("    <summary>%s</summary>\n" % sanitise_xml(self.comments['C']))
        for lang in self.comments:
            if lang != 'C':
                f.write("    <summary xml:lang=\"%s\">%s</summary>\n" % (sanitise_xml(lang), sanitise_xml(self.comments[lang])))
        if self.icon:
            if self.cached_icon:
                f.write("    <icon type=\"cached\">%s</icon>\n" % self.app_id)
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
                f.write("      <keyword>%s</keyword>\n" % sanitise_xml(keyword))
            f.write("    </keywords>\n")
        if self.mimetypes:
            f.write("    <mimetypes>\n")
            for mimetype in self.mimetypes:
                f.write("      <mimetype>%s</mimetype>\n" % sanitise_xml(mimetype))
            f.write("    </mimetypes>\n")
        if self.homepage_url:
            f.write("    <url type=\"homepage\">%s</url>\n" % sanitise_xml(self.homepage_url))
        if 'C' in self.descriptions:
            f.write("    <description>%s</description>\n" % sanitise_xml(self.descriptions['C']))
            for lang in self.descriptions:
                if lang != 'C':
                    f.write("    <description xml:lang=\"%s\">%s</description>\n" % (sanitise_xml(lang), sanitise_xml(self.descriptions[lang])))
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
