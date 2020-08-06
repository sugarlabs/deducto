# -*- coding: utf-8 -*-
# Copyright (c) 2012 Walter Bender
# Ported to Gtk3:
# Ignacio Rodríguez <ignaciorodriguez@sugarlabs.org>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

from gi.repository import Gdk, GdkPixbuf, Gtk
import cairo

from random import uniform

from sprites import Sprites, Sprite

import traceback

import logging
_logger = logging.getLogger('reflection-activity')

try:
    from sugar3.graphics import style
    GRID_CELL_SIZE = style.GRID_CELL_SIZE
except ImportError:
    GRID_CELL_SIZE = 0


LEVELS_TRUE = ['def generate_pattern(self):\n\
    # Level 1: Center dot is True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    dot_list[12] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 2: Corners match\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    dot_list[4] = dot_list[0]\n\
    dot_list[20] = dot_list[0]\n\
    dot_list[24] = dot_list[0]\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 3: more than 12 True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    def dot_sum(dot_list):\n\
       sum = 0\n\
       for i in dot_list:\n\
           sum += i\n\
       return sum\n\
    while dot_sum(dot_list) < 13:\n\
       dot_list[int(uniform(0, 25))] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 4: even number of True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    def dot_sum(dot_list):\n\
       sum = 0\n\
       for i in dot_list:\n\
           sum += i\n\
       return sum\n\
    while dot_sum(dot_list) % 2 == 1:\n\
       dot_list[int(uniform(0, 25))] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 5: diagonal is True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    if int(uniform(0, 2)) == 1:\n\
        dot_list[0] = 1\n\
        dot_list[6] = 1\n\
        dot_list[12] = 1\n\
        dot_list[18] = 1\n\
        dot_list[24] = 1\n\
    else:\n\
        dot_list[4] = 1\n\
        dot_list[8] = 1\n\
        dot_list[12] = 1\n\
        dot_list[16] = 1\n\
        dot_list[20] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 6: True above each False\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    for i in range(20):\n\
        j = 24 - i\n\
        if dot_list[j] == 0:\n\
            dot_list[j - 5] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 7: True in each row\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    def row_sum(dot_list, row):\n\
       sum = 0\n\
       for i in range(5):\n\
           sum += dot_list[row * 5 + i]\n\
       return sum\n\
    for y in range(5):\n\
        if row_sum(dot_list, y) == 0:\n\
            dot_list[y * 5 + int(uniform(0, 5))] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 8: True path to center\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    dot_list[12] = 1\n\
    paths = [[2, 7], [10, 11], [13, 14], [17, 22]]\n\
    n = int(uniform(0, 4))\n\
    dot_list[paths[n][0]] = 1\n\
    dot_list[paths[n][1]] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 9: more True on top half than on bottom half\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    def top_sum(dot_list):\n\
       sum = 0\n\
       for i in range(10):\n\
           sum += dot_list[i]\n\
       return sum\n\
    def bot_sum(dot_list):\n\
       sum = 0\n\
       for i in range(10):\n\
           sum += dot_list[i + 15]\n\
       return sum\n\
    while top_sum(dot_list) < (bot_sum(dot_list) + 1):\n\
       dot_list[int(uniform(0, 10))] = 1\n\
    return dot_list\n',
               'def generate_pattern(self):\n\
    # Level 10: smilely face\n\
    dot_list = []\n\
    parity = int(uniform(0, 2))\n\
    for i in range(25):\n\
        dot_list.append(parity)\n\
    dot_list[6] = 1 - parity\n\
    dot_list[8] = 1 - parity\n\
    dot_list[15] = 1 - parity\n\
    dot_list[19] = 1 - parity\n\
    dot_list[21] = 1 - parity\n\
    dot_list[22] = 1 - parity\n\
    dot_list[23] = 1 - parity\n\
    return dot_list\n'
               ]
