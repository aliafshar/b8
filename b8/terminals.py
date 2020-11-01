# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

"""Bominade Terminal Emulator"""

import webbrowser, os, pwd

from gi.repository import Gtk, Vte, GLib, GObject, Gio, Gdk, Pango

from b8 import ui


class CwdDiscovery(GObject.GObject):

  __gtype_name__ = 'b8-terminals-cwddiscovery'

  cwd = GObject.Property(type=Gio.File)
  running = GObject.Property(type=bool, default=False)

  __gsignals__ = {
    'cwd-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
  }

  def __init__(self, pid):
    GObject.GObject.__init__(self)
    self.pid = pid
    self.connect('notify::cwd', self._on_cwd_changed)

  def start(self):
    self.running = True
    self.refresh()
    GLib.timeout_add(1000, self.refresh)

  def stop(self):
    self.running = False

  def refresh(self):
    l = Gio.File.new_for_path(self.proclink).query_info('*', 0, None)
    new = Gio.File.new_for_path(l.get_symlink_target())
    if not self.cwd or (new.get_path() != self.cwd.get_path()):
      self.cwd = new
    return self.running

  def _on_cwd_changed(self, w, prop):
    self.emit('cwd-changed', self.cwd)

  @property
  def proclink(self):
    return f'/proc/{self.pid}/cwd'


class TerminalTheme(GObject.GObject):

  def __init__(self):
    GObject.GObject.__init__(self)
    self.default_theme = TERMINAL_THEMES.get('b8')
    #theme_name = self.b8.config.get('terminal', 'theme')
    raw_theme = TERMINAL_THEMES.get('b8')
    if not raw_theme:
      self.error(f'theme {theme_name} does not exist, using default')
      raw_theme = self.default_theme
    self.parse(raw_theme)
    self.font_name = 'Monospace 13'
    self.font_desc = Pango.font_description_from_string(self.font_name)

  def parse(self, theme):
    self.foreground = Gdk.RGBA()
    self.foreground.parse(theme['foreground'])
    self.background = Gdk.RGBA()
    self.background.parse(theme['background'])
    self.cursor = Gdk.RGBA()
    self.cursor.parse(theme.get('cursor', theme['foreground']))
    self.palette = []
    theme_palette = theme['palette']
    for s in theme_palette:
      c = Gdk.RGBA()
      c.parse(s)
      self.palette.append(c)


class Terminals(Gtk.Notebook, ui.MenuHandlerMixin):

  __gtype_name__ = 'b8-terminals'

  __gsignals__ = {
    'file-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'file-destroyed': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'terminal-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'directory-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
  }

  def __init__(self):
    Gtk.Notebook.__init__(self)
    self.theme = TerminalTheme()
    self.set_tab_pos(Gtk.PositionType.BOTTOM)
    self.set_scrollable(True)

  def create(self, wd=None):
    if not wd:
      wd = os.path.expanduser('~')
    t = Terminal(self)
    t.start(wd)
    self.append(t)
    #self.pack_start(t, True, True, 0)

  def append(self, t):
    pagenum = self.append_page(t, t.label)
    self.show_all()
    self.set_current_page(pagenum)

  def prev(self):
    c = self.get_current_page()
    n = c - 1
    if n < 0:
      n = self.get_n_pages() - 1
    self.change_tab(n)
    
  def next(self):
    c = self.get_current_page()
    n = c + 1
    if n == self.get_n_pages():
      n = 0
    self.change_tab(n)

  def change_tab(self, n):
    self.set_current_page(n)
    p = self.get_nth_page(n)
    if hasattr(p, 'term'):
      p = p.term
    p.grab_focus()
    


