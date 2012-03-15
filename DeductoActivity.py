# -*- coding: utf-8 -*-
#Copyright (c) 2012 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


import gtk

from sugar.activity import activity
from sugar import profile
try:
    from sugar.graphics.toolbarbox import ToolbarBox
    _have_toolbox = True
except ImportError:
    _have_toolbox = False

if _have_toolbox:
    from sugar.activity.widgets import ActivityToolbarButton
    from sugar.activity.widgets import StopButton
from sugar.graphics.objectchooser import ObjectChooser

from toolbar_utils import button_factory, label_factory, separator_factory
from utils import json_load, json_dump

import telepathy
import dbus
from dbus.service import signal
from dbus.gobject_service import ExportedGObject
from sugar.presence import presenceservice
from sugar.presence.tubeconn import TubeConnection

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
        except dbus.exceptions.DBusException, e:
            _logger.error(str(e))

        self.nick = profile.get_nick_name()
        if profile.get_color() is not None:
            self.colors = profile.get_color().to_string().split(',')
        else:
            self.colors = ['#A0FFA0', '#FF8080']

        self.playing = True
        self.level = 0
        self.correct = 0
        self.game_over = False

        self._setup_toolbars(_have_toolbox)
        self._setup_dispatch_table()

        # Create a canvas
        canvas = gtk.DrawingArea()
        canvas.set_size_request(gtk.gdk.screen_width(), \
                                gtk.gdk.screen_height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._game = Game(canvas, parent=self, colors=self.colors)
        self._setup_presence_service()

        if 'level' in self.metadata:
            self.level = int(self.metadata['level'])
            self.status.set_label(_('Resuming level %d') % (self.level + 1))
            self._game.show_random()
        else:
            self._game.new_game()

    def _setup_toolbars(self, have_toolbox):
        """ Setup the toolbars. """

        self.max_participants = 0

        if have_toolbox:
            toolbox = ToolbarBox()

            # Activity toolbar
            activity_button = ActivityToolbarButton(self)

            toolbox.toolbar.insert(activity_button, 0)
            activity_button.show()

            self.set_toolbar_box(toolbox)
            toolbox.show()
            self.toolbar = toolbox.toolbar

        else:
            # Use pre-0.86 toolbar design
            games_toolbar = gtk.Toolbar()
            toolbox = activity.ActivityToolbox(self)
            self.set_toolbox(toolbox)
            toolbox.add_toolbar(_('Game'), games_toolbar)
            toolbox.show()
            toolbox.set_current_toolbar(1)
            self.toolbar = games_toolbar

        self._new_game_button = button_factory(
            'new-game', self.toolbar, self._new_game_cb,
            tooltip=_('Start a new game.'))

        if _have_toolbox:
            separator_factory(toolbox.toolbar, False, True)

        self._true_button = button_factory(
            'true', self.toolbar, self._true_cb,
            tooltip=_('The pattern matches the rule.'))

        self._false_button = button_factory(
            'false', self.toolbar, self._false_cb,
            tooltip=_('The pattern does not match the rule.'))

        if _have_toolbox:
            separator_factory(toolbox.toolbar, False, True)

        self._example_button = button_factory(
            'example', self.toolbar, self._example_cb,
            tooltip=_('Explore some examples.'))

        self.status = label_factory(self.toolbar, '')

        if _have_toolbox:
            separator_factory(toolbox.toolbar, True, False)

        self._gear_button = button_factory(
            'view-source', self.toolbar,
            self._gear_cb,
            tooltip=_('Load a custom level.'))

        if _have_toolbox:
            stop_button = StopButton(self)
            stop_button.props.accelerator = '<Ctrl>q'
            toolbox.toolbar.insert(stop_button, -1)
            stop_button.show()

    def _new_game_cb(self, button=None):
        ''' Start a new game. '''
        self.game_over = False
        self.correct = 0
        self.level = 0
        self._game.new_game()

    def _test_for_game_over(self):
        ''' If we are at maximum levels, the game is over '''
        if self.level == self._game.max_levels:
            self.status.set_label(_('Game over.'))
            self.level = 0
            self.game_over = True
        else:
            self.status.set_label(_('Playing level %d') % (self.level + 1))
            self.correct = 0
            self._game.show_random()

    def _true_cb(self, button=None):
        ''' Declare pattern true or show an example of a true pattern. '''
        if self.game_over:
            self.status.set_label(_('Click on new game button to begin.'))
            return
        if self.playing:
            if self._game.this_pattern:
                self.correct += 1
                if self.correct == 5:
                    self.level += 1
                    self._test_for_game_over()
                    self.metadata['level'] = str(self.level)
                else:
                    self.status.set_label(
                        _('%d correct answers.') % (self.correct))
                    self._game.show_random()
            else:
                self.status.set_label(_('Pattern was false.'))
                self.correct = 0
        else:
            self._game.show_true()

    def _false_cb(self, button=None):
        ''' Declare pattern false or show an example of a false pattern. '''
        if self.game_over:
            self.status.set_label(_('Click on new game button to begin.'))
            return
        if self.playing:
            if not self._game.this_pattern:
                self.correct += 1
                if self.correct == 5:
                    self.level += 1
                    self._test_for_game_over()
                else:
                    self.status.set_label(
                        _('%d correct answers.') % (self.correct))
                    self._game.show_random()
            else:
                self.status.set_label(_('Pattern was true.'))
                self.correct = 0
        else:
            self._game.show_false()

    def _example_cb(self, button=None):
        ''' Show examples or resume play of current level. '''
        if self.playing:
            self._example_button.set_icon('resume-play')
            self._example_button.set_tooltip(_('Resume play'))
            self._true_button.set_tooltip(
                _('Show a pattern that matches the rule.'))
            self._false_button.set_tooltip(
                _('Show a pattern that does not match the rule.'))
            self.status.set_label(
                _('Explore patterns with the ☑ and ☒ buttons'))
            self.playing = False
        else:
            self._example_button.set_icon('example')
            self._example_button.set_tooltip(_('Explore some examples.'))
            self._true_button.set_tooltip(
                _('The pattern matches the rule.'))
            self._false_button.set_tooltip(
                _('The pattern does not match the rule.'))
            self.status.set_label(_('playing level %s') % (self.level))
            self.playing = True
            self.correct = 0

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
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        if chooser is not None:
            try:
                result = chooser.run()
                if result == gtk.RESPONSE_ACCEPT:
                    dsobject = chooser.get_selected_object()
                    action(dsobject)
                    dsobject.destroy()
            finally:
                chooser.destroy()
                del chooser

    # Collaboration-related methods

    def _setup_presence_service(self):
        ''' Setup the Presence Service. '''
        self.pservice = presenceservice.get_instance()
        self.initiating = None  # sharing (True) or joining (False)

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

        self.initiating = sharer
        self.waiting_for_hand = not sharer

        self.conn = self._shared_activity.telepathy_conn
        self.tubes_chan = self._shared_activity.telepathy_tubes_chan
        self.text_chan = self._shared_activity.telepathy_text_chan

        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal(
            'NewTube', self._new_tube_cb)

        if sharer:
            _logger.debug('This is my activity: making a tube...')
            id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
                SERVICE, {})
        else:
            _logger.debug('I am joining an activity: waiting for a tube...')
            self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
                reply_handler=self._list_tubes_reply_cb,
                error_handler=self._list_tubes_error_cb)
        self._game.set_sharing(True)

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

        if (type == telepathy.TUBE_TYPE_DBUS and service == SERVICE):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[ \
                              telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(id)

            tube_conn = TubeConnection(self.conn,
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES], id, \
                group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])

            self.chattube = ChatTube(tube_conn, self.initiating, \
                self.event_received_cb)

    def _setup_dispatch_table(self):
        ''' Associate tokens with commands. '''
        self._processing_methods = {
            'n': [self._receive_new_game, 'get a new game grid'],
            'p': [self._receive_dot_click, 'get a dot click'],
            }

    def event_received_cb(self, event_message):
        ''' Data from a tube has arrived. '''
        if len(event_message) == 0:
            return
        try:
            command, payload = event_message.split('|', 2)
        except ValueError:
            _logger.debug('Could not split event message %s' % (event_message))
            return
        self._processing_methods[command][0](payload)

    def send_new_game(self):
        ''' Send a new grid to all players '''
        self.send_event('n|%s' % (json_dump(self._game.save_game())))

    def _receive_new_game(self, payload):
        ''' Sharer can start a new game. '''
        (dot_list, move_list) = json_load(payload)
        self._game.restore_game(dot_list, move_list)

    def send_dot_click(self, dot):
        ''' Send a dot click to all the players '''
        self.send_event('p|%s' % (json_dump(dot)))

    def _receive_dot_click(self, payload):
        ''' When a dot is clicked, everyone should change its color. '''
        dot = json_load(payload)
        self._game.remote_button_press(dot)

    def send_event(self, entry):
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

        self.tube.add_signal_receiver(self.send_stack_cb, 'SendText', IFACE,
                                      path=PATH, sender_keyword='sender')

    def send_stack_cb(self, text, sender=None):
        if sender == self.tube.get_unique_name():
            return
        self.stack = text
        self.stack_received_cb(text)

    @signal(dbus_interface=IFACE, signature='s')
    def SendText(self, text):
        self.stack = text
