
# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

import argparse, code, configparser, io, math, os, pwd, subprocess, sys, threading, uuid

import gi
gi.require_version("Gtk", "3.0")
gi.require_version('Vte', '2.91')
gi.require_version('PangoCairo', '1.0')
gi.require_version('Gdk', '3.0')


from gi.repository import GLib, GObject, Gdk, Gtk, Pango, PangoCairo, Vte

import cairo
import msgpack


class B8Object:
  """Base class for all B8-aware instances. I'm lazy. Welcome."""

  def __init__(self, b8):
    self.b8 = b8
    self.init()

  def init(self):
    """Override for initialization."""

  def destroy(self):
    """Override for ending."""
  
  def log(self, level, msg):
    """Because who can ever work out logging."""
    logmsg = f'{level}:{self.__class__.__name__}:{msg}'
    if self.b8.terminals and self.b8.arguments.args.debug:
      self.b8.terminals.logger.msg(logmsg)
    print(logmsg)

  def debug(self, msg):
    """Debug a message."""
    if self.b8.arguments.args.debug:
      self.log('D', msg)

  def info(self, msg):
    """Info a message."""
    self.log('I', msg)

  def error(self, msg):
    """Error a message."""
    self.log('E', msg)


class B8View(B8Object):
  """Base View class."""

  def init(self):
    self.widget = self.create_ui()
    if not self.widget:
      self.error(f'view object {self} has no root widget')
    self.connect_ui()

  def create_ui(self):
    """Override to create and return the UI."""

  def connect_ui(self):
    """Override to do any event connecting."""

  def connect(self, event, widget=None, widget_name=None):
    if widget is None:
      widget = self.widget
    widget_part = ''
    if widget_name:
      widget_part = f'{widget_name}_'
    event_part = event.replace('-', '_')
    fname = f'on_{widget_part}{event_part}'
    self.debug(f'connecting {widget} to {fname}')
    f = getattr(self, fname, None)
    if not f:
      self.error(f'connecting {fname} does not exist for {self}')
    widget.connect(event, f)

  def mini_button(self, icon_name, tooltip, btype=Gtk.Button):
    b = btype()
    i = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.SMALL_TOOLBAR)
    b.set_image(i)
    b.set_tooltip_text(tooltip)
    return b




class B8:
  """The Bominade monolith.

  This knows about everything. And everything knows about it.
  No doubt there are circular references and leaks everywhere.
  """

  log_level = None
  terminals = None

  def __init__(self):
    self.arguments = Arguments(self)
    self.instance = Instance(self)
    self.config = Config(self)
    if self.arguments.args.remote:
      self.running = False
      self.remote = Remote(self)
    else:
      self.running = True
      self.ipc = Ipc(self)
      self.contexts = Contexts(self)
      self.terminals = Terminals(self)
      self.vim = Vim(self)
      self.buffers = Buffers(self)
      self.files = Files(self)
      self.ui = B8Window(self)
      self.show_shell(os.getcwd())

  def show_path(self, path, is_dir=False):
    if is_dir or os.path.isdir(path):
      self.files.browse(path)
    else:
      self.vim.nvim_open_buffer(path)
      self.ui.vimview.drawing_area.grab_focus()

  def show_shell(self, path):
    self.terminals.create(path)

  def close_path(self, path):
    self.vim.nvim_delete_buffer(path)

  def run(self):
    """Run until the Gtk main loop ends."""
    Gtk.main()

  def quit(self):
    self.running = False
    self.ipc.destroy()
    Gtk.main_quit()


class B8Window(B8View):
  """Bominade top-level window."""

  def create_ui(self):
    self.window = Gtk.Window()
    self.window.set_icon_name('media-seek-forward')
    self.window.set_title('b8 ♡ u')
    hsplit = Gtk.HPaned()
    lsplit = Gtk.VPaned()
    rsplit = Gtk.VPaned()
    self.rsplit = rsplit

    lsplit.pack1(self.b8.buffers.widget, resize=True, shrink=False)
    lsplit.pack2(self.b8.files.widget, resize=True, shrink=False)
    hsplit.pack1(lsplit, resize=True, shrink=False)
    hsplit.pack2(rsplit, resize=True, shrink=False)
    hsplit.set_property('position', 200)
    self.window.add(hsplit)

    rsplit.set_property('position', 600)
    #self.lsplit.set_property('position', 600)
    self.vimview = VimView(self.b8)
    rsplit.pack1(self.vimview.view, resize=True, shrink=False)
    rsplit.pack2(self.b8.terminals.widget, resize=True, shrink=False)
    self.window.resize(1024, 800)
    self.window.show_all()
    return self.window

  def connect_ui(self):
    self.connect('destroy')
    self.connect('configure-event')
    

  def on_configure_event(self, w, e):
    self.rsplit.set_position(2.0 * e.height / 3)

  def on_destroy(self, w):
    self.b8.quit()



class Arguments(B8Object):

  def init(self):
    parser = argparse.ArgumentParser(
        prog='b8',
        description='The bominade IDE')
    parser.add_argument(
        '--remote',
        action='store_true',
        help='Open in a running b8')
    parser.add_argument('--debug', action='store_true', help='Debug log output')
    parser.add_argument('files', nargs='*', help='Files to open')
    self.args = parser.parse_args()
    self.parser = parser


class Instance(B8Object):

  def init(self):
    self.root_path = os.path.expanduser('~/.config/b8')
    self.run_path = os.path.join(self.root_path, 'run')
    self.config_path = os.path.join(self.root_path, 'b8rc')
    self.create()
  
  def create(self):
    try:
      os.makedirs(self.root_path)
      self.debug('create config directory {self.root_path}')
    except FileExistsError:
      self.debug(f'config directory exists {self.root_path}')
    try:
      os.makedirs(self.run_path)
      self.debug('create run directory {self.run_path}')
    except FileExistsError:
      self.debug(f'run exists {self.root_path}')
    if not os.path.exists(self.config_path):
      with open(self.config_path, 'w') as f:
        f.write('# Bominade Config File\n')


class Config(B8Object):

  default_config = {
      'logging': {
        'level': 'info',  
      },
      'terminal': {
        'theme':'b8',
        'font': 'Monospace 13',
      },
      'vim': {
        'font': 'Monospace 13',
      }
  }

  def init(self):
    self.parser = configparser.ConfigParser()
    self.parser.read(self.b8.instance.config_path)

  def get(self, section, key):
    if self.parser.has_section(section):
      value = self.parser.get(section, key, fallback=None)
      if value:
        return value
    else:
      return self.default_config[section][key]


