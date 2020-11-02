# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

"""Embeddable NeoVim for PyGTK.

This module can be used entirely on its own separate from B8. This is a basic
requirement of the thing. It is also a clean-room implementation as it uses
NeoVim's `ext_linegrid` as the older methods are depracated and the existing
PyGTK widget for NeoVim uses the depracated method.

Consider the bare minimum script:

    w = Gtk.Window()
    w.connect('destroy', Gtk.main_quit)
    w.resize(800, 600)

    vim = Embedded()
    w.add(vim)


    def on_vim_started(widget):
      # Show the window once Vim has started and given use the right Gui options,
      # i.e. the font.
      w.show_all()

    # the `started` signal tells us Vim is up and running and configured enough to
    # display.
    vim.connect('started', on_vim_started)

    Gtk.main()

The startup flow is a bit annoying because we don't want to display the widget
until Vim is started and has told us the value of `guifont` otherwise we will
guess a size of the Vim grid and then have tor esize in front of the user which
will be janky at least. In reality it's worse than just jank. We don't have
enough data to render a widget so we'd have to just show a blank screen.
"""

from typing import Iterable, List
import msgpack
from gi.repository import Gio, GLib, GObject, Gdk, Gtk, Pango, PangoCairo
import cairo

from b8 import ui, logs


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

  def copy_to(self, c):
    c.text = self.text
    c.hl = self.hl

  def is_same(self, other):
    return self.text == other.text and self.hl is other.hl


class Mode(GObject.GObject):
  """Information about a NeoVim mode."""

  __gtype_name__ = 'b8-vim-modeinfo'

  name = GObject.Property(type=str)

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
  short_name = None

  def __repr__(self):
    return f'<Mode name={self.name} {self.cursor_shape} {self.mouse_shape}>'


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

  def __repr__(self):
    return f'<Highlight fg={self.foreground} bg={self.background}>'


class Color:
  """NeoVim color with conversion to RGB"""

  def __init__(self, color_value):
    self.r = ((color_value >> 16) & 255) / 256.0
    self.g = ((color_value >> 8) & 255) / 256.0
    self.b = (color_value & 255) / 256.0

  def __repr__(self):
    return f'Color<{self.r} {self.g} {self.b}>'


class Cursor(GObject.GObject):

  __gtype_name__ = 'b8-vim-cursorposition'

  x = GObject.Property(type=int, default=0)
  y = GObject.Property(type=int, default=0)

  def __init__(self, x, y):
    GObject.GObject.__init__(self)
    self.x = x
    self.y = y

  def __repr__(self):
    return f'<Cursor x={self.x} y={self.y}'


class Buffer(GObject.GObject):

  __gtype_name__ = 'b8-vim-buffer'

  number = GObject.Property(type=int)
  file = GObject.Property(type=Gio.File)

  def __init__(self, number, file):
    GObject.GObject.__init__(self)
    self.number = number
    self.file = file
    self.path = file.get_path()
    self.parent = file.get_parent()
    self.name = file.get_basename()
    self.ename = GLib.markup_escape_text(self.name)
    self.eparent = GLib.markup_escape_text(self.parent.get_path())
    self.markup = (f'<span size="medium" weight="bold">{self.ename}</span>\n'
                   f'<span size="x-small">{self.parent.get_path()}</span>')

  @classmethod
  def from_ext_hook(cls, ext_data):
    """Alternative constructor from msgpack protocol."""
    return cls(msgpack.unpackb(ext_data), None)


class Result(GObject.GObject):

  __gtype_name__ = 'b8-vim-result'

  __gsignals__ = {
      'success': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
      'error': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
  }

  def __init__(self, cid, name, args):
    GObject.GObject.__init__(self)
    self.cid = cid
    self.name = name
    self.args = args

  def respond(self, cid, error, success):
    if error:
      self.emit('error', error)
    else:
      self.emit('success', success)


class Drag(GObject.GObject):

  __gtype_name__ = 'b8-vim-drag'

  button = GObject.Property(type=int)
  pressed = GObject.Property(type=bool, default=False)


class Embedded(Gtk.DrawingArea, logs.LoggerMixin):

  __gtype_name__ = 'b8-vim'

  __gsignals__ = {
      'ready': (GObject.SignalFlags.RUN_FIRST, None, ()),
      'exited': (GObject.SignalFlags.RUN_FIRST, None, ()),
      'buffer-changed': (GObject.SignalFlags.RUN_FIRST, None, (int, Gio.File,)),
      'buffer-deleted': (GObject.SignalFlags.RUN_FIRST, None, (int, Gio.File,)),
      'mode-changed': (GObject.SignalFlags.RUN_FIRST, None, (Mode,)),
      'cursor-changed': (GObject.SignalFlags.RUN_FIRST, None, (Cursor,)),
  }

  cursor = GObject.Property(type=Cursor, default=Cursor(0, 0))
  width = GObject.Property(type=int, default=20)
  height = GObject.Property(type=int, default=20)
  cid = GObject.Property(type=int, default=0)
  mode = GObject.Property(type=Mode)

  button_drag = False
  button_pressed = False

  def __init__(self):
    Gtk.DrawingArea.__init__(self)
    logs.LoggerMixin.__init__(self)
    self.unpacker = msgpack.Unpacker(ext_hook=self._ext_hook, raw=False)
    self.options = {}
    self.highlights = {}
    self.mode = None
    self.modes = {}
    self.pending_commands = {}
    self.drag = Drag()
    self.default_highlight = None
    self.button_pressed = None
    self.set_can_focus(True)
    self.add_events(Gdk.EventMask.KEY_PRESS_MASK |
                                 Gdk.EventMask.BUTTON_PRESS_MASK |
                                 Gdk.EventMask.BUTTON_RELEASE_MASK |
                                 Gdk.EventMask.POINTER_MOTION_MASK |
                                 Gdk.EventMask.SCROLL_MASK |
                                 Gdk.EventMask.FOCUS_CHANGE_MASK)
    self.connect('size-allocate', self._on_size_allocate)
    self.connect('realize', self._on_realize)
    self.connect('draw', self._on_draw)
    self.connect('key-press-event', self._on_key_press_event)
    self.connect('button-press-event', self._on_button_press_event)
    self.connect('button-release-event', self._on_button_release_event)
    self.connect('motion-notify-event', self._on_motion_notify_event)
    self.connect('focus-in-event', self._on_focus_in_event)
    self.connect('focus-out-event', self._on_focus_out_event)
    self.connect('scroll-event', self._on_scroll_event)
    self.connect('notify::mode', self._on_notify_mode)
    self.connect('notify::cursor', self._on_notify_cursor)

  def open_buffer(self, path):
    self._cmd('nvim_command', [f'e!{path}']);

  def change_buffer(self, bnum):
    self._cmd('nvim_command', [f'b!{bnum}']);

  def close_buffer(self, path):
    self._cmd('nvim_command', [f'confirm bd{path}']);

  def command(self, name, *args):
    return self._cmd(name, list(args))

  def start(self):
    self._start()

  def _ext_hook(self, ext_type, ext_data):
    """Called when NeoVim sends extended type information."""
    if ext_type == 0:
      return Buffer.from_ext_hook(ext_data)

  def _generate_message(self, name: str, args: list):
    self.cid = (self.cid + 1) % 256
    return [0, self.cid, name, args]

  def _serialize_message(self, msg: list) -> str:
    return msgpack.dumps(msg)

  def _cmd(self, name: str, args: list) -> int:
    msg = self._generate_message(name, args)
    d = self._serialize_message(msg)
    self.vim_in.write_all(d, None)
    r = self.pending_commands[self.cid] = Result(self.cid, name, args)
    return r

  def _out_callback(self, *args):
    if self.vim_out.is_readable():
      d = self.vim_out.read_bytes(1024)
      self.unpacker.feed(d.get_data())
      for msg in self.unpacker:
        self._msg_callback(msg)
    return True

  def _msg_callback(self, msg):
    msg_handlers = {
        1: self._reply_callback,
        2: self._notification_callback,
    }
    msg_handlers[msg[0]](msg[1:])

  def _reply_callback(self, msg):
    rid, err, result = msg
    result = self.pending_commands.pop(rid)
    result.respond(rid, err, result)
    self.debug(f'reply {msg}')

  def _notification_callback(self, msg):
    msg_handlers = {
        'buffers': self._buffers_callback,
        'system': self._system_callback,
        'redraw': self._redraw_callback,
    }
    msg_handlers[msg[0]](msg[1])

  def _buffers_callback(self, msg):
    action, bs, path = msg
    if not path:
      return
    bnum = int(bs)
    gf = Gio.File.new_for_path(path)
    msg_handlers = {
        'enter': self._buffers_enter_callback,
        'delete': self._buffers_delete_callback,
    }
    f = msg_handlers.get(action)
    if f:
      f(bnum, gf)
    else:
      print('unhandled buffers', msg)
    print('buffers', msg)

  def _buffers_enter_callback(self, bnum, f):
    self.emit('buffer-changed', bnum, f)
  
  def _buffers_delete_callback(self, bnum, f):
    self.emit('buffer-deleted', bnum, f)
  
  def _system_callback(self, msg):
    action = msg[0]
    msg_handlers = {
        'leave': self._system_leave_callback,
    }
    f = msg_handlers.get(action)
    if f:
      f()
    else:
      print('unhandled system', msg)

  def _system_leave_callback(self):
    """Called for a Vim VimLeave notification."""
    self.emit('exited')

  def _redraw_callback(self, msgs):
    """Called for a Vim redraw notification."""
    msg_handlers = {
        'grid_resize': self._grid_resize_callback,
        'option_set': self._option_set_callback,
        'default_colors_set': self._default_colors_set_callback,
        'hl_attr_define': self._hl_attr_define_callback,
        'grid_cursor_goto': self._grid_cursor_goto_callback,
        'mode_info_set': self._mode_info_set_callback,
        'mode_change': self._mode_change_callback,
        'grid_line': self._grid_line_callback,
        'grid_scroll': self._grid_scoll_callback,
        'flush': self._flush_callback,
    }
    for msg in msgs:
      f = msg_handlers.get(msg[0])
      if f:
        f(*msg[1:])
      else:
        self.debug(f'redraw unhandled {msg[0]}, {len(msg)}')

  def _grid_resize_callback(self, msg):
    gid, cols, rows = msg
    self.grid = Grid(cols, rows)

  def _option_set_callback(self, *args):
    self.options.update(args)
    if self.options.get('guifont'):
      self._calculate_font_size()
      self.emit('ready')

  def _default_colors_set_callback(self, hl):
    fg, bg, special, tfg, tbg = hl
    c = self.default_highlight = Highlight()
    c.foreground = Color(fg)
    c.background = Color(bg)
    c.special = Color(special)

  def _hl_attr_define_callback(self, *args):
    for hl_id, cs, tcs, empty in args:
      c = self.highlights[hl_id] = Highlight()
      for k in cs:
        v = cs[k]
        if isinstance(v, int):
          v = Color(v)
        setattr(c, k, v)

  def _mode_info_set_callback(self, *args):
    modes = args[0][1]
    for mode in modes:
      m = Mode()
      for k in mode:
        v = mode[k]
        setattr(m, k, v)
      self.modes[m.name] = m

  def _mode_change_callback(self, msg):
    mode_name = msg[0]
    mode_id = msg[1]
    self.mode = self.modes[mode_name]

  def _grid_cursor_goto_callback(self, msg):
    gid, rows, cols = msg
    self.cursor = Cursor(cols, rows)

  def _grid_line_callback(self, *args):
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
          c.hl = self.highlights.get(hl)
          colstart += 1

  def _grid_scoll_callback(self, msg):
    gid, top, bottom, left, right, rows, cols = msg
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

  def _flush_callback(self, *args):
    self.queue_draw()

  def _start(self):
    p = Gio.Subprocess.new(['nvim', '--embed'],
        Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE |
        Gio.SubprocessFlags.STDIN_PIPE)
    self.vim_in = p.get_stdin_pipe()
    self.vim_out = p.get_stdout_pipe()
    source = self.vim_out.create_source()
    source.set_callback(self._out_callback)
    source.attach(None)

    self._vim_attach()
    self._vim_subscribe()

  def _calculate_font_size(self):
    self.font_name = self.options['guifont']
    self.font_desc = Pango.font_description_from_string(self.font_name)
    sfc = cairo.ImageSurface(cairo.FORMAT_RGB24, 300, 300)
    cr = cairo.Context(sfc)
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(self.font_desc)
    layout.set_alignment(Pango.Alignment.LEFT)
    layout.set_markup('<span>M</span>')
    self.cell_width, self.cell_height = layout.get_pixel_size()

  def _on_size_allocate(self, w, alloc):
    self.width = int(alloc.width / self.cell_width)
    self.height = int(alloc.height / self.cell_height)
    self._vim_resize()

  def _on_realize(self, w):
    self.pango_layout = PangoCairo.create_layout(w.get_window().cairo_create())
    self.pango_layout.set_alignment(Pango.Alignment.LEFT)
    self.pango_layout.set_font_description(self.font_desc)

  def _on_key_press_event(self, widget, event, *args):
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
      input_str = self._key_input(input_str, event.state)


    self.debug(f'keypress chr:{input_str} '
               f'utf8:{repr(utf8)} '
               f'name:{key_name} '
               f'state:{event.state}')

    if input_str == '\x00':
      self.error(f'empty string {key_name}')
    self._vim_input(input_str)
    return True


  def _on_button_press_event(self, widget, event, *args):
    self.grab_focus()
    if event.type != Gdk.EventType.BUTTON_PRESS:
      return
    
    button = BUTTON_NAMES.get(event.button)
    if not button:
      return
    
    mod, row, col = self._parse_mouse(event)
    self._vim_input_mouse(button, 'press', mod, row, col)
    self.button_pressed = button
    return True

  def _on_button_release_event(self, widget, event, *args):
    self.button_pressed = None
    self.button_drag = False

  def _on_motion_notify_event(self, widget, event, *args):
    if not self.button_pressed:
        return
    if not self.button_drag:
      self.button_drag = True
    mod, row, col = self._parse_mouse(event)
    self._vim_input_mouse(self.button_pressed, 'drag', mod, row, col)

  def _on_scroll_event(self, widget, event, *args):
    if event.direction == Gdk.ScrollDirection.UP:
      direction = 'up'
    elif event.direction == Gdk.ScrollDirection.DOWN:
      direction = 'down'
    else:
      return
    mod, row, col = self._parse_mouse(event)
    self._vim_input_mouse('wheel', direction, mod, row, col)


  def _on_focus_in_event(self, widget, event):
    self.queue_draw()

  def _on_focus_out_event(self, widget, event):
    self.queue_draw()

  def _on_notify_mode(self, w, prop):
    self.emit('mode-changed', self.mode)

  def _on_notify_cursor(self, w, prop):
    self.emit('cursor-changed', self.cursor)

  def _parse_mouse(self, event):
    col = int(event.x / self.cell_width)
    row = int(event.y / self.cell_height)
    mods = []
    if event.state & Gdk.ModifierType.SHIFT_MASK:
      out.append('S')
    if event.state & Gdk.ModifierType.CONTROL_MASK:
      out.append('C')
    if event.state & Gdk.ModifierType.MOD1_MASK:
      out.append('A')
    mod = ''.join(mods)
    return mod, row, col

  def _key_input(self, input_str, state):
    out = []
    if state & Gdk.ModifierType.SHIFT_MASK:
      out.append('S')
    if state & Gdk.ModifierType.CONTROL_MASK:
      out.append('C')
    if state & Gdk.ModifierType.MOD1_MASK:
      out.append('A')
    out.append(input_str)
    return f'<{"-".join(out)}>'

  def _on_draw(self, w, cr):
    w.get_window().freeze_updates()
    bg = self.default_highlight.background
    cr.set_source_rgb(bg.r, bg.g, bg.b)
    cr.paint()
    for (cy, row) in enumerate(self.grid.cells):
      for (cx, cell) in enumerate(row):


        x = cx * self.cell_width
        y = cy * self.cell_height

        bg = None
        if cell.hl is None:
          bg = self.default_highlight.background
        else:
          bg = cell.hl.background
        if bg is None:
          bg = self.default_highlight.background

        fg = None
        if cell.hl is None:
          fg = self.default_highlight.foreground
        else:
          fg = cell.hl.foreground
        if fg is None:
          fg = self.default_highlight.foreground


        if cell.hl and cell.hl.reverse:
          fg, bg = bg, fg

        if bg is not self.default_highlight.background:
          cr.move_to(x, y)
          cr.set_source_rgb(bg.r, bg.g, bg.b)
          cr.rectangle(x, y, self.cell_width, self.cell_height)
          cr.fill()

        if cx == self.cursor.x and cy == self.cursor.y:
          cursorColor = self.default_highlight.foreground
          cr.set_source_rgb(cursorColor.r, cursorColor.g, cursorColor.b)
          cursor_width = self.cell_width
          if self.has_focus():
            if self.mode.cell_percentage:
              cursor_width *= (self.mode.cell_percentage / 100.0)
            else:
              fg = self.default_highlight.background
            cr.rectangle(x, y, cursor_width, self.cell_height)
            cr.fill()
          else:
            cr.set_line_width(1.2)
            cr.rectangle(x, y, cursor_width-1, self.cell_height-1)
            cr.stroke()

        if cell.text != ' ':
          cr.move_to(x, y)
          cr.set_source_rgb(fg.r, fg.g, fg.b)
          self.pango_layout.set_text(cell.text, -1)
          PangoCairo.update_layout(cr, self.pango_layout)
          PangoCairo.show_layout(cr, self.pango_layout)
          _, r = self.pango_layout.get_pixel_extents()

    w.get_window().thaw_updates()


  def _vim_attach(self):
    self._cmd('nvim_ui_attach', [self.width, self.height, {'ext_linegrid':
      True}])

  def _vim_subscribe(self):
    types = set()
    for sig in VIM_SIGNALS:
      self._cmd('nvim_command', [VIM_SIGNAL_TEMPLATE.format(*sig)])
      types.add(sig[1])
    for t in types:
      self._cmd('nvim_subscribe', [t]);


  def _vim_resize(self):
    self._cmd('nvim_ui_try_resize', [self.width, self.height])

  def _vim_input(self, keys):
    self._cmd('nvim_input', [keys])

  def _vim_input_mouse(self, button, action, modifier, row, col):
    self._cmd('nvim_input_mouse', [button, action, modifier, 0, row, col])


