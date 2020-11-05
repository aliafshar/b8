
"""Grab the terminal themes from xfce4-terminal"""

import os, configparser, json

ROOT = '/usr/share/xfce4/terminal/colorschemes/'


def sanitize_name(n):
  return n.replace('(', '').replace(')', '').replace(' ', '_').lower()

def split_palette(s):
  if not s:
    return []
  return s.split(';')

def main():
  themes = {}
  ns = os.listdir(ROOT)
  for n in ns:
    p = os.path.join(ROOT, n)
    cfg = configparser.ConfigParser()
    cfg.read(p)
    sch = cfg['Scheme']
    print(f'Doing {cfg["Scheme"]["Name"]}')
    theme = {
      'name': sanitize_name(sch['Name']),
      'foreground': sch.get('ColorForeground'),
      'background': sch.get('ColorBackground'),
      'cursor': sch.get('ColorCursor'),
      'activity': sch.get('TabActivityColor'),
      'palette': split_palette(sch.get('ColorPalette')),
    }
    themes[theme['name']] = theme
  print(json.dumps(themes, indent='  '))


if __name__ == '__main__':
  main()
