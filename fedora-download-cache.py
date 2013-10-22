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

# internal
from config import Config
from logger import Logger, LoggerItem

timestamp = datetime.datetime.now().strftime('%Y%m%d')
sys.stdout = Logger("download-cache-%s.txt" % timestamp)

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
    return newest.values()

def update():

    log = LoggerItem()

    # create if we're starting from nothing
    if not os.path.exists('./packages'):
        os.makedirs('./packages')

    # get extra packages needed for some applications
    cfg = Config()
    extra_packages = []
    for e in cfg.get_package_data_list():
        extra_packages.append(e[1])

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
    log.write(LoggerItem.INFO, "found %i existing packages for %s" % (len(existing), cfg.distro_tag))

    # setup yum
    yb = yum.YumBase()
    yb.preconf.releasever = cfg.distro_tag[1:]
    yb.doConfigSetup(errorlevel=-1, debuglevel=-1)
    yb.conf.cache = 0

    # reget the metadata every day
    for repo in yb.repos.listEnabled():
        repo.metadata_expire = 60 * 60 * 24  # 24 hours

    # what is native for this arch
    basearch = rpmUtils.arch.getBaseArch()
    if basearch == 'i386':
        basearch_list = ['i386', 'i486', 'i586', 'i686']
    else:
        basearch_list = [basearch]
    basearch_list.append('noarch')

    # find all packages
    downloaded = {}
    try:
        pkgs = yb.pkgSack
    except yum.Errors.NoMoreMirrorsRepoError as e:
        log.write(LoggerItem.FAILED, str(e))
        sys.exit(1)
    newest_packages = _do_newest_filtering(pkgs)
    newest_packages.sort()
    for pkg in newest_packages:

        log.update_key(pkg.nvra)

        # not our repo
        if pkg.repoid not in cfg.repo_ids:
            continue

        # not our arch
        if pkg.arch not in basearch_list:
            continue

        # don't download blacklisted packages
        if pkg.name in cfg.get_package_blacklist():
            continue

        # make sure the metadata exists
        repo = yb.repos.getRepo(pkg.repoid)

        # find out if any of the files ship a desktop file
        interesting_files = []
        for instfile in pkg.returnFileEntries():
            for match in cfg.get_interesting_installed_files():
                if fnmatch.fnmatch(instfile, match):
                    interesting_files.append(instfile)
                    break

        # don't download packages without desktop files
        if len(interesting_files) == 0 and pkg.name not in extra_packages:
            continue

        # get base name without the slash
        relativepath = pkg.returnSimple('relativepath')
        pos = relativepath.rfind('/')
        if pos != -1:
            relativepath = relativepath[pos+1:]

        # is in cache?
        path = './packages/' + relativepath
        if os.path.exists(path) and os.path.getsize(path) == int(pkg.returnSimple('packagesize')):
            log.write(LoggerItem.INFO, "up to date")
            downloaded[pkg.name] = True
        else:
            pkg.localpath = path

            # download now
            log.update_key(os.path.basename(path))
            log.write(LoggerItem.INFO, "downloading")
            repo.getPackage(pkg)

            # do we have an old version of this?
            if existing.has_key(pkg.name):
                log.update_key(os.path.basename(existing[pkg.name]))
                log.write(LoggerItem.INFO, "deleting")
                os.remove(existing[pkg.name])
        downloaded[pkg.name] = True

    # have any packages been removed?
    log.update_key()
    for i in existing:
        if not downloaded.has_key(i):
            log.write(LoggerItem.INFO, "deleting %s" % existing[i])
            os.remove(existing[i])

def main():

    # check we're not top level
    if os.path.exists('./application.py'):
        print 'You cannot run these tools from the top level directory'
        sys.exit(1)

    # update all the packages
    update()
    sys.exit(0)

if __name__ == "__main__":
    main()
