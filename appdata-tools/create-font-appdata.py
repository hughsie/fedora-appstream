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

# Copyright (C) 2013
#    Richard Hughes <richard@hughsie.com>
#

import csv
import sys

class FontCollection:

    def __init__(self):
        self.fonts = [] # (id, classifier)
        self.parent_id = None
        self.name = None
        self.summary = None
        self.description = None

    def add_font(self, font_id, classifier):
        self.fonts.append((font_id, classifier))

def main():

    csvfile = open('./fonts.csv', 'r')
    data = csv.reader(csvfile)

    fonts = {}

    for row in data:

        if row[1].startswith('All the content'):
            continue
        if row[1].startswith('AppStream ID'):
            continue

        font = FontCollection()
        font_id = row[1]
        parent_id = row[3]
        classifier = row[4]
        name = row[5]
        summary = row[6]
        description = row[7]

        if name == '-':
            continue

        if len(name) == 0:
            print "WARNING", font_id, "missing name using", row[1]
            name = row[1]
        if len(summary) == 0:
            print "WARNING", font_id, "missing summary"
        if len(classifier) == 0 or classifier == '-':
            classifier = 'Regular'
        if len(parent_id) == 0 or parent_id == '-':
            parent_id = font_id

        if parent_id in fonts:
            font = fonts[parent_id]
        else:
            # add to collection
            font = FontCollection()
            font.parent_id = parent_id
            fonts[parent_id] = font

        font.add_font(font_id, classifier)
        if name != "^":
            if font.name:
                print "WARNING: already set", font.name, "overwriting with", name
            font.name = name
        if summary != "^":
            if font.summary:
                print "WARNING: already set", font.summary, "overwriting with", summary
            font.summary = summary
            #font.description = description

    for key in fonts:
        fc = fonts[key]

        # create metadata appdata files
        for font_id, classifier in fc.fonts:

            filename = '../appdata-extra/font/' + font_id.rsplit('.', 2)[0] + '.appdata.xml'
            txt = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            txt += "<application>\n"
            txt += "  <id type=\"font\">%s</id>\n" % font_id
            txt += "  <licence>CC0</licence>\n"
            txt += "  <name>%s</name>\n" % fc.name
            txt += "  <summary>%s</summary>\n" % fc.summary
            txt += "  <metadata>\n"
            txt += "    <value key=\"FontClassifier\">%s</value>\n" % classifier
            txt += "    <value key=\"FontParent\">%s</value>\n" % fc.parent_id
            txt += "  </metadata>\n"
            txt += "</application>\n"
            f = open(filename, 'w')
            f.write(txt)
            f.close()

    csvfile.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