LEVELS_FALSE = ['def generate_pattern(self):\n\
    # Level 1: Center dot is False\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    dot_list[12] = 0\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 2: Corners do not match\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    n = int(uniform(0, 3))\n\
    corner = [4, 20, 24]\n\
    dot_list[corner[n]] = 1 - dot_list[0]\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 3: less than 13 True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    def dot_sum(dot_list):\n\
       sum = 0\n\
       for i in dot_list:\n\
           sum += i\n\
       return sum\n\
    while dot_sum(dot_list) > 12:\n\
       dot_list[int(uniform(0, 25))] = 0\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 4: odd number of True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    def dot_sum(dot_list):\n\
       sum = 0\n\
       for i in dot_list:\n\
           sum += i\n\
       return sum\n\
    while dot_sum(dot_list) % 2 == 0:\n\
       dot_list[int(uniform(0, 25))] = 1\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 5: diagonal is True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    if int(uniform(0, 2)) == 1:\n\
        dot_list[0] = 1\n\
        dot_list[6] = 1\n\
        dot_list[12] = 1\n\
        dot_list[18] = 1\n\
        dot_list[24] = 1\n\
        n = int(uniform(0, 5))\n\
        diagonal = [0, 6, 12, 18, 24]\n\
        dot_list[diagonal[n]] = 1 - dot_list[0]\n\
    else:\n\
        dot_list[4] = 1\n\
        dot_list[8] = 1\n\
        dot_list[12] = 1\n\
        dot_list[16] = 1\n\
        dot_list[20] = 1\n\
        n = int(uniform(0, 5))\n\
        diagonal = [4, 8, 12, 16, 20]\n\
        dot_list[diagonal[n]] = 1 - dot_list[0]\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 6: True to right of each False\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    for y in range(5):\n\
        for x in range(4):\n\
            j = y * 5 + x\n\
            if dot_list[j] == 0:\n\
                dot_list[j + 1] = 1\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 7: One row with no True\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    y = int(uniform(0, 5))\n\
    for i in range(5):\n\
        dot_list[y * 5 + i] = 0\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 8: No True path to center\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    dot_list[12] = 1\n\
    paths = [[2, 7], [10, 11], [13, 14], [17, 22]]\n\
    for n in range(4):\n\
        if int(uniform(0, 2)) == 1:\n\
            dot_list[paths[n][0]] = 1\n\
            dot_list[paths[n][1]] = 0\n\
        else:\n\
            dot_list[paths[n][0]] = 0\n\
            dot_list[paths[n][1]] = 1\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 9: more True on bottom half than on top half\n\
    dot_list = []\n\
    for i in range(25):\n\
        dot_list.append(int(uniform(0, 2)))\n\
    def top_sum(dot_list):\n\
       sum = 0\n\
       for i in range(10):\n\
           sum += dot_list[i]\n\
       return sum\n\
    def bot_sum(dot_list):\n\
       sum = 0\n\
       for i in range(10):\n\
           sum += dot_list[i + 15]\n\
       return sum\n\
    while (top_sum(dot_list) + 1) > bot_sum(dot_list):\n\
       dot_list[int(uniform(0, 10)) + 15] = 1\n\
    return dot_list\n',
                'def generate_pattern(self):\n\
    # Level 10: frowny face\n\
    dot_list = []\n\
    parity = int(uniform(0, 2))\n\
    for i in range(25):\n\
        dot_list.append(parity)\n\
    dot_list[6] = 1 - parity\n\
    dot_list[8] = 1 - parity\n\
    dot_list[16] = 1 - parity\n\
    dot_list[17] = 1 - parity\n\
    dot_list[18] = 1 - parity\n\
    dot_list[20] = 1 - parity\n\
    dot_list[24] = 1 - parity\n\
    return dot_list\n']

# Grid dimensions
GRID = 5
WHITE = 2
DOT_SIZE = 80


