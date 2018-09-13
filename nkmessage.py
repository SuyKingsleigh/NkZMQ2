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
        #print(raw_data)
        r = json.loads(raw_data)
        self.cmd = r[0]
        self.data = r[1]
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

    def get(self, k):
        return self.data[k]
    
    def serialize(self):
      'serializa a mensagem em JSON'
      return json.dumps((self.cmd, self.data)).encode('ascii')

