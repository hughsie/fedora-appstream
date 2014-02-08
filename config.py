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
        self.icon_size = self._config.get_integer(self._group_name, 'IconSize')
        self.min_icon_size = self._config.get_integer(self._group_name, 'MinIconSize')

        # get the project defaults
        self.cfg_project = ConfigParser.ConfigParser()
        self.cfg_project.read('./project.conf')
        self.distro_name = self.cfg_project.get('AppstreamProject', 'DistroName')
        self.distro_tag = self.cfg_project.get('AppstreamProject', 'DistroTag')
        self.repo_ids = self.cfg_project.get('AppstreamProject', 'RepoIds').split(',')

    def get_id_blacklist(self):
        blacklist = []
        try:
            blacklist = self._config.get_string_list(self._group_name, 'BlacklistIds')
        except Exception as e:
            pass
        return blacklist

    def get_content_licences(self):
        licences = []
        try:
            licences = self._config.get_string_list(self._group_name, 'AcceptableContentLicences')
        except Exception as e:
            pass
        return licences

    def get_category_blacklist(self):
        blacklist = []
        try:
            blacklist = self._config.get_string_list(self._group_name, 'BlacklistCategories')
        except Exception as e:
            pass
        return blacklist

    def get_package_blacklist(self):
        blacklist = []
        try:
            blacklist = self._config.get_string_list(self._group_name, 'BlacklistPackages')
        except Exception as e:
            pass
        return blacklist

    def get_category_ignore_list(self):
        blacklist = []
        try:
            blacklist = self._config.get_string_list(self._group_name, 'IgnoreCategories')
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

    def get_screenshot_mirror_url(self):

        data = []
        try:
            data = self.cfg_project.get('AppstreamProject', 'ScreenshotMirrorUrl')
        except Exception as e:
            pass
        return data

    def get_screenshot_thumbnail_sizes(self):
        data = []
        sizes = []
        try:
            data = self._config.get_string_list(self._group_name, 'ScreenshotThumbnailSizes')
        except Exception as e:
            pass
        for d in data:
            tmp = d.split('x')
            sizes.append((int(tmp[0]), int(tmp[1])))
        return sizes

    def get_preferred_icon_sizes(self):
        prefs = []
        try:
            prefs = self._config.get_string_list(self._group_name, 'PreferredIconSizes')
        except Exception as e:
            pass
        return prefs

    def get_int(self, key):
        prefs = []
        try:
            prefs = self._config.get_integer(self._group_name, key)
        except Exception as e:
            pass
        return prefs

    def get_stock_icons(self):
        # get the list of stock icons
        f = open('../data/stock-icon-names.txt', 'r')
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
        add = []
        try:
            add = self._config.get_string_list(self._group_name, 'CategoryAdd(' + id + ')')
        except Exception as e:
            pass
        return add

    def get_project_group_for_id(self, id):
        # get project group for a specific application id
        value = None
        try:
            value = self._config.get_string(self._group_name, 'ProjectGroup(' + id + ')')
        except Exception as e:
            pass
        return value

def main():
    cfg = Config()
    print 'distro-name:\t\t', cfg.distro_name
    print 'icon-size:\t\t', cfg.icon_size
    print 'min-icon-size:\t\t', cfg.min_icon_size
    print 'screenshot-mirror-url:\t', cfg.get_screenshot_mirror_url()
    print 'screenshot-thumbnail-sizes:\t', cfg.get_screenshot_thumbnail_sizes()
    print 'preferred-sizes:\t', cfg.get_preferred_icon_sizes()
    print 'interesting-installed-files:\t', cfg.get_interesting_installed_files()
    print 'content-licences:\t', cfg.get_content_licences()
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
