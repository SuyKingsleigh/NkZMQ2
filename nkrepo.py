#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 16:53:31 2018

@author: msobral
"""

#####################################################################
import nkdb

class NetworkRepository:

    'Respositório de configurações de rede'

    def __init__(self, db_name):
        'construtor: acessa o repositório em disco dado por "db_name".db'
        self.db = nkdb.NetkitDB("%s.db" % db_name)

    # adiciona uma nova rede
    def addNetwork(self, **args):
        'Adiciona uma rede ao repositório. Se a rede já existir, não a adiciona e retorna false'
        r = list(self.db.search(nkdb.Network, name=args['name']))
        if not r:
            data = nkdb.Network(**args)
            self.db.insert(data)
            return True
        else:
            return False
            # Rede ja existe

    # remove uma rede pelo nome
    def removeNetwork(self, name):
        'remove uma rede do repositório. Se não existir, retorna falso'
        r = list(self.db.search(nkdb.Network, name=name))
        if r:
            self.db.delete(r[0].id)
            return True
        else:
            return False
            # rede nao existe

    # obtem uma rede pelo nome
    def getNetwork(self, name):
        'Obtém a descrição de uma rede do repositório. Se não existir, retorna false'
        r = list(self.db.search(nkdb.Network, name=name))
        if r:
            return r[0]
        else:
            return None

    # atualiza ou adiciona uma rede
    def updateNetwork(self, **args):
        'Atualiza os dados de uma rede. "args" contém os valores de atributos da rede a serem modificados'
        data = nkdb.Network(**args)
        self.db.update(data)

    def getNetworkInfo(self, name, flag):
        if flag == 'all':
            return self.getNetwork(name)
        elif flag == 'author':
            return self.getNetwork(name)[1]
        elif flag == 'desc':
            return self.getNetwork(name)[2]
        elif flag == 'preferences':
            return self.getNetwork(name)[3]
        else:
            return False

    def listNetworks(self):
        'retorna uma lista com os nomes das redes do catálogo'
        r = map(lambda x: x.name, self.db.search(nkdb.Network))
        return list(r)
