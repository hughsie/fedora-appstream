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

import os
import sys
import csv

# internal
from application import Application
from package import Package

class AppdataException(Exception):
    pass

class Codec(Application):

    def __init__(self, pkg, cfg):
        Application.__init__(self, pkg, cfg)
        self.type_id = u'codec'
        self.requires_appdata = True
        self.categories = []
        self.cached_icon = False
        self.icon = 'application-x-executable'
        self.categories.append(u'Addons')
        self.categories.append(u'Codecs')

        # use the pkgname as the id
        app_id = pkg.name
        app_id = app_id.replace('gstreamer1-', '')
        app_id = app_id.replace('gstreamer-', '')
        app_id = app_id.replace('plugins-', '')
        self.set_id('gstreamer-' + app_id)

        # map the ID to a nice codec name
        self.codec_name = {}
        csvfile = open('../data/gstreamer-data.csv', 'r')
        data = csv.reader(csvfile)
        for row in data:
            if row[1] == '-':
                continue
            codec_id = row[0][31:-3]
            self.codec_name[codec_id] = row[1].split('|')
        csvfile.close()

    def parse_files(self, files):

        app_ids = []
        summary = []

        for f in files:
            if not f.startswith('./tmp/usr/lib64/gstreamer-1.0/libgst'):
                continue
            if not f.endswith('.so'):
                continue
            app_id = f[36:-3]
            if not app_id in self.codec_name:
                continue
            app_ids.append(app_id)

            # add each short name if it's not existing before
            new = self.codec_name[app_id]
            for n in new:
                if n.count('encoder') > 0:
                    continue
                if not n in summary:
                    self.keywords.append(n)
                    summary.append(n)

        # nothing codec_name
        if len(app_ids) == 0:
            return False

        # get a description
        summary.sort()
        self.names['C'] = 'GStreamer Multimedia Codecs'
        if len(summary) > 1:
            summary_str = ', '.join(summary[0:-1]) + ' and ' + summary[-1]
        else:
            summary_str = summary[0]
        self.comments['C'] = 'Multimedia playback for ' + summary_str
        return True

def main():
    sys.exit(0)

if __name__ == "__main__":
    main()
