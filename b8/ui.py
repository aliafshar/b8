# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

"""The Bominade basic widgets."""

import os

from typing import Iterable

from gi.repository import Gio, GLib, GObject, Gdk, Gtk



class Base(Gtk.EventBox):
  """Base B8 Widget."""

  def __init__(self, b8):
    self.b8 = b8
    Gtk.EventBox.__init__(self)

  def create_ui(self):
    """Override to create the UI."""
    raise NotImplementedError


class BaseButtonMixin:
  """Mixin for button operations."""

  def create_button(self, key: str, icon: str, tooltip: str,
                    size: Gtk.IconSize=Gtk.IconSize.SMALL_TOOLBAR):
    """Creating the content for buttons is always the same."""
    self.key = key
    im = Gtk.Image.new_from_icon_name(icon, size)
    self.set_image(im)
    self.set_tooltip_text(tooltip)


class ImageButton(Gtk.Button, BaseButtonMixin):
  """Button with an image."""

  __gtype_name__ = 'b8-imagebutton'

  key = GObject.Property(type=str)

  def __init__(self, *args, **kw):
    Gtk.Button.__init__(self)
    self.create_button(*args, **kw)


class ImageToggleButton(Gtk.ToggleButton, BaseButtonMixin):
  """Toggle button with an image."""

  __gtype_name__ = 'b8-imagetogglebutton'

  name = GObject.Property(type=str)

  def __init__(self, *args, **kw):
    Gtk.ToggleButton.__init__(self)
    self.create_button(*args, **kw)


class MiniToolbar(Gtk.Box):

  __gtype_name__ = 'b8-minitoolbar'

  __gsignals__ = {
    'clicked': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.Button, str,)),
    'right-clicked': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.Button, str,))
  }

  def __init__(self, buttons: Iterable[Gtk.Widget], orientation: Gtk.Orientation, spacing: int=0):
    Gtk.Box.__init__(self, orientation=orientation, spacing=spacing)
    for b in buttons:
      if hasattr(b, 'key'):
        b.connect('clicked', self.on_clicked)
        b.connect('button-press-event', self.on_button_press_event)
        self.pack_start(b, False, False, 0)
      else:
        self.pack_start(b, True, True, 2)

  @staticmethod
  def spacer():
    return Gtk.Frame()

  @classmethod
  def horizontal(cls, buttons):
    return cls(buttons, Gtk.Orientation.HORIZONTAL)

  @classmethod
  def vertical(cls, buttons):
    return cls(buttons, Gtk.Orientation.VERTICAL)

  def on_clicked(self, w):
    self.emit('clicked', w, w.key)

  def on_button_press_event(self, w, event):
    if event.button == Gdk.BUTTON_SECONDARY:
      self.emit('right-clicked', w, w.key)


class PopupMenuItem(Gtk.MenuItem):
  """Menu item for a popup menu."""

  __gtype_name__ = 'b8-popupmenuitem'

  def __init__(self, key, icon, text, size=Gtk.IconSize.SMALL_TOOLBAR):
    self.key = key
    Gtk.MenuItem.__init__(self)
    b = Gtk.HBox()
    self.add(b)
    i = Gtk.Image.new_from_icon_name(icon, size)
    b.pack_start(i, False, False, 0)
    l = Gtk.Label()
    l.set_label(text)
    b.pack_start(l, False, False, 12)


class FilesystemPopupMenu(Gtk.Menu):

  SEPARATOR = object()

  __gtype_name__ = 'b8-fspopupmenu'

  __gsignals__ = {
    'activate': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.MenuItem, str, Gio.File)),
  }

  gfile = GObject.Property(type=Gio.File)

  def __init__(self, gfile, suppress=None):
    Gtk.Menu.__init__(self)
    self.gfile = gfile
    title = PopupMenuItem(
        key='title',
        icon='open-menu',
        text=gfile.get_basename(),
    )
    title.set_sensitive(False)
    self.add(title)
    self.add(FilesystemPopupMenu.separator())
    if not suppress:
      suppress = set()
    for i in self.items():
      self.add(i)
      if hasattr(i, 'key'):
        i.connect('activate', self.on_activate)
        if i.key in suppress:
          i.set_sensitive(False)

  def items(self) -> Iterable[Gtk.MenuItem]:
    """Override to return menu items."""
    raise NotImplementedError()

  def popup(self, event):
    self.show_all()
    Gtk.Menu.popup(self, None, None, None, None, event.button, event.time)

  def on_activate(self, w):
    self.emit('activate', w, w.key, self.gfile)

  @staticmethod
  def separator():
    return Gtk.SeparatorMenuItem()


class FilePopupMenu(FilesystemPopupMenu):
  """Popup menu for files."""

  __gtype_name__ = 'b8-filepopupmenu'

  def items(self) -> Iterable[Gtk.MenuItem]:
    return [
      PopupMenuItem(
        key='open',
        icon='document-open',
        text='Open file',
      ),
      FilesystemPopupMenu.separator(),
      PopupMenuItem(
        key='browseparent',
        icon='folder-open',
        text='Browse parent directory',
      ),
      PopupMenuItem(
        key='terminalparent',
        icon='utilities-terminal',
        text='Terminal in parent directory',
      ),
      FilesystemPopupMenu.separator(),
      PopupMenuItem(
        key='close',
        icon='window-close',
        text='Close file',
      ),
    ]


class DirectoryPopupMenu(FilesystemPopupMenu):

  __gtype_name__ = 'b8-directorypopupmenu'

  def items(self):
    return [
      PopupMenuItem(
        key='browse',
        icon='folder-open',
        text='Browse directory',
      ),
      PopupMenuItem(
        key='terminal',
        icon='utilities-terminal',
        text='Terminal in directory',
      ),
    ]


class MenuHandlerMixin:

  def _on_menu_activate(self, w, m, key, gfile):
    keyhandlers = {
        'open': self._on_open_activate,
        'browseparent': self._on_browseparent_activate,
        'terminalparent': self._on_terminalparent_activate,
        'close': self._on_close_activate,
        'browse': self._on_browse_activate,
        'terminal': self._on_terminal_activate,
    }
    f = keyhandlers.get(key)
    if f:
      f(m, gfile)

  def _on_open_activate(self, w, gfile):
    self.emit('file-activated', gfile)

  def _on_browseparent_activate(self, w, gfile):
    self.emit('directory-activated', gfile.get_parent())

  def _on_terminalparent_activate(self, w, gfile):
    self.emit('terminal-activated', gfile.get_parent())

  def _on_close_activate(self, w, gfile):
    self.emit('file-destroyed', gfile)

  def _on_browse_activate(self, w, gfile):
    self.emit('directory-activated', gfile)

  def _on_terminal_activate(self, w, gfile):
    self.emit('terminal-activated', gfile)



def parse_color(s: str) -> Gdk.RGBA:
  """Parse a color string."""
  c = Gdk.RGBA()
  c.parse(s)
  return c


class Colors:
  """The default colors used in B8."""

  RED = parse_color('#d30102')
  ORANGE = parse_color('#cb4b16')
  GREEN = parse_color('#859900')


