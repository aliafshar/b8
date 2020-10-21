
# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

import math, os, pwd, subprocess, sys, threading, uuid

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
    print(f'{level}:{self.__class__.__name__}:{msg}')

  def debug(self, msg):
    """Debug a message."""
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

  def mini_button(self, icon_name, toolip, btype=Gtk.Button):
    b = btype()
    i = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.SMALL_TOOLBAR)
    b.set_image(i)
    return b




class B8:
  """The Bominade monolith.

  This knows about everything. And everything knows about it.
  No doubt there are circular references and leaks everywhere.
  """

  def __init__(self):
    self.instance = Instance(self)
    self.ipc = Ipc(self)
    self.contexts = Contexts(self)
    self.vim = Vim(self)
    self.buffers = Buffers(self)
    self.files = Files(self)
    self.terminals = Terminals(self)
    self.ui = B8Window(self)

  def show_path(self, path, is_dir=False):
    if is_dir or os.path.isdir(path):
      self.files.browse(path)
    else:
      self.vim.nvim_open_buffer(path)
      self.vim.view.grab_focus()

  def show_shell(self, path):
    self.terminals.create(path)

  def close_path(self, path):
    self.vim.nvim_delete_buffer(path)

  def run(self):
    """Run until the Gtk main loop ends."""
    Gtk.main()

  def quit(self):
    self.ipc.destroy()
    Gtk.main_quit()


class B8Window(B8View):
  """Bominade top-level window."""

  def create_ui(self):
    self.window = Gtk.Window()
    self.window.set_icon_name('media-seek-forward')
    self.window.set_title('b8 <3 u')

    #self.window.connect('configure-event', self.on_configure_event)

    #self.window.connect('destroy', Gtk.main_quit)

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


class Instance(B8Object):

  def init(self):
    self.root_path = os.path.expanduser('~/.config/b8')
    self.run_path = os.path.join(self.root_path, 'run')
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






class Ipc(B8Object):

  def init(self):
    pass

  def destroy(self):
    pass



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
    return Gtk.Label(self.label_text)

  def menuitem(self):
    item = Gtk.ImageMenuItem()
    item.set_label(self.label_text)
    item.set_image(self.icon())
    item.set_always_show_image(True)
    return item



class Config:

  class Terminal:
    ColorForeground='#839496'
    ColorBackground='#002b36'
    ColorCursor='#93a1a1'
    ColorPalette='#073642;#dc322f;#859900;#b58900;#268bd2;#d33682;#2aa198;#eee8d5;#002b36;#cb4b16;#586e75;#657b83;#839496;#6c71c4;#93a1a1;#fdf6e3'
    ColorBold='#93a1a1'





class Contexts(B8Object):

  BUFFER = 'buffer'
  FILE = 'file'
  DIRECTORY = 'firectory'

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
      'file': (
          r'"([^"]|\\")+"|' + \
          r"'[^']+'|" + \
          r'(\\ |\\\(|\\\)|\\=|[^]\[[:space:]"\':\$()=])+'
      )
  }


  def init(self):
    pass

  def regex(self, name):
    return GLib.Regex(self.ereg_exprs[name], 0, 0) 

  def on_open(self, path):
    print('open')

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


  


class Terminals(B8View):

  def create_ui(self):
    widget = Gtk.HBox()
    self.book = Gtk.Notebook()
    self.book.set_tab_pos(Gtk.PositionType.BOTTOM)
    self.book.set_scrollable(True)
    widget.pack_start(self.book, True, True, 0)
    self.create(os.path.expanduser('~'))
    return widget

  def create(self, wd):
    t = TerminalView(self.b8)
    pagenum = self.book.append_page(t.widget, t.create_tab_label())
    self.book.show_all()
    self.book.set_current_page(pagenum)
    t.start(wd)



