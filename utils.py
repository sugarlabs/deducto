# Copyright (c) 2011 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


from io import StringIO
import json


def json_load(text):
    """ Load JSON data. """
    listdata = json.read(text)
    return listdata


def json_dump(data):
    """ Save data. """
    return json.write(data) 
