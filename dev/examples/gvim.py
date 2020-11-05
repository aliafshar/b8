# (c) 2005-2020 Ali Afshar <aafshar@gmail.com>.
# MIT License. See LICENSE.
# vim: ft=python sw=2 ts=2 sts=2 tw=80

"""Example of embedding the NeoVim widget on its own."""

import gi
gi.require_version("Gtk", "3.0")

from b8 import vim
from gi.repository import Gtk


def main():
  window = Gtk.Window()
  vimembed = vim.Embedded()
  window.add(vimembed)
  window.resize(800, 600)

  def on_window_delete(widget, event):
    vimembed.quit()
    # True blocks the delete-event propagating
    # Otherwise the Window and Vim would be destroyed before Vim exists properly
    return True

  window.connect('delete-event', on_window_delete)

  def on_vim_ready(widget):
    # You really don't want to display anything until vim is "ready"
    # The "ready" signals is triggered on the VimEnter autocmd
    window.show_all()

  vimembed.connect('ready', on_vim_ready)

  def on_vim_exit(widget):
    # Similarly, you really want to wait for vim to "exit"
    # The "exited" signal is triggered by the VimLeave autocmd
    Gtk.main_quit()

  vimembed.connect('exited', on_vim_exit)

  # Finally start vim
  vimembed.start()
  # And the Gtk main loop
  Gtk.main()


if __name__ == '__main__':
  main()

