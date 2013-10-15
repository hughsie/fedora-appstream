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

import glob
import os
import sys
import shutil
import datetime

# internal
from build import Build
from logger import Logger
from package import Package

timestamp = datetime.datetime.now().strftime('%Y%m%d')
sys.stdout = Logger("build-all-%s.txt" % timestamp)

def _do_newest_filtering(filelist):
    '''
    Only return the newest package for each name.arch
    '''
    newest = {}
    for f in filelist:
        pkg = Package(f)
        key = (pkg.name, pkg.arch)
        if key in newest:

            # the current package is older
            if pkg.verCMP(newest[key]) < 0:
                continue

            # the current package is the same version
            if pkg.verCMP(newest[key]) == 0:
                continue

            # the current package is newer than what we have stored
            del newest[key]

        newest[key] = pkg

    # get back the file list
    filelist_new = []
    for pkg in newest.values():
        filelist_new.append(pkg.filename)
    return filelist_new

def main():

    # remove appstream
    if os.path.exists('./appstream'):
        shutil.rmtree('./appstream')
    if os.path.exists('./icons'):
        shutil.rmtree('./icons')

    files_all = glob.glob("./packages/*.rpm")
    files = _do_newest_filtering(files_all)
    files.sort()

    job = Build()
    for f in files:
        try:
            job.build(f)
        except Exception as e:
            print 'WARNING\t', f, str(e)

if __name__ == "__main__":
    main()
