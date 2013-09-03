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
#    Florian Festi <ffesti@redhat.com>
#

import struct

class CpioArchive:

    headerformat = ">6s" + "8s" * 13

    def __init__(self, f):
        if not hasattr(f, "read"):
            f = open(f, "r")
        self.f = f
        self._read = 0
        self.filesize = 0

    def __iter__(self):
        return self

    def next(self):
        # fast forward
        if self._read < self.filesize:
            if hasattr(self.f, "seek"):
                self.f.seek(self.filesize - self._read, 1)
            else:
                self.f.read(self.filesize - self._read)

        if self.filesize % 4:
            self.f.read(4 - (self.filesize % 4))

        header = self.f.read(110)
        e =  struct.unpack_from(self.headerformat, header)
        if e[0] != "070701":
            raise ValueError, "Not a valid cpio archive"

        for i, n in enumerate(("inode", "mode", "uid", "gid", "nlink",
                               "mtime", "filesize", "devMajor", "devMinor",
                               "rdevMajor", "rdevMinor", "nameSize",
                               "checksum")):
            setattr(self, n, int(e[i+1], 16))

        self.filename = self.f.read(self.nameSize)[:-1]
        if (self.nameSize+2) % 4:
            self.f.read(4 - ((self.nameSize+2) % 4))

        self._read = 0

        if self.filesize == 0  and self.inode == 0  and self.mode == 0 \
                and self.filename == "TRAILER!!!":
            raise StopIteration
        return self.filename

    def read(self, size=None):
        if self._read == self.filesize:
            raise StopIteration

        if size == None or self._read + size > self.filesize:
            size = self.filesize - self._read

        result = self.f.read(size)
        if not len(result):
            raise StopIteration
        self._read += len(result)
        
        return result

def main():
    cpio = CpioArchive("testrpms/gnome-terminal-2.30.1-1.fc13.x86_64.cpio")
    for entry in cpio:
        print repr(cpio.filename)
        while True:
            try:
                r = cpio.read(512)
            except StopIteration:
                break
            if not r:
                break

if __name__ == "__main__":
    main()
