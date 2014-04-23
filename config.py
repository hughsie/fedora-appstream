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

import sys
import ConfigParser

from gi.repository import GLib

class Config:

    def __init__(self, filename='../data/fedora-appstream.conf'):

        self._config = GLib.KeyFile()
        self._config.load_from_file(filename, GLib.KeyFileFlags.NONE)
        self._group_name = u'fedora-appstream'

        # get the project defaults
        self.cfg_project = ConfigParser.ConfigParser()
        self.cfg_project.read('./project.conf')
        self.distro_name = self.cfg_project.get('AppstreamProject', 'DistroName')
        self.distro_tag = self.cfg_project.get('AppstreamProject', 'DistroTag')
        self.repo_ids = self.cfg_project.get('AppstreamProject', 'RepoIds').split(',')

    def get_package_blacklist(self):
        blacklist = []
        try:
            blacklist = self._config.get_string_list(self._group_name, 'BlacklistPackages')
        except Exception as e:
            pass
        return blacklist

    def get_interesting_installed_files(self):
        data = []
        try:
            data = self._config.get_string_list(self._group_name, 'InterestingInstalledFiles')
        except Exception as e:
            pass
        return data

    def get_package_data_list(self):
        # add any extra packages required
        common_packages = []
        for k in self._config.get_keys(self._group_name)[0]:
            if k.startswith('PackageData'):
                tmp = k[12:-1]
                common_packages.append((tmp, self._config.get_string(self._group_name, k)))
        return common_packages
