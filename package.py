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

import os
import sys
import rpm

# internal
from logger import LoggerItem

import rpmUtils.miscutils

_ts = rpm.ts()
_ts.setVSFlags(0x7FFFFFFF)

class Package:

    def __init__(self, filename):
        self.filename = filename
        self.name = None
        self.homepage_url = None
        self._default_wildcards = []

        # open the rpm file
        fd = os.open(filename, os.O_RDONLY)
        hdr = _ts.hdrFromFdno(fd)
        if hdr.name:
            self.name = hdr.name.decode('utf-8')
        self.epoch = hdr.epoch
        self.version = hdr.version.decode('utf-8')
        self.release = hdr.release.decode('utf-8')
        self.arch = hdr.arch.decode('utf-8')
        self.summary = hdr.summary.decode('utf-8')
        if hdr.license:
            self.licence = hdr.license.decode('utf-8')
        self.sourcerpm = hdr.sourcerpm.decode('utf-8')
        if hdr['url']:
            self.homepage_url = hdr['url'].decode('utf-8')
        os.close(fd)
        self.log = LoggerItem(os.path.basename(filename))

    def verCMP(self, other):
        rc = cmp(self.name, other.name)
        if rc == 0:
            (e1, v1, r1) = (self.epoch, self.version, self.release)
            (e2, v2, r2) = (other.epoch, other.version, other.release)
            rc = rpmUtils.miscutils.compareEVR((e1, v1, r1), (e2, v2, r2))
        return rc

def main():
    pkg = Package(sys.argv[1])
    print 'name:\t\t', pkg.name
    sys.exit(0)

if __name__ == "__main__":
    main()
