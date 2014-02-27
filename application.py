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
import subprocess
import sys
import urllib
import xml.etree.ElementTree as ET

from PIL import Image

# internal
from appdata import AppData
from logger import LoggerItem
from package import Package
from screenshot import Screenshot

class Release:

    def __init__(self):
        self.timestamp = 0
        self.version = None

class Application:

    def __init__(self, pkg, cfg):
        self.log = LoggerItem()
        self.app_id = None
        self.app_id_full = None
        self.names = {}
        self.categories = []
        self.descriptions = {}
        self.comments = {}
        self.mimetypes = None
        self.urls = {}
        self.licence = None
        self.pkgnames = []
        self.releases = []
        self.languages = {}
        self.metadata = {}
        if pkg:
            self.licence = pkg.licence
            self.pkgnames = [pkg.name]
            if pkg.homepage_url:
                self.urls[u'homepage'] = pkg.homepage_url
        self.icon = None
        self.keywords = []
        self.cached_icon = False
        self.cfg = cfg
        self.screenshots = []
        self.compulsory_for_desktop = []
        self.type_id = None
        self.project_group = None
        self.requires_appdata = False
        self.thumbnail_screenshots = True

    def __str__(self):
        s = {}
        s['app-id'] = self.app_id_full
        s['type_id'] = self.type_id
        s['names'] = self.names
        s['comments'] = self.comments
        s['categories'] = self.categories
        s['descriptions'] = self.descriptions
        s['mimetypes'] = self.mimetypes
        s['urls'] = self.urls
        s['metadata'] = self.metadata
        s['licence'] = self.licence
        s['pkgnames'] = self.pkgnames
        s['icon'] = self.icon
        s['keywords'] = self.keywords
        s['cached_icon'] = self.cached_icon
        s['screenshots'] = self.screenshots
        s['compulsory_for_desktop'] = self.compulsory_for_desktop
        s['project_group'] = self.project_group
        s['requires_appdata'] = self.requires_appdata
        return str(s)

    def add_appdata_file(self):

        # do we have an AppData file?
        filename = './tmp/usr/share/appdata/' + self.app_id + '.appdata.xml'
        fn_extra = '../appdata-extra/' + self.type_id + '/' + self.app_id + '.appdata.xml'
        if os.path.exists(filename) and os.path.exists(fn_extra):
            self.log.write(LoggerItem.INFO,
                           "deleting %s as upstream AppData file exists" % fn_extra)
            os.remove(fn_extra)

        # just use the extra file in places of the missing upstream one
        if os.path.exists(fn_extra):
            filename = fn_extra

        # need to extract details
        if not os.path.exists(filename):
            return False

        data = AppData()
        if not data.extract(filename):
            self.log.write(LoggerItem.WARNING,
                           "AppData file '%s' could not be parsed" % filename)
            return False

        # check AppData file validates
        enable_validation = self.type_id != 'font'
        if enable_validation and os.path.exists('/usr/bin/appdata-validate'):
            env = os.environ
            p = subprocess.Popen(['/usr/bin/appdata-validate',
                                  '--relax', filename],
                                 cwd='.', env=env, stdout=subprocess.PIPE)
            p.wait()
            if p.returncode:
                for line in p.stdout:
                    line = line.replace('\n', '').decode('utf-8')
                    self.log.write(LoggerItem.WARNING,
                                   "AppData did not validate: %s" % line)

        # check the id matches
        if data.get_id() != self.app_id and data.get_id() != self.app_id_full:
            self.log.write(LoggerItem.WARNING,
                           "The AppData id does not match: " + self.app_id)
            return False

        # check the licence is okay
        if data.get_licence() not in self.cfg.get_content_licences():
            self.log.write(LoggerItem.WARNING,
                           "The AppData licence is not okay for " +
                           self.app_id + ': \'' +
                           data.get_licence() + '\'')
            return False

        # if we have an override, use it for all languages
        tmp = data.get_names()
        if tmp:
            self.names = tmp

        # if we have an override, use it for all languages
        tmp = data.get_summaries()
        if tmp:
            self.comments = tmp

        # get metadata
        tmp = data.get_metadata()
        if tmp:
            # and extra packages we want to add in?
            if 'ExtraPackages' in tmp:
                for pkg in tmp['ExtraPackages'].split(','):
                    if pkg not in self.pkgnames:
                        self.pkgnames.append(pkg)
                del tmp['ExtraPackages']
            self.metadata.update(tmp)

        # get optional bits
        tmp = data.get_urls()
        if tmp:
            for key in tmp:
                self.urls[key] = tmp[key]
        tmp = data.get_project_group()
        if tmp:
            self.project_group = tmp
        try:
            self.descriptions = data.get_descriptions()
        except StandardError, e:
            self.log.write(LoggerItem.WARNING,
                           "failed to add description: %s" % str(e))

        # get screenshots
        tmp = data.get_screenshots()
        for image in tmp:
            self.log.write(LoggerItem.INFO, "downloading %s" % image)
            self.add_screenshot_url(image)

        # get compulsory_for_desktop
        for c in data.get_compulsory_for_desktop():
            if c not in self.compulsory_for_desktop:
                self.compulsory_for_desktop.append(c)
        return True

    def add_screenshot_filename(self, filename, caption=None):

        # just add it
        try:
            img = Image.open(filename)
        except IOError as e:
            self.log.write(LoggerItem.WARNING,
                           "Failed to open %s: %s" % (filename, str(e)))
        else:
            self.screenshots.append(Screenshot(self.app_id, img, caption))

    def add_screenshot_url(self, url, caption=None):

        # download image and add it
        cache_filename = './screenshot-cache/' + self.app_id
        cache_filename += '-' + os.path.basename(url)
        if not os.path.exists(cache_filename):
            urllib.urlretrieve (url, cache_filename)
        self.add_screenshot_filename(cache_filename, caption)

    def set_id(self, app_id):

        # we use the full AppID when writing to AppStream XML
        self.app_id_full = app_id
        self.app_id_full = self.app_id_full.replace('&', '-')
        self.app_id_full = self.app_id_full.replace('<', '-')
        self.app_id_full = self.app_id_full.replace('>', '-')

        # we use the short version (without the extension) internally when
        # refering to things like icon names
        self.app_id = self.app_id_full
        split = self.app_id_full.rsplit('.', 1)
        if len(split) > 1:
            self.app_id = split[0]

        # update the log name
        self.log.update_key(self.app_id_full)

    def build_xml_screenshots(self, root):

        # any screenshots
        mirror_url = self.cfg.get_screenshot_mirror_url()
        if not mirror_url:
            return
        if len(self.screenshots) == 0:
            return

        screenshots = ET.SubElement(root, 'screenshots')
        screenshots.tail = u'\n'
        for s in self.screenshots:

            screenshot = ET.SubElement(screenshots, 'screenshot')
            screenshot.tail = u'\n'
            if s == self.screenshots[0]:
                screenshot.set(u'type', u'default')
            else:
                screenshot.set(u'type', u'normal')

            if s.caption:
                caption = ET.SubElement(screenshot, u'caption')
                caption.text = s.caption
                caption.tail = u'\n'

            # write the full size source image
            image = ET.SubElement(screenshot, u'image')
            image.set(u'type', u'source')
            image.set(u'width', unicode(s.width))
            image.set(u'height', unicode(s.height))
            image.text = mirror_url + 'source/' + s.basename
            image.tail = u'\n'
            s.dump_to_file('./screenshots/source')

            # write all the thumbnail sizes too
            if self.thumbnail_screenshots:
                for width, height in self.cfg.get_screenshot_thumbnail_sizes():
                    size_str = unicode(width) + 'x' + unicode(height)
                    image = ET.SubElement(screenshot, 'image')
                    image.set(u'type', u'thumbnail')
                    image.set(u'width', str(width))
                    image.set(u'height', str(height))
                    image.text = mirror_url + size_str + '/' + s.basename
                    image.tail = u'\n'
                    s.dump_to_file('./screenshots/' + size_str, (width, height))

    def build_xml(self, root):

        application = ET.SubElement(root, 'application')
        application.tail = u'\n'

        # write id
        elem = ET.SubElement(application, 'id')
        elem.set(u'type', self.type_id)
        elem.text = self.app_id_full
        elem.tail = u'\n'

        # write pkgnames
        for pkgname in self.pkgnames:
            elem = ET.SubElement(application, 'pkgname')
            elem.text = pkgname
            elem.tail = u'\n'

        # write name
        elem = ET.SubElement(application, 'name')
        elem.text = self.names['C']
        elem.tail = u'\n'
        for lang in self.names:
            if lang == 'C':
                continue
            elem = ET.SubElement(application, 'name')
            elem.set(u'xml:lang', lang)
            elem.text = self.names[lang]
            elem.tail = u'\n'

        # write summary
        elem = ET.SubElement(application, 'summary')
        elem.text = self.comments['C']
        elem.tail = u'\n'
        for lang in self.comments:
            if lang == 'C':
                continue
            elem = ET.SubElement(application, 'summary')
            elem.set(u'xml:lang', lang)
            elem.text = self.comments[lang]
            elem.tail = u'\n'

        # write icon
        if self.icon:
            elem = ET.SubElement(application, 'icon')
            elem.tail = u'\n'
            if self.cached_icon:
                elem.set(u'type', 'cached')
                elem.text = self.app_id + '.png'
            else:
                elem.set(u'type', 'stock')
                elem.text = self.icon

        # write categories
        if self.categories:
            elem = ET.SubElement(application, 'appcategories')
            elem.tail = u'\n'

            # check for a common problem
            if 'AudioVideo' in self.categories:
                if not 'Audio' in self.categories and not 'Video' in self.categories:
                    self.log.write(LoggerItem.WARNING,
                                   "has AudioVideo but not Audio or Video")
                    self.categories.extend([u'Audio', u'Video'])
            for cat in self.categories:
                if cat in self.cfg.get_category_ignore_list():
                    continue
                if cat.startswith('X-'):
                    continue
                # simple substitution
                if cat == 'Feed':
                    cat = u'News'
                elem2 = ET.SubElement(elem, 'appcategory')
                elem2.text = cat
                elem2.tail = u'\n'

        # write keywords
        if len(self.keywords) > 0:
            elem = ET.SubElement(application, 'keywords')
            elem.tail = u'\n'
            for keyword in self.keywords:
                elem2 = ET.SubElement(elem, 'keyword')
                elem2.text = keyword
                elem2.tail = u'\n'

        # write mimetypes
        if self.mimetypes:
            elem = ET.SubElement(application, 'mimetypes')
            elem.tail = u'\n'
            for mimetype in self.mimetypes:
                elem2 = ET.SubElement(elem, 'mimetype')
                elem2.text = mimetype
                elem2.tail = u'\n'

        # write licence
        if self.licence:
            elem = ET.SubElement(application, 'project_license')
            elem.text = self.licence
            elem.tail = u'\n'
            # write the deprecated tag too; FIXME: remove this after 2015
            elem = ET.SubElement(application, 'licence')
            elem.text = self.licence
            elem.tail = u'\n'

        # write urls
        for key in self.urls:
            elem = ET.SubElement(application, 'url')
            elem.set(u'type', key)
            elem.text = self.urls[key]
            elem.tail = u'\n'

        # write project_group
        if self.project_group:
            elem = ET.SubElement(application, 'project_group')
            elem.text = self.project_group
            elem.tail = u'\n'

        # write description
        if self.descriptions and 'C' in self.descriptions:
            elem = ET.SubElement(application, 'description')
            elem.text = self.descriptions['C']
            elem.tail = u'\n'
            for lang in self.descriptions:
                if lang == 'C':
                    continue
                continue
                elem = ET.SubElement(application, 'description')
                elem.set(u'xml:lang', lang)
                elem.text = self.descriptions[lang]
                elem.tail = u'\n'

        # compulsory for any specific desktop?
        if len(self.compulsory_for_desktop) > 0:
            for c in self.compulsory_for_desktop:
                elem = ET.SubElement(application, 'compulsory_for_desktop')
                elem.text = c
                elem.tail = u'\n'

        # write screenshots
        self.build_xml_screenshots(application)

        # write languages
        if len(self.languages) > 0:
            elem_langs = ET.SubElement(application, u'languages')
            elem_langs.tail = u'\n'
            for m in self.languages:
                elem = ET.SubElement(elem_langs, u'lang')
                elem.set(u'percentage', self.languages[m])
                elem.text = m
                elem.tail = u'\n'

        # any metadata
        if len(self.metadata) > 0:
            elem_md = ET.SubElement(application, u'metadata')
            elem_md.tail = u'\n'
            for m in self.metadata:
                elem = ET.SubElement(elem_md, u'value')
                elem.set(u'key', m)
                elem.text = self.metadata[m]
                elem.tail = u'\n'

        # any releases
        if len(self.releases) > 0:
            elem_r = ET.SubElement(application, u'releases')
            elem_r.tail = u'\n'
            for rel in self.releases[:3]:
                if not rel.version:
                    continue
                elem = ET.SubElement(elem_r, u'release')
                elem.set(u'timestamp', str(rel.timestamp))
                elem.set(u'version', rel.version)
                elem.tail = u'\n'

def main():
    pkg = Package(sys.argv[1])
    app = Application(pkg, None)
    app.app_id = 'test'
    app.names['C'] = 'test'
    app.comments['C'] = 'Test package'
    f = open('/tmp/test.xml', 'w')
    app.write(f)
    f.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
