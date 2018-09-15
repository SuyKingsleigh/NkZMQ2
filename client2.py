#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 16:51:11 2018

@author: msobral
"""
import os
import pty
import sys

import gi
import zmq

from nkmessage import Message

gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Vte, GLib, Gtk


class Client:

    # inicia o socket de controel
    def __init__(self, ip, port):
        self.context = zmq.Context()
        self.ip = ip
        self.port = port
        self.socketCMD = self.context.socket(zmq.DEALER)
        self.socketCMD.connect("tcp://%s:%d" % (ip, port))
        self._started = False

    # nome da rede
    # se tudo ocorrer bem, coloca status started=True
    def start(self, netname):
        request = Message(cmd='start', data=netname)
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        self._started = True

    # verifica se o objeto foi iniciado
    @property
    def started(self):
        return self._started

    @property
    def networks(self):
        '''lista as redes no catalogo'''
        request = Message(cmd='list')
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        return resp.get('networks')

    def get_network(self, name):
        '''obtem informacoes sobre a rede especificada por nome'''
        request = Message(cmd='get', data=name)
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        return resp.get('network')

    def get_data(self):
        '''Obtem uma mensagem de dados de terminal. Deve ser chamado somente se houver uma mensagem
        pendente no socket. Depende portanto de previamente se usar um poller ou IOChannel para 
        verificar o socket.'''
        msg = self.socketCMD.recv()
        resp = Message(0, msg)
        if resp.cmd != 'data':
            raise Exception('Erro: %s' % msg.decode('ascii'))
        return resp.data

    # envia uma mensagem pro servidor
    # todo receber a mensagem do servidor
    def _exchangeData(self, chan, cond, fdout):
        termName = 'pc1'
        payload = {'term': termName, 'data': chan.read(128).decode('ascii')}
        request = Message(cmd='data', data=payload)
        self.socketCMD.send(request.serialize())
        os.write(fdout, self.readTerm())
        return True


    def _buildTerm(self):
        # cria o terminal
        terminal = Vte.Terminal()
        ptm, pts = pty.openpty()
        terminal.set_pty(Vte.Pty.new_foreign_sync(ptm))
        chanDoCliente = GLib.IOChannel(pts)  # canal para obter mensagens escritas no vte e envia-las pro socket
        chanDoServidor = GLib.IOChannel(self.socketCMD.fileno())  # recebidas do servidor

        chanDoCliente.set_flags(GLib.IO_FLAG_NONBLOCK)
        chanDoServidor.set_flags(GLib.IO_FLAG_NONBLOCK)

        condition = GLib.IOCondition(GLib.IOCondition.IN)

        # a ideia eh pegar os dados escritos e escreve-los em algum lugar
        # para posteriormente envia-los pelo socket
        chanDoServidor.add_watch(condition, self._exchangeData, 1) # escreve e manda pro servidor
        chanDoCliente.add_watch(condition, self._exchangeData, pts) # deve escrever no vte

        return terminal

    # todo criar um metodo ou dar um jeito de fazer isso pra todos os pcs na instancia
    def _buildWindow(self, terminal, pc):
        win = Gtk.Window()
        win.set_name(pc)
        win.connect('delete-event', Gtk.main_quit)
        win.add(terminal)
        win.show_all()
        Gtk.main()

    def run(self):
        # criar uma janela pra cada vte e depois dar um jeito de agrupar
        term = self._buildTerm()
        self._buildWindow(term, "pc1")
        while True:
            self.readTerm()


    def _buildTermVM(self):
        pass

    def readTerm(self):
        resp = self.socketCMD.recv()
        return resp


#####################################################################################


if __name__ == '__main__':
    c = Client('127.0.0.1', 5555)
    # print('Redes do catálogo:', c.networks)
    # net = c.get_network('rede1')
    # print('dados da rede rede2:', net)
    # print(net['conf'])
    c.start('rede1')
    c.run()
    sys.exit(0)
