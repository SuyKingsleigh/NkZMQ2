#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 16:51:11 2018

@author: msobral
"""

import sys
import zmq
from nkmessage import Message,Response

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
        request = Message(id=0, cmd='start', data=netname)
        self.socketCMD.send_string(request.serialize())
        resp = self.socketCMD.recv()
        resp = Response(resp)
        if resp.status != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        self._started = True

    # verifica se o objeto foi iniciado
    @property
    def started(self):
        return self._started

    def list_networks(self):
        request = Message(id=0, cmd='list')
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv_string()
        resp = Response(resp)
        if resp.status != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        return resp.get('networks')

if __name__ == '__main__':
    c = Client('127.0.0.1', 5555)
    print('Redes do catálogo:', c.list_networks())
    sys.exit(0)

