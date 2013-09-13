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
from gi.repository import GLib

class AppstreamConfig:

    def __init__(self, filename='./data/fedora-appstream.conf'):

        self._config = GLib.KeyFile()
        self._config.load_from_file(filename, GLib.KeyFileFlags.NONE)
        self._group_name = 'fedora-appstream'
        self.distro_name = self._config.get_string(self._group_name, 'DistroName')

    def get_id_blacklist(self):
        return self._config.get_string_list(self._group_name, 'BlacklistIds')

    def get_category_blacklist(self):
        return self._config.get_string_list(self._group_name, 'BlacklistCategories')

    def get_package_blacklist(self):
        return self._config.get_string_list(self._group_name, 'BlacklistPackages')

    def get_category_ignore_list(self):
        return self._config.get_string_list(self._group_name, 'IgnoreCategories')

    def get_stock_icons(self):
        # get the list of stock icons
        f = open('./data/stock-icon-names.txt', 'r')
        stock_icons = f.read().rstrip().split('\n')
        f.close()
        return stock_icons

    def get_package_data_list(self):
        # add any extra packages required
        common_packages = []
        for k in self._config.get_keys(self._group_name)[0]:
            if k.startswith('PackageData'):
                tmp = k[12:-1]
                common_packages.append((tmp, self._config.get_string(self._group_name, k)))
        return common_packages

    def get_category_extra_list(self):
        # add any extra categories required
        categories_add = {}
        for k in self._config.get_keys(self._group_name)[0]:
            if k.startswith('CategoryAdd'):
                tmp = k[12:-1]
                categories_add[tmp] = self._config.get_string(self._group_name, k)
        return categories_add

    def get_category_extra_for_id(self, id):
        # get additional categories for a specific application id
        return self._config.get_string_list(self._group_name, 'CategoryAdd(' + id + ')')

def main():
    cfg = AppstreamConfig()
    print 'distro-name:\t\t', cfg.distro_name
    print 'ignore-categories:\t', cfg.get_category_ignore_list()
    print 'blacklist-categories:\t', cfg.get_category_blacklist()
    print 'blacklist-packages:\t', cfg.get_package_blacklist()
    print 'common-packages:\t', len(cfg.get_package_data_list())
    print 'blacklist-ids:\t\t', len(cfg.get_id_blacklist())
    print 'stock-icons:\t\t', len(cfg.get_stock_icons())
    print 'categories-add:\t\t', len(cfg.get_category_extra_list())
    sys.exit(0)

if __name__ == "__main__":
    main()
