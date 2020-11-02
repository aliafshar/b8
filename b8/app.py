# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
gi.require_version("Vte", "2.91")

import os, sys
from gi.repository import GLib, Gio, Gtk, Gdk

from b8 import logs, configs, vim, files, buffers, terminals


class B8Window(Gtk.ApplicationWindow, logs.LoggerMixin):

  __gtype_name__ = 'b8-app-window'

  def __init__(self, b8):
    Gtk.ApplicationWindow.__init__(self, application=b8)
    logs.LoggerMixin.__init__(self)
    self.b8 = b8
    self.set_icon_name('media-seek-forward')
    self.set_title('b8 ♡ u')
    hsplit = Gtk.HPaned()
    lsplit = Gtk.VPaned()
    rsplit = Gtk.VPaned()
    self.rsplit = rsplit

    lsplit.pack1(self.b8.buffers, resize=True, shrink=False)
    lsplit.pack2(self.b8.files, resize=True, shrink=False)
    hsplit.pack1(lsplit, resize=True, shrink=False)
    hsplit.pack2(rsplit, resize=True, shrink=False)
    hsplit.set_property('position', 250)
    self.add(hsplit)

    rsplit.set_property('position', 600)
    rsplit.pack1(self.b8.vim, resize=True, shrink=False)
    rsplit.pack2(self.b8.terminals, resize=True, shrink=False)
    self.resize(1024, 900)


class B8(Gtk.Application, logs.LoggerMixin):

  __gtype_name__ = 'b8-app'

  def __init__(self):
    Gtk.Application.__init__(self,
            flags=Gio.ApplicationFlags.FLAGS_NONE)
    logs.LoggerMixin.__init__(self)
    self.config = configs.Config()
    self._add_actions()
    self.vim = vim.Embedded()
    self.vim.connect('ready', self._on_vim_ready)
    self.buffers = buffers.Buffers()
    self.files = files.Files()
    self.terminals = terminals.Terminals()
    self.connect('activate', self._on_activate)

    for w in [self.buffers, self.files, self.terminals]:
      w.connect('directory-activated', self._on_directory_activated)
      w.connect('file-activated', self._on_file_activated)
      w.connect('terminal-activated', self._on_terminal_activated)
      w.connect('file-destroyed', self._on_file_destroyed)

    self.vim.connect('buffer-changed', self._on_buffer_changed)
    self.vim.connect('buffer-deleted', self._on_buffer_deleted)
    self.buffers.connect('buffer-activated', self._on_buffer_activated)

  def _on_directory_activated(self, w, f):
    self.files.browse(f)

  def _on_file_activated(self, w, f):
    self.vim.open_buffer(f.get_path())

  def _on_buffer_changed(self, w, bnum, f):
    self.buffers.change(f, bnum)
    self.window.set_title(f.get_path())

  def _on_buffer_deleted(self, w, bnum, f):
    self.buffers.remove(f, bnum)

  def _on_file_destroyed(self, w, f):
    self.vim.close_buffer(f.get_path())

  def _on_buffer_activated(self, w, b):
    self.vim.change_buffer(b.number)

  def _on_terminal_activated(self, w, f):
    self.terminals.create(f.get_path())

  def _add_actions(self):
    self.keymap = {}
    config_map = {
        'next-buffer': self._on_nextbuffer_activate,
        'previous-buffer': self._on_prevbuffer_activate,
        'next-terminal': self._on_nextterminal_activate,
        'previous-terminal': self._on_prevterminal_activate,
        'new-terminal': self._on_newterminal_activate,
    }
    for act in config_map:
      accel = self.config.get(('shortcuts', act))
      km = Gtk.accelerator_parse(accel)
      self.keymap[km] = config_map[act]

  def _on_newterminal_activate(self):
    self.terminals.create()

  def _on_prevterminal_activate(self):
    self.terminals.prev()

  def _on_nextterminal_activate(self):
    self.terminals.next()

  def _on_nextbuffer_activate(self):
    self.buffers.next()

  def _on_prevbuffer_activate(self):
    self.buffers.prev()

  def _on_activate(self, w):
    self.debug('activating')
    self.window = B8Window(self)
    self.window.connect('key-press-event', self._on_key_press_event)
    self._add_actions()
    self.vim.start()
    self.terminals.create(os.path.expanduser('~'))
    self.files.browse_path(os.path.expanduser('~'))

  def _on_key_press_event(self, w, event):
    kn = Gdk.keyval_name(event.keyval)
    if kn in vim.MODIFIER_NAMES:
      return
    state = event.state & Gdk.ModifierType.MOD1_MASK
    act = self.keymap.get(
        (event.keyval,
         event.state & Gdk.ModifierType.MOD1_MASK))
    if act:
      act()
      return True

  def _on_vim_ready(self, w):
    self.debug('vim is ready')
    self.window.show_all()
    self.vim.grab_focus()
    self.window.present()


def main():
  app = B8()
  app.run()


if __name__ == '__main__':
  main()

