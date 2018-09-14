#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Vte
import os,time
import pty

# esta função cria um pseudo-tty, retornando o lado mestre
# ela também cria um processo filho, que repetidamente envia dados
# pelo lado escravo

def app():
  mestre,escravo = pty.openpty() # cria um novo pty
  pid = os.fork() # divide o processo
  if pid:
    ptm = Vte.Pty.new_foreign_sync(mestre) # sincroniza o Vte com o pseudo terminal criado
    return ptm
  while True:
    os.write(escravo, 'abcedfgh\n'.encode('ascii')) #escreve no lado escravo do pty
    time.sleep(1)

# cria um vte
terminal = Vte.Terminal()

# obtém o pseudo-tty mestre
pts = app()

# vincula o pseudo-tty ao terminal
terminal.set_pty(pts)

# cria uma janela e associa o Vte a ela
win = Gtk.Window()
win.connect('delete-event', Gtk.main_quit)
win.add(terminal)
win.show_all()

Gtk.main()