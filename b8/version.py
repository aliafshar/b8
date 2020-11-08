# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

"""B8 version information"""

VERSION  = '0.2.1'

def parse():
  return VERSION.split('.')

def as_dict():
  mj, mn, pt = parse()
  return {
      'major': mj,
      'minor': mn,
      'patch': pt,
  }
