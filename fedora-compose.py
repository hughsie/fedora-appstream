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
import tarfile
import gzip
import datetime
import xml.etree.ElementTree as ET

import config
from logger import Logger, LoggerItem
from application import Application

timestamp = datetime.datetime.now().strftime('%Y%m%d')
sys.stdout = Logger("compose-%s.txt" % timestamp)

class Compose:

    def __init__(self):
        self.cfg = config.Config()
        self.log = LoggerItem()
        self.application_ids = {}

        # used as a temp location
        if os.path.exists('./tmp'):
            shutil.rmtree('./tmp')
        os.makedirs('./tmp')
        if os.path.exists('./' + self.cfg.distro_name + '.xml.gz'):
            os.remove('./' + self.cfg.distro_name + '.xml.gz')
        if os.path.exists('./' + self.cfg.distro_name + '-icons.tar.gz'):
            os.remove('./' + self.cfg.distro_name + '-icons.tar.gz')

    def run(self):

        files = glob.glob("./appstream/*.xml")
        files.sort()

        # setup the output XML
        master_root = ET.Element("applications")
        master_root.set("version", "0.1")
        master_tree = ET.ElementTree(master_root)

        recognised_types = ['desktop', 'codec', 'font', 'inputmethod']
        for filename in files:
            self.log.update_key(filename)
            try:
                tree = ET.parse(filename)
            except ET.ParseError, e:
                self.log.write(LoggerItem.WARNING, "XML could not be parsed: %s" % str(e))
                continue
            root = tree.getroot()
            for app in root:
                app_id = app.find('id')

                # check type is known
                app_id_type = app_id.get('type')
                if app_id_type not in recognised_types:
                    self.log.write(LoggerItem.WARNING,
                              "appstream id type %s not recognised" % app_id_type)
                    continue

                # detect duplicate IDs in the data
                if self.application_ids.has_key(app_id):
                    found = self.application_ids[app_id.text]
                    self.log.write(LoggerItem.WARNING,
                              "duplicate ID found in %s and %s" % (filename, found))
                    continue

                # add everything that isn't private
                new = ET.SubElement(master_root, 'application')
                for elem in app:
                    if elem.tag.startswith("X-"):
                        continue
                    new.append(elem)

                # success
                self.application_ids[app_id.text] = filename
                self.log.write(LoggerItem.INFO, "adding %s" % app_id.text)

        # write to compressed file
        master = gzip.open('./' + self.cfg.distro_name + '.xml.gz', 'wb')
        master_tree.write(master, 'UTF-8')
        master.close()

        # we have to do this as "tar --concatenate" is broken
        files = glob.glob("./appstream/*.tar")
        files.sort()
        for f in files:
            tar = tarfile.open(f, "r")
            tar.extractall(path='./tmp')
            tar.close()

        # create master icons file
        tar = tarfile.open('./' + self.cfg.distro_name + '-icons.tar', "w")
        files = glob.glob("./tmp/*.png")
        for f in files:
            tar.add(f, arcname=f.split('/')[-1])
        tar.close()

        # compress to save a few Mb
        f_in = open('./' + self.cfg.distro_name + '-icons.tar', 'rb')
        f_out = gzip.open('./' + self.cfg.distro_name + '-icons.tar.gz', 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove('./' + self.cfg.distro_name + '-icons.tar')

if __name__ == "__main__":

    # check we're not top level
    if os.path.exists('./application.py'):
        print 'You cannot run these tools from the top level directory'
        sys.exit(1)

    compose = Compose()
    compose.run()
    sys.exit(0)
