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

import os
import sys

class Logger(object):

    def __init__(self, filename=None):
        self.terminal = sys.stdout
        if filename:
            if not os.path.exists('./logs'):
                os.makedirs('./logs')
            self.log = open('./logs/' + filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

class LoggerItem(object):

    INFO = 'INFO'
    WARNING = 'WARNING'
    FAILED = 'FAILED'

    def __init__(self, key=''):
        self.key = key

    def update_key(self, key=''):
        self.key = key

    def write(self, enum, msg):
        print enum.ljust(10) + self.key.ljust(50) + ' ' + msg
