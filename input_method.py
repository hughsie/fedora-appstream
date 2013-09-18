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

    def parse_file(self, f):

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

        dom = xml.dom.minidom.parse(f)
        desc = dom.getElementsByTagName("description")
        if desc:
            self.names['C'] = getText(desc[0].childNodes)
            self.comments['C'] = getText(desc[0].childNodes)
        desc = dom.getElementsByTagName("homepage")
        if desc:
            self.homepage_url = getText(desc[0].childNodes)

        return True

def main():
    pkg = Package(sys.argv[1])
    app = InputMethod(pkg, None)
    app.app_id = 'test'
    f = open('/tmp/test.xml', 'w')
    app.write(f)
    f.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