class Remote(B8Object):

  def init(self):
    fs = self.b8.arguments.args.files
    if not fs:
      self.error('but you did not pass any files')
      self.b8.arguments.parser.print_usage()
      return
    command = fs[0]

    potentials = os.listdir(self.b8.instance.run_path)
    if len(potentials) == 1:
      if command == 'list':
        pass

      elif command == 'ping':
        pass

      else:
        msg = msgpack.dumps(['open', command])
        pipe_path = os.path.join(self.b8.instance.run_path, potentials[0])
        pipe = os.open(pipe_path, os.O_WRONLY)
        os.write(pipe, msg)
        os.close(pipe)



class Ipc(B8Object):

  def init(self):
    self.uid = str(uuid.uuid4())
    self.pipe_path = os.path.join(self.b8.instance.run_path, self.uid)
    self.debug(f'opening rpc fifo at {self.pipe_path}')
    self.unpacker = msgpack.Unpacker()
    os.mkfifo(self.pipe_path)
    self.fifo = os.open(self.pipe_path, os.O_RDONLY | os.O_NONBLOCK)
    GLib.io_add_watch(self.fifo, 0, GLib.IOCondition.IN, self.on_raw)

  def on_raw(self, channel, condition):
    while True:
      d = os.read(self.fifo, 1024)
      self.unpacker.feed(d)
      if len(d) < 1024:
        break
    for msg in self.unpacker:
      self.debug(f'ipc message {msg}')
      if msg[0] == 'open':
        self.b8.show_path(msg[1])

  def destroy(self):
    os.close(self.fifo)
    os.remove(self.pipe_path)



class Action:
  """User-initiated action."""

  icon_size = Gtk.IconSize.SMALL_TOOLBAR

  def __init__(self, key, label_text, icon_name, tooltip_text):
    self.key = key
    self.label_text = label_text
    self.icon_name = icon_name
    self.tooltip_text = tooltip_text

  def icon(self):
    return Gtk.Image.new_from_icon_name(self.icon_name, self.icon_size)

  def label(self):
    l = Gtk.Label()
    l.set_label(self.label_text)
    return l

  def menuitem(self):
    item = Gtk.MenuItem()
    hb = Gtk.HBox()
    hb.pack_start(self.icon(), expand=False, fill=False, padding=0)
    l = Gtk.Label()
    l.set_label(self.label_text)
    hb.pack_start(l, expand=True, fill=False, padding=0)
    item.add(hb)
    return item








class Contexts(B8Object):

  BUFFER = 'buffer'
  FILE = 'file'
  DIRECTORY = 'directory'

  actions = {
      FILE: [
        Action('open', 'Open File', 'document-open',
               'Open this file in the editor'),
        None,
        Action('browse', 'Browse Parent Directory', 'folder-open',
               'Browse the parent directory'),
        Action('terminal', 'Terminal in Parent Directory', 'utilities-terminal',
               'Open a terminal in the parent directory'),
        None,
        Action('close', 'Close the file', 'window-close',
               'Close the file if it is opened.'),

      ],
      DIRECTORY: [
        Action('browse', 'Browse Directory', 'folder-open',
               'Browse this directory'),
        None,
        Action('terminal', 'Terminal in Directory', 'utilities-terminal',
               'Open a terminal in this directory'),
      ],
  }

  ereg_exprs = {
      'file2': (
          r'"([^"]|\\")+"|' + \
          r"'[^']+'|" + \
          r'(\\ |\\\(|\\\)|\\=|[^]\[[:space:]"\':\$()=])+'
      ),
      'file': (
          r'(\H+)'
      )
  }


  def init(self):
    pass

  def regex(self, name):
    #https://github.com/luvit/pcre2/blob/master/src/pcre2.h.in
    PCRE2_MULTILINE = 0x00000400
    return Vte.Regex.new_for_match(self.ereg_exprs[name], -1, PCRE2_MULTILINE)

  def menu(self, name, data):
    menu = Gtk.Menu()
    for action in self.actions[name]:
      if action:
        item = action.menuitem()
        fname = f'on_{name}_{action.key}_activate'
        f = getattr(self, fname)
        item.connect('activate', f, action, data)
      else:
        item = Gtk.SeparatorMenuItem()
      menu.append(item)
    menu.show_all()
    return menu

  def on_file_open_activate(self, w, action, data):
    self.b8.show_path(data, is_dir=False)

  def on_file_browse_activate(self, w, action, data):
    self.b8.show_path(os.path.dirname(data))

  def on_file_terminal_activate(self, w, action, data):
    self.b8.show_shell(os.path.dirname(data))

  def on_file_close_activate(self, w, action, data):
    self.b8.close_path(data)

  def on_directory_browse_activate(self, w, action, data):
    self.b8.show_path(data, is_dir=True)

  def on_directory_terminal_activate(self, w, action, data):
    self.b8.show_shell(data)



class TerminalTheme(B8Object):

  def init(self):
    self.default_theme = TERMINAL_THEMES.get('b8')
    theme_name = self.b8.config.get('terminal', 'theme')
    raw_theme = TERMINAL_THEMES.get(theme_name)
    if not raw_theme:
      self.error(f'theme {theme_name} does not exist, using default')
      raw_theme = self.default_theme
    self.parse(raw_theme)
    self.font_name = self.b8.config.get('terminal', 'font')
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
    


class Terminals(B8View):

  def create_ui(self):
    widget = Gtk.HBox()
    self.book = Gtk.Notebook()
    self.book.set_tab_pos(Gtk.PositionType.BOTTOM)
    self.book.set_scrollable(True)
    widget.pack_start(self.book, True, True, 0)
    self.theme = TerminalTheme(self.b8)
    if self.b8.arguments.args.debug:
      self.logger = LogView(self.b8)
      self.append(self.logger)
      self.console = Console(self.b8)
      self.append(self.console)

    return widget

  def append(self, w):
    pagenum = self.book.append_page(w.widget, w.create_tab_label())
    self.book.show_all()
    self.book.set_current_page(pagenum)

  def create(self, wd):
    t = TerminalView(self.b8)
    pagenum = self.book.append_page(t.widget, t.create_tab_label())
    self.book.show_all()
    self.book.set_current_page(pagenum)
    t.start(wd)



