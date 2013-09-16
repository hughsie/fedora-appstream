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
        self.contains_desktop_file = False
        self.filename = filename
        self.name = None
        self._f = None
        self._default_wildcards = []

        # open the rpm file
        fd = os.open(filename, os.O_RDONLY)
        hdr = _ts.hdrFromFdno(fd)
        self.name = hdr.name
        self.homepage_url = hdr['url']
        fi = hdr.fiFromHeader()

        # does this have a desktop file
        for (fname, size, mode, mtime, flags, dev, inode,
             nlink, state, vflags, user, group, digest) in fi:
            if fname.endswith(".desktop"):
                self.contains_desktop_file = True
                break
        self._f = os.fdopen(fd)

    def __del__(self):
        self._f.close()

    def extract(self, targetpath, wildcards):
        lf = LZMA(self._f)
        cpioarchive = cpio.CpioArchive(lf)
        files = []
        for filename in cpioarchive:
            for w in wildcards:
                if fnmatch.fnmatch(filename, w):
                    extract_file_from_cpio(targetpath, cpioarchive)
                    files.append(filename)
                    break
        return files

def main():
    pkg = Package(sys.argv[1])
    print 'name:\t\t', pkg.name
    print 'is-app:\t\t', pkg.contains_desktop_file
    print 'decompressed:\t', pkg.extract('/tmp', [ './usr/share/applications/*.desktop' ])
    sys.exit(0)

if __name__ == "__main__":
    main()
