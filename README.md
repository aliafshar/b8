# bominade (b8)

**Vim-based IDE**

Bominade is the successor to a8 and PIDA. It is an extremely light-weight IDE
based on NeoVim, a file browser and a terminal emulator. It is currently in
heavy development.

## Features

* NeoVim - that's right, use all your Vim and NeoVim plugins. The NeoVim integration uses LineGrid and renders using Cairo. It's pretty fast and comparable with Vim-gtk
* Proper terminal emulator - this has real PTY support and uses VTE, the backend to gnome-terminal and xfce4-terminal.
* File manager with Git integration - see the statuses of your files directly in the file manager
* Open files in the terminal emulator or file browser just by clicking on them
* Sync terminal emulator working directory with the file manager to auto-browse when you cd
* Terminal themes - love solarized-dark? Great, use it.
* Vim Buffer list - literally the only missing thing from Vim and we provide a nice way to view the path name and the parent directory
* Works on Linux - this thing hasn't been tested on other platforms where it probably works, but we care about Linux

## Obligatory screenshot

This is what we mean...

![Bominade screenshot](https://gitlab.com/afshar-oss/b8/-/raw/dev/tools/screenshot.png)

## Getting started

I only tested it on an old LTS ubuntu.

You will need a few dependencies: NeoVim, python3, gtk, vte, msgpack.

Something like this should be enough, but let me know:

```
# apt install python3 python3-gi python3-gi-cairo libvte-2.91-0
```

It uses NeoVim's non-deprecated linegrid methodology, so you need a
recent NeoVim. I use 0.4.4-1 from [neovim stable
ppa](https://launchpad.net/~neovim-ppa/+archive/ubuntu/stable).

```
pip install b8
```

In a virtualenv you need some trickery to use gi from the system:

```
virtualenv -p python3 --system-site-packages env
./env/bin/pip install -I b8  # -I ignores site packages for what it can
```

Or of course if you have everything already and you dgaf just run the script:

```
$ PYTHONPATH=. python3 b8/app.py
```

## Manual

```
🞄 b8 --help

usage: b8 [-h] [-d] [-f CONFIG] [--logging-level LOGGING_LEVEL] [--terminal-theme TERMINAL_THEME] [--terminal-font TERMINAL_FONT] [--shortcuts-previous-buffer SHORTCUTS_PREVIOUS_BUFFER] [--shortcuts-next-buffer SHORTCUTS_NEXT_BUFFER]
          [--shortcuts-previous-terminal SHORTCUTS_PREVIOUS_TERMINAL] [--shortcuts-next-terminal SHORTCUTS_NEXT_TERMINAL] [--shortcuts-new-terminal SHORTCUTS_NEW_TERMINAL]

The bominade IDE, version 0.1.0

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           Run with logging level debug
  -f CONFIG, --config CONFIG
                        Configuration file to use
  --logging-level LOGGING_LEVEL
                        The logging level to use
  --terminal-theme TERMINAL_THEME
                        The terminal theme to use
  --terminal-font TERMINAL_FONT
                        The terminal font to use, e.g. "Monospace 13"
  --shortcuts-previous-buffer SHORTCUTS_PREVIOUS_BUFFER
                        Shortcut key to switch to the previous buffer
  --shortcuts-next-buffer SHORTCUTS_NEXT_BUFFER
                        Shortcut key to switch to the next buffer
  --shortcuts-previous-terminal SHORTCUTS_PREVIOUS_TERMINAL
                        Shortcut key to switch to the previous terminal
  --shortcuts-next-terminal SHORTCUTS_NEXT_TERMINAL
                        Shortcut key to switch to the next terminal
  --shortcuts-new-terminal SHORTCUTS_NEW_TERMINAL
                        Shortcut key to create a new terminal


```


## Keyboard Shortcuts

The following actions are available at the top-level. You can modify them in the
config (see config section below).

| Key Press 	| Action            	|
|-----------	|-------------------	|
| `Alt-Up`    | Previous Buffer   	|
| `Alt-Down`  | Next Buffer       	|
| `Alt-Right` | Previous Terminal 	|
| `Alt-Left`  | Next Terminal     	|
| `Alt-t`     | New Terminal      	|

## FAQ

**Why is the mouse behaving stupidly?** Unlike GVim where the mouse is
configured to be on, you have to explicitly do it for NeoVim. Instead of forcing
it on the b8 side, we request you run `:set mouse=a` to do that.

## Config

Set up your NeoVim however you like it. Yummy!

Edit `~/.config/b8/b8rc` which is a standard ini file.
```
[terminal]
theme = solarized_dark

[vim]
font = Liberation Mono 14

[shortcuts]
next_buffer = <Alt>Down
prev_buffer = <Alt>Up
next_terminal = <Alt>Right
prev_terminal = <Alt>Left
new_terminal = <Alt>t
```

There are other themes: tango, dark_pastels, green_on_black and others. I should list them.
