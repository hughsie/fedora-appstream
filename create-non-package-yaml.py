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

import xml.etree.ElementTree as ET
import gzip
import sys
import os

# internal
from application import Application
from logger import LoggerItem
from config import Config
from screenshot import Screenshot

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'

def _to_utf8(txt, errors='replace'):
    if isinstance(txt, str):
        return txt
    if isinstance(txt, unicode):
        return txt.encode('utf-8', errors=errors)
    return str(txt)

def _to_yaml(app):
    doc = "- id: %s\n" % app.app_id
    doc += "  name: %s\n" % app.names['C']
    doc += "  summary: %s\n" % app.comments['C']
    return doc

def ensure_unicode(text):
    if isinstance(text, unicode):
        return text
    return text.decode('utf-8')

def main():
    log = LoggerItem()
    cfg = Config()

    # read in AppStream file into several Application objects
    f = gzip.open(sys.argv[1], 'rb')
    tree = ET.parse(f)
    apps = []
    for app in tree.getroot():
        a = Application(None, cfg)
        for elem in app:
            if elem.tag == 'id':
                a.set_id(elem.text)
                a.type_id = elem.get('type')
                log.update_key(a.app_id_full)
                log.write(LoggerItem.INFO, "parsing")
            elif elem.tag == 'pkgname':
                a.pkgnames.append(ensure_unicode(elem.text))
            elif elem.tag == 'name':
                if elem.get(XML_LANG):
                    continue
                a.names['C'] = ensure_unicode(elem.text)
            elif elem.tag == 'summary':
                if elem.get(XML_LANG):
                    continue
                a.comments['C'] = ensure_unicode(elem.text)
        apps.append(a)
    f.close()

    # build yaml
    status = open('./screenshots/applications-to-import.yaml', 'w')
    status.write('# automatically generated, do not edit\n')
    status.write('# see https://github.com/hughsie/fedora-appstream/blob/master/create-non-package-yaml.py\n')
    for app in apps:
        #if app.type_id == 'desktop':
        #    continue
        if len(app.pkgnames):
            continue
        try:
            status.write(_to_utf8(_to_yaml(app)))
        except AttributeError, e:
            log.write(LoggerItem.WARNING, "failed to write %s: %s" % (app, str(e)))
            continue
    status.close()

if __name__ == "__main__":
    main()
