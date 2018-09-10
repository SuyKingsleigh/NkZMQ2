import os
import re
import sqlite3
import sys
import time

sys.path.append('%s/bin' % os.environ['NETKIT2_HOME'])
import nkparser, fcntl, traceback, zmq
from threading import Thread


###################################################################
# 
#

class TermPool:
    'Concentrador de terminais'

    def __init__(self):
        # dicionário com as VMs: chave=nome da vm, valor=instância de VM
        self.terms = {}
        # dicionário com os descritores das consoles: chave=descritor, valor=nome da vm
        self._fds = {}
        # vm ativa: não usado pelo servidor de instancias
        self._active = None

    def addVM(self, vm):
        'Adiciona uma vm ao pool'
        self.terms[vm.get_name()] = vm
        if not self._active: self._active = vm

    def start(self):
        '''Inicia as vms do pool: para cada vm, configura sua console em modo não bloqueante.'''
        self._fds = {}
        for vm in self.terms:
            fd = self.terms[vm].start()
            rfd_flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
            fcntl.fcntl(fd, fcntl.F_SETFL, rfd_flags)
            self._fds[fd] = vm.name
        return self._fds.keys()

    def stop(self):
        '''para as vms do pool'''
        for vm in self.terms:
            self.terms[vm].stop()
        self._fds = {}

    def get_term(self, name):
        'Obtém a vm com nome dado por name'
        return self.terms[name]

    def get_terms(self):
        'Obtém o dicionário de vms'
        return self.terms

    def set_active(self, name):
        'muda a vm ativa'
        if name in self.terms.keys():
            self._active = self.terms[name]

    def get_term_name(self, fd):
      'obtém o nome da vm associado ao descritor de pseudo-tty dado por fd'
      return self._fds[fd]

    @property
    def active(self):
        'obtém a vm ativa'
        return self._active

    @property
    def fds(self):
        'obtém a lista de fds das consoles das vms'
        return self._fds.keys()

    def set_output(self, conn):
        for name in self.terms:
            self.terms[name].set_output(conn)

    def transfer(self, rl, wl):
        self._active.transfer(rl, wl)


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


######################################################################

# representa uma rede em execucao
class Instancia:
    'Representa uma rede em execução'

    Num = 1 # variável de classe ... 

    def __init__(self, address, netinfo):
        '''address: identificador do cliente
netinfo: descrição da rede a ser executada (objeto nkdb.Network)'''
        self.netinfo = netinfo
        self.address = address
        self.id = Instancia.Num
        Instancia.Num += 1

    def start(self):
        'Inicia a rede'

        conf = open('%s.conf' % self.netinfo.name, 'w')
        conf.write(self.netinfo.value)
        conf.close()

        try:
            os.system('rm -rf lab')
        except:
            pass

        parser = nkparser.NetkitParser('%s.conf' % self.netinfo.name)
        if not parser.parse():
            return False

        try:
            # inicia a rede com um termpool especifico
            self.rede = parser.get_network()
            self.pool = TermPool()
            self.rede.start(self.pool)
            self.pool.start()
        except:
            return False

        return True

    # para essa rede *falar com o Sobral*
    def stop(self):
        'Para a rede'
        self.rede.stop()
        time.sleep(1)
        return True

    def handle_fd(self, fd):
      'Obtém o nome da vm associada ao descritor de pseudo-tty fd'
      try:
        return self.pool.get_term_name(fd)
      except:
        return None

    def getTerms(self):
        'obtém a lista de nomes de vms'
        terms = list(self.pool.get_terms())
        return terms

#######################################################################################

# Mensagens: (id_instancia,cmd,data) serializados com json
## id_instancia: int
## cmd: string
## data: bytes

import json

class Message:

    'Representa uma mensagem recebida do cliente. Serve para mensagens de comando ou de dados de terminal'

    def __init__(self, address, raw_data=b'', **args):
      '''address: identificador do cliente.
raw_data: bytes de uma mensagem recebida do cliente (serializada em JSON)
args: parâmetros para compor uma nova mensagem'''
      self.address = address
      if raw_data:
        r = json.loads(raw_data)
        self.id = r[0]
        self.cmd = r[1]
        self.data = r[2]
      else:
        self.id = self._get(args, 'id', 0)    
        self.cmd = self._get(args, 'cmd', '')
        self.data = self._get(args, 'data', [])

    def _get(self, args, k, defval):
      try:
        return args[k]
      except:
        return defval

    def serialize(self):
      'serializa a mensagem em JSON'
      return json.dumps((self.id, self.cmd, self.data))