class Game():

    def __init__(self, canvas, parent=None, colors=['#A0FFA0', '#FF8080']):
        self._activity = parent
        self._colors = [colors[0]]
        self._colors.append(colors[1])

        self._canvas = canvas
        if parent is not None:
            parent.show_all()
            self._parent = parent

        self._canvas.connect("draw", self.__draw_cb)

        self._width = Gdk.Screen.width()
        self._height = Gdk.Screen.height() - (GRID_CELL_SIZE * 1.5)
        self._scale = self._width / (10 * DOT_SIZE * 1.2)
        self._dot_size = int(DOT_SIZE * self._scale)
        self._space = int(self._dot_size / 5.)
        self.max_levels = len(LEVELS_TRUE)
        self.this_pattern = False

        # Generate the sprites we'll need...
        self._sprites = Sprites(self._canvas)
        self._dots = []
        self._generate_grid()

    def _generate_grid(self):
        ''' Make a new set of dots for a grid of size edge '''
        i = 0
        for y in range(GRID):
            for x in range(GRID):
                xoffset = int((self._width - GRID * self._dot_size -
                               (GRID - 1) * self._space) / 2.)
                if i < len(self._dots):
                    self._dots[i].move(
                        (xoffset + x * (self._dot_size + self._space),
                         y * (self._dot_size + self._space) + self._space))
                else:
                    self._dots.append(
                        Sprite(self._sprites,
                               xoffset + x * (self._dot_size + self._space),
                               y * (self._dot_size + self._space) +
                               self._space,
                               self._new_dot(self._colors[0])))
                self._dots[i].type = 0
                self._dots[-1].set_label_attributes(40)
                i += 1

    def show(self, dot_list):
        for i in range(GRID * GRID):
            self._dots[i].set_shape(self._new_dot(self._colors[dot_list[i]]))
            self._dots[i].type = dot_list[i]

    def show_true(self):
        self.show(self._generate_pattern(LEVELS_TRUE[self._activity.level]))
        self.this_pattern = True

    def show_false(self):
        self.show(self._generate_pattern(LEVELS_FALSE[self._activity.level]))
        self.this_pattern = False

    def show_random(self):
        ''' Fill the grid with a true or false pattern '''
        if int(uniform(0, 2)) == 0:
            self.show_true()
        else:
            self.show_false()

    def _initiating(self):
        return self._activity._collab.props.leader

    def new_game(self):
        ''' Start a new game. '''
        self.show_random()

    def restore_grid(self, dot_list, boolean, color):
        ''' Restore a grid from the share '''
        self.show(dot_list)
        self.this_pattern = boolean
        self._colors = color

    def save_grid(self):
        ''' Return dot list for sharing '''
        dot_list = []
        for dot in self._dots:
            dot_list.append(dot.type)
        return dot_list, self.this_pattern, self._colors

    def _grid_to_dot(self, pos):
        ''' calculate the dot index from a column and row in the grid '''
        return pos[0] + pos[1] * GRID

    def _dot_to_grid(self, dot):
        ''' calculate the grid column and row for a dot '''
        return [dot % GRID, int(dot // GRID)]

    def _set_label(self, string):
        ''' Set the label in the toolbar or the window frame. '''
        self._activity.status.set_label(string)

    def _generate_pattern(self, f):
        ''' Run Python code passed as argument '''
        userdefined = {}
        try:
            exec(f, globals(), userdefined)
            return userdefined['generate_pattern'](self)
        except ZeroDivisionError as e:
            self._set_label('Python zero-divide error: %s' % (str(e)))
        except ValueError as e:
            self._set_label('Python value error: %s' % (str(e)))
        except SyntaxError as e:
            self._set_label('Python syntax error: %s' % (str(e)))
        except NameError as e:
            self._set_label('Python name error: %s' % (str(e)))
        except OverflowError as e:
            self._set_label('Python overflow error: %s' % (str(e)))
        except TypeError as e:
            self._set_label('Python type error: %s' % (str(e)))
        except BaseException:
            self._set_label('Python error')
        traceback.print_exc()
        return None

    def __draw_cb(self, canvas, cr):
        self._sprites.redraw_sprites(cr=cr)

    def do_expose_event(self, event):
        ''' Handle the expose-event by drawing '''
        # Restrict Cairo to the exposed area
        cr = self._canvas.window.cairo_create()
        cr.rectangle(event.area.x, event.area.y,
                     event.area.width, event.area.height)
        cr.clip()
        # Refresh sprite list
        if cr is not None:
            self._sprites.redraw_sprites(cr=cr)

    def _destroy_cb(self, win, event):
        Gtk.main_quit()

    def _new_dot(self, color):
        ''' generate a dot of a color color '''
        self._dot_cache = {}
        if color not in self._dot_cache:
            self._stroke = color
            self._fill = color
            self._svg_width = self._dot_size
            self._svg_height = self._dot_size
            pixbuf = svg_str_to_pixbuf(
                self._header() +
                self._circle(self._dot_size / 2., self._dot_size / 2.,
                             self._dot_size / 2.) +
                self._footer())

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         self._svg_width, self._svg_height)
            context = cairo.Context(surface)
            Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
            context.rectangle(0, 0, self._svg_width, self._svg_height)
            context.fill()
            self._dot_cache[color] = surface

        return self._dot_cache[color]

    def _header(self):
        return '<svg\n' + 'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
            'xmlns="http://www.w3.org/2000/svg"\n' + \
            'xmlns:xlink="http://www.w3.org/1999/xlink"\n' + \
            'version="1.1"\n' + 'width="' + str(self._svg_width) + '"\n' + \
            'height="' + str(self._svg_height) + '">\n'

    def _circle(self, r, cx, cy):
        return '<circle style="fill:' + str(self._fill) + ';stroke:' + \
            str(self._stroke) + ';" r="' + str(r - 0.5) + '" cx="' + \
            str(cx) + '" cy="' + str(cy) + '" />\n'

    def _footer(self):
        return '</svg>\n'


def svg_str_to_pixbuf(svg_string):
    """ Load pixbuf from SVG string """
    pl = GdkPixbuf.PixbufLoader.new_with_type('svg')
    pl.write(svg_string.encode('utf-8'))
    pl.close()
    pixbuf = pl.get_pixbuf()
    return pixbuf
