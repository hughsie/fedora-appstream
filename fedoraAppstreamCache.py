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

class Logger(object):
    def __init__(self, filename="Default.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

sys.stdout = Logger("cache.txt")

_ts = rpm.ts()
_ts.setVSFlags(0x7FFFFFFF)

def update(repos, reponame):

    # create if we're starting from nothing
    if not os.path.exists('./packages'):
        os.makedirs('./packages')

    # get extra packages needed for some applications
    f = open('./data/common-packages.txt', 'r')
    entries = common_packages = f.read().rstrip().split('\n')
    extra_packages = []
    for e in entries:
        extra_packages.append(e.split('\t')[1])
    f.close()

    # find out what we've got already
    files = glob.glob("./packages/*.rpm")
    files.sort()
    existing = {}
    for f in files:
        fd = os.open(f, os.O_RDONLY)
        hdr = _ts.hdrFromFdno(fd)
        existing[hdr.name] = f
        os.close(fd)
    print "INFO:\t\tFound %i existing packages for %s" % (len(existing), reponame)

    # load package blacklist
    f = open('./data/blacklist-packages.txt')
    blacklisted_packages = f.read().rstrip().split('\n')
    f.close()

    # setup yum
    yb = yum.YumBase()
    yb.preconf.releasever = reponame[1:]
    yb.doConfigSetup(errorlevel=-1, debuglevel=-1)
    yb.conf.cache = 0

    # what is native for this arch
    basearch = rpmUtils.arch.getBaseArch()
    if basearch == 'i386':
        basearch_list = ['i386', 'i486', 'i586', 'i686']
    else:
        basearch_list = [basearch]
    basearch_list.append('noarch')

    # find all packages
    downloaded = {}
    pkgs = yb.pkgSack
    for pkg in pkgs:

        # not our repo
        if pkg.repoid not in repos:
            continue

        # not our arch
        if pkg.arch not in basearch_list:
            continue

        # don't download blacklisted packages
        if pkg.name in blacklisted_packages:
            continue

        # make sure the metadata exists
        repo = yb.repos.getRepo(pkg.repoid)

        # find out if any of the files ship a desktop file
        desktop_files = []
        for instfile in pkg.returnFileEntries():
            if instfile.startswith('/usr/share/applications/') and instfile.endswith('.desktop'):
                desktop_files.append(instfile[24:])

        # don't download packages without desktop files
        if len(desktop_files) == 0 and pkg.name not in extra_packages:
            continue

        # get base name without the slash
        relativepath = pkg.returnSimple('relativepath')
        pos = relativepath.rfind('/')
        if pos != -1:
            relativepath = relativepath[pos+1:]

        # is in cache?
        path = './packages/' + relativepath
        if os.path.exists(path) and os.path.getsize(path) == int(pkg.returnSimple('packagesize')):
            print 'INFO:\t\t' + pkg.name + ' already in cache'
            downloaded[pkg.name] = True
        else:
            pkg.localpath = path

            # download now
            print 'DOWNLOAD:\t', path
            repo.getPackage(pkg)

            # do we have an old version of this?
            if existing.has_key(pkg.name):
                print 'DELETE:\t\t', existing[pkg.name]
                os.remove(existing[pkg.name])
        downloaded[pkg.name] = True

    # have any packages been removed?
    for i in existing:
        if not downloaded.has_key(i):
            print 'DELETE:\t\t' + existing[i]
            os.remove(existing[i])

def main():
    default_repos = [ 'fedora', 'fedora-updates' ]
    if len(sys.argv) == 3:
        update(sys.argv[2].split(','), sys.argv[1])
    elif len(sys.argv) == 2:
        update(default_repos, sys.argv[1])
    else:
        update(default_repos, 'f20')
    sys.exit(0)

if __name__ == "__main__":
    main()
