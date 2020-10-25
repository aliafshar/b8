
# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

from setuptools import setup

with open('README.md') as f:
  long_description = f.read()

with open('b8.py') as f:
  for line in f:
    if line.startswith('VERSION'):
      version = line.strip().split(' ')[-1][1:-1]
      break


setup(    
  name = 'b8',
  version = version,
  description = 'Ultralight IDE based on NeoVim',
  long_description = long_description,
  long_description_content_type='text/markdown',
  author = 'Ali Afshar',
  author_email = 'aafshar@gmail.com',
  url = 'https://gitlab.com/afshar-oss/b8',
  python_requires='>=3.7',
  install_requires=['msgpack>=1.0.0'],
  py_modules = ['b8'],
  entry_points={
    'console_scripts': [
      'b8=b8:main',
    ],
  },

)
