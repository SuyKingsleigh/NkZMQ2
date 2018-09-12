#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 16:52:22 2018

@author: msobral
"""

#######################################################################################

# Mensagens: (id_instancia,cmd,data) serializados com json
## id_instancia: int
## cmd: string
## data: bytes

import json

class Message:

    'Representa uma mensagem recebida do cliente. Serve para mensagens de comando ou de dados de terminal'

    def __init__(self, address='', raw_data='', **args):
      '''address: identificador do cliente.
raw_data: bytes de uma mensagem recebida do cliente (serializada em JSON)
args: parâmetros para compor uma nova mensagem'''
      self.address = address      
      if raw_data:
        raw_data = raw_data.decode('ascii')
        print(raw_data)
        r = json.loads(raw_data)
        self.cmd = r[1]
        self.data = r[2]
      else:
        self.cmd = self._get(args, 'cmd', '')
        self.data = self._get(args, 'data', [])

    def _get(self, args, k, defval):
      try:
        return args[k]
      except:
        return defval

    def __bytes__(self):
        return self.serialize()

    def serialize(self):
      'serializa a mensagem em JSON'
      return json.dumps((self.cmd, self.data)).encode('ascii')

class Response:

    '''Mensagem de resposta a enviar ao cliente. Pode ser resposta a um comando, ou mensagem de dados de terminal'''

    def __init__(self, raw_data='', **args):
        if raw_data:
            raw_data = str(raw_data)
            self._data = json.loads(raw_data)
        else:
            if not 'status' in args: raise ValueError('missing status')
            self._data = {}
            self._data.update(args)

    @property
    def status(self):
        return self._data['status']
    
    def __bytes__(self):
        return self.serialize()

    def get(self, k):
        return self._data[k]
    
    def serialize(self):
      'serializa a mensagem em JSON'
      return json.dumps(self._data).encode('ascii')
      
