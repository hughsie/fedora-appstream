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

def main():

    csvfile = open('./fonts.csv', 'r')
    data = csv.reader(csvfile)

    old_name = None
    old_summary = None

    for row in data:

        if row[0].startswith('AppStream ID'):
            continue

        font_id = row[0]
        parent = row[1]
        classifier = row[2]
        name = row[3]
        summary = row[4]

        # save
        if name == '^':
            if not old_name:
                print("WARNING: No old name for %s" % font_id)
                continue
            name = old_name
        elif len(name) > 0:
            old_name = name
        elif len(name) == 0:
            old_name = None
        if summary == '^':
            if not old_summary:
                print("WARNING: No old summary for %s" % font_id)
                continue
            summary = old_summary
        elif len(summary) > 0:
            old_summary = summary
        elif len(summary) == 0:
            old_summary = None

        filename = '../appdata-extra/font/' + font_id.rsplit('.', 1)[0] + '.appdata.xml'
        txt = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        txt += "<application>\n"
        txt += "  <id type=\"font\">%s</id>\n" % font_id
        txt += "  <licence>CC0</licence>\n"
        if len(name) > 0:
            txt += "  <name>%s</name>\n" % name
        if len(summary) > 0:
            txt += "  <summary>%s</summary>\n" % summary
        if len(classifier) > 0 or len(parent) > 0:
            txt += "  <metadata>\n"
            if len(classifier) > 0:
                txt += "    <value key=\"FontSubFamily\">%s</value>\n" % classifier
            if len(parent) > 0:
                txt += "    <value key=\"FontParent\">%s</value>\n" % parent
            txt += "  </metadata>\n"
        txt += "</application>\n"
        f = open(filename, 'w')
        f.write(txt)
        f.close()

    csvfile.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
