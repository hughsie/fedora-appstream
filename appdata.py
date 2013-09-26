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
import re
import xml.etree.ElementTree as ET

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'

def _to_utf8(txt, errors='replace'):
    if isinstance(txt, str):
        return txt
    if isinstance(txt, unicode):
        return txt.encode('utf-8', errors=errors)
    return str(txt)

class AppData:

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
        if ss is not None:
            # just return the fist one found
            s = ss.find('screenshot')
            if s is not None:
                return s.text

    def _append_for_lang(self, descriptions, lang, content):
        if not lang:
            lang = 'C'

        if lang in descriptions:
            descriptions[lang] = descriptions[lang] + content
        else:
            descriptions[lang] = content

    def get_descriptions(self):
        descriptions = {}
        ss = self.root.find("description")
        if ss is None:
            return
        for item in ss:
            if item.tag == 'p':
                para = _to_utf8(item.text)
                para = para.lstrip()
                para = para.replace('\n', ' ')
                para = re.sub('\ +', ' ', para)
                self._append_for_lang(descriptions, item.get(XML_LANG), para + '\n\n')
            elif item.tag == 'ul':
                for li in item:
                    txt = _to_utf8(li.text)
                    txt = txt.replace('\n', ' ')
                    txt = re.sub('\ +', ' ', txt)
                    self._append_for_lang(descriptions, item.get(XML_LANG), ' • ' + txt + '\n')
            elif item.tag == 'ol':
                cnt = 1
                for li in item:
                    txt = _to_utf8(li.text)
                    txt = txt.replace('\n', ' ')
                    txt = re.sub('\ +', ' ', txt)
                    self._append_for_lang(descriptions, item.get(XML_LANG), ' ' + str(cnt) + '. ' + txt + '\n')
                    cnt = cnt + 1
            else:
                raise StandardError('Do not know how to parse' + item.tag + ' for ' + self.filename)

        for lang in descriptions:
            descriptions[lang] = descriptions[lang].replace('  ', ' ').rstrip()
        return descriptions

    def get_url(self):
        ss = self.root.find("url")
        if ss is not None:
            return ss.text

    def get_project_group(self):
        ss = self.root.find("project_group")
        if ss is not None:
            return ss.text

    def _get_localized_tags(self, name):
        values = {}
        for item in self.root:
            if item.tag == name:
                lang = item.get(XML_LANG)
                if not lang:
                    lang = 'C'
                values[lang] = item.text
        if len(values) == 0:
            return None
        return values

    def get_names(self):
        return self._get_localized_tags('name')

    def get_summaries(self):
        return self._get_localized_tags('summary')

def main():
    data = AppData()
    data.extract(sys.argv[1])
    print 'id:\t\t', data.get_id()
    print 'licence:\t', data.get_licence()
    print 'url:\t\t', data.get_url()
    print 'project_group:\t\t', data.get_project_group()
    print 'screenshot:\t\t', data.get_screenshot()
    print 'description:\t', data.get_descriptions()
    print 'END'
    sys.exit(0)

if __name__ == "__main__":
    main()
