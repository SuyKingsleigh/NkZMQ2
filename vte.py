#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte
from gi.repository import GLib
import os
import pty

# callback para tratar leitura do IOChannel
def exchange_data(chan, cond, fdout):
  data = chan.read(128)
  #print('Lido:', data.decode('ascii'))
  os.write(fdout, data)
  return True

terminal = Vte.Terminal()
# Cria um pseudo-tty: ptm=lado mestre, pts=lado escravo
ptm,pts = pty.openpty()

# vincula o lado mestre ao terminal
terminal.set_pty(Vte.Pty.new_foreign_sync(ptm))

# cria um IOChannel associado ao lado escravo
chan = GLib.IOChannel(pts)
# cria um IOChannel associado a entrada padrão
chan2 = GLib.IOChannel(0)

# define o IOChannel como não-bloqueante
chan.set_flags(GLib.IO_FLAG_NONBLOCK)
chan2.set_flags(GLib.IO_FLAG_NONBLOCK)

# registra um callback no IOChannel para condição de leitura
cond = GLib.IOCondition(GLib.IOCondition.IN)
# callback para o iochannel do vte ... deve escrever na saída padrão
chan.add_watch(cond, exchange_data, 1)

# callback para o iochannel da entrada padrão... deve escrever no vte
chan2.add_watch(cond, exchange_data, pts)

# cria a tela principal e nela embute o terminal
win = Gtk.Window()
win.connect('delete-event', Gtk.main_quit)
win.add(terminal)
win.show_all()

Gtk.main()
