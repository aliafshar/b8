---
layout: layout.njk
eleventyNavigation:
  key: Home
  order: 0
---
# bominade (b8) NeoVim-based IDE

Bominade is the successor to Abominade and PIDA. It is an extremely light-weight IDE based on NeoVim, a file browser and a terminal emulator. It is currently in heavy development.

## Features

* NeoVim - that's right, use all your Vim and NeoVim plugins. The NeoVim integration uses LineGrid and renders using Cairo. It's pretty fast and comparable with Vim-gtk
* Proper terminal emulator - this has real PTY support and uses VTE, the backend to gnome-terminal and xfce4-terminal.
* File manager with Git integration - see the statuses of your files directly in the file manager
* Open files in the terminal emulator or file browser just by clicking on them
* Sync terminal emulator working directory with the file manager to auto-browse when you cd
* Terminal themes - we have them and you can make your own. Love solarized-dark? Great, me too, but not in the terminal - so you can use it.
* Vim Buffer list - literally the only missing thing from Vim and we provide a nice way to view the path name and the parent directory
* Works on Linux - this thing hasn't been tested on other platforms where it probably works, but we care about Linux

## You like, yes?


## Obligatory screenshot

![Bominade screenshot](https://gitlab.com/afshar-oss/b8/-/raw/dev/tools/screenshot.png)

