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

import sys
import os
import operator

from fontTools import ttLib

from PIL import Image, ImageOps, ImageFont, ImageDraw, ImageChops

# internal
from application import Application
from package import Package
from screenshot import Screenshot
from logger import LoggerItem

def _get_sortable_idx(font_str):
    idx = 0
    if font_str.find('Ita') != -1:
        idx += 1
    if font_str.find('Bol') != -1:
        idx += 2
    return idx

class FontFileFilter():

    def merge(self, valid_apps):
        """
        Merge fonts with the same family name.
        """
        font_families = {}
        unique_apps = []
        for app in valid_apps:
            if app.type_id != 'font':
                unique_apps.append(app)
                continue

            # sort in a sane way
            app.screenshots[0].sort_id = _get_sortable_idx(app.metadata['FontSubFamily'])

            # steal the screenshot if the family is the same
            font_family = app.metadata['FontFamily']
            if font_family not in font_families:
                font_families[font_family] = app
                unique_apps.append(app)
            else:
                found = font_families[font_family]
                found.screenshots.append(app.screenshots[0])
                if app.pkgnames[0] not in found.pkgnames:
                    found.pkgnames.append(app.pkgnames[0])

                # the lower index name is better
                if _get_sortable_idx(app.app_id) < _get_sortable_idx(found.app_id):
                    found.set_id(app.app_id_full)
                    os.remove("./icons/%s.png" % found.icon)
                    found.icon = app.icon
                else:
                    os.remove("./icons/%s.png" % app.icon)

                # resort the screenshots
                found.screenshots = sorted(found.screenshots, key=operator.attrgetter('sort_id'))

        # these are no longer valid as we're merged them together
        for app in unique_apps:
            if app.type_id == 'font':
                del app.metadata['FontFamily']
                del app.metadata['FontFullName']
                del app.metadata['FontSubFamily']

        return unique_apps

def autocrop(im, alpha):
    if alpha:
        bg = Image.new("RGBA", im.size, alpha)
    else:
        bg = Image.new("RGBA", im.size)
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return None

def _decode_record(record):
    text = ''
    if '\000' in record.string:
        text = unicode(record.string, 'utf-16-be').encode('utf-8')
    else:
        text = record.string
    return text

def get_font_metadata(font):
    """Get the short name from the font's names table"""

    # these are specified in http://stsf.sourceforge.net/st/sttypes_8h.html#a231
    FONT_SPECIFIER_FONTFAMILY = 1
    FONT_SPECIFIER_FONTSUBFAMILY = 2
    FONT_SPECIFIER_FULLFONTNAME = 4

    # extract
    metadata = {}
    for record in font['name'].names:
        if record.nameID == FONT_SPECIFIER_FONTFAMILY and 'FontFamily' not in metadata:
            metadata['FontFamily'] = _decode_record(record)
        elif record.nameID == FONT_SPECIFIER_FONTSUBFAMILY and 'FontSubFamily' not in metadata:
            metadata['FontSubFamily'] = _decode_record(record)
        elif record.nameID == FONT_SPECIFIER_FULLFONTNAME and 'FontFullName' not in metadata:
            metadata['FontFullName'] = _decode_record(record)
    return metadata