class TerminalView(B8View):

  child_pid = 0 
  child_cwd = ''
  linked_browser = False

  def create_ui(self):
    self.term = Vte.Terminal()
    self.term.match_add_gregex(self.b8.contexts.regex('file'), 0)
    self.term.match_set_cursor(0, Gdk.Cursor(Gdk.CursorType.HAND2))
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
    #self.configure()
    return widget

  def connect_ui(self):
    self.connect('clicked', self.link_button, 'link_button')
    self.connect('clicked', self.browse_button, 'browse_button')
    self.connect('clicked', self.copy_button, 'copy_button')
    self.connect('clicked', self.paste_button, 'paste_button')
    self.connect('clicked', self.select_button, 'select_button')
    self.connect('clicked', self.term_button, 'term_button')

  def configure(self):
    fg = Gdk.RGBA()
    fg.parse(Config.Terminal.ColorForeground)
    bg = Gdk.RGBA()
    bg.parse(Config.Terminal.ColorBackground)
    pl = [Gdk.RGBA() for i in range(16)]
    pl = []
    for s in Config.Terminal.ColorPalette.split(';'):
      c = Gdk.RGBA()
      c.parse(s)
      pl.append(c)
    self.term.set_colors(fg, bg, pl)


  def start(self, wd):
    self.child_cwd = wd
    (success, self.child_pid) = self.term.spawn_sync(Vte.PtyFlags.DEFAULT,
            self.child_cwd, [self.get_default_shell()], [],
        GLib.SpawnFlags.DEFAULT, None, None, None);
    GLib.timeout_add(500, self.label_updater)
    self.update_label()
    self.widget.grab_focus()

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
    new_cwd = self.get_cwd()
    if new_cwd != self.child_cwd:
      self.child_cwd = new_cwd
      self.update_label()
      if self.linked_browser:
        self.b8.show_path(self.child_cwd)
    return True

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
    print(event.button)
    selected = None
    action = None
    m, tag = w.match_check_event(event)
    if not m:
      # Fail fast if not matching.
      return
    if tag == 0:
      path = os.path.join(self.child_cwd, m)
      if os.path.exists(path):
        selected = path

    if event.button == Gdk.BUTTON_PRIMARY:
      self.b8.show_path(selected)
    elif event.button == Gdk.BUTTON_SECONDARY:
      if os.path.isdir(selected):
        action = 'directory'
      else:
        action = 'file'
      menu = self.b8.contexts.menu(action, selected)
      menu.popup(None, None, None, None, event.button, event.time)

  def on_file_menu_activated(self, w, action, data):
    print (w, action, data)

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
    self.path = path
    self.number = number
    self.name = os.path.basename(path)
    self.parent = os.path.dirname(path)
    self.ename = GLib.markup_escape_text(self.name)
    self.eparent = GLib.markup_escape_text(self.parent)
    self.markup = (f'<span size="medium" weight="bold">{self.ename}</span>\n'
                   f'<span size="x-small">{self.parent}</span>')


class Fileish:

  path = ''

  def __init__(self, name, parent):
    self.name = name
    self.parent = parent
    self.path = os.path.join(self.parent, name)
    self.is_dir = os.path.isdir(self.path)
    if self.is_dir:
      self.prefix='0'
      self.icon = Gtk.STOCK_DIRECTORY
    else:
      self.prefix='1'
      self.icon = Gtk.STOCK_FILE
    self.ename = GLib.markup_escape_text(self.name)
    self.sortable = f'{self.prefix}_{self.name}'
    self.markup = f'<span size="medium">{self.ename}</span>'








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
    self.tree.set_activate_on_single_click(True)
    widget = Gtk.ScrolledWindow()
    widget.add(self.tree)
    return widget

  
  def has(self, path):
    pass
    
  def select(self, giter):
    print('select', giter)
    selection = self.tree.get_selection()

    if selection.get_selected() != giter:
      self.tree.get_selection().select_iter(giter)

    self.b8.ui.window.set_title(self.model.get(giter, 0)[0].path)
    self.b8.ui.vimview.drawing_area.grab_focus()

  def change(self, path, number):
    for grow in self.model:
      b = self.model.get_value(grow.iter, 0)

      if b.number == number and b.path == path:
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
    print('row-activated', b)

  def render(self, cell_layout, cell, tree_model, iter, *data):
    b = tree_model.get_value(iter, 0)
    cell.set_property('markup', b.markup)



