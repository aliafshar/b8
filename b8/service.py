# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

import uuid

from gi.repository import Gio, Gtk, GObject, GLib

import msgpack

from b8 import logs

logs.LoggerMixin.level = 0


class Runtime(GObject.GObject, logs.LoggerMixin):

  __gtype_name__ = 'b8-service-runtime'

  root = GObject.Property(type=Gio.File)

  def __init__(self):
    GObject.GObject.__init__(self)
    logs.LoggerMixin.__init__(self)
    run = Gio.File.new_for_path(GLib.get_user_runtime_dir())
    self.root = run.get_child('b8')
    
    try:
      self.root.make_directory()
    except GLib.Error:
      pass

  def clean(self):
    pass

  def server(self):
    uid = uuid.uuid4()
    return self.root.get_child(f'{uid}.sock')

  def available(self):
    cs = self.root.enumerate_children('*', Gio.FileQueryInfoFlags.NONE, None)
    for info in cs:
      gf = self.root.get_child(info.get_name())
      c = Client(gf)
      resp = c.ping()
      if resp:
        yield c
      else:
        c.gfile.delete(None)





class Service(Gio.SocketService, logs.LoggerMixin):

  __gtype_name__ = 'b8-service'

  run = GObject.Property(type=Runtime)
  address = GObject.Property(type=Gio.UnixSocketAddress)
  gfile = GObject.Property(type=Gio.File)

  def __init__(self, b8):
    Gio.SocketService.__init__(self)
    logs.LoggerMixin.__init__(self)
    self.b8 = b8
    self.run = Runtime()
    self.gfile = self.run.server()
    self.address = Gio.UnixSocketAddress.new(self.gfile.get_path())
    self.connect('incoming', self._on_incoming)

  def start(self):
    self.add_address(self.address,
                     Gio.SocketType.STREAM,
                     Gio.SocketProtocol.DEFAULT,
                     None)
    self.debug(f'started at {self.gfile.get_path()}')


  def _on_reply(self, stream, task):
    stream.write_bytes_finish(task)

  def _on_read(self, stream, task, conn):
    bs = stream.read_bytes_finish(task) 
    cmd, args = msgpack.unpackb(bs.get_data())
    self.debug(f'incoming: {cmd} {args}')
    resp = self.b8._on_service(cmd, args)
    self.debug(f'outgoing: {resp}')
    out = conn.get_output_stream()
    out.write_bytes_async(GLib.Bytes.new(msgpack.packb(resp)), 0, None,
        self._on_reply)

  def _on_incoming(self, svc, conn, *args):
    stream = conn.get_input_stream()
    stream.read_bytes_async(8192, 0, None, self._on_read, conn)

  def _on_cmd_ping(self):
    return 'pong'

  def shutdown(self):
    #self.close()
    self.gfile.delete(None)


class Client(Gio.SocketClient, logs.LoggerMixin):

  __gtype_name__ = 'b8-service-client'

  run = GObject.Property(type=Runtime)
  address = GObject.Property(type=Gio.UnixSocketAddress)
  gfile = GObject.Property(type=Gio.File)

  def __init__(self, gfile):
    Gio.SocketClient.__init__(self)
    logs.LoggerMixin.__init__(self)
    self.run = Runtime()
    self.gfile = gfile
    self.address = Gio.UnixSocketAddress.new(self.gfile.get_path())

  def ping(self):
    self.debug('calling ping')
    return self.command('ping')

  def open(self, files):
    self.debug('calling open')
    resp = self.command('open', files)
    self.info(f'received {resp}')
    return resp

  def command(self, name, args=None):
    if not args:
      args = []
    try:
      conn = self.connect(self.address, None)
    except GLib.Error:
      self.debug(f'bad socket {self.gfile.get_path()}')
      return
    out = conn.get_output_stream()
    msg = msgpack.packb([name, args])
    out.write_bytes(GLib.Bytes.new(msg))
    inp = conn.get_input_stream()
    bs = inp.read_bytes(8192)
    msg = msgpack.unpackb(bs.get_data())
    self.debug(f'reply {msg}')
    return msg





if __name__ == '__main__':
  #ty = Gio.SocketType.STREAM
  #pr = Gio.SocketProtocol.DEFAULT
  #addr = Gio.UnixSocketAddress.new('banana.sock')
  #l = Gio.SocketService()
  #l.add_address(addr, ty, pr, None)
  #l.connect('incoming', on_incoming)

  #svc = Service()
  
  run = Runtime()

  #client = Client(run.available())

  def on_quit(w, event):
    print('quit')
    #svc.shutdown()
    Gtk.main_quit()

  w = Gtk.Window()
  b = Gtk.HBox()
  w.add(b)
  w.connect('delete-event', on_quit)
  w.resize(500, 500)

  def on_but(b, i):
    print(i)
    if i == 0:
      client.command('button', [i])
    if i == 1:
      client.command('ping')

  for i in range(5):
    bt = Gtk.Button()
    bt.set_label(str(i))
    bt.connect('clicked', on_but, i)
    b.pack_start(bt, True, True, 0)

  r = Runtime()
  for c in r.available():
    print(c)

  w.show_all()

  Gtk.main()

