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

class PackageBuild:
    def __init__(self):
        self.timestamp = 0
        self.packager_name = None
        self.version = None
        self.releases = []
        self.changelog = None

class Package:

    def __init__(self, filename):
        self.filename = filename
        self.name = None
        self.homepage_url = None
        self.deps = {}
        self.filelist = []
        self.builds = []
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

        # add requires
        for dep in hdr[rpm.RPMTAG_REQUIRENAME]:
            name = dep.split('(')[0]
            if name == 'rpmlib':
                continue
            if name == '/bin/sh':
                continue
            self.deps[name] = True
        for f in hdr[rpm.RPMTAG_FILENAMES]:
            self.filelist.append(f)

        # add any release information we know
        self.add_builds(hdr[rpm.RPMTAG_CHANGELOGTEXT],
                        hdr[rpm.RPMTAG_CHANGELOGTIME],
                        hdr[rpm.RPMTAG_CHANGELOGNAME]);

        os.close(fd)
        self.log = LoggerItem(os.path.basename(filename))

    def add_builds(self, cl_text, cl_time, cl_name):
        for i in range(len(cl_time)):
            r = PackageBuild()
            r.timestamp = cl_time[i]

            # parse cl_name which can be in a few forms:
            # * "Richard Hughes <rhughes@redhat.com> - 3.11.1-1"
            # * "Richard Hughes <richard@hughsie.com> 0.1-3"
            # * "richard@hughsie.com - 0.1-3"
            # * "Richard Hughes <richard at hughsie com> - 0.1-3"
            # * "Richard Hughes <richard at hughsie com>"
            # * "Richard Hughes <richard at hughsie com> -0.1-3"
            # * "<richard at hughsie.com>"
            temp = cl_name[i].decode('utf-8')

            # get packager name
            idx = temp.find('<')
            if idx >= 0:
                # has a <> section
                r.packager_name = temp[:idx-1]

                # get packager email address
                idx2 = temp.find('>', idx)
                if idx2 < 0:
                    continue
                r.packager_email = temp[idx+1:idx2-1]
                temp = temp[idx2+2:]
            else:
                # has no <> section
                idx2 = temp.find(' ')
                if idx2 < 0:
                    continue
                r.packager_name = None
                r.packager_email = temp[:idx2]
                temp = temp[idx2+1:]

            # get version and release
            if temp.startswith('- '):
                temp = temp[2:]
            if temp.startswith('-'):
                temp = temp[1:]
            if len(temp):
                vr = temp.split('-')
                if len(vr) == 1:
                    r.version = vr[0]
                elif len(vr) == 2:
                    r.version = vr[0]
                    r.releases = [vr[1]]
                else:
                    continue
            r.changelog = cl_text[i].decode('utf-8')

            # add every release to the array
            self.builds.append(r)

        # deduplicate releases with the same version
        for r in self.builds:
            for r2 in self.builds:
                if r == r2:
                    continue
                if r.version == r2.version:

                    # add the release
                    r.releases.extend(r2.releases)

                    # just join the changelog
                    if r2.changelog:
                        r.changelog += '\n' + r2.changelog

                    # choose the earlier timestamp to ignore auto-rebuilds
                    # with just a bumped soname
                    if r2.timestamp < r.timestamp:
                        r.timestamp = r2.timestamp
                    self.builds.remove(r2)
                    break

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