class Terminal(Gtk.HBox):

  __gtype_name__ = 'b8-terminals-terminal'


  file_match = GObject.Property(type=int)
  url_match = GObject.Property(type=int)
  cwd_discovery = GObject.Property(type=CwdDiscovery)
  label = GObject.Property(type=Gtk.Label)
  pid = GObject.Property(type=int)
  cwd = GObject.Property(type=Gio.File)

  def __init__(self, parent):
    Gtk.HBox.__init__(self)
    self.parent = parent
    self.term = Vte.Terminal()
    sw = Gtk.ScrolledWindow()
    sw.add(self.term)
    self.pack_start(sw, True, True, 0)
    self.pack_start(self._create_toolbar(), False, False, 0)
    self._add_matches()
    self._set_theme(parent.theme)
    self.label = self._create_tab_label()
    self.term.connect('button-press-event', self._on_button_press_event)

  def _create_tab_label(self):
    self.label = Gtk.Label()
    self.label.set_ellipsize(Pango.EllipsizeMode.START)
    self.label.set_width_chars(18)
    return self.label

  def _update_label(self):
    self.label.set_markup(self._markup())

  def _set_theme(self, theme):
    self.term.set_colors(theme.foreground, theme.background, theme.palette)
    self.term.set_color_cursor(theme.cursor)
    self.term.set_color_cursor_foreground(theme.cursor)
    self.term.set_font(theme.font_desc)

  def _markup(self):
    ecwd = GLib.markup_escape_text(self.cwd.get_path())
    return f'<span size="small">{ecwd} [<span weight="bold">{self.pid}</span>]</span>'
    
  def _create_toolbar(self):
    t = ui.MiniToolbar.vertical(
        [
          ui.ImageButton(
            key='terminal',
            icon='utilities-terminal',
            tooltip='New terminal in the same directory',
          ),
          ui.ImageButton(
            key='browse',
            icon='folder-open',
            tooltip='Browse the current working directory',
          ),
          ui.ImageButton(
            key='copy',
            icon='edit-copy',
            tooltip='Copy selected text to clipboard',
          ),
          ui.ImageButton(
            key='paste',
            icon='edit-paste',
            tooltip='Paste the clipboard at the cursor',
          ),
          ui.ImageButton(
            key='selectall',
            icon='edit-select-all',
            tooltip='Select all the text in the terminal',
          ),
          Gtk.Frame(),
        ]
    )
    t.connect('clicked', self._on_toolbar_clicked)
    return t


  def _on_toolbar_clicked(self, w, b, key):
    print(b, key)
    handlers = {
        'browse': self._on_browse_clicked,
        'terminal': self._on_terminal_clicked,
        'copy': self._on_copy_clicked,
        'paste': self._on_paste_clicked,
        'selectall': self._on_selectall_clicked,
    }
    f = handlers.get(key)
    if f:
      f(b)

  def _on_browse_clicked(self, w):
    self.parent.emit('directory-activated', self.cwd)

  def _on_copy_clicked(self, w):
    self.term.copy_clipboard_format(Vte.Format.TEXT)

  def _on_paste_clicked(self, w):
    self.term.paste_clipboard()

  def _on_selectall_clicked(self, w):
    self.term.select_all()

  def _on_terminal_clicked(self, w):
    self.parent.emit('terminal-activated', self.cwd)

  def _add_matches(self):
    self.url_match = self.term.match_add_regex(URL_RE, 0)
    self.file_match = self.term.match_add_regex(FILE_RE, 0)
    for m in [self.url_match, self.file_match]:
      self.term.match_set_cursor_name(m, MATCH_CURSOR)

  def _started_callback(self, t, pid, *args):
    self.pid = pid
    self.cwd_discovery = CwdDiscovery(pid)
    self.cwd_discovery.connect('cwd-changed', self._on_cwd_changed)
    self.cwd_discovery.start()
    self.term.watch_child(pid)
    #self._update_label()
    #self.update_label()
    #GLib.timeout_add(1000, self.label_updater)
    self.grab_focus()

  def _on_cwd_changed(self, w, cwd):
    self.cwd = cwd
    self._update_label()

  def start(self, wd):
    self.term.spawn_async(
        Vte.PtyFlags.DEFAULT,
        wd,
        [self._get_default_shell()],
        [],
        GLib.SpawnFlags.DEFAULT | GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        None,
        None,
        -1,
        None,
        self._started_callback,
        None)
    self.started = True
    self.term.grab_focus()

  def _get_default_shell(self):
    """Returns the default shell for the user"""
    # Environ, or fallback to login shell
    return os.environ.get('SHELL', pwd.getpwuid(os.getuid())[-1])

  def _get_selection(self):
    if self.term.get_has_selection():
      # Get the selection value from the primary buffer
      clipboard = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
      selection = clipboard.wait_for_text()
      return selection

  def _on_button_press_event(self, w, event):
    # First check the selection
    m, tag = self._get_selection(), self.file_match
    if not m:
      m, tag = w.match_check_event(event)
    if not m:
      return
    m = m.strip()
    tag_handlers = {
        self.file_match: self._on_match_fs_click,
        self.url_match: self._on_match_url_click,
    }
    f = tag_handlers.get(tag)
    if f:
      f(m, event)

  def _on_match_fs_click(self, m, event):
    if m.startswith('/'):
      f = Gio.File.new_for_path(m)
    else:
      f = self.cwd.get_child(m)
    if not f.query_exists(None):
      return
    if f.query_file_type(0, None) == Gio.FileType.DIRECTORY:
      if event.button == Gdk.BUTTON_PRIMARY:
        self.parent.emit('directory-activated', f)
      elif event.button == Gdk.BUTTON_SECONDARY:
        menu = ui.DirectoryPopupMenu(f)
        menu.connect('activate', self.parent._on_menu_activate)
        menu.popup(event)
    else:
      if event.button == Gdk.BUTTON_PRIMARY:
        self.parent.emit('file-activated', f)
      elif event.button == Gdk.BUTTON_SECONDARY:
        menu = ui.FilePopupMenu(f)
        menu.connect('activate', self.parent._on_menu_activate)
        menu.popup(event)

  def _on_match_url_click(self, m, event):
    webbrowser.open(m)



