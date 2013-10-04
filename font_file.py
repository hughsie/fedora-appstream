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

from fontTools import ttLib

from PIL import Image, ImageOps, ImageFont, ImageDraw, ImageChops

# internal
from application import Application
from package import Package
from screenshot import Screenshot

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

def get_font_name(font):
    """Get the short name from the font's names table"""
    FONT_SPECIFIER_NAME_ID = 4
    FONT_SPECIFIER_FAMILY_ID = 1
    name = ""
    family = ""
    for record in font['name'].names:
        if record.nameID == FONT_SPECIFIER_NAME_ID and not name:
            if '\000' in record.string:
                name = unicode(record.string, 'utf-16-be').encode('utf-8')
            else:
                name = record.string
        elif record.nameID == FONT_SPECIFIER_FAMILY_ID and not family:
            if '\000' in record.string:
                family = unicode(record.string, 'utf-16-be').encode('utf-8')
            else:
                family = record.string
        if name and family:
            break
    return name, family

class FontFile(Application):

    def __init__(self, pkg, cfg):
        Application.__init__(self, pkg, cfg)
        self.type_id = 'font'
        self.categories = [ 'Addons', 'Fonts' ]
        self.thumbnail_screenshots = False

    def create_icon(self, font, filename):
        # create a large canvas to draw the font to -- we don't know the width yet
        img_size_temp = (256, 256)
        bg_color = (255,255,255)
        fg_color = (0,0,0)
        im_temp = Image.new("RGBA", img_size_temp)
        draw = ImageDraw.Draw(im_temp)
        font = ImageFont.truetype(font, 160)
        draw.text((20, 20), "Aa", fg_color, font=font)

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
        img = img.resize((64,64), Image.ANTIALIAS)
        img.save(filename, 'png')
        return True

    def create_screenshot(self, font_file, filename):

        # create a large canvas to draw the font to
        img_size_temp = (2560, 256)
        bg_color = (255,255,255)
        fg_color = (0,0,0)
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
        im_temp = autocrop(im_temp, (255,255,255))
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
        self.screenshots.append(Screenshot(self.app_id, img))

        return True

    def parse_file(self, f):

        tt = ttLib.TTFont(f)
        self.names['C'] = get_font_name(tt)[0]
        self.comments['C'] = "A font family from " + get_font_name(tt)[1]
        icon_fullpath = './icons/' + self.app_id + '.png'

        # generate a preview icon
        if not self.create_icon(f, icon_fullpath):
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
