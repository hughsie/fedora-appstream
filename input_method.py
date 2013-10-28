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
import sqlite3

# internal
from application import Application
from package import Package

import xml.dom.minidom

def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

class InputMethod(Application):

    def __init__(self, pkg, cfg):
        Application.__init__(self, pkg, cfg)
        self.type_id = 'inputmethod'
        self.categories = [ 'Addons', 'InputSources' ]
        self.icon = 'system-run-symbolic'
        self.cached_icon = False
        self.requires_appdata = True

class InputMethodComponent(InputMethod):

    def __init__(self, pkg, cfg):
        InputMethod.__init__(self, pkg, cfg)

    def parse_file(self, f):

        # gahh, some components start with a comment (invalid XML) and some
        # don't even have '<?xml'
        file_xml = open(f, 'r')
        lines = file_xml.read().split('\n')
        found_header = False
        valid_xml = ''
        for line in lines:
            if line.startswith('<?xml') or line.startswith('<component>'):
                found_header = True
            if found_header:
                valid_xml = valid_xml + line + '\n'
        file_xml.close()

        # read the component header which all input methods have
        #
        #<component>
        #	<name>org.freedesktop.IBus.Anthy</name>
        #	<description>Anthy Component</description>
        #	<exec>/usr/libexec/ibus-engine-anthy --ibus</exec>
        #	<version>1.5.3</version>
        #	<author>Peng Huang &lt;shawn.p.huang@gmail.com&gt;</author>
        #	<license>GPL</license>
        #	<homepage>http://code.google.com/p/ibus</homepage>
        #	<textdomain>ibus-anthy</textdomain>
        #	<!-- for engines -->
        #	<observed-paths>
        #		<path>~/.config/ibus-anthy/engines.xml</path>
        #		<path>/usr/share/ibus-anthy/engine/default.xml</path>
        #	</observed-paths>
        #	<engines exec="/usr/libexec/ibus-engine-anthy --xml" />
        #</component>
        dom = xml.dom.minidom.parseString(valid_xml)
        desc = dom.getElementsByTagName("description")
        if desc:
            self.names['C'] = getText(desc[0].childNodes)
            self.comments['C'] = getText(desc[0].childNodes)
        desc = dom.getElementsByTagName("homepage")
        if desc:
            self.urls['homepage'] = getText(desc[0].childNodes)

        # do we have a engine section we can use?
        #
        #<engines>
        #  <engine>
        #    <name>cangjie</name>
        #    <longname>Cangjie</longname>
        #    <description>Cangjie Input Method</description>
        #    <language>zh_HK</language>
        #    <layout>us</layout>
        #    <symbol>倉頡</symbol>
        #    <license>GPLv3+</license>
        #    <author>The IBus Cangjie authors</author>
        #    <setup>/usr/bin/ibus-setup-cangjie cangjie</setup>
        #    <rank>0</rank>
        #  </engine>
        #</engines>
        engines = dom.getElementsByTagName("engine")
        if len(engines) == 1:
            desc = engines[0].getElementsByTagName("longname")
            if desc:
                self.names['C'] = getText(desc[0].childNodes)
            desc = engines[0].getElementsByTagName("description")
            if desc:
                self.comments['C'] = getText(desc[0].childNodes)

        return True

class InputMethodTable(InputMethod):

    def __init__(self, pkg, cfg):
        InputMethod.__init__(self, pkg, cfg)

    def parse_file(self, f):
        # get details about the table from the database
        name = None
        description = None
        conn = sqlite3.connect(f)
        c = conn.cursor()
        for row in c.execute('SELECT * FROM ime'):
            if row[0] == 'name':
                name = row[1]
            if row[0] == 'description':
                description = row[1]
        conn.close()

        # not specified
        if not name or not description:
            return False

        self.names['C'] = name
        self.comments['C'] = description

        return True

def main():
    pkg = Package(sys.argv[1])
    app = InputMethodComponent(pkg, None)
    app.app_id = 'test'
    f = open('/tmp/test.xml', 'w')
    app.write(f)
    f.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
