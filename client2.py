#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 16:51:11 2018

@author: msobral
"""
import os
import pty
import sys
import time
from threading import Thread

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
        self.terminaisDict = dict()
        self.daemonStarted = False

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
        self.terminais = resp.data['terms']

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

    # retorna um dicionario [terminal]->dado(str)
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
    def _exchangeData(self, chan, cond, fdout, termName):
        payload = {'term': termName, 'data': chan.read(128).decode('ascii')}
        request = Message(cmd='data', data=payload)
        self.socketCMD.send(request.serialize())
        # if not self.daemonStarted: self._daemon()
        self._daemon()
        return True

    def _daemon(self):
        self.instanciaDaemon = Thread(target=self._readMessage)
        self.instanciaDaemon.daemon = True
        self.instanciaDaemon.start()


    def _buildTerm(self):
        for term in self.terminais:
            terminal = Vte.Terminal()
            ptm, pts = pty.openpty()
            terminal.set_pty(Vte.Pty.new_foreign_sync(ptm))  # sincroniza com o master
            terminal.set_name(term)  # da um nome para o terminal

            chanDoCliente = GLib.IOChannel(pts)  # canal para obter mensagens escritas no vte e envia-las pro socket
            # chanDoServidor = GLib.IOChannel(self.socketCMD.fileno())  # recebidas do servidor

            # define flags para leitura nao bloqueante
            chanDoCliente.set_flags(GLib.IO_FLAG_NONBLOCK)
            # chanDoServidor.set_flags(GLib.IO_FLAG_NONBLOCK)

            # define condicao
            condition = GLib.IOCondition(GLib.IOCondition.IN)

            # chanDoServidor.add_watch(condition, self._exchangeData, 1, term)  # escreve e manda pro servidor //Funciona
            chanDoCliente.add_watch(condition, self._exchangeData, pts, term)  # deve escrever no vte //fuck
            self.terminaisDict[term] = (terminal, ptm, pts)

    # todo quando fechar a janela, enviar um sinal de stop pro servidor.
    def _buildWindow(self, terminal, pc):
        '''Metodo para criar uma janela, agrega a ela um terminal e o nome do mesmo(pc)'''
        win = Gtk.Window()
        win.set_title(pc)
        win.connect('delete-event', Gtk.main_quit)
        win.add(terminal)
        win.show_all()
        return win

    def _buildTermWindow(self):
        gtkMainWin = Gtk.WindowGroup()
        self._buildTerm()
        for termName in self.terminaisDict.keys():
            win = self._buildWindow(self.terminaisDict[termName][0], termName)
            gtkMainWin.add_window(win)

        Gtk.main()

    def _readMessage(self):
        while self.socketCMD.poll() == zmq.POLLIN:
            resp = self.socketCMD.recv()
            if resp:
                resp = Message(0, resp)
                if (resp.cmd == 'data'):
                    term = resp.data['term']
                    data = resp.data['data']
                    print("recebeu", term, data)
                    os.write(self.terminaisDict[term][2], data.encode('ascii'))
            else: time.sleep(0.1)

    def run(self):
        self._buildTermWindow()


#####################################################################################


if __name__ == '__main__':
    c = Client('127.0.0.1', 5555)
    # print('Redes do catálogo:', c.networks)
    net = c.get_network('rede2')
    # print('dados da rede rede2:', net)
    # print(net['conf'])
    c.start('rede2')
    c.run()
    sys.exit(0)