class FontFile(Application):

    def __init__(self, pkg, cfg):
        Application.__init__(self, pkg, cfg)
        self.type_id = 'font'
        self.categories = [ 'Addons', 'Fonts' ]
        self.thumbnail_screenshots = False

    def get_font_chars(self, font):

        # get two UTF-8 chars that are present in the set
        glyphs = font['hmtx'].metrics
        if all(glyph in glyphs for glyph in ['A', 'a']):
            return 'Aa'
        if all(glyph in glyphs for glyph in ['one', 'two']):
            return "12"
        if all(glyph in glyphs for glyph in ['mail', 'thumbs-down']):
            return u"📤👎"
        if all(glyph in glyphs for glyph in ['Lambda', 'Sigma']):
            return u"ΛΣ"
        if all(glyph in glyphs for glyph in ['hamza_medial', 'veh.medi']):
            return u"ڤء"
        if all(glyph in glyphs for glyph in ['shatamil', 'uutamil']):
            return u"ஶூ"
        if all(glyph in glyphs for glyph in ['ashortdeva', 'ocandranuktadeva']):
            return u"आऴ"
        if all(glyph in glyphs for glyph in ['alef', 'pe']):
            return u"פא"
        if all(glyph in glyphs for glyph in ['earth', 'gemini']):
            return u"♁♊"
        if all(glyph in glyphs for glyph in ['lessnotequal', 'emptyset']):
            return u"≨∅"
        if all(glyph in glyphs for glyph in ['nabla', 'existential']):
            return u"∇∃"
        if all(glyph in glyphs for glyph in ['ttho', 'pho']):
            return u"ꠑꠚ"
        if all(glyph in glyphs for glyph in ['tilde', 'dagger']):
            return u"†~"

        # we failed, so show a list of glyphs we could use in the error
        banned_glyphs = ['space', 'nonmarkingreturn']
        possible_glyphs = []
        for glyph in glyphs:
            if glyph.startswith('uni'):
                continue
            if glyph in banned_glyphs:
                continue
            if not any((c in set('0123456789.-')) for c in glyph):
                possible_glyphs.append(glyph)
        if len(possible_glyphs) == 0:
            self.log.write(LoggerItem.WARNING, "no suitable glyphs found")
        else:
            possible_glyphs.sort()
            self.log.write(LoggerItem.WARNING, "no suitable glyphs found: %s" %
                           ', '.join(possible_glyphs))
        return None

    def create_icon(self, font, tt, filename):
        # create a large canvas to draw the font to -- we don't know the width yet
        img_size_temp = (256, 256)
        fg_color = (0, 0, 0)
        im_temp = Image.new("RGBA", img_size_temp)
        draw = ImageDraw.Draw(im_temp)
        font = ImageFont.truetype(font, 160)

        # these fonts take AAAGGES to decompile
        if self.app_id in [ 'batang', 'dotum', 'gulim', 'hline'] :
            chars = 'Aa'
        else:
            chars = self.get_font_chars(tt)
        if not chars:
            return False
        draw.text((20, 20), chars, fg_color, font=font)

        # crop to the smallest size
        im_temp = autocrop(im_temp, None)
        if not im_temp:
            return False

        # create a new image and paste the cropped image into the center
        img = Image.new('RGBA', img_size_temp)
        img_w, img_h = im_temp.size
        bg_w, bg_h = img.size
        offset = ((bg_w - img_w) / 2, (bg_h - img_h) / 2)
        img.paste(im_temp, offset)

        # rescale the image back to 64x64
        img = img.resize((64, 64), Image.ANTIALIAS)
        img.save(filename, 'png')
        return True

    def create_screenshot(self, font_file, filename):

        # create a large canvas to draw the font to
        img_size_temp = (2560, 256)
        bg_color = (255, 255, 255)
        fg_color = (0, 0, 0)
        border_width = 5
        basewidth = self.cfg.get_int('FontScreenshotWidth')

        text = 'How quickly daft jumping zebras vex.'
        im_temp = Image.new("RGBA", img_size_temp, bg_color)
        draw = ImageDraw.Draw(im_temp)
        font = ImageFont.truetype(font_file, 40)
        draw.text((20, 20), text, fg_color, font=font)

        font = ImageFont.truetype(font_file, 60)
        draw.text((20, 70), text, fg_color, font=font)

        font = ImageFont.truetype(font_file, 80)
        draw.text((20, 140), text, fg_color, font=font)

        # crop to the smallest size
        im_temp = autocrop(im_temp, (255, 255, 255))
        if not im_temp:
            return False

        # create a new image and paste the cropped image with a border
        img = Image.new('RGBA', (im_temp.size[0] + border_width * 2,
                                 im_temp.size[1] + border_width * 2), bg_color)
        img.paste(im_temp, (border_width, border_width))

        # resize to a known width */
        wpercent = (basewidth / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), Image.ANTIALIAS)
        caption = self.metadata['FontSubFamily']
        self.screenshots.append(Screenshot(self.app_id, img, caption))

        return True

    def parse_file(self, f):

        tt = ttLib.TTFont(f, recalcBBoxes=False)
        metadata = get_font_metadata(tt)
        self.metadata.update(metadata)
        self.names['C'] = metadata['FontFamily']
        self.comments['C'] = "A font from " + metadata['FontFamily']
        icon_fullpath = './icons/' + self.app_id + '.png'

        # generate a preview icon
        if not self.create_icon(f, tt, icon_fullpath):
            return False
        self.icon = self.app_id
        self.cached_icon = True

        # generate a screenshot
        icon_fullpath = './screenshots/' + self.app_id + '.png'
        if not self.create_screenshot(f, icon_fullpath):
            return False

        return True

def main():
    pkg = Package(sys.argv[1])
    app = FontFile(pkg, None)
    app.app_id = 'test'
    f = open('/tmp/test.xml', 'w')
    app.write(f)
    f.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