class Response:

    '''Mensagem de resposta a enviar ao cliente. Pode ser resposta a um comando, ou mensagem de dados de terminal'''

    def __init__(self, status, **info):
      self.status = status
      self.info = info

    def serialize(self):
      'serializa a mensagem em JSON'
      return json.dumps((self.status, self.info))
      
# gerencia as redes em execucao
class Dispatcher:
    '''Dispatcher: trata mensagens recebidas do socket, e dados recebidos das consoles das vms
Encamina os dados para as instãncias correspondentes'''

    Dsn = 'catalogo_de_redes.db'

    def __init__(self, port, dsn=Dsn):
        '''port: port do socket, dsn: nome do arquivo de dados do catálogo de redes'''
        # cria o socket de controle
        self.port = port
        self.context = zmq.Context()
        self.poller = zmq.Poller()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind("tcp://*:%d" % port)
        self.poller.register(self.socket, zmq.POLLIN)
        # dicionario para as instancias
        self.instancias = {}
        self.repositorio = NetworkRepository(dsn)

    def _processCmd(self, msg):
        'processa comandos recebidos do cliente'

        if msg.cmd == 'start':
            name = msg.data
            r = self.repositorio.getNetwork(name)
            if not r: return
            inst = Instancia(msg.address, r)
            self.instancias[inst.id] = inst

            # se conseguir inicia a rede envia um ok
            if inst.start():
                # registra os pseudo-tty das vm da rede
                for fd in inst.pool.fds:
                  self.poller.register(fd, zmq.POLLIN)
                resp = Response(200, id=inst.id)
                self.socket.send_multipart([msg.address, resp.serialize()])
            else:
                del self.instancias[inst.id]
                err = Response(400, info='falhou ao iniciar a rede')
                self.socket.send_multipart([msg.address, err.serialize()])

        elif msg.cmd == 'stop':
            if msg.id in self.instancias:
              inst = self.instancias[msg.id]
              for fd in inst.pool.fds:
                self.poller.unregister(fd)
              inst.stop()
              del self.instancias[msg.id]
              resp = Response(200, id=inst.id)
              self.socket.send_multipart([msg.address, resp.serialize()])

        elif msg.cmd == 'data': # dados para um terminal ... não precisa de resposta
            if msg.id in self.instancias:
              inst = self.instancias[msg.id]
              term = inst.pool.get_term(msg.data.term)
              fd = term.getPty()
              os.write(fd, msg.data.data)

        elif msg.cmd == 'getTerms':
            ans = self.instancias[msg.id].getTerms()
            resp = Response(200, terms=ans)
            self.socket.send_multipart([address, resp.serialize])

        elif msg.cmd == 'list': # lista redes do catálogo
            ans = self.repositorio.listNeworks()
            resp = Response(200, terms=ans)
            self.socket.send_multipart([address, resp.serialize])

    def dispatch(self):
        '''Aguarda um evento (mensagem vinda do cliente ou dados em alguma console de vm.
Encaminha o tratamento do evento'''

        ev = dict(self.poller.poll())        
        for fd in ev:
          if self.socket == fd:
            address, req = self.socket.recv_multipart()
            msg = Message(address, req)
            self._processCmd(msg)
          else: # lê dados dos consoles das vms e envia para os clientes correspondentes
            for id, inst in self.instancias:
              term = inst.handle_fd(fd)
              if term:
                data = os.read(fd, 256)
                resp = Response(200, id=id, term=term, data=data)
                self.socket.send_multipart([inst.address, resp.serialize])

    def run(self):
       'Trata eventos indefinidamente'

       while True:
            self.dispatch()


####################################################################

try:
    dispatcher = Dispatcher(5555)
    dispatcher.run()
except Exception as e:
    print('erro', e)
    print(traceback.format_exc())
    sys.exit(0)
