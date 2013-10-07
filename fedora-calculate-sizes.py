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
import rpm
import rpmUtils
import sys
import yum
import fnmatch
import datetime
from yum.constants import *

# internal
from config import Config
from logger import Logger
from package import Package

timestamp = datetime.datetime.now().strftime('%Y%m%d')
sys.stdout = Logger("calculate-sizes-%s.txt" % timestamp)

_ts = rpm.ts()
_ts.setVSFlags(0x7FFFFFFF)

def _do_newest_filtering(pkglist):
    '''
    Only return the newest package for each name.arch
    '''
    newest = {}
    for pkg in pkglist:
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
    return newest.values()[0]

def update():

    # find out what we've got already
    files = glob.glob("./packages/*.rpm")
    files.sort()
    existing = {}
    for f in files:
        fd = os.open(f, os.O_RDONLY)
        try:
            hdr = _ts.hdrFromFdno(fd)
        except Exception as e:
            pass
        else:
            existing[hdr.name] = f
        os.close(fd)
    print "Found %i packages" % len(existing)

    # setup yum
    yb = yum.YumBase()
    yb.doConfigSetup(errorlevel=-1, debuglevel=-1)
    yb.conf.cache = 0
    yb.conf.skip_broken = 0

    # reget the metadata every day
    for repo in yb.repos.listEnabled():
        repo.metadata_expire = -1

    data = ''
    for f in files:
        p = Package(f)

        # clear previous transaction data
        yb._tsInfo = None

        # find the package in the remote repos
        available_pkgs = []
        repos = yb.repos.repos.values()
        for repo in repos:
            if not repo.isEnabled():
                continue
            yb.repos.populateSack(repo.id)
            pkgs = repo.sack.searchNevra(name=p.name)
            if not pkgs:
                continue
            for pkg in pkgs:
                if pkg.arch in [ 'x86_64', 'noarch' ]:
                    available_pkgs.append(pkg)
        pkg = _do_newest_filtering(available_pkgs)
        print "INFO\tProcessing", p.name

        # install it and get the deplist
        txmbr = yb.install(po=pkg)
        try:
            rc, msgs = yb.buildTransaction()
        except Exception, e:
            print e

        # get the sizes
        size_total = pkg.size
        for txmbr in yb.tsInfo:
            if txmbr.output_state in TS_INSTALL_STATES:
                print "\tRequires dependency", txmbr.po.name
                size_total += txmbr.po.size
        data += p.name + '\t' + str(size_total) + '\n'
        print "INFO\tRequires %iMb in deps" % (size_total / (1024 * 1024))

    # save to disk
    outfile = open("./sizes.txt", 'w')
    outfile.write(data)
    outfile.close()

def main():
    update()
    sys.exit(0)

if __name__ == "__main__":
    main()
