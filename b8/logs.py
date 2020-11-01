# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

"""Simple logging to stdout/stderr."""

import datetime, pprint

class Level:
  DEBUG = 0
  INFO = 1
  ERROR = 2
  CRITICAL = 3

  @staticmethod
  def name(level: int) -> str:
    return {
        Level.DEBUG: 'D',
        Level.INFO: 'I',
        Level.ERROR: 'E',
        Level.CRITICAL: 'C',
    }.get(level)

    


class LoggerMixin:

  level = Level.INFO

  @classmethod
  def set_level(cls, lstr):
    LoggerMixin.level = {
        'debug': Level.DEBUG,
        'info': Level.INFO,
        'error': Level.ERROR,
        'critical': Level.CRITICAL,
    }.get(lstr)

  def __init__(self):
    self.name = self.__gtype_name__

  def msg(self, msg: str, level: int):
    if level >= LoggerMixin.level:
      print(f'{Level.name(level)}:{self.name}:{msg}')

  def debug(self, msg: str, data=None):
    if LoggerMixin.level:
      return
    if data:
      msg = f'{msg} ->\n{pprint.pformat(data)}\n<-'
    self.msg(msg, Level.DEBUG)

  def info(self, msg: str):
    self.msg(msg, Level.INFO)

  def error(self, msg: str):
    self.msg(msg, Level.ERROR)

