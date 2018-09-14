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
from gi.repository import Vte, GLib


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
        self.socketCMD.send_string(request.serialize())
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

    # todo: metodo para executar uma rede
    # todo: criar os vtes e alimenta-los

    def _exchangeData(self, chan, cond, fdout):
        data = chan.read(128)
        os.write(fdout, data)

    def _buildTerm(self):
        # cria o terminal
        self.terminal = Vte.Terminal()
        ptm, pts = pty.openpty()
        self.terminal.set_pty(Vte.Pty.new_foreign_sync(ptm))
        # cria os canais de comunicacao
        self.chanFromClient = GLib.IOChannel(pts)
        self.chanFromServer = GLib.IOChannel(self.socketCMD)
        # coisa pra leitura nao bloqueante
        self.chanFromClient.set_flags(GLib.IO_FLAG_NONBLOCK)
        self.chanFromServer.set_flags(GLib.IO_FLAG_NONBLOCK)

#####################################################################################



if __name__ == '__main__':
    c = Client('127.0.0.1', 5555)
    print('Redes do catálogo:', c.networks)
    net = c.get_network('rede2')
    print('dados da rede rede2:', net)
    print(net['conf'])
    sys.exit(0)
