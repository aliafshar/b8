---
layout: layout.njk
permalink: install.html
eleventyNavigation:
  key: Installation
  order: 1
---

# Installing Bominade

## Simple version

This is the fastest way to get up and running. If you have pip set up correctly
into your home directory.

```bash
$ pip install b8
```

## Requirements

I only tested it on an old LTS ubuntu. You will need a few dependencies: NeoVim,
python3, gtk, vte, msgpack. Something like this should be enough, but let us
know.

```bash
$ sudo apt install python3 python3-gi python3-gi-cairo libvte-2.91-0
```

Bominade uses NeoVim's non-deprecated linegrid methodology, so you need a
recent NeoVim. I use 0.4.4-1 from
[neovim stable ppa](https://launchpad.net/~neovim-ppa/+archive/ubuntu/stable).

NeoVim is constantly improving so we will chase releases and functionality in
their stable branch up to at least v1.0.

## Run from source

In a virtualenv you need some trickery to use gi from the system:

```bash
virtualenv -p python3 --system-site-packages env
./env/bin/pip install -I b8  # -I ignores site packages for what it can
./env/bin/b8
```

Or of course if you have everything already and you dgaf just run the script:

```bash
$ python3 b8/app.py
```
