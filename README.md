# bominade (b8)

**Vim-based IDE**

Bominade is the successor to a8 and PIDA. It is an extremely light-weight IDE
based on NeoVim, a file browser and a terminal emulator. It is currently in
heavy development.

![Bominade screenshot](tools/screenshot.png)

## Getting started

I only tested it on an old LTS ubuntu.

You will need a few dependencies: NeoVim, python3, gtk, vte, msgpack.

Something like this should be enough, but let me know:

```
# apt install python3 python3-gi python3-gi-cairo libvte-2.91-0 python3-msgpack neovim
```

It uses NeoVim's non-deprecated linegrid methodology, so you need a reasonably
recent NeoVim. I use 0.4.4-1 from ppa, but the stock in the latest LTS Ubuntu
works too.

Then just run the script:

```
$ python3 b8.py
```

## Config

Set up your NeoVim however you like it. Yummy!

Nothing yet for terminals, but coming soon. I'm sorry.
