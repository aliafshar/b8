# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

"""The Bominade file browser."""

import os

from gi.repository import Gio, GLib, GObject, Gdk, Gtk, GdkPixbuf, Pango

from b8 import ui


DEFAULT_FILE_ATTRIBUTES = '*'


class FileListItem:
  """Item to go in the file list.

  This is a thin wrapper over a Gio.FileInfo.
  """

  def __init__(self, info: Gio.FileInfo, parent: Gio.File):
    self.info = info
    self.parent = parent
    self.name = info.get_name()
    self.path = parent.get_child(self.name).get_path()
    self.file = parent.get_child(self.name)
    icon_to_load = Gtk.IconTheme.get_default().choose_icon(
        self.info.get_icon().get_names(),
        Gtk.IconSize.SMALL_TOOLBAR, 0
    )
    if icon_to_load:
      self.icon = icon_to_load.load_icon()
    else:
      self.icon = None
    self.file_type = self.info.get_file_type()
    self.is_directory = self.file_type == Gio.FileType.DIRECTORY
    if self.is_directory:
      self.sort_prefix = 0
    else:
      self.sort_prefix = 1
    self.sort_key = f'{self.sort_prefix}_{self.name}'


class Files(Gtk.VBox, ui.MenuHandlerMixin):
  """File browser widget."""

  __gtype_name__ = 'b8-files'

  __gsignals__ = {
    'directory-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'file-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'file-destroyed': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'terminal-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'directory-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
  }

  directory = GObject.Property(type=Gio.File)
  show_hidden = GObject.Property(type=bool, default=False)

  def __init__(self):
    """Generate the user interface."""
    Gtk.VBox.__init__(self)
    self.title = self.create_title_label()
    self.pack_start(self.create_toolbar(), False, False, 0)
    c = Gtk.ScrolledWindow()
    self.pack_start(c, True, True, 0)
    self.model = self.create_model()
    self.tree = self.create_tree(self.model)
    c.add(self.tree)
    self.connect('notify::directory', self.on_directory_notify)

  def create_model(self):
    """Create the tree model."""
    m = Gtk.ListStore(
        object,
        GObject.TYPE_STRING, # sort key
        GdkPixbuf.Pixbuf, # icon
        GObject.TYPE_STRING, # name
        GObject.TYPE_STRING, # mod
        Gdk.RGBA, # mod color
    )
    m.set_sort_column_id(1, Gtk.SortType.ASCENDING)
    return m

  def create_tree(self, m: Gtk.ListStore):
    """Create the tree view."""
    t = Gtk.TreeView(m)
    t.set_activate_on_single_click(False)
    t.set_headers_visible(False)
    t.connect('row-activated', self.on_row_activated)
    t.connect('button-press-event', self.on_button_press_event)

    ce_icon = Gtk.CellRendererPixbuf()
    co_icon = Gtk.TreeViewColumn('Icon', ce_icon)
    co_icon.add_attribute(ce_icon, 'pixbuf', 2)
    t.append_column(co_icon)

    ce_mods = Gtk.CellRendererText()
    ce_mods.set_property('weight', 800)
    co_mods = Gtk.TreeViewColumn('Modifiers', ce_mods)
    co_mods.add_attribute(ce_mods, 'markup', 4)
    co_mods.add_attribute(ce_mods, 'foreground-rgba', 5)
    t.append_column(co_mods)

    ce_name = Gtk.CellRendererText()
    co_name = Gtk.TreeViewColumn('Filename', ce_name)
    co_name.set_expand(True)
    co_name.add_attribute(ce_name, 'text', 3)
    t.append_column(co_name)
    return t

  def create_title_label(self):
    """Create the current directory label"""
    l = Gtk.Label()
    l.set_ellipsize(Pango.EllipsizeMode.START)
    return l

  def create_toolbar(self):
    """Create the mini toolbar."""
    self.title_label = Gtk.Label()
    t = ui.MiniToolbar.horizontal(
        [
          ui.ImageButton(
            key='up',
            icon='go-up',
            tooltip='Navigate to the parent directory',
          ),
          ui.ImageButton(
            key='refresh',
            icon='view-refresh',
            tooltip='Refresh the current directory',
          ),
          ui.ImageButton(
            key='terminal',
            icon='utilities-terminal',
            tooltip='Start a terminal in this directory',
          ),
          self.title,
          ui.ImageToggleButton(
            key='hidden',
            icon='view-more',
            tooltip='Show or hide hidden files',
          ),
        ]
    )
    t.connect('clicked', self.on_toolbar_clicked)
    return t

  def browse_path(self, path: str, refresh: bool=False):
    """Browse the given path."""
    if self.directory and self.directory.get_path() == path:
      if not refresh:
        return

    f = Gio.File.new_for_path(path)
    f.enumerate_children_async(
      DEFAULT_FILE_ATTRIBUTES,
      Gio.FileQueryInfoFlags.NONE,
      GLib.PRIORITY_DEFAULT,
      None, # cancellable
      self.browse_path_callback,
      f,
    )

  def browse(self, gfile: Gio.File, refresh: bool=True):
    self.browse_path(gfile.get_path(), refresh=refresh)

  def refresh(self):
    """Refresh the current path."""
    self.browse(self.directory, refresh=True)

  def browse_path_callback(self, src, res, parent: Gio.File) -> None:
    """Async callback for finishing a File list enumeration."""
    self.model.clear()
    self.directory = parent
    for file_info in src.enumerate_children_finish(res):
      if not self.show_hidden and file_info.get_is_hidden():
        continue
      f = FileListItem(file_info, parent)
      self.append(f)
    self.git_revparse()

  def append(self, f):
    """Append an item to the model."""
    self.model.append([f, f.sort_key, f.icon, f.name, '', None])

  def git_revparse_callback(self, src, res):
    """Async callback for revparse command."""
    success, stdout, stderr = src.communicate_finish(res)
    if not success:
      return
    d = stdout.get_data().strip().decode('utf-8')
    self.git_status(Gio.File.new_for_path(d))

  def git_revparse(self):
    """Get the Git root directory."""
    l = Gio.SubprocessLauncher()
    l.set_flags(Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
    l.set_cwd(self.directory.get_path())
    p = l.spawnv(['git', 'rev-parse', '--show-toplevel'])
    p.communicate_async(None, None, self.git_revparse_callback)

  def git_status_callback(self, src, res, parent):
    """Async callback for finishing a git status call."""
    success, stdout, stderr = src.communicate_finish(res)
    if not success:
      return
    d = stdout.get_data().decode('utf-8').splitlines()
    mods = {}
    cols = {
      'M': ui.Colors.RED,
      '??': ui.Colors.GREEN,
    }
    for line in d:
      line = line.strip().rstrip('/')
      mod, name = line.split()
      path = parent.get_child(name).get_path()
      mods[path] = mod
    for row in self.model:
      path = self.model.get_value(row.iter, 0).file.get_path()
      mod = mods.get(os.path.realpath(path))
      if mod:
        self.model.set_value(row.iter, 4, mod)
        c = cols.get(mod, ui.Colors.GREEN)
        self.model.set_value(row.iter, 5, c)

  def git_status(self, parent):
    """Call git status on the current directory."""
    l = Gio.SubprocessLauncher()
    l.set_flags(Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
    l.set_cwd(self.directory.get_path())
    p = l.spawnv(['git', 'status', '--porcelain', '.'])
    p.communicate_async(None, None, self.git_status_callback, parent)

  def on_menu_activate(self, w, m, key, gfile):
    """Callback for menu item being activated."""
    fname = f'on_{key}_activate'
    f = getattr(self, fname)
    f(m, gfile)

  def on_toolbar_clicked(self, w, b, key):
    """Callback for toolbar button being clicked."""
    fname = f'on_{key}_clicked'
    f = getattr(self, fname)
    f(b)

  def on_up_clicked(self, b):
    parent = self.directory.get_parent()
    if parent:
      self.browse(parent)

  def on_terminal_clicked(self, b):
    self.emit('terminal-activated', self.directory)

  def on_hidden_clicked(self, b):
    self.show_hidden = b.get_active()
    self.refresh()

  def on_refresh_clicked(self, b):
    self.refresh()

  def on_row_activated(self, w, path, column):
    giter = self.model.get_iter(path)
    f = self.model.get_value(giter, 0)
    if f.is_directory:
      self.emit('directory-activated', f.file)
    else:
      child = self.directory.get_child(f.name)
      self.emit('file-activated', child)

  def on_button_press_event(self, w, event):
    if event.button != Gdk.BUTTON_SECONDARY:
      return
    spec = w.get_path_at_pos(int(event.x), int(event.y))
    if not spec:
      return
    path, c, rx, ry = spec
    giter = self.model.get_iter(path)
    f = self.model.get_value(giter, 0)
    if f.is_directory:
      menu = ui.DirectoryPopupMenu(f.file)
    else:
      menu = ui.FilePopupMenu(f.file, suppress=['browseparent'])
    menu.connect('activate', self._on_menu_activate)
    menu.popup(event)
    return True

  def on_directory_notify(self, w, prop):
    self.title.set_label(self.directory.get_path())
    self.emit('directory-changed', self.directory)


if __name__ == '__main__':
  w = Gtk.Window()
  w.connect('destroy', Gtk.main_quit)
  fs = Files(None)
  fs.create_ui()
  w.add(fs)
  w.resize(400, 400)
  w.show_all()

  fs.browse_path('/home/aa/src/bominade')

  def term_activated(w, f):
    print('term-activated', w, f, f.get_path())

  def file_activated(w, f):
    print('file-activated', w, f, f.get_path())

  def directory_changed(w, f):
    print('directory-changed', w, f, f.get_path())

  def directory_activated(w, f):
    print('directory activate')
    w.browse(f)

  def file_destroyed(w, f):
    print('file-destroyed', w, f, f.get_path())

  fs.connect('terminal-activated', term_activated)
  fs.connect('file-activated', file_activated)
  fs.connect('directory-changed', directory_changed)
  fs.connect('directory-activated', directory_activated)
  fs.connect('file-destroyed', file_destroyed)


  Gtk.main()