class Console(B8View):

  ps1 = 'b8 >>> '
  ps2 = 'b8 ... '

  def create_ui(self):
    self.term = Vte.Terminal()
    theme = TerminalTheme(self.b8)
    self.term.set_colors(theme.foreground, theme.background, theme.palette)
    self.term.set_color_cursor(theme.cursor)
    self.term.set_color_cursor_foreground(theme.cursor)
    self.term.set_font(theme.font_desc)
    self.term.set_scroll_on_output(True)
    self.term.connect('commit', self.on_commit)
    self.buffer = []
    self.prompt = self.ps1
    self.feed('bominade interactive console\n')
    self.feed(self.prompt)
    self.interactive = code.InteractiveInterpreter(locals={'b8': self.b8})
    #self.term.connect()
    return self.term

  def on_commit(self, w, text, size):
    self.buffer.append(text.replace('\r', '\r\n'))
    self.feed(text)
    if text == '\r':
      line = ''.join(self.buffer)
      oldstdout = sys.stdout
      newstdout = io.StringIO()
      sys.stdout = newstdout
      more = self.interactive.runsource(line)
      sys.stdout = oldstdout
      if more:
        self.prompt = self.ps2
      else:
        self.prompt = self.ps1
        self.buffer = []
        newstdout.seek(0)
        reply = newstdout.read()
        self.feed(reply)
      self.feed(self.prompt)

  def feed(self, t):
    t = t.replace('\n', '\r\n')
    b = t.encode('utf-8')
    self.term.feed(b)

  def create_tab_label(self):
    self.label = Gtk.Label()
    self.label.set_label('b8 console')
    self.label.set_width_chars(8)
    return self.label



class LogView(B8View):

  def create_ui(self):
    self.term = Vte.Terminal()
    theme = TerminalTheme(self.b8)
    self.term.set_colors(theme.foreground, theme.background, theme.palette)
    self.term.set_color_cursor(theme.cursor)
    self.term.set_color_cursor_foreground(theme.cursor)
    self.term.set_font(theme.font_desc)
    self.term.set_scroll_on_output(True)
    return self.term

  def msg(self, s):
    self.term.feed(s.encode('utf-8') + b'\r\n')

  def create_tab_label(self):
    self.label = Gtk.Label()
    self.label.set_label('log')
    self.label.set_width_chars(8)
    return self.label



class TerminalView(B8View):

  child_pid = 0 
  child_cwd = ''
  linked_browser = False
  started = False

  def create_ui(self):
    self.term = Vte.Terminal()
    self.term.match_add_regex(self.b8.contexts.regex('file'), 0)
    self.term.match_set_cursor_name(0, 'pointer')
    self.term.connect('button-press-event', self.on_button_press_event)
    widget = Gtk.HBox()
    tools = Gtk.VBox()
    widget.pack_start(self.term, expand=True, fill=True, padding=0)
    widget.pack_start(tools, expand=False, fill=False, padding=0)


    self.term_button = self.mini_button(
      'utilities-terminal', 'Open a new terminal in this directory',
    )
    tools.pack_start(self.term_button, expand=False, fill=False, padding=0)
    self.browse_button = self.mini_button(
        'folder-open', 'Browse the current directory')
    tools.pack_start(self.browse_button, expand=False, fill=False, padding=0)
    self.copy_button = self.mini_button(
      'edit-copy', 'Copy the selection',
    )
    tools.pack_start(self.copy_button, expand=False, fill=False, padding=0)
    self.paste_button = self.mini_button(
        'edit-paste', 'Paste the current clipboard')
    tools.pack_start(self.paste_button, expand=False, fill=False, padding=0)
    self.select_button = self.mini_button(
        'edit-select-all', 'Select all')
    tools.pack_start(self.select_button, expand=False, fill=False, padding=0)
    self.link_button = self.mini_button(
      'insert-link', 'Connect browser with terminal', btype=Gtk.ToggleButton)
    tools.pack_start(Gtk.Frame(), expand=True, fill=True, padding=0)
    tools.pack_start(self.link_button, expand=False, fill=False, padding=0)

    theme = self.b8.terminals.theme
    self.term.set_colors(theme.foreground, theme.background, theme.palette)
    self.term.set_color_cursor(theme.cursor)
    self.term.set_color_cursor_foreground(theme.cursor)
    self.term.set_font(theme.font_desc)
    return widget

  def connect_ui(self):
    self.connect('clicked', self.link_button, 'link_button')
    self.connect('clicked', self.browse_button, 'browse_button')
    self.connect('clicked', self.copy_button, 'copy_button')
    self.connect('clicked', self.paste_button, 'paste_button')
    self.connect('clicked', self.select_button, 'select_button')
    self.connect('clicked', self.term_button, 'term_button')
    self.connect('child-exited', self.term)

  def on_child_exited(self, ti, status):
    self.started = False
    self.pid = None
    self.term.feed(f'\x1b[0;1;34mExited, '
                   f'status: \x1b[0;1;31m{status} \r\n'
                   f'\x1b[0mpress enter to close'.encode('utf-8'))
    self.term.connect('key-press-event', self.on_keypress_after_exit)

  def on_keypress_after_exit(self, terminal, event):
    key_name = Gdk.keyval_name(event.keyval)
    if key_name == 'Return':
      self.close()

  def close(self):
    self.widget.get_parent().remove(self.widget)

  def on_started(self, t, pid, *args):
    self.child_pid = pid
    t.watch_child(pid)
    self.update_label()
    GLib.timeout_add(500, self.label_updater)
    self.widget.grab_focus()

  def start(self, wd):
    self.child_cwd = wd
    self.term.spawn_async(
        Vte.PtyFlags.DEFAULT,
        self.child_cwd,
        [self.get_default_shell()],
        [],
        GLib.SpawnFlags.DEFAULT | GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        None,
        None,
        -1,
        None,
        self.on_started,
        None)
    self.started = True

  def get_selection_text(self):
    if self.term.get_has_selection():
      # Get the selection value from the primary buffer
      clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
      selection = clipboard.wait_for_text()
      return selection
    return None

  def get_default_shell(self):
    """Returns the default shell for the user"""
    # Environ, or fallback to login shell
    return os.environ.get('SHELL', pwd.getpwuid(os.getuid())[-1])

  def create_tab_label(self):
    self.label = Gtk.Label()
    self.label.set_ellipsize(Pango.EllipsizeMode.START)
    self.label.set_width_chars(18)
    return self.label

  def label_updater(self):
    if not self.child_pid:
      return
    if not self.started:
      return
    new_cwd = self.get_cwd()
    if new_cwd != self.child_cwd:
      self.child_cwd = new_cwd
      self.update_label()
      if self.linked_browser:
        self.b8.show_path(self.child_cwd)
    return self.b8.running and self.started

  def update_label(self):
    self.label.set_markup(self.markup())

  def markup(self):
    ecwd = GLib.markup_escape_text(self.child_cwd)
    return f'<span size="small">{ecwd} [<span weight="bold">{self.child_pid}</span>]</span>'

  def get_cwd(self):
    path = os.readlink(f'/proc/{self.child_pid}/cwd')
    path = path.split('\x00')[0]
    if path.endswith(' (deleted)') and not os.path.exists(path):
        path = path[:-10]
    return path

  def on_button_press_event(self, w, event):
    action = None
    selected = None
    m, tag = w.match_check_event(event)
    if not m:
      # Fail fast if not matching.
      return
    m = m.strip()
    if tag == 0:
      if not m.startswith('/'):
        m = os.path.join(self.child_cwd, m)
      if os.path.exists(m):
        selected = m

    if not selected:
      return

    if event.button == Gdk.BUTTON_PRIMARY:
      self.b8.show_path(selected)
    elif event.button == Gdk.BUTTON_SECONDARY:
      if os.path.isdir(selected):
        action = 'directory'
      else:
        action = 'file'
      menu = self.b8.contexts.menu(action, selected)
      menu.popup(None, None, None, None, event.button, event.time)

  def on_link_button_clicked(self, w):
    self.linked_browser = w.get_active()
    if self.linked_browser:
      self.b8.show_path(self.child_cwd)

  def on_browse_button_clicked(self, w):
    self.b8.show_path(self.child_cwd)

  def on_copy_button_clicked(self, w):
    self.term.copy_clipboard()

  def on_paste_button_clicked(self, w):
    self.term.paste_clipboard()

  def on_select_button_clicked(self, w):
    self.term.select_all()

  def on_term_button_clicked(self, w):
    self.b8.show_shell(self.child_cwd)


