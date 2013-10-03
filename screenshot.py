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
import hashlib
from PIL import Image

class Screenshot:

    def __init__(self, app_id, img):
        self._img = img
        self.width = img.size[0]
        self.height = img.size[1]
        self.basename = app_id
        self.basename += '-'
        self.basename += hashlib.md5(img.tostring()).hexdigest()
        self.basename += '.png'

    def dump_to_file(self, pathname, size=(0,0)):
        if size[0] > 0:
            #img = self._img.resize(size, Image.ANTIALIAS)
            img = self._img.copy()
            img.thumbnail(size, Image.ANTIALIAS)

            # if we didn't have the exact aspect ratio, pad with alpha
            if img.size != size:
                img2 = Image.new("RGBA", size)
                offset = ((size[0] - img.size[0]) / 2,
                          (size[1] - img.size[1]) / 2)
                img2.paste(img, offset, img);
                img = img2
        else:
            img = self._img
        img.save(pathname + '/' + self.basename, 'png')
