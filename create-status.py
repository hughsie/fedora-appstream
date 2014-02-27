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

import xml.etree.ElementTree as ET
import gzip
import sys
import os

# internal
from application import Application
from logger import LoggerItem
from config import Config
from screenshot import Screenshot

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'

def _to_utf8(txt, errors='replace'):
    if isinstance(txt, str):
        return txt
    if isinstance(txt, unicode):
        return txt.encode('utf-8', errors=errors)
    return str(txt)

def _to_html(app):
    doc = "<a name=\"%s\"/><h2>%s</h2>\n" % (app.app_id, app.app_id)
    mirror_url = app.cfg.get_screenshot_mirror_url()
    if mirror_url and len(app.screenshots) > 0:
        for s in app.screenshots:
            url = mirror_url + u'624x351/' + s.basename
            thumb_url = mirror_url + u'112x63/' + s.basename
            if s.caption:
                doc += u"<a href=\"%s\"><img src=\"%s\" alt=\"%s\"/></a>\n" % (url, thumb_url, s.caption)
            else:
                doc += u"<a href=\"%s\"><img src=\"%s\"/></a>\n" % (url, thumb_url)
    doc += u"<table>\n"
    doc += u"<tr><td>%s</td><td><code>%s</code></td></tr>\n" % ("Type", app.type_id)
    doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % ("Name", app.names['C'])
    doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % ("Comment", app.comments['C'])
    if app.descriptions and 'C' in app.descriptions:
        doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % ("Description", app.descriptions['C'])
    if len(app.pkgnames) > 0:
        for pkgname in app.pkgnames:
            url = 'https://apps.fedoraproject.org/packages/' + pkgname
            doc += u"<tr><td>%s</td><td><a href=\"%s\"><code>%s</code></a></td></tr>\n" % ("Package", url, pkgname)
    if app.categories:
        doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % ("Categories", ', '.join(app.categories))
    if len(app.keywords):
        doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % ("Keywords", ', '.join(app.keywords))
    if 'homepage' in app.urls:
        doc += u"<tr><td>%s</td><td><a href=\"%s\">%s</a></td></tr>\n" % ("Homepage", app.urls['homepage'], app.urls['homepage'])
    if app.project_group:
        doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % ("Project", app.project_group)
    if len(app.compulsory_for_desktop):
        doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % ("Compulsory", ', '.join(app.compulsory_for_desktop))

    # add all possible Kudo's for desktop files
    if app.type_id == 'desktop':
        possible_kudos = []
        possible_kudos.append('X-Kudo-SearchProvider')
        possible_kudos.append('X-Kudo-InstallsUserDocs')
        possible_kudos.append('X-Kudo-UsesAppMenu')
        possible_kudos.append('X-Kudo-GTK3')
        possible_kudos.append('X-Kudo-RecentRelease')
        possible_kudos.append('X-Kudo-UsesNotifications')
        for kudo in possible_kudos:
            doc += u"<tr><td>%s</td><td>%s</td></tr>\n" % (kudo, kudo in app.metadata)

    doc += u"</table>\n"
    doc += u"<hr/>\n"
    return doc

def ensure_unicode(text):
    if isinstance(text, unicode):
        return text
    return text.decode('utf-8')