class Buffer:

  path = ''
  number = ''

  def __init__(self, path, number):
    self.path = os.path.realpath(path)
    self.number = number
    self.name = os.path.basename(path)
    self.parent = os.path.dirname(path)
    self.ename = GLib.markup_escape_text(self.name)
    self.eparent = GLib.markup_escape_text(self.parent)
    self.markup = (f'<span size="medium" weight="bold">{self.ename}</span>\n'
                   f'<span size="x-small">{self.parent}</span>')

  def __repr__(self):
    return f'<Buffer path={self.path} number={self.number}'


class Buffers(B8View):

  def create_ui(self):
    self.model = Gtk.ListStore(object)
    self.tree = Gtk.TreeView(model=self.model)
    self.tree.set_headers_visible(False)
    self.cell = Gtk.CellRendererText()
    self.cell.set_padding(6, 1)
    self.column = Gtk.TreeViewColumn('name', self.cell)
    self.column.set_cell_data_func(self.cell, self.render)
    self.tree.append_column(self.column)
    self.tree.connect('row-activated', self.on_row_activated)
    self.tree.connect('button-press-event', self.on_button_press_event)
    self.tree.set_activate_on_single_click(True)
    widget = Gtk.ScrolledWindow()
    widget.add(self.tree)
    return widget
    
  def select(self, giter):
    selection = self.tree.get_selection()
    if selection.get_selected() != giter:
      self.tree.get_selection().select_iter(giter)
    b = self.model.get(giter, 0)[0]
    self.debug(f'select {b}')
    self.b8.ui.window.set_title(b.path)
    self.b8.ui.vimview.drawing_area.grab_focus()

  def change(self, path, number):
    self.debug(f'buffer change {path} {number}')
    for grow in self.model:
      b = self.model.get_value(grow.iter, 0)

      if b.number == number and b.path == path:
        self.debug(f'existing {b}')
        self.select(grow.iter)
        return

    b = Buffer(path, number)
    giter = self.model.append([b])
    self.select(giter)

  def remove(self, path, number):
    for grow in self.model:
      b = self.model.get_value(grow.iter, 0)
      if b.number == number and b.path == path:
        self.model.remove(grow.iter)
        return


  def on_row_activated(self, w, path, column):
    giter = self.model.get_iter(path)
    b = self.model.get(giter, 0)[0]
    self.b8.vim.nvim_change_buffer(b.number)
    self.debug(f'row-activated {b}')

  def render(self, cell_layout, cell, tree_model, iter, *data):
    b = tree_model.get_value(iter, 0)
    cell.set_property('markup', b.markup)

  def on_button_press_event(self, treeview, event):
    if event.button != Gdk.BUTTON_SECONDARY:
      return
    item_spec = self.tree.get_path_at_pos(int(event.x), int(event.y))
    if item_spec is not None:
      # clicked on an actual cell
      path, col, rx, ry = item_spec
      giter = self.model.get_iter(path)
      b = self.model.get_value(giter, 0)
      action = 'file'
      menu = self.b8.contexts.menu(action, b.path)
      menu.popup(None, None, None, None, event.button, event.time)
      return True


class File:

  path = ''
  modifier = ' '

  def __init__(self, name, parent):
    self.name = name
    self.parent = parent
    self.path = os.path.join(self.parent, name)
    self.is_dir = os.path.isdir(self.path)
    if self.is_dir:
      self.prefix='0'
      self.icon = Gtk.STOCK_DIRECTORY
      self.modifier = '/'
    else:
      self.prefix='1'
      self.icon = Gtk.STOCK_FILE
    self.ename = GLib.markup_escape_text(self.name)
    self.sortable = f'{self.prefix}_{self.name}'
    self.markup = f'<span size="medium">{self.ename}</span>'

  modifier_colors = {
    'M': '#d30102',
    '??': '#cb4b16',
    '/': '#859900',
  }

  @property
  def modifier_color(self):
    c = self.modifier_colors.get(self.modifier, self.modifier_colors['/'])
    col = Gdk.RGBA()
    col.parse(c)
    return col

  def __repr__(self):
    return f'<File path={self.path} is_dir={self.is_dir}>'

