# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80


"""The Bominade file browser."""


import os

from gi.repository import Gio, GLib, GObject, Gdk, Gtk, GdkPixbuf, Pango

from b8 import ui, vim, logs



class Buffers(Gtk.ScrolledWindow, ui.MenuHandlerMixin, logs.LoggerMixin):

  __gtype_name__ = 'b8-buffers'

  __gsignals__ = {
    'directory-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'file-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'file-destroyed': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'terminal-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'directory-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gio.File,)),
    'buffer-activated':(GObject.SignalFlags.RUN_FIRST, None, (vim.Buffer,)),
  }
 
  
  def __init__(self):
    Gtk.ScrolledWindow.__init__(self)
    logs.LoggerMixin.__init__(self)
    self.model = self._create_model()
    self.tree = self._create_tree(self.model)
    self.add(self.tree)

  def _create_model(self):
    m = Gtk.ListStore(object, str)
    return m

  def _create_tree(self, model):
    t = Gtk.TreeView(model=model)
    t.set_headers_visible(False)
    ce = Gtk.CellRendererText()
    ce.set_padding(6, 1)
    co = Gtk.TreeViewColumn('name', ce)
    co.add_attribute(ce, 'markup', 1)
    t.append_column(co)
    t.connect('row-activated', self.on_row_activated)
    t.connect('button-press-event', self.on_button_press_event)
    t.set_activate_on_single_click(True)
    return t

  def next(self):
    l = self.model.iter_n_children(None)
    if not l:
      return
    m, siter = self.tree.get_selection().get_selected()
    giter = self.model.iter_next(siter)
    if not giter:
      # We are at the end or there is only 1, doesn't matter
      giter = self.model.iter_nth_child(None, 0)
    self.activate_iter(giter)

  def prev(self):
    l = self.model.iter_n_children(None)
    if not l:
      return
    m, siter = self.tree.get_selection().get_selected()
    giter = self.model.iter_previous(siter)
    if not giter:
      # We are at the beginning or there is only 1, doesn't matter
      giter = self.model.iter_nth_child(None, l - 1)
    self.activate_iter(giter)

  def activate_iter(self, giter):
    b = self.model.get_value(giter, 0)
    self.emit('buffer-activated', b)
    
  def select(self, giter):
    selection = self.tree.get_selection()
    m, siter = selection.get_selected()
    if siter != giter:
      self.tree.get_selection().select_iter(giter)
    b = self.model.get(giter, 0)[0]
    self.debug(f'select {b}')
    #self.b8.ui.window.set_title(b.path)
    #self.b8.ui.vimview.drawing_area.grab_focus()

  def change(self, f, number):
    self.debug(f'buffer change {f.get_path()} {number}')
    for grow in self.model:
      b = self.model.get_value(grow.iter, 0)

      if b.number == number and b.path == f.get_path():
        self.debug(f'existing {b}')
        self.select(grow.iter)
        return
    b = vim.Buffer(number, f)
    giter = self.model.append([b, b.markup])
    self.select(giter)
    #self.b8.sessions.buffers.append(b.path)
    #self.b8.sessions.save()

  def remove(self, f, number):
    for grow in self.model:
      b = self.model.get_value(grow.iter, 0)
      print(b.path, f.get_path())
      if b.number == number and b.path == os.path.realpath(f.get_path()):
        self.model.remove(grow.iter)
        #self.b8.sessions.buffers.remove(b.path)
        #self.b8.sessions.save()
        return


  def on_row_activated(self, w, path, column):
    giter = self.model.get_iter(path)
    b = self.model.get(giter, 0)[0]
    #self.b8.vim.nvim_change_buffer(b.number)
    self.emit('buffer-activated', b)
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
      menu = ui.FilePopupMenu(b.file)
      menu.connect('activate', self._on_menu_activate)
      menu.popup(event)
      return True

if __name__ == '__main__':
  w = Gtk.Window()
  w.connect('destroy', Gtk.main_quit)
  fs = Buffers()
  w.add(fs)
  w.resize(400, 400)
  w.show_all()

  fs.change(Gio.File.new_for_path('/home/aa/.vimrc'), 1)
  fs.change(Gio.File.new_for_path('/home/aa/.zshrc'), 1)


  def term_activated(w, f):
    print('term-activated', w, f, f.get_path())

  def file_activated(w, f):
    print('file-activated', w, f, f.get_path())

  def directory_changed(w, f):
    print('directory-changed', w, f, f.get_path())

  def directory_activated(w, f):
    print('directory activate')
    w.browse(f)

  def buffer_activated(w, b):
    print('buffer-activated', b)

  def file_destroyed(w, f):
    print('file-destroyed', w, f, f.get_path())

  fs.connect('terminal-activated', term_activated)
  fs.connect('file-activated', file_activated)
  fs.connect('directory-changed', directory_changed)
  fs.connect('directory-activated', directory_activated)
  fs.connect('file-destroyed', file_destroyed)
  fs.connect('buffer-activated', buffer_activated)


  Gtk.main()