def main():
    log = LoggerItem()
    cfg = Config()

    # read in AppStream file into several Application objects
    f = gzip.open(sys.argv[1], 'rb')
    tree = ET.parse(f)
    apps = []
    for app in tree.getroot():
        a = Application(None, cfg)
        for elem in app:
            if elem.tag == 'id':
                a.set_id(elem.text)
                a.type_id = elem.get('type')
                log.update_key(a.app_id_full)
                log.write(LoggerItem.INFO, "parsing")
            elif elem.tag == 'name':
                if elem.get(XML_LANG):
                    continue
                a.names['C'] = ensure_unicode(elem.text)
            elif elem.tag == 'summary':
                if elem.get(XML_LANG):
                    continue
                a.comments['C'] = ensure_unicode(elem.text)
            elif elem.tag == 'pkgname':
                a.pkgnames.append(ensure_unicode(elem.text))
            elif elem.tag == 'appcategories':
                for elem2 in elem:
                    a.categories.append(ensure_unicode(elem2.text))
            elif elem.tag == 'keywords':
                for elem2 in elem:
                    a.keywords.append(ensure_unicode(elem2.text))
            elif elem.tag == 'url':
                a.urls[elem.get('type')] = ensure_unicode(elem.text)
            elif elem.tag == 'compulsory_for_desktop':
                a.compulsory_for_desktop.append(ensure_unicode(elem.text))
            elif elem.tag == 'project_group':
                a.project_group = ensure_unicode(elem.text)
            elif elem.tag == 'description':
                description = ''
                if len(elem._children):
                    for elem2 in elem:
                        description += elem2.text + u' '
                else:
                    description = elem.text
                a.descriptions['C'] = ensure_unicode(description)
            elif elem.tag == 'metadata':
                for elem2 in elem:
                    a.metadata[elem2.get('key')] = elem2.text
            elif elem.tag == 'screenshots':
                if a.type_id == 'font':
                    continue
                for elem2 in elem:
                    if elem2.tag != 'screenshot':
                        continue
                    caption = None
                    for elem3 in elem2:
                        if elem3.tag == 'caption':
                            caption = elem3.text
                        elif elem3.tag == 'image':
                            if elem3.get('type') != 'source':
                                continue
                            s = Screenshot(a.app_id, None, caption)
                            s.basename = os.path.basename(elem3.text)
                            a.screenshots.append(s)
        apps.append(a)
    f.close()

    # build status page
    status = open('./screenshots/status.html', 'w')
    status.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 ' +
                 'Transitional//EN" ' +
                 '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')
    status.write('<html xmlns="http://www.w3.org/1999/xhtml">\n')
    status.write('<head>\n')
    status.write('<meta http-equiv="Content-Type" content="text/html; ' +
                          'charset=UTF-8" />\n')
    status.write('<title>Application Data Review</title>\n')
    status.write('</head>\n')
    status.write('<body>\n')

    status.write('<h1>Executive summary</h1>\n')
    status.write('<ul>\n')

    # long descriptions
    cnt = 0
    total = len(apps)
    for app in apps:
        if len(app.descriptions) > 0:
            cnt += 1
    tmp = 100 * cnt / total
    status.write("<li>Applications in Fedora with long descriptions: %i (%i%%)</li>" % (cnt, tmp))

    # keywords
    cnt = 0
    total = len(apps)
    for app in apps:
        if len(app.keywords) > 0:
            cnt += 1
    tmp = 100 * cnt / total
    status.write("<li>Applications in Fedora with keywords: %i (%i%%)</li>" % (cnt, tmp))

    # categories
    cnt = 0
    total = len(apps)
    for app in apps:
        if len(app.categories) > 0:
            cnt += 1
    tmp = 100 * cnt / total
    status.write("<li>Applications in Fedora with categories: %i (%i%%)</li>" % (cnt, tmp))

    # screenshots
    cnt = 0
    total = len(apps)
    for app in apps:
        if len(app.screenshots) > 0:
            cnt += 1
    tmp = 100 * cnt / total
    status.write("<li>Applications in Fedora with screenshots: %i (%i%%)</li>" % (cnt, tmp))

    # project apps with appdata
    for project_group in ['GNOME', 'KDE', 'XFCE']:
        cnt = 0
        total = 0
        for app in apps:
            if app.project_group != project_group:
                continue
            total += 1
            if len(app.screenshots) > 0 or len(app.descriptions) > 0:
                cnt += 1
        tmp = 0
        if total > 0:
            tmp = 100 * cnt / total
        status.write("<li>Applications in %s with AppData: %i (%i%%)</li>" % (project_group, cnt, tmp))
    status.write('</ul>\n')

    # write applications
    status.write('<h1>Applications</h1>\n')
    for app in apps:
        if app.type_id == 'font':
            continue
        if app.type_id == 'inputmethod':
            continue
        if app.type_id == 'codec':
            continue
        log.update_key(app.app_id_full)
        log.write(LoggerItem.INFO, "writing")
        try:
            status.write(_to_utf8(_to_html(app)))
        except AttributeError, e:
            log.write(LoggerItem.WARNING, "failed to write %s: %s" % (app, str(e)))
            continue
    status.write('</body>\n')
    status.write('</html>\n')
    status.close()

if __name__ == "__main__":
    main()
