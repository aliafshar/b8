# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80


from gi.repository import Gio, GLib, GObject

import os, argparse, configparser

import b8
from b8 import logs



class Item(GObject.GObject):

  __gtype_name__ = 'b8-config-item'

  section = GObject.Property(type=str)
  name = GObject.Property(type=str)
  default = GObject.Property(type=str)
  value = GObject.Property(type=str)
  description = GObject.Property(type=str)
  short = GObject.Property(type=str)

  def __init__(self, section: str, name: str, default: str, description: str):
    GObject.GObject.__init__(self)
    self.section = section
    self.name = name
    self.default = default
    self.description = description

  def prime_argparser(self, p):
    p.add_argument(self.arg_name, help=self.description)

  def read_argparser(self, ns):
    return getattr(ns, self.ns_key)

  def read_configparser(self, p):
    return p.get(self.section, self.name, fallback=None)

  def read_env(self, e):
    pass

  @property
  def key(self):
    return (self.section, self.name)

  @property
  def arg_name(self):
    return f'--{self.section}-{self.name}'

  @property
  def ns_name(self):
    return self.name.replace('-', '_')

  @property
  def ns_key(self):
    return f'{self.section}_{self.ns_name}'




class Instance(GObject.GObject):

  __gtype_name__  = 'b8-config-instance'

  def __init__(self):
    GObject.GObect.__init__(self)

  def init(self):
    self.root_path = os.path.expanduser('~/.config/b8')
    self.run_path = os.path.join(self.root_path, 'run')
    self.config_path = os.path.join(self.root_path, 'b8rc')
    self.sessions_path = os.path.join(self.root_path, 'session.json')
    self.create()
  
  # Switch to Gio
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


CONFIG_DIR = Gio.File.new_for_path(GLib.get_user_config_dir()).get_child('b8')
CONFIG_FILE = CONFIG_DIR.get_child('b8.ini')
CONFIG_EMPTY = '# Bominade Config File\n##\n'.encode('utf-8')

class ConfigError(RuntimeError):
  """Error with configuration."""


class Config(GObject.GObject, logs.LoggerMixin):

  __gtype_name__ = 'b8-config'

  root = GObject.Property(type=Gio.File, default=CONFIG_DIR)
  file = GObject.Property(type=Gio.File, default=CONFIG_FILE)

  items = [
      Item('logging', 'level', 'info',
        'The logging level to use'),
      Item('terminal', 'theme', 'b8',
        'The terminal theme to use'),
      Item('terminal', 'font', 'Monospace 13',
        'The terminal font to use, e.g. "Monospace 13"'),
      Item('shortcuts', 'previous-buffer', '<Alt>Up',
        'Shortcut key to switch to the previous buffer'),
      Item('shortcuts', 'next-buffer', '<Alt>Down',
        'Shortcut key to switch to the next buffer'),
      Item('shortcuts', 'previous-terminal', '<Alt>Left',
        'Shortcut key to switch to the previous terminal'),
      Item('shortcuts', 'next-terminal', '<Alt>Right',
        'Shortcut key to switch to the next terminal'),
      Item('shortcuts', 'new-terminal', '<Alt>t', 
        'Shortcut key to create a new terminal'),
  ]

  def __init__(self):
    GObject.GObject.__init__(self)
    logs.LoggerMixin.__init__(self)
    self._create_root()
    self.values = {}
    self._read_default()
    ns = self._read_args()
    self._read_configparser()
    self._read_argparser(ns)
    logs.LoggerMixin.set_level(self.values['logging', 'level'])
    self.debug(f'root user directory is at {self.root.get_path()}')
    self.debug('values', data=self.values)

  def _create_root(self):
    try:
      self.root.make_directory_with_parents(None)
    except GLib.Error as e:
      if e.code != Gio.IOErrorEnum.EXISTS:
        raise
    if not self.file.query_exists(None):
      f = self.file.create_readwrite(Gio.FileCreateFlags.NONE, None)
      s = f.get_output_stream()
      s.write(CONFIG_EMPTY)
      s.close()

  def _read_default(self):
    for item in self.items:
      self.values[item.key] = item.default

  def _read_configparser(self):
    p = configparser.ConfigParser()
    p.read(self.file.get_path())
    for item in self.items:
      v = item.read_configparser(p)
      if v is not None:
        self.values[item.key] = v

  def _read_args(self):
    p = argparse.ArgumentParser(
        prog = 'b8',
        description = f'The bominade IDE, version {b8.__version__}',
    )
    p.add_argument('-d', '--debug', action='store_true',
        help='Run with logging level debug')
    p.add_argument('-f', '--config', help='Configuration file to use',
        default=self.file.get_path())
    for item in self.items:
      item.prime_argparser(p)
    ns = p.parse_args()
    if ns.config:
      self.file = Gio.File.new_for_path(os.path.expanduser(ns.config))
      if not self.file.query_exists(None):
        e = f'config file "{ns.config}" does not exist'
        self.error(e)
        raise ConfigError(e)
    if ns.debug:
      ns.logging_level = 'debug'
    return ns

  def _read_argparser(self, ns):
    for item in self.items:
      v = item.read_argparser(ns)
      if v is not None:
        self.values[item.key] = v

  def get(self, key):
    return self.values.get(key)


if __name__ == '__main__':
  c = Config()
