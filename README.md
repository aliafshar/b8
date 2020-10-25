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
$ python3 b8.py
```

## Manual

```
🞄 b8 --help                                                                                                                                                                                                                                            
usage: b8 [-h] [--remote] [--debug] [files [files ...]]

The bominade IDE

positional arguments:
  files       Files to open

optional arguments:
  -h, --help  show this help message and exit
  --remote    Open in a running b8
  --debug     Debug log output
```

So, you can pass file names as a positional argument to open.

You can also use --remote to open a file in a running b8. Note: this is barely
built so it only uses the first b8 instance it can find.

## FAQ

**Why do you ignore my guifont setting?** Raise a bug if this annoys you, but by the
time we get that option from NeoVim things are already drawn and you get a jank
which annoys me even more. Instead just set the font in b8's config file e.g. below.

## Config

Set up your NeoVim however you like it. Yummy!

Edit `~/.config/b8/b8rc` which is a standard ini file.
```
[terminal]
theme = solarized_dark

[vim]
font = Liberation Mono 14
```

There are other themes: tango, dark_pastels, green_on_black and others. I should list them.
