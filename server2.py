import os
import re
import sqlite3
import sys
import time

sys.path.append('%s/bin' % os.environ['NETKIT2_HOME'])
import nkparser, fcntl, traceback, zmq
from threading import Thread


###################################################################

class TermPool:

    def __init__(self):
        self.terms = {}
        self._fds = {}
        self._active = None

    def addVM(self, vm):
        self.terms[vm.get_name()] = vm
        if not self._active: self._active = vm

    def start(self):
        self._fds = {}
        for vm in self.terms:
            fd = self.terms[vm].start()
            rfd_flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
            fcntl.fcntl(fd, fcntl.F_SETFL, rfd_flags)
            self._fds[vm] = fd
        return self._fds.keys()

    def stop(self):
        for vm in self.terms:
            self.terms[vm].stop()
        self._fds = {}

    def get_term(self, name):
        return self.terms[name]

    def get_terms(self):
        return self.terms

    def set_active(self, name):
        if name in self.terms.keys():
            self._active = self.terms[name]

    def get_term_name(self, fd):
      return self._fds[fd]

    @property
    def active(self):
        return self._active

    @property
    def fds(self):
        return self._fds.keys()

    def set_output(self, conn):
        for name in self.terms:
            self.terms[name].set_output(conn)

    def transfer(self, rl, wl):
        self._active.transfer(rl, wl)


#####################################################################
import nkdb

class NetworkRepository:
    def __init__(self, db_name):
	self.db = nkdb.NetkitDB("%s.db" % db_name)

    # adiciona uma nova rede
    def addNetwork(self, **args):
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
        r = list(self.db.search(nkdb.Network, name=name))
        if r:
	    self.db.delete(r[0].id)
            return True
        else:
            return False
            # rede nao existe

    # obtem uma rede pelo nome
    def getNetwork(self, name):
        r = list(self.db.search(nkdb.Network, name=name))
        if r:
	    return r[0]
	else:
	    return None

    # atualiza ou adiciona uma rede
    def updateNetwork(self, **args):
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
        r = (map lambda x: x.name, self.db.search(nkdb.Network))
        return list(r)


######################################################################

# representa uma rede em execucao
class Instancia:
    expr = re.compile('(?P<action>[a-zA-Z]+) +(?P<arg>.*)')
    IDLE = 1
    STARTED = 2
    STOPPED = 3
    Num = 1 # variável de classe ... 

    def __init__(self, address, netinfo):
        self.netinfo = netinfo
        self.address = address
        self.id = Instancia.Num
        Instancia.Num += 1

    def _startNet(self, name):
        os.chdir(self.path)
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
        self.rede.stop()
        time.sleep(1)
        return True

    # inicia uma rede dada pelo nome
    def start(self):
        conf = open('%s.conf' % self.netinfo.name, 'w')
	conf.write(self.netinfo.value)
        conf.close()

        if self._startNet():
            return True
        else:
            return False

    def handle_fd(self, fd):
      try:
        return self.pool.get_term_name(fd)
      except:
        return None

    def getTerms(self):
        terms = list(self.pool.get_terms())
        return terms

#######################################################################################

# Mensagens: (id_instancia,cmd,data) serializados com json
## id_instancia: int
## cmd: string
## data: bytes

import json

class Message:

    def __init__(self, address, *raw_data, **args):
      self.address = address
      if raw_data:
        r = pickle.loads(raw_data[0])
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
      return json.dumps((self.id, self.cmd, self.data))

class Response:

    def __init__(self, status, **info):
      self.status = status
      self.info = info

    def serialize(self):
      return json.dumps((self.status, self.info))
      
# gerencia as redes em execucao
class Dispatcher:
    Dsn = 'catalogo_de_redes.db'

    def __init__(self, port, dsn=Dsn):
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