VIM_SIGNAL_TEMPLATE = 'autocmd {} * call rpcnotify(0, "{}", "{}", {})'

VIM_SIGNALS = [
    ('BufAdd', 'buffers', 'add', 'expand("<abuf>"), expand("<amatch>")'),
    ('BufEnter', 'buffers', 'enter', 'expand("<abuf>"), expand("<amatch>")'),
    ('BufDelete', 'buffers', 'delete', 'expand("<abuf>"), expand("<amatch>")'),
    ('VimLeave', 'system', 'leave', ''),
]



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

if __name__ == '__main__':
  w = Gtk.Window()
  w.connect('destroy', Gtk.main_quit)
  w.resize(400, 400)

  v = Embedded()
  w.add(v)

  def on_list_bufs(r, bufs):
    print(['onlistbufs', bufs])

  def on_buffer_changed(e, bnum, path):
    print('buffer changed', bnum, path)
    v.command('nvim_list_bufs').connect('success', on_list_bufs)

  def on_buffer_deleted(e, bnum, path):
    print('buffer deleted', bnum, path)

  def on_mode(e, mode):
    print(mode)

  def on_exited(e):
    print('vim exited')
    Gtk.main_quit()

  v.connect('buffer-changed', on_buffer_changed)
  v.connect('buffer-deleted', on_buffer_deleted)
  v.connect('exited', on_exited)
  v.connect('mode-changed', on_mode)

  def on_vim_started(e):
    w.show_all()
    print('ready', w)




  v.connect('ready', on_vim_started)
  v._start()


  #GLib.log_writer_standard_streams(
  #    GLib.LogLevelFlags.LEVEL_INFO)

  #s = GLib.String()
  #s.append('ffs')

  #field = GLib.LogField()
  #field.key = 'msg'
  #field.value = s
  #GLib.log_structured_array(GLib.LogLevelFlags.LEVEL_INFO, [field])
  #v._cmd('blah', [1,2,3])

  Gtk.main()