# https://github.com/luvit/pcre2/blob/master/src/pcre2.h.in
PCRE2_MULTILINE = 0x00000400

FILE_RE = Vte.Regex.new_for_match(
  r'(\H+)',
  -1,
  PCRE2_MULTILINE,
)

URL_RE = Vte.Regex.new_for_match(
  (r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.'
   r'[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'),
  -1,
  PCRE2_MULTILINE,
)

MATCH_CURSOR = 'pointer'


TERMINAL_THEMES = {
  "b8": {
    "name": "b8",
    "foreground": "#839496",
    "background": "#2e2e2e",
    "cursor": "#f0544c",
    "activity": "#dc322f",
    "palette": [
      "#073642",
      "#dc322f",
      "#859900",
      "#b58900",
      "#268bd2",
      "#d33682",
      "#2aa198",
      "#eee8d5",
      "#002b36",
      "#cb4b16",
      "#586e75",
      "#657b83",
      "#839496",
      "#6c71c4",
      "#93a1a1",
      "#fdf6e3"
    ]
  },
  "xubuntu_dark": {
    "name": "xubuntu_dark",
    "foreground": "#b7b7b7",
    "background": "#131926",
    "cursor": "#0f4999",
    "activity": "#0f4999",
    "palette": [
      "#000000",
      "#aa0000",
      "#44aa44",
      "#aa5500",
      "#0039aa",
      "#aa22aa",
      "#1a92aa",
      "#aaaaaa",
      "#777777",
      "#ff8787",
      "#4ce64c",
      "#ded82c",
      "#295fcc",
      "#cc58cc",
      "#4ccce6",
      "#ffffff"
    ]
  },
  "solarized_dark": {
    "name": "solarized_dark",
    "foreground": "#839496",
    "background": "#002b36",
    "cursor": "#93a1a1",
    "activity": "#dc322f",
    "palette": [
      "#073642",
      "#dc322f",
      "#859900",
      "#b58900",
      "#268bd2",
      "#d33682",
      "#2aa198",
      "#eee8d5",
      "#002b36",
      "#cb4b16",
      "#586e75",
      "#657b83",
      "#839496",
      "#6c71c4",
      "#93a1a1",
      "#fdf6e3"
    ]
  },
  "white_on_black": {
    "name": "white_on_black",
    "foreground": "#ffffff",
    "background": "#000000",
    "palette": []
  },
  "black_on_white": {
    "name": "black_on_white",
    "foreground": "#000000",
    "background": "#ffffff",
    "palette": []
  },
  "green_on_black": {
    "name": "green_on_black",
    "foreground": "#17f018",
    "background": "#000000",
    "palette": []
  },
  "xubuntu_light": {
    "name": "xubuntu_light",
    "foreground": "#1f3566",
    "background": "#f1f1f1",
    "cursor": "#0f4999",
    "activity": "#0f4999",
    "palette": [
      "#000000",
      "#aa0000",
      "#44aa44",
      "#aa5500",
      "#0039aa",
      "#aa22aa",
      "#1a92aa",
      "#aaaaaa",
      "#888888",
      "#ff8787",
      "#4ce64c",
      "#ded82c",
      "#295fcc",
      "#cc58cc",
      "#4ccce6",
      "#ffffff"
    ]
  },
  "tango": {
    "name": "tango",
    "foreground": "#ffffff",
    "background": "#000000",
    "palette": [
      "#000000",
      "#cc0000",
      "#4e9a06",
      "#c4a000",
      "#3465a4",
      "#75507b",
      "#06989a",
      "#d3d7cf",
      "#555753",
      "#ef2929",
      "#8ae234",
      "#fce94f",
      "#739fcf",
      "#ad7fa8",
      "#34e2e2",
      "#eeeeec"
    ]
  },
  "solarized_light": {
    "name": "solarized_light",
    "foreground": "#073642",
    "background": "#fdf6e3",
    "cursor": "#073642",
    "activity": "#dc322f",
    "palette": [
      "#073642",
      "#dc322f",
      "#859900",
      "#b58900",
      "#268bd2",
      "#d33682",
      "#2aa198",
      "#eee8d5",
      "#002b36",
      "#cb4b16",
      "#586e75",
      "#657b83",
      "#839496",
      "#6c71c4",
      "#93a1a1",
      "#fdf6e3"
    ]
  },
  "dark_pastels": {
    "name": "dark_pastels",
    "foreground": "#dcdcdc",
    "background": "#2c2c2c",
    "cursor": "#dcdcdc",
    "palette": [
      "#3f3f3f",
      "#705050",
      "#60b48a",
      "#dfaf8f",
      "#9ab8d7",
      "#dc8cc3",
      "#8cd0d3",
      "#dcdcdc",
      "#709080",
      "#dca3a3",
      "#72d5a3",
      "#f0dfaf",
      "#94bff3",
      "#ec93d3",
      "#93e0e3",
      "#ffffff"
    ]
  },
  "xterm": {
    "name": "xterm",
    "foreground": "#000000",
    "background": "#ffffff",
    "palette": [
      "#000000",
      "#cd0000",
      "#00cd00",
      "#cdcd00",
      "#0000cd",
      "#cd00cd",
      "#00cdcd",
      "#e5e5e5",
      "#7f7f7f",
      "#ff0000",
      "#00ff00",
      "#ffff00",
      "#5c5cff",
      "#ff00ff",
      "#00ffff",
      "#ffffff"
    ]
  }
}

if __name__ == '__main__':
  w = Gtk.Window()
  w.connect('destroy', Gtk.main_quit)
  w.resize(400, 400)
  t = Terminals()
  t.create('/home/aa/src/a8')
  w.add(t)

  fs = t

  w.show_all()
  def term_activated(w, f):
    print('term-activated', w, f, f.get_path())

  def file_activated(w, f):
    print('file-activated', w, f, f.get_path())

  def directory_activated(w, f):
    print('directory activate', f.get_path())

  def file_destroyed(w, f):
    print('file-destroyed', w, f, f.get_path())

  fs.connect('terminal-activated', term_activated)
  fs.connect('file-activated', file_activated)
  fs.connect('directory-activated', directory_activated)
  fs.connect('file-destroyed', file_destroyed)
  Gtk.main()
