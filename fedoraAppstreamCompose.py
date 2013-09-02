#!/usr/bin/python
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
import gzip
import shutil
import tarfile
import gzip

def main():

    # used as a temp location
    if os.path.exists('./tmp'):
        shutil.rmtree('./tmp')
    os.makedirs('./tmp')
    if os.path.exists('./appstream.xml.gz'):
        os.remove('./appstream.xml.gz')
    if os.path.exists('./appstream-icons.tar.gz'):
        os.remove('./appstream-icons.tar.gz')

    files = glob.glob("./appstream/*.xml")
    files.sort()

    master = gzip.open('./appstream.xml.gz', 'wb')
    master.write('<?xml version="1.0"?>\n')
    master.write('<applications version="0.1">\n')
    for f in files:
        f = open(f, 'r')
        s = f.read()
        # TODO: such a hack....
        s = s.replace('<?xml version="1.0"?>\n', '')
        s = s.replace('<applications version="0.1">\n', '')
        s = s.replace('</applications>\n', '')
        f.close()
        master.write(s)
    master.write('</applications>\n')
    master.close()

    # we have to do this as "tar --concatenate" is broken
    files = glob.glob("./appstream/*.tar")
    files.sort()
    for f in files:
        tar = tarfile.open(f, "r")
        tar.extractall(path='./tmp')
        tar.close()

    # create master icons file
    tar = tarfile.open("./appstream-icons.tar", "w")
    files = glob.glob("./tmp/*.png")
    for f in files:
        tar.add(f, arcname=f.split('/')[-1])
    tar.close()

    # compress to save a few Mb
    f_in = open('./appstream-icons.tar', 'rb')
    f_out = gzip.open('./appstream-icons.tar.gz', 'wb')
    f_out.writelines(f_in)
    f_out.close()
    f_in.close()
    os.remove('./appstream-icons.tar')

if __name__ == "__main__":
    main()
