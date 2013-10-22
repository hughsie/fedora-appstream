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
#    Florian Festi <ffesti@redhat.com>
#

import os
import sys
import rpm
import lzma
import cpio
import fnmatch

# internal
from logger import LoggerItem

import rpmUtils.miscutils

_ts = rpm.ts()
_ts.setVSFlags(0x7FFFFFFF)

def extract_file_from_cpio(directory, cpioarchive):
    path = os.path.join(directory, os.path.dirname(cpioarchive.filename))
    if not os.path.exists(path):
        os.makedirs(path)
    output_file = os.path.join(directory, cpioarchive.filename)
    f = open(output_file, "w")
    f.write(cpioarchive.read())
    f.close()

class LZMA:
    def __init__(self, f):
        self._f = f
        self.decomp = lzma.LZMADecompressor()
        self.leftover = ""

    def read(self, size):
        # highly inefficient
        while not size < len(self.leftover):
            c = self._f.read(size)
            if not c:
                break
            d = self.decomp.decompress(c)
            self.leftover += d
        result = self.leftover[:size]
        self.leftover = self.leftover[size:]
        return result

class Package:

    def __init__(self, filename):
        self.filename = filename
        self.name = None
        self._default_wildcards = []

        # open the rpm file
        fd = os.open(filename, os.O_RDONLY)
        hdr = _ts.hdrFromFdno(fd)
        self.name = hdr.name
        self.epoch = hdr.epoch
        self.version = hdr.version
        self.release = hdr.release
        self.arch = hdr.arch
        self.summary = hdr.summary
        self.licence = hdr.license
        self.homepage_url = hdr['url']
        os.close(fd)
        self.log = LoggerItem(os.path.basename(filename))

    def verCMP(self, other):
        rc = cmp(self.name, other.name)
        if rc == 0:
            (e1, v1, r1) = (self.epoch, self.version, self.release)
            (e2, v2, r2) = (other.epoch, other.version, other.release)
            rc = rpmUtils.miscutils.compareEVR((e1, v1, r1), (e2, v2, r2))
        return rc

    def extract(self, targetpath, wildcards):

        # reopen
        fd = os.open(self.filename, os.O_RDONLY)
        hdr = _ts.hdrFromFdno(fd)
        fi = hdr.fiFromHeader()
        f = os.fdopen(fd)
        lf = LZMA(f)
        cpioarchive = cpio.CpioArchive(lf)
        files = []
        for filename in cpioarchive:
            for w in wildcards:
                if fnmatch.fnmatch(filename, w):
                    extract_file_from_cpio(targetpath, cpioarchive)
                    files.append(filename)
                    break
        f.close()
        return files

def main():
    pkg = Package(sys.argv[1])
    print 'name:\t\t', pkg.name
    print 'decompressed:\t', pkg.extract('/tmp', [ './usr/share/applications/*.desktop' ])
    sys.exit(0)

if __name__ == "__main__":
    main()