class Files(B8View):

  current_path = None
  show_hidden = False

  def create_ui(self):
    widget = Gtk.VBox()
    tools = Gtk.HBox()
    widget.pack_start(tools, expand=False, fill=True, padding=0)
    container = Gtk.ScrolledWindow()
    widget.pack_start(container, expand=True, fill=True, padding=0)
    self.model = Gtk.ListStore(object, GObject.TYPE_STRING)
    self.tree = Gtk.TreeView(model=self.model)
    container.add(self.tree)
    self.tree.set_headers_visible(False)
    self.cell = Gtk.CellRendererText()
    self.column = Gtk.TreeViewColumn('', self.cell)
    self.column.set_cell_data_func(self.cell, self.render)
    self.icon_cell = Gtk.CellRendererPixbuf()
    self.icon_column = Gtk.TreeViewColumn('icon', self.icon_cell)
    self.icon_column.set_cell_data_func(self.icon_cell, self.render_icon)
    #self.tree.append_column(self.icon_column)
    self.model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
    self.modifier_cell = Gtk.CellRendererText()
    self.modifier_cell.set_property('family', 'Monospace')
    self.modifier_cell.set_property('weight', 800)
    self.modifier_cell.set_padding(3, 1)
    self.modifier_column = Gtk.TreeViewColumn('', self.modifier_cell)
    self.modifier_column.set_cell_data_func(self.modifier_cell,
        self.render_modifier)
    self.tree.append_column(self.modifier_column)
    self.tree.append_column(self.column)
    self.tree.connect('row-activated', self.on_row_activated)
    self.tree.connect('button-press-event', self.on_button_press_event)
    self.tree.set_activate_on_single_click(False)


    self.terminal_button = self.mini_button(
        'utilities-terminal',
        'Start a terminal in this directory.'
    )

    self.up_button = self.mini_button(
        'go-up',
        'Navigate to the parent directory.'
    )

    self.refresh_button = self.mini_button(
        'view-refresh',
        'Refresh the current directory list.',
    )

    self.hidden_button = self.mini_button(
        'view-more',
        'Show / Hide hidden files.',
        btype=Gtk.ToggleButton,
    )

    tools.pack_start(self.up_button, expand=False, fill=False, padding=0)
    tools.pack_start(self.refresh_button, expand=False, fill=False, padding=0)
    tools.pack_start(self.terminal_button, expand=False, fill=False,
        padding=0)
    tools.pack_start(Gtk.Frame(), expand=True, fill=True, padding=0)
    tools.pack_start(self.hidden_button, expand=False, fill=False, padding=0)


    self.up_button.connect('clicked', self.on_up_button_clicked)
    self.refresh_button.connect('clicked', self.on_refresh_button_clicked)
    self.terminal_button.connect('clicked', self.on_terminal_button_clicked)
    self.hidden_button.connect('clicked', self.on_hidden_button_clicked)

    p = os.path.expanduser('~')
    self.browse(p)
    return widget

  def render(self, cell_layout, cell, tree_model, iter, *data):
    b = tree_model.get_value(iter, 0)
    cell.set_property('markup', b.markup)

  def render_icon(self, cell_layout, cell, tree_model, iter, *data):
    b = tree_model.get_value(iter, 0)
    cell.set_property('icon_name', b.icon)

  def render_modifier(self, cell_layout, cell, tree_model, iter, *data):
    b = tree_model.get_value(iter, 0)
    cell.set_property('text', b.modifier[0])
    cell.set_property('foreground-rgba', b.modifier_color)


  def on_row_activated(self, w, path, column):
    giter = self.model.get_iter(path)
    f = self.model.get_value(giter, 0)
    self.debug(f'row-activated {f}')
    self.b8.show_path(f.path, is_dir=f.is_dir)

  def on_button_press_event(self, treeview, event):
    if event.button != Gdk.BUTTON_SECONDARY:
      return
    item_spec = self.tree.get_path_at_pos(int(event.x), int(event.y))
    if item_spec is not None:
      # clicked on an actual cell
      path, col, rx, ry = item_spec
      giter = self.model.get_iter(path)
      f = self.model.get_value(giter, 0)
      if f.is_dir:
        action = 'directory'
      else:
        action = 'file'
      menu = self.b8.contexts.menu(action, f.path)
      menu.popup(None, None, None, None, event.button, event.time)

  def append(self, f):
    self.model.append([f, f.sortable])

  def browse_thread(self, path):
    d = os.listdir(path)
    for p in d:
      f = File(p, path)
      if not self.show_hidden and f.name.startswith('.'):
        continue
      GLib.idle_add(self.append, f)
    GLib.idle_add(self.scroll_to_top)
    for t in [0, 10, 20, 50, 100, 200]:
      GLib.timeout_add(t, self.scroll_to_top)
    self.git_thread(path)

  def git_thread(self, path):
    try:
      p = subprocess.Popen(['git', 'status', '--porcelain', '.'], cwd=path,
          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      p.wait()
      ignored = p.stderr.read()
      if p.returncode > 0:
        return
      git_status = p.stdout.read().splitlines()
      for l in git_status:
        mod, name = l.decode('utf-8').split()
        name = os.path.basename(name)
        mod = mod.strip()
        GLib.idle_add(self.apply_git_data, name, mod)

    except FileNotFoundError:
      self.error('if you want Git stuff, install it')


    GLib.idle_add(self.scroll_to_top)

  def apply_git_data(self, name, modifier):
    for grow in self.model:
      f = self.model.get_value(grow.iter, 0)
      if f.name == name:
        f.modifier = modifier
        self.model.row_changed(self.model.get_path(grow.iter), grow.iter)

  def browse(self, path, refresh=False):
    if refresh or path != self.current_path:
      self.debug(f'browsing {path}')
      self.current_path = path
      t = threading.Thread(target=self.browse_thread, args=(path,))
      t.start()
      self.model.clear()
    else:
      self.debug(f'not browsing the path I am already at {path}')

  def scroll_to_top(self):
    self.tree.scroll_to_point(0, 0)


  def on_up_button_clicked(self, w):
    parent = os.path.dirname(self.current_path)
    self.browse(parent)

  def on_refresh_button_clicked(self, w):
    self.debug('refresh button clicked')
    self.browse(self.current_path, refresh=True)

  def on_terminal_button_clicked(self, w):
    self.debug('terminal button clicked')
    self.b8.show_shell(self.current_path)

  def on_hidden_button_clicked(self, w):
    self.show_hidden = self.hidden_button.get_active()
    self.browse(self.current_path, refresh=True)



class Grid:
  """NeoVim grid"""

  def __init__(self, width, height):
    self.width = width
    self.height = height
    self.cells = [[Cell() for col in range(self.width)] for col in
        range(self.height)]

  def clone(self):
    g = Grid(self.width, self.height)
    for (row, orow) in zip(self.cells, g.cells):
      for (cell, ocell) in zip(row, orow):
        cell.copy_to(ocell)
    return g


class Cell:
  """Single cell within a NeoVim grid"""
  text = ''  
  hl = None

  def copy_to(self, c):
    c.text = self.text
    c.hl = self.hl

  def is_same(self, other):
    return self.text == other.text and self.hl is other.hl


class ModeInfo:
  """Information about a NeoVim mode."""
  mouse_shape = None
  cursor_shape = None
  cell_percentage = None
  blinkwait = None
  blinkon = None
  blinkoff = None
  hl_id = None
  id_lm = None
  attr_id = None
  attr_id_lm = None
  name = None
  short_name = None


class Highlight:
  """Information about a NeoVim highlight."""
  foreground = None 
  background = None
  special = None
  bold = False
  undercurl = False
  reverse = False
  strikethrough = False
  underline = False
  blend = False
  italic = False


class Color:
  """BeoVim color with conversion to RGB"""

  def __init__(self, color_value):
    self.r = ((color_value >> 16) & 255) / 256.0
    self.g = ((color_value >> 8) & 255) / 256.0
    self.b = (color_value & 255) / 256.0

class Vim(B8Object):
  """NeoVim Library for embedding, using GLib's async model."""
  command_id = 0
  width = 10
  height = 10
  started = False
  current_buffer = None
  cursor_x = -1
  cursor_y = -1

  nvim_binary = 'nvim'
  nvim_base_args = ['--embed']

  def init(self):
    self.grid = None
    self.unpacker = msgpack.Unpacker()
    self.flush_callback = None
    self.highlights = {}
    self.modes = {}
    self.current_mode = None
    self.options = {}
    self.start()

  def get_nvim_argv(self):
    return [self.nvim_binary] + self.nvim_base_args +  self.b8.arguments.args.files

  def start(self):
    if not self.width and self.height:
      return

    self.started = True


    self.proc = subprocess.Popen(self.get_nvim_argv(),
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE)

    self.pipe_in = self.proc.stdin
    self.pipe_out = self.proc.stdout
    self.fd_out = self.pipe_out.fileno()
    self.chan_out = GLib.IOChannel.unix_new(self.fd_out)

    self.pipe_err = self.proc.stderr
    self.fd_err = self.pipe_err.fileno()
    self.chan_err = GLib.IOChannel.unix_new(self.fd_err)

    GLib.io_add_watch(self.chan_out, 0, GLib.IOCondition.IN, self.on_raw)
    #GLib.io_add_watch(self.chan_err, 0, GLib.IOCondition.IN, self.on_raw)

    self.cmd('nvim_ui_attach', [self.width, self.height, {'ext_linegrid': True,
      }])

    self.cmd('nvim_command', [
      'autocmd BufAdd * call rpcnotify(0, "buffers", "add", expand("<abuf>"), expand("<amatch>"))'
    ]);
    self.cmd('nvim_command', [
      'autocmd BufEnter * call rpcnotify(0, "buffers", "enter", expand("<abuf>"), expand("<amatch>"))'
    ]);

    self.cmd('nvim_command', [
      'autocmd BufDelete * call rpcnotify(0, "buffers", "delete", expand("<abuf>"), expand("<amatch>"))'
    ]);
    self.cmd('nvim_subscribe', ['buffers']);

    #self.cmd('nvim_command', ['vsplit'])
    
  def on_raw(self, channel, condition):
    self.debug('received:raw data')
    while True:
      d = os.read(self.fd_out, 1024)
      self.unpacker.feed(d)
      if len(d) < 1024:
        break
    for msg in self.unpacker:
      msg_type = msg[0]

      if msg_type == 1:
        self.debug(f'received:reply {msg}')

      elif msg_type == 2:
        msg_name = msg[1]
        msg_args = msg[2]
        self.debug(f'received:notification {msg_name}')
        fname = f'on_{msg_name}'
        f = getattr(self, fname)
        f(msg_args)

    return True



  def cmd(self, name: str, args: []):
    msg = [0, self.command_id, name, args]
    self.debug(f'send:cmd:{msg}')
    d = msgpack.dumps(msg)
    self.pipe_in.write(d)
    self.pipe_in.flush()
    self.command_id += 1

  def nvim_input(self, keys):
    self.cmd('nvim_input', [keys])

  def nvim_input_mouse(self, button, action, modifier, row, col):
    self.cmd('nvim_input_mouse', [button, action, modifier, 0, row, col])

  def nvim_resize(self):
    self.cmd('nvim_ui_try_resize', [self.width, self.height]);

  def nvim_change_buffer(self, number):
    self.cmd('nvim_command', [f'b!{number}']);

  def nvim_open_buffer(self, path):
    self.cmd('nvim_command', [f'e!{path}']);

  def nvim_delete_buffer(self, path):
    self.cmd('nvim_command', [f'confirm bd{path}']);


  def on_buffers(self, opts):
    action = opts[0]
    buffer_number = int(opts[1])
    vim_path = opts[2]
    if not vim_path:
      # New files and things
      return 
    buffer_path = os.path.realpath(vim_path)
    self.debug(f'buffers {action} {buffer_number} {buffer_path}')
    if action == 'enter':
      self.b8.buffers.change(buffer_path, buffer_number)
    elif action == 'delete':
      self.b8.buffers.remove(buffer_path, buffer_number)


  def on_redraw(self, opts):
    for opt in opts:
      msg_name = opt[0]
      msg_args = opt[1:]
      fname = f'on_{msg_name}'
      #print(msg)
      f = getattr(self, fname, None)
      if f:
        f(*msg_args)
      else:
        self.error(f'missing function {fname}')

  def on_option_set(self, *args):
    self.options = {}
    for k, v in args:
      self.options[k] = v

  def on_update_menu(self, *args):
    self.debug(f'redraw:update_menu {args}')

  def on_default_colors_set(self, hl, *args):
    fg, bg, special, tfg, tbg = hl
    c = self.default_hl = Highlight()
    c.foreground = Color(fg)
    c.background = Color(bg)
    c.special = Color(special)


  def on_hl_attr_define(self, *args):
    for hl_id, cs, tcs, empty in args:
      c = self.highlights[hl_id] = Highlight()
      for k in cs:
        v = cs[k]
        if isinstance(v, int):
          v = Color(v)
        setattr(c, k, v)


  def on_hl_group_set(self, *args):
    self.debug(f'redraw:hl_group_set (not used)')
      
  def on_grid_resize(self, gridargs):
    grid_id, cols, rows = gridargs
    self.debug(f'redraw:grid_resize {grid_id} {cols} {rows}')
    self.grid = Grid(cols, rows)
    self.width = cols
    self.height = rows

  def on_grid_clear(self, *args):
    self.debug(f'redraw:grid_clear')

  def on_busy_start(self, *args):
    self.debug('redraw:busy start')

  def on_busy_stop(self, *args):
    self.debug('redraw:busy stop')

  def on_grid_cursor_goto(self, gridargs):
    grid_id, rows, cols = gridargs
    self.debug(f'redraw:grid_cursor_goto {cols} {rows}')
    self.cursor_x = cols
    self.cursor_y = rows

  def on_mouse_on(self, *args):
    """Mouse was put on, we ignore this. Leave it on!"""

  def on_mode_info_set(self, *args):
    modes = args[0][1]
    for mode in modes:
      m = ModeInfo()
      for k in mode:
        v = mode[k]
        setattr(m, k, v)
      self.modes[m.name] = m

  def on_mode_change(self, modeargs):
    self.debug('redraw:mode_change')
    mode_name = modeargs[0]
    mode_id = modeargs[1]
    self.current_mode = self.modes[mode_name]


  def on_grid_line(self, *args):
    self.debug('redraw:grid_line')
    for arg in args:
      row = arg[1]
      colstart = arg[2]
      cells = arg[3]

      last_hl = -1
      for cell in cells:
        text = cell[0]
        hl = last_hl
        repeat = 1
        if len(cell) > 1:
          hl = cell[1]
        if len(cell) > 2:
          repeat = cell[2]
        last_hl = hl

        for i in range(repeat):
          c = self.grid.cells[row][colstart]
          c.text = text
          c.hl = self.highlights.get(hl, self.default_hl)
          colstart += 1;

  def on_grid_scroll(self, scrollargs):
    grid_id, top, bottom, left, right, rows, cols = scrollargs

    if rows > 0:
      row = top
      while row <= bottom - rows:
        col = left
        while col < right:
          c = self.grid.cells[row][col]
          nc = self.grid.cells[min(row+rows, self.height-1)][col]
          c.text = nc.text
          c.hl = nc.hl
          col += 1
        row += 1
    else:
      row = bottom - 1
      while row >= top - rows:
        col = left
        while col < right:
          c = self.grid.cells[row][col]
          nc = self.grid.cells[row+rows][col]
          c.text = nc.text
          c.hl = nc.hl
          col += 1
        row -= 1
    


  def on_msg_showmode(self, *args):
    self.debug(f'msgshowmode {args}')


  def on_flush(self, *args):
    self.debug('redraw:flush')
    if self.flush_callback:
      self.flush_callback()




class VimView(B8View):

  button_pressed = None
  button_drag = None

  attempt_optimize = False
  old_grid = None
  old_surface = None

  def init(self):
    self.vim = self.b8.vim
    self.vim.flush_callback = self.queue_redraw
    self.drawing_area = Gtk.DrawingArea()
    self.view = self.drawing_area
    self.drawing_area.set_can_focus(True)
    self.drawing_area.connect('draw', self.on_draw)
    self.drawing_area.connect('realize', self.on_realize)
    self.drawing_area.connect('configure-event', self.on_configure_event)
    self.drawing_area.connect('size-allocate', self.on_size_allocate)
    self.drawing_area.add_events(Gdk.EventMask.KEY_PRESS_MASK |
                                 Gdk.EventMask.BUTTON_PRESS_MASK |
                                 Gdk.EventMask.BUTTON_RELEASE_MASK |
                                 Gdk.EventMask.POINTER_MOTION_MASK |
                                 Gdk.EventMask.SCROLL_MASK |
                                 Gdk.EventMask.FOCUS_CHANGE_MASK)
    self.drawing_area.connect('key-press-event', self.on_key_press_event)
    self.drawing_area.connect('button-press-event', self.on_button_press_event)
    self.drawing_area.connect('button-release-event', self.on_button_release_event)
    self.drawing_area.connect('motion-notify-event', self.on_motion_notify_event)
    self.drawing_area.connect('focus-in-event', self.on_focus_in_event)
    self.drawing_area.connect('focus-out-event', self.on_focus_out_event)
    self.drawing_area.connect('scroll-event', self.on_scroll_event)
    self._cairo_surface = None
    self.drawing_area

  def queue_redraw(self):
    self.drawing_area.queue_draw()

  def on_configure_event(self, w, event):
    self.debug(f'configure-event')


  def on_size_allocate(self, w, allocation):
    self.debug('size-allocate')
    ims = cairo.ImageSurface(cairo.FORMAT_RGB24, 300, 300)
    cr = cairo.Context(ims)
    font_name = self.b8.config.get('vim', 'font')
    self.font = Pango.font_description_from_string(font_name)
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(self.font)
    layout.set_alignment(Pango.Alignment.LEFT)
    layout.set_markup('<span>A</span>')
    self.cell_width, self.cell_height = layout.get_pixel_size()
    normal_width, normal_height = layout.get_size()

    rows = allocation.height / self.cell_height
    cols = allocation.width / self.cell_width

    self.draw_width = allocation.width
    self.draw_height = allocation.height
    self.draw_x = allocation.x
    self.draw_y = allocation.y
    self.vim.width = int(cols)
    self.vim.height = int(rows)

    if self.vim.started:
      self.vim.nvim_resize() 
    else:
      self.vim.start()

  def on_realize(self, w):
    self.debug('realize')
    self._pango_layout = PangoCairo.create_layout(w.get_window().cairo_create())
    self._pango_layout.set_alignment(Pango.Alignment.LEFT)
    self._pango_layout.set_font_description(self.font)
    self.drawing_area.queue_draw()
    self.drawing_area.grab_focus()

  def on_draw(self, w, cr):
    if not self.vim.grid:
      return

    w.get_window().freeze_updates()

    if self.attempt_optimize and self.old_surface:
      cr.move_to(0, 0)
      cr.set_source_surface(self.old_surface)
      #cr.rectangle(0, 0, self.draw_width, self.draw_height)
      #cr.fill()
      cr.paint()
    else:
      bg = self.vim.default_hl.background
      cr.set_source_rgb(bg.r, bg.g, bg.b)
      cr.paint()
    for (cy, row) in enumerate(self.vim.grid.cells):
      for (cx, cell) in enumerate(row):

        is_dirty = True
        if self.attempt_optimize and self.old_grid:
          old_cell = self.old_grid.cells[cy][cx]
          if cell.text == old_cell.text and cell.hl is old_cell.hl:
            is_dirty = False

        x = cx * self.cell_width
        y = cy * self.cell_height

        bg = None
        if cell.hl is None:
          bg = self.vim.default_hl.background
        else:
          bg = cell.hl.background
        if bg is None:
          bg = self.vim.default_hl.background

        fg = None
        if cell.hl is None:
          fg = self.vim.default_hl.foreground
        else:
          fg = cell.hl.foreground
        if fg is None:
          fg = self.vim.default_hl.foreground


        if cell.hl and cell.hl.reverse:
          fg, bg = bg, fg


        if bg is not self.vim.default_hl.background:
          cr.move_to(x, y)
          cr.set_source_rgb(bg.r, bg.g, bg.b)
          cr.rectangle(x, y, self.cell_width, self.cell_height)
          cr.fill()

        if cx == self.vim.cursor_x and cy == self.vim.cursor_y:
          cursorColor = self.vim.default_hl.foreground
          cr.set_source_rgb(cursorColor.r, cursorColor.g, cursorColor.b)
          cursor_width = self.cell_width
          if self.drawing_area.has_focus():
            if self.vim.current_mode.cell_percentage:
              cursor_width *= (self.vim.current_mode.cell_percentage / 100.0)
            else:
              fg = self.vim.default_hl.background
            cr.rectangle(x, y, cursor_width, self.cell_height)
            cr.fill()
          else:
            cr.set_line_width(1.2)
            cr.rectangle(x, y, cursor_width-1, self.cell_height-1)
            cr.stroke()


        if is_dirty and cell.text != ' ':
          cr.move_to(x, y)
          cr.set_source_rgb(fg.r, fg.g, fg.b)
          self._pango_layout.set_text(cell.text, -1)
          PangoCairo.update_layout(cr, self._pango_layout)
          PangoCairo.show_layout(cr, self._pango_layout)
          _, r = self._pango_layout.get_pixel_extents()


    w.get_window().thaw_updates()

    if self.attempt_optimize:
      self.old_surface =  w.get_window().create_similar_surface(cairo.CONTENT_COLOR, self.draw_width,
          self.draw_height)
      ocr = cairo.Context(self.old_surface)
      Gdk.cairo_set_source_window(ocr, w.get_window(), 0, 0)
      #ocr.set_source_surface(sfc, sfc.get_width() - self.draw_width, 0)
      #ocr.move_to(0, 0)
      #ocr.rectangle(0, 0, self.draw_width, self.draw_height)
      #ocr.fill()
      ocr.paint()
      self.old_grid = self.vim.grid.clone()

  def on_key_press_event(self, widget, event, *args):
    key_name = Gdk.keyval_name(event.keyval)
    # Fail fast on a known modifier
    if key_name in MODIFIER_NAMES:
      return
    utf8 = chr(Gdk.keyval_to_unicode(event.keyval))
    # Default to the character
    input_str = utf8
    # Known named keys
    if key_name in KEY_NAMES:
      input_str = KEY_NAMES[key_name]
    # Convert to <> format
    needs_stringify = (
      (key_name in KEY_NAMES) |
      event.state & Gdk.ModifierType.CONTROL_MASK |
      event.state & Gdk.ModifierType.MOD1_MASK
    )
    if needs_stringify:
      input_str = self.key_input(input_str, event.state)


    self.debug(f'keypress chr:{input_str} '
               f'utf8:{repr(utf8)} '
               f'name:{key_name} '
               f'state:{event.state}')

    if input_str == '\x00':
      self.error(f'empty string {key_name}')
    self.vim.nvim_input(input_str)
    return True


  def on_button_press_event(self, widget, event, *args):
    self.drawing_area.grab_focus()
    if event.type != Gdk.EventType.BUTTON_PRESS:
      return
    
    button = BUTTON_NAMES.get(event.button)
    if not button:
      return
    
    mod, row, col = self.parse_mouse(event)
    self.vim.nvim_input_mouse(button, 'press', mod, row, col)
    self.button_pressed = button
    return True

  def on_button_release_event(self, widget, event, *args):
    self.button_pressed = None
    self.button_drag = False

  def on_motion_notify_event(self, widget, event, *args):
    if not self.button_pressed:
        return
    if not self.button_drag:
      self.button_drag = True
    mod, row, col = self.parse_mouse(event)
    self.vim.nvim_input_mouse(self.button_pressed, 'drag', mod, row, col)

  def on_scroll_event(self, widget, event, *args):
    if event.direction == Gdk.ScrollDirection.UP:
      direction = 'up'
    elif event.direction == Gdk.ScrollDirection.DOWN:
      direction = 'down'
    else:
      return
    mod, row, col = self.parse_mouse(event)
    self.vim.nvim_input_mouse('wheel', direction, mod, row, col)


  def on_focus_in_event(self, widget, event):
    self.debug('focus in')
    self.queue_redraw()

  def on_focus_out_event(self, widget, event):
    self.debug('focus out')
    self.queue_redraw()


  def parse_mouse(self, event):
    col = int(math.floor(event.x / self.cell_width))
    row = int(math.floor(event.y / self.cell_height))
    mods = []
    if event.state & Gdk.ModifierType.SHIFT_MASK:
      out.append('S')
    if event.state & Gdk.ModifierType.CONTROL_MASK:
      out.append('C')
    if event.state & Gdk.ModifierType.MOD1_MASK:
      out.append('A')
    mod = ''.join(mods)
    return mod, row, col



  def key_input(self, input_str, state):
    out = []
    if state & Gdk.ModifierType.SHIFT_MASK:
      out.append('S')
    if state & Gdk.ModifierType.CONTROL_MASK:
      out.append('C')
    if state & Gdk.ModifierType.MOD1_MASK:
      out.append('A')
    out.append(input_str)
    return f'<{"-".join(out)}>'

    

MODIFIER_NAMES = {
    'Shift_L',
    'Shift_R',
    'Control_L',
    'Control_R',
    'Alt_R',
    'Alt_L'
}

BUTTON_NAMES = {
    1: 'left',
    2: 'middle',
    3: 'right',
}

KEY_NAMES = {
    'less': 'LT',
    'BackSpace': 'BS',
    'Return': 'CR',
    'Escape': 'Esc',
    'Delete': 'Del',
    'Page_Up': 'PageUp',
    'Page_Down': 'PageDown',
    'Enter': 'CR',
    'ISO_Left_Tab': 'Tab',
    'Right': 'Right',
    'Left': 'Left',
    'Up': 'Up',
    'Down': 'Down',
    'Insert': 'Insert',
    'End': 'End',
    'Home': 'Home',
}

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


def main():
  b8 = B8()
  if b8.running:
    b8.run()


if __name__ == '__main__':
  main()