class Files(B8View):

  current_path = None

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
    self.icon_cell.set_padding(3, 1)
    self.icon_column = Gtk.TreeViewColumn('icon', self.icon_cell)
    self.icon_column.set_cell_data_func(self.icon_cell, self.render_icon)
    self.tree.append_column(self.icon_column)
    self.model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
    self.tree.append_column(self.column)
    self.tree.connect('row-activated', self.on_row_activated)
    self.tree.connect('button-press-event', self.on_button_press_event)
    self.tree.set_activate_on_single_click(False)

    #pixbuf = Gtk.IconTheme.get_default().load_icon('utilities-terminal',
    #    Gtk.IconSize.SMALL_TOOBAR, 0)

    #print([k for k in Gtk.IconTheme.get_default().list_icons() if 'terminal' in
    #  k])

    #w = Gtk.Image.new_from_icon_name('utilities-x-terminal',
    #    Gtk.IconSize.LARGE_TOOLBAR)
    #print(w)


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

    tools.pack_start(self.up_button, expand=False, fill=False, padding=0)
    tools.pack_start(self.refresh_button, expand=False, fill=False, padding=0)
    tools.pack_start(self.terminal_button, expand=False, fill=False,
        padding=0)


    self.up_button.connect('clicked', self.on_up_button_clicked)
    self.refresh_button.connect('clicked', self.on_refresh_button_clicked)
    self.terminal_button.connect('clicked', self.on_terminal_button_clicked)

    p = os.path.expanduser('~')
    self.browse(p)
    return widget


  def render(self, cell_layout, cell, tree_model, iter, *data):
    b = tree_model.get_value(iter, 0)
    cell.set_property('markup', b.markup)

  def render_icon(self, cell_layout, cell, tree_model, iter, *data):
    b = tree_model.get_value(iter, 0)
    cell.set_property('icon_name', b.icon)

  def on_row_activated(self, w, path, column):
    print('row-activated')
    giter = self.model.get_iter(path)
    f = self.model.get_value(giter, 0)
    if f.is_dir:
      self.browse(f.path)
    else:
      self.b8.vim.nvim_open_buffer(f.path)
      self.b8.vim.view.grab_focus()

  def on_button_press_event(self, treeview, event):
    print('button', event.button)
    if event.button != Gdk.BUTTON_SECONDARY:
      return
    item_spec = self.tree.get_path_at_pos(int(event.x), int(event.y))
    print(item_spec)
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
      f = Fileish(p, path)
      if f.name.startswith('.'):
        continue
      GLib.idle_add(self.append, f)

  def browse(self, path, refresh=False):
    if refresh or path != self.current_path:
      self.debug(f'browsing {path}')
      self.current_path = path
      t = threading.Thread(target=self.browse_thread, args=(path,))
      t.start()
      self.model.clear()
    else:
      self.debug(f'not browsing the path I am already at {path}')

  def on_up_button_clicked(self, w):
    parent = os.path.dirname(self.current_path)
    self.browse(parent)

  def on_refresh_button_clicked(self, w):
    self.browse(self.current_path)

  def on_terminal_button_clicked(self, w):
    print('terminal button')
    self.b8.show_shell(self.current_path)



class Grid:
  """NeoVim grid"""

  def __init__(self, width, height):
    self.width = width
    self.height = height
    self.cells = [[Cell() for col in range(self.width)] for col in
        range(self.height)]


