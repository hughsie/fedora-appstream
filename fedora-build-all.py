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
from logger import Logger, LoggerItem
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

    # check we're not top level
    if os.path.exists('./application.py'):
        print 'You cannot run these tools from the top level directory'
        sys.exit(1)

    # remove appstream
    if os.path.exists('./appstream'):
        shutil.rmtree('./appstream')
    if os.path.exists('./icons'):
        shutil.rmtree('./icons')

    # the status HTML page goes here too
    if not os.path.exists('./screenshots'):
        os.makedirs('./screenshots')

    files_all = glob.glob("./packages/*.rpm")
    files = _do_newest_filtering(files_all)
    files.sort()

    log = LoggerItem()
    job = Build()

    # build status page
    job.status_html = open('./screenshots/status.html', 'w')
    job.status_html.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 ' +
                          'Transitional//EN" ' +
                          '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')
    job.status_html.write('<html xmlns="http://www.w3.org/1999/xhtml">\n')
    job.status_html.write('<head>\n')
    job.status_html.write('<meta http-equiv="Content-Type" content="text/html; ' +
                          'charset=UTF-8" />\n')
    job.status_html.write('<title>Application Data Review</title>\n')
    job.status_html.write('</head>\n')
    job.status_html.write('<body>\n')

    for f in files:
        log.update_key(f)
        try:
            job.build(f)
        except Exception as e:
            log.write(LoggerItem.WARNING, str(e))
    job.write_appstream()

    job.status_html.write('</body>\n')
    job.status_html.write('</html>\n')
    job.status_html.close()

if __name__ == "__main__":
    main()
