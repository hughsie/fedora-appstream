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

#import os
import sys
import xml.etree.ElementTree as ET

class AppstreamData:

    def __init__(self):
        self.root = None

    def extract(self, filename):
        tree = ET.parse(filename)
        self.root = tree.getroot()
        self.filename = filename

    def get_id(self):
        tmp = self.root.find("id").text
        if tmp:
            tmp = tmp.replace('.desktop', '')
        return tmp
    def get_licence(self):
        return self.root.find("licence").text
    def get_screenshot(self):
        ss = self.root.find("screenshots")
        if ss:
            # just return the fist one found
            s = ss.find('screenshot')
            if s:
                return s.text
    def get_description(self):
        desc = ''
        for item in self.root.find("description"):
            if item.tag == 'p':
                para = item.text
                para = para.replace('\n', ' ')
                desc = desc.lstrip() + para.replace('  ', ' ') + '\n\n'
            elif item.tag == 'ul':
                for li in item:
                    desc = desc + ' • ' + li.text + '\n'
            elif item.tag == 'ol':
                cnt = 1
                for li in item:
                    desc = desc + ' ' + str(cnt) + '. ' + li.text + '\n'
                    cnt = cnt + 1
            else:
                raise StandardError('Do not know how to parse' + item.tag + ' for ' + self.filename)
        if len(desc) == 0:
            return None
        return desc.replace('  ', ' ').rstrip()
    def get_url(self):
        return self.root.find("url").text

def main():
    data = AppstreamData()
    data.extract(sys.argv[1])
    print 'id:\t\t', data.get_id()
    print 'licence:\t', data.get_licence()
    print 'url:\t\t', data.get_url()
    print 'screenshot:\t\t', data.get_screenshot()
    print 'description:\t', data.get_description()
    print 'END'
    sys.exit(0)

if __name__ == "__main__":
    main()
