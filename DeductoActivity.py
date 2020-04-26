# -*- coding: utf-8 -*-
# Copyright (c) 2012 Walter Bender
# Ported to gtk3:
# Ignacio Rodríguez <ignaciorodriguez@sugarlabs.org>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('TelepathyGLib', '0.12')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import TelepathyGLib

from sugar3.activity import activity
from sugar3 import profile
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics.objectchooser import ObjectChooser

from toolbar_utils import button_factory, label_factory, separator_factory
from utils import json_load, json_dump

import dbus
from dbus.service import signal
from dbus.gi_service import ExportedGObject
from sugar3.presence import presenceservice
from sugar3.presence.tubeconn import TubeConnection

from gettext import gettext as _

from game import Game, LEVELS_TRUE, LEVELS_FALSE

import logging
_logger = logging.getLogger('deducto-activity')


SERVICE = 'in.seeta.Deducto'
IFACE = SERVICE
PATH = '/in/seeta/DeductoActivity'



class DeductoActivity(activity.Activity):
    """ Logic puzzle game """

    def __init__(self, handle):
        """ Initialize the toolbars and the game board """
        try:
            super(DeductoActivity, self).__init__(handle)
        except dbus.exceptions.DBusException as e:
            _logger.error(str(e))

        self.nick = profile.get_nick_name()
        if profile.get_color() is not None:
            self.colors = profile.get_color().to_string().split(',')
        else:
            self.colors = ['#A0FFA0', '#FF8080']

        self.level = 0
        self._correct = 0
        self._playing = True
        self._game_over = False

        self._python_code = None

        self._setup_toolbars()
        self._setup_dispatch_table()

        # Create a canvas
        canvas = Gtk.DrawingArea()
        canvas.set_size_request(Gdk.Screen.width(),
                                Gdk.Screen.height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._game = Game(canvas, parent=self, colors=self.colors)

        self._sharing = False
        self._initiating = False
        self._setup_presence_service()

        if 'level' in self.metadata:
            self.level = int(self.metadata['level'])
            self.status.set_label(_('Resuming level %d') % (self.level + 1))
            self._game.show_random()
        else:
            self._game.new_game()

    def _setup_toolbars(self):
        """ Setup the toolbars. """

        self.max_participants = 4

        toolbox = ToolbarBox()

        # Activity toolbar
        activity_button = ActivityToolbarButton(self)

        toolbox.toolbar.insert(activity_button, 0)
        activity_button.show()

        self.set_toolbar_box(toolbox)
        toolbox.show()
        self.toolbar = toolbox.toolbar

        self._new_game_button = button_factory(
            'new-game', self.toolbar, self._new_game_cb,
            tooltip=_('Start a new game.'))

        separator_factory(toolbox.toolbar, False, True)

        self._true_button = button_factory(
            'true', self.toolbar, self._true_cb,
            tooltip=_('The pattern matches the rule.'))

        self._false_button = button_factory(
            'false', self.toolbar, self._false_cb,
            tooltip=_('The pattern does not match the rule.'))

        separator_factory(toolbox.toolbar, False, True)

        self._example_button = button_factory(
            'example', self.toolbar, self._example_cb,
            tooltip=_('Explore some examples.'))

        self.status = label_factory(self.toolbar, '', width=300)

        separator_factory(toolbox.toolbar, True, False)

        self._gear_button = button_factory(
            'view-source', self.toolbar,
            self._gear_cb,
            tooltip=_('Load a custom level.'))

        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl>q'
        toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()

    def _new_game_cb(self, button=None):
        ''' Start a new game. '''
        if (not self._sharing) or self._initiating:
            self._game_over = False
            self._correct = 0
            self.level = 0
            if not self._playing:
                self._example_cb()
            self._game.new_game()
            if self._initiating:
                _logger.debug('sending new game and new grid')
                self._send_new_game()
                self._send_new_grid()
            self.status.set_label(_('Playing level %d') % (self.level + 1))
        else:
            self.status.set_label(_('Only sharer can start a new game.'))

    def _test_for_game_over(self):
        ''' If we are at maximum levels, the game is over '''
        if self.level == self._game.max_levels:
            self.level = 0
            self._game_over = True
            self.status.set_label(_('Game over.'))
        else:
            self.status.set_label(_('Playing level %d') % (self.level + 1))
            self._correct = 0
            if (not self._sharing) or self._initiating:
                self._game.show_random()
                if self._initiating:
                    self._send_new_grid()

    def _true_cb(self, button=None):
        ''' Declare pattern true or show an example of a true pattern. '''
        if self._game_over:
            if (not self._sharing) or self._initiating:
                self.status.set_label(_('Click on new game button to begin.'))
            else:
                self.status.set_label(_('Wait for sharer to start ' +
                                        'a new game.'))
            return
        if self._playing:
            if self._game.this_pattern:
                self._correct += 1
                if self._correct == 5:
                    self.level += 1
                    self._test_for_game_over()
                    self.metadata['level'] = str(self.level)
                else:
                    self.status.set_label(
                        _('%d correct answers.') % (self._correct))
                    if (not self._sharing) or self._initiating:
                        self._game.show_random()
                        if self._initiating:
                            self._send_new_grid()
            else:
                self.status.set_label(_('Pattern was false.'))
                self._correct = 0
            if (button is not None) and self._sharing:
                self._send_true_button_click()
        else:
            self._game.show_true()

    def _false_cb(self, button=None):
        ''' Declare pattern false or show an example of a false pattern. '''
        if self._game_over:
            if (not self._sharing) or self._initiating:
                self.status.set_label(_('Click on new game button to begin.'))
            else:
                self.status.set_label(_('Wait for sharer to start ' +
                                        'a new game.'))
            return
        if self._playing:
            if not self._game.this_pattern:
                self._correct += 1
                if self._correct == 5:
                    self.level += 1
                    self._test_for_game_over()
                else:
                    self.status.set_label(
                        _('%d correct answers.') % (self._correct))
                    if (not self._sharing) or self._initiating:
                        self._game.show_random()
                        if self._initiating:
                            self._send_new_grid()
            else:
                self.status.set_label(_('Pattern was true.'))
                self._correct = 0
            if (button is not None) and self._sharing:
                self._send_false_button_click()
        else:
            self._game.show_false()

    def _example_cb(self, button=None):
        ''' Show examples or resume play of current level. '''
        if self._playing:
            self._example_button.set_icon_name('resume-play')
            self._example_button.set_tooltip(_('Resume play'))
            self._true_button.set_tooltip(
                _('Show a pattern that matches the rule.'))
            self._false_button.set_tooltip(
                _('Show a pattern that does not match the rule.'))
            Button1 = '☑'
            Button2 = '☒'
            text = f"Explore patterns with the {Button1} and {Button2} buttons."
            self.status.set_label(_(text))
            self._playing = False
        else:
            self._example_button.set_icon_name('example')
            self._example_button.set_tooltip(_('Explore some examples.'))
            self._true_button.set_tooltip(
                _('The pattern matches the rule.'))
            self._false_button.set_tooltip(
                _('The pattern does not match the rule.'))
            self.status.set_label(_('Playing level %d') % (self.level + 1))
            self._playing = True
            self._correct = 0

    def _gear_cb(self, button=None):
        ''' Load a custom level. '''
        self.status.set_text(
            _('Load a "True" pattern generator from the journal'))
        self._chooser('org.laptop.Pippy',
                      self._load_python_code_from_journal)
        if self._python_code is None:
            return
        LEVELS_TRUE.append(self._python_code)
        self.status.set_text(
            _('Load a "False" pattern generator from the journal'))
        self._chooser('org.laptop.Pippy',
                      self._load_python_code_from_journal)
        LEVELS_FALSE.append(self._python_code)
        if self._python_code is None:
            return
        self.status.set_text(_('New level added'))
        self._game.max_levels += 1

    def _load_python_code_from_journal(self, dsobject):
        ''' Read the Python code from the Journal object '''
        self._python_code = None
        try:
            _logger.debug("opening %s " % dsobject.file_path)
            file_handle = open(dsobject.file_path, "r")
            self._python_code = file_handle.read()
            file_handle.close()
        except IOError:
            _logger.debug("couldn't open %s" % dsobject.file_path)

    def _chooser(self, filter, action):
        ''' Choose an object from the datastore and take some action '''
        chooser = None
        try:
            chooser = ObjectChooser(parent=self, what_filter=filter)
        except TypeError:
            chooser = ObjectChooser(
                None, self,
                Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
        if chooser is not None:
            try:
                result = chooser.run()
                if result == Gtk.ResponseType.ACCEPT:
                    dsobject = chooser.get_selected_object()
                    action(dsobject)
                    dsobject.destroy()
            finally:
                chooser.destroy()
                del chooser

    # Collaboration-related methods

    # The sharer sends patterns and everyone shares whatever vote is
    # cast first among all the sharer and joiners.

    def _setup_presence_service(self):
        ''' Setup the Presence Service. '''
        self.pservice = presenceservice.get_instance()
        self._initiating = None  # sharing (True) or joining (False)

        owner = self.pservice.get_owner()
        self.owner = owner
        self._share = ""
        self.connect('shared', self._shared_cb)
        self.connect('joined', self._joined_cb)

    def _shared_cb(self, activity):
        ''' Either set up initial share...'''
        self._new_tube_common(True)

    def _joined_cb(self, activity):
        ''' ...or join an exisiting share. '''
        self._new_tube_common(False)

    def _new_tube_common(self, sharer):
        ''' Joining and sharing are mostly the same... '''
        if self._shared_activity is None:
            _logger.debug("Error: Failed to share or join activity ... \
                _shared_activity is null in _shared_cb()")
            return

        self._initiating = sharer
        self._sharing = True

        self.conn = self._shared_activity.telepathy_conn
        self.tubes_chan = self._shared_activity.telepathy_tubes_chan
        self.text_chan = self._shared_activity.telepathy_text_chan

        self.tubes_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES].connect_to_signal(
            'NewTube', self._new_tube_cb)

        if sharer:
            _logger.debug('This is my activity: making a tube...')
        else:
            _logger.debug('I am joining an activity: waiting for a tube...')
            self.tubes_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES].ListTubes(
                reply_handler=self._list_tubes_reply_cb,
                error_handler=self._list_tubes_error_cb)

    def _list_tubes_reply_cb(self, tubes):
        ''' Reply to a list request. '''
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        ''' Log errors. '''
        _logger.debug('Error: ListTubes() failed: %s' % (e))

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        ''' Create a new tube. '''
        _logger.debug('New tube: ID=%d initator=%d type=%d service=%s \
params=%r state=%d' % (id, initiator, type, service, params, state))

        if (type == TelepathyGLib.TubeType.DBUS and service == SERVICE):
            if state == TelepathyGLib.TubeState.LOCAL_PENDING:
                self.tubes_chan[
                    TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES].AcceptDBusTube(id)

            tube_conn = TubeConnection(self.conn,
                                       self.tubes_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES],
                                       id,
                                       group_iface=self. text_chan[TelepathyGLib.IFACE_CHANNEL_INTERFACE_GROUP])

            self.chattube = ChatTube(tube_conn, self._initiating,
                                     self._event_received_cb)

    def _setup_dispatch_table(self):
        ''' Associate tokens with commands. '''
        self._processing_methods = {
            'n': [self._receive_new_game, 'new game'],
            'g': [self._receive_new_grid, 'get a new grid'],
            't': [self._receive_true_button_click, 'get a true button press'],
            'f': [self._receive_false_button_click, 'get a false ' +
                                                    'button press'],
        }

    def _event_received_cb(self, event_message):
        ''' Data from a tube has arrived. '''
        if len(event_message) == 0:
            return
        try:
            command, payload = event_message.split('|', 2)
        except ValueError:
            _logger.debug('Could not split event message %s' % (event_message))
            return
        self._processing_methods[command][0](payload)

    def _send_new_game(self):
        '''
        Send a new game message to all players
        (only sharer sends grids)
        '''
        self._send_event('n| ')

    def _receive_new_game(self, payload):
        ''' Receive a new game notification from the sharer. '''
        self._game_over = False
        self._correct = 0
        self.level = 0
        if not self._playing:
            self._example_cb()
        self.status.set_label(_('Playing level %d') % (self.level + 1))

    def _send_new_grid(self):
        ''' Send a new grid to all players (only sharer sends grids) '''
        self._send_event('g|%s' % (json_dump(self._game.save_grid())))

    def _receive_new_grid(self, payload):
        ''' Receive a grid from the sharer. '''
        (dot_list, boolean) = json_load(payload)
        self._game.restore_grid(dot_list, boolean)

    def _send_true_button_click(self):
        ''' Send a true click to all the players '''
        self._send_event('t|t')

    def _receive_true_button_click(self, payload):
        ''' When a button is clicked, everyone should react. '''
        self._playing = True
        self._true_cb()

    def _send_false_button_click(self):
        ''' Send a false click to all the players '''
        self._send_event('f|f')

    def _receive_false_button_click(self, payload):
        ''' When a button is clicked, everyone should react. '''
        self._playing = True
        self._false_cb()

    def _send_event(self, entry):
        ''' Send event through the tube. '''
        if hasattr(self, 'chattube') and self.chattube is not None:
            self.chattube.SendText(entry)


class ChatTube(ExportedGObject):
    ''' Class for setting up tube for sharing '''

    def __init__(self, tube, is_initiator, stack_received_cb):
        super(ChatTube, self).__init__(tube, PATH)
        self.tube = tube
        self.is_initiator = is_initiator  # Are we sharing or joining activity?
        self.stack_received_cb = stack_received_cb
        self.stack = ''

        self.tube.add_signal_receiver(self._send_stack_cb, 'SendText', IFACE,
                                      path=PATH, sender_keyword='sender')

    def _send_stack_cb(self, text, sender=None):
        if sender == self.tube.get_unique_name():
            return
        self.stack = text
        self.stack_received_cb(text)

    @signal(dbus_interface=IFACE, signature='s')
    def SendText(self, text):
        self.stack = text