class Cell:
  """Single cell within a NeoVim grid"""
  text = ''  
  hl = None


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
  width = 0
  height = 0
  started = False
  current_buffer = None

  def init(self):
    self.grid = None
    self.unpacker = msgpack.Unpacker()
    self.flush_callback = None
    self.highlights = {}
    self.modes = {}
    self.current_mode = None

  def start(self):
    if not self.width and self.height:
      return

    self.started = True

    self.proc = subprocess.Popen(['/usr/bin/nvim', '--embed'],
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
    self.info('rcvd:raw data')
    while True:
      d = os.read(self.fd_out, 1024)
      self.unpacker.feed(d)
      if len(d) < 1024:
        break
    for msg in self.unpacker:
      msg_type = msg[0]

      if msg_type == 1:
        self.info(f'rcvd:reply {msg}')

      elif msg_type == 2:
        msg_name = msg[1].decode('utf-8')
        msg_args = msg[2]
        self.info(f'rcvd:notification "{msg_name}"')
        fname = f'on_{msg_name}'
        f = getattr(self, fname)
        f(msg_args)

    return True



  def cmd(self, name: str, args: []):
    msg = [0, self.command_id, name, args]
    self.info(f'send:cmd:{msg}')
    d = msgpack.dumps(msg)
    self.pipe_in.write(d)
    self.pipe_in.flush()
    self.command_id += 1

  def nvim_input(self, keys):
    self.cmd('nvim_input', [keys])

  def nvim_resize(self):
    self.cmd('nvim_ui_try_resize', [self.width, self.height]);

  def nvim_change_buffer(self, number):
    self.cmd('nvim_command', [f'b!{number}']);

  def nvim_open_buffer(self, path):
    self.cmd('nvim_command', [f'e!{path}']);

  def nvim_delete_buffer(self, path):
    self.cmd('nvim_command', [f'confirm bd{path}']);


  def on_buffers(self, opts):
    action = opts[0].decode('utf-8')
    buffer_number = int(opts[1])
    buffer_path = opts[2].decode('utf-8')
    if action == 'enter':
      if not buffer_path:
        return
      self.b8.buffers.change(buffer_path, buffer_number)
    elif action == 'delete':
      print(action, buffer_path)
      if not buffer_path:
        return
      self.b8.buffers.remove(buffer_path, buffer_number)
      

    print('buffer', action, buffer_number, buffer_path)

  def on_redraw(self, opts):
    for opt in opts:
      msg_name = opt[0].decode('utf-8')
      msg_args = opt[1:]
      fname = f'on_{msg_name}'
      #print(msg)
      f = getattr(self, fname)
      f(*msg_args)

  def on_option_set(self, *args):
    self.options = {}
    for bk, bv in args:
      k = bk.decode('utf-8')
      v = bv
      if isinstance(bv, bytes):
        v = bv.decode('utf-8')
      self.options[k] = v

  def on_default_colors_set(self, hl, *args):
    fg, bg, special, tfg, tbg = hl
    c = self.default_hl = Highlight()
    c.foreground = Color(fg)
    c.background = Color(bg)
    c.special = Color(special)


  def on_hl_attr_define(self, *args):
    for hl_id, cs, tcs, empty in args:
      c = self.highlights[hl_id] = Highlight()
      for bk in cs:
        k = bk.decode('utf-8')
        v = cs[bk]
        if isinstance(v, int):
          v = Color(v)
        setattr(c, k, v)


  def on_hl_group_set(self, *args):
    print('hl_group_set not used')
      
  def on_grid_resize(self, gridargs):
    grid_id, cols, rows = gridargs
    print('grid  resize', grid_id, cols, rows)
    self.grid = Grid(cols, rows)
    self.width = cols
    self.height = rows

  def on_grid_clear(self, *args):
    print('grid clear', args)

  def on_busy_start(self, *args):
    print('busy start', args)

  def on_busy_stop(self, *args):
    print('busy stop', args)

  def on_grid_cursor_goto(self, gridargs):
    grid_id, rows, cols = gridargs
    print('grid  cursor goto', grid_id, cols, rows)
    self.cursor_x = cols
    self.cursor_y = rows

  def on_mode_info_set(self, *args):
    modes = args[0][1]
    for mode in modes:
      m = ModeInfo()
      for bk in mode:
        k = bk.decode('utf-8')
        bv = v = mode[bk]
        if isinstance(bv, bytes):
          v = bv.decode('utf-8')
        setattr(m, k, v)
      self.modes[m.name] = m

  def on_mode_change(self, modeargs):
    mode_name = modeargs[0].decode('utf-8')
    mode_id = modeargs[1]
    self.current_mode = self.modes[mode_name]

    print('mode change', mode_name, mode_id)

  def on_grid_line(self, *args):
    print('grid_line')
    for arg in args:
      row = arg[1]
      colstart = arg[2]
      cells = arg[3]

      last_hl = -1
      for cell in cells:
        text = cell[0].decode('utf-8')
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
    #for col in self.grid.cells:
    #  print(''.join([c.text for c in col]))

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
    print('msgshowmode', args)


  def on_flush(self, *args):
    print('flush')
    if self.flush_callback:
      self.flush_callback()


SHIFT = Gdk.ModifierType.SHIFT_MASK
CTRL = Gdk.ModifierType.CONTROL_MASK
ALT = Gdk.ModifierType.MOD1_MASK


MODIFIERS = {'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_R', 'Alt_L'}

class VimView:

  button_pressed = None
  button_drag = None

  def __init__(self, b8):
    self.b8 = b8
    self.vim = b8.vim
    self.vim.flush_callback = self.queue_redraw
    self.drawing_area = Gtk.DrawingArea()
    self.view = self.drawing_area
    self.drawing_area.set_can_focus(True)
    self.drawing_area.connect('draw', self._gtk_draw)
    self.drawing_area.connect('realize', self._gtk_realize)
    self.drawing_area.connect('configure-event', self.on_configure_event)
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

  def queue_redraw(self):
    self.drawing_area.queue_draw()

  def on_configure_event(self, w, event):
    print('configure', w, event, event.height, event.width)

    ims = cairo.ImageSurface(cairo.FORMAT_RGB24, 300, 300)
    cr = cairo.Context(ims)
    self._font = Pango.font_description_from_string('Liberation Mono 11')
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(self._font)
    layout.set_alignment(Pango.Alignment.LEFT)
    layout.set_markup('<span font_weight="bold">A</span>')
    bold_width, bold_height = layout.get_size()
    layout.set_markup('<span>A</span>')
    self.cell_width, self.cell_height = layout.get_pixel_size()
    normal_width, normal_height = layout.get_size()

    rows = event.height / self.cell_height
    cols = event.width / self.cell_width
    self.vim.width = int(cols)
    self.vim.height = int(rows)

    if self.vim.started:
      self.vim.nvim_resize() 
    else:
      self.vim.start()


  def _gtk_realize(self, w):
    print('realize')
    content = cairo.CONTENT_COLOR
    gdkwin = self.drawing_area.get_window()
    self._cairo_surface = gdkwin.create_similar_surface(content,
                                                        self.cell_width,
                                                        self.cell_height)
    self._cairo_context = cairo.Context(self._cairo_surface)
    self._pango_layout = PangoCairo.create_layout(self._cairo_context)
    self._pango_layout.set_alignment(Pango.Alignment.LEFT)
    self._pango_layout.set_font_description(self._font)
    self.drawing_area.queue_draw()
    self.drawing_area.grab_focus()

  def _gtk_draw(self, wid, cr):
    if not self._cairo_surface:
      return
    if not self.vim.grid:
      return
    #self._cairo_surface.flush()
    #cr.save()
    #cr.rectangle(0, 0, self.vim.width * self.cell_width, self.vim.height *
    #    self.cell_height)
    #cr.clip()
    #cr.set_source_surface(self._cairo_surface, 0, 0)
    #cr.paint()
    #cr.restore()

    bg = self.vim.default_hl.background
    cr.set_source_rgb(bg.r, bg.g, bg.b)
    cr.paint()
    for (cy, row) in enumerate(self.vim.grid.cells):
      for (cx, cell) in enumerate(row):
        # Draw the text
        #x, y = self._get_coords(row, col)
        x = cx * self.cell_width
        y = cy * self.cell_height
        #if cursor and self._insert_cursor:
        #    cr.rectangle(x, y, self._cell_pixel_width / 4,
        #                 self._cell_pixel_height)
        #    cr.clip()
        cr.move_to(x, y)

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

        cr.move_to(x, y)
        cr.set_source_rgb(fg.r, fg.g, fg.b)

        if cell.text != ' ':
          self._pango_layout.set_text(cell.text, -1)
          PangoCairo.update_layout(cr, self._pango_layout)
          PangoCairo.show_layout(cr, self._pango_layout)
          _, r = self._pango_layout.get_pixel_extents()
        #cr.show_text(cell.text)

  def on_key_press_event(self, widget, event, *args):
    keyval = event.keyval
    state = event.state
    if Gdk.keyval_name(event.keyval) in MODIFIERS:
        # We don't need to track the state of modifier bits
        return
    # translate keyval to nvim key
    key_name = Gdk.keyval_name(keyval)
    if key_name.startswith('KP_'):
        key_name = key_name[3:]
    #input_str = _stringify_key(KEY_TABLE.get(key_name, key_name), state)
    #input_str = KEY_TABLE.get(key_name, key_name)

    input_str = chr(Gdk.keyval_to_unicode(keyval))



    #input_str = key_name
    if key_name in KEY_TABLE:
      input_str = _stringify_key(KEY_TABLE[key_name], state)
    #print(input_str)
    self.vim.nvim_input(input_str)
    return True


  def on_button_press_event(self, widget, event, *args):
    self.drawing_area.grab_focus()
    if event.type != Gdk.EventType.BUTTON_PRESS:
        return
    button = 'Left'
    if event.button == 2:
        button = 'Middle'
    elif event.button == 3:
        button = 'Right'
    col = int(math.floor(event.x / self.cell_width))
    row = int(math.floor(event.y / self.cell_height))
    input_str = _stringify_key(button + 'Mouse', event.state)
    input_str += '<{0},{1}>'.format(col, row)
    self.vim.nvim_input(input_str)
    self.button_pressed = button
    return True

  def on_button_release_event(self, widget, event, *args):
    self.button_pressed = None
    self.button_drag = False

  def on_motion_notify_event(self, widget, event, *args):
    if not self.button_pressed:
        return
    if not self.button_drag:
      self.vim.cmd('nvim_input', ['<Esc>v'])
      self.button_drag = True
    col = int(math.floor(event.x / self.cell_width))
    row = int(math.floor(event.y / self.cell_height))
    input_str = _stringify_key(self.button_pressed + 'Drag', event.state)
    input_str += '<{0},{1}>'.format(col, row)
    self.vim.nvim_input(input_str)

  def on_scroll_event(self, widget, event, *args):
    col = int(math.floor(event.x / self.cell_width))
    row = int(math.floor(event.y / self.cell_width))
    if event.direction == Gdk.ScrollDirection.UP:
        key = 'ScrollWheelUp'
    elif event.direction == Gdk.ScrollDirection.DOWN:
        key = 'ScrollWheelDown'
    else:
        return
    input_str = _stringify_key(key, event.state)
    input_str += '<{0},{1}>'.format(col, row)
    self.vim.nvim_input(input_str)

  def on_focus_in_event(self, widget, event):
    print('focus in')
    self.queue_redraw()

  def on_focus_out_event(self, widget, event):
    print('focus out')
    self.queue_redraw()
    

def _stringify_key(key, state):
    send = []
    if state & SHIFT:
        send.append('S')
    if state & CTRL:
        send.append('C')
    if state & ALT:
        send.append('A')
    send.append(key)
    return '<' + '-'.join(send) + '>'


# Translation table for the names returned by Gdk.keyval_name that don't match
# the corresponding nvim key names.
KEY_TABLE = {
    #'slash': '/',
    #'backslash': '\\',
    #'dead_circumflex': '^',
    #'at': '@',
    #'numbersign': '#',
    #'dollar': '$',
    #'percent': '%',
    #'ampersand': '&',
    #'asterisk': '*',
    #'parenleft': '(',
    #'parenright': ')',
    #'underscore': '_',
    #'plus': '+',
    #'minus': '-',
    #'bracketleft': '[',
    #'bracketright': ']',
    #'braceleft': '{',
    #'braceright': '}',
    #'dead_diaeresis': '"',
    #'dead_acute': "'",
    #'less': "<",
    #'greater': ">",
    #'comma': ",",
    #'period': ".",
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
}

def main():
  b8 = B8()
  b8.run()


if __name__ == '__main__':
  main()
