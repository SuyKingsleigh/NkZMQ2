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
        self._active = None

    def addVM(self, vm):
        self.terms[vm.get_name()] = vm
        if not self._active: self._active = vm

    def start(self):
        fds = []
        for vm in self.terms:
            fds.append(self.terms[vm].start())
        return fds

    def stop(self):
        for vm in self.terms:
            self.terms[vm].stop()

    def get_term(self, name):
        return self.terms[name]

    def get_terms(self):
        return self.terms

    def set_active(self, name):
        if name in self.terms.keys():
            self._active = self.terms[name]

    @property
    def active(self):
        return self._active

    @property
    def fds(self):
        _fds = []
        for vm in self.terms.values():
            _fds.append(vm.getPty())
        return _fds

    def set_output(self, conn):
        for name in self.terms:
            self.terms[name].set_output(conn)

    def transfer(self, rl, wl):
        self._active.transfer(rl, wl)


#####################################################################

class NetworkRepository:
    def __init__(self, db_name):
        self.set = set()

        self.connection = sqlite3.connect("%s.db" % db_name)
        self.cursor = self.connection.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS rep (\
    name TEXT NON NULL,\
    author TEXT NON NULL,\
    description TEXT NON NULL,\
    preferences TEXT NON NULL,\
    published_date TEXT NON NULL,\
    value TEXT NON NULL\
    );""")
        self.cursor.execute("""
    SELECT name FROM rep 
    """)
        for name in self.cursor.fetchall():
            self.set.add(name[0])

    # adiciona uma nova rede
    def addNetwork(self, arglist):
        if not arglist[0] in self.set:
            self.set.add(arglist[0])
            self.cursor.execute(
                """INSERT INTO rep (name, author, description, preferences, published_date, value) VALUES (?, ?, ?, ?, ?, ?)""",
                (arglist[0], arglist[1], arglist[2], arglist[3], arglist[4], arglist[5]))
            self.connection.commit()
            return True
        else:
            return False
            # Rede ja existe

    # remove uma rede pelo nome
    def removeNetwork(self, name):
        if name in self.set:
            self.cursor.execute("""DELETE FROM rep WHERE name = ? """, (name,))
            self.connection.commit()
            self.set.remove(name)
            return True
        else:
            return False
            # rede nao existe

    # obtem uma rede pelo nome
    def getNetwork(self, name):
        self.cursor.execute("""SELECT * FROM rep WHERE name=?""", [(name)])
        return self.cursor.fetchone()

    # atualiza ou adiciona uma rede
    def updateNetwork(self, name, newdata):
        if name in self.set:
            self.removeNetwork(name)
            self.addNetwork(newdata)
        else:
            self.addNetwork(newdata)

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
        return ';-;'.join(list(self.set))


######################################################################

# representa uma rede em execucao
class Instancia:
    expr = re.compile('(?P<action>[a-zA-Z]+) +(?P<arg>.*)')
    IDLE = 1
    STARTED = 2
    STOPPED = 3

    def __init__(self, port, name):
        self.port = port
        self.context = zmq.Context()
        self.poller = zmq.Poller()
        self.data = b''
        self.addr = ''
        self.path = os.path.abspath(os.curdir)
        self.repositorio = NetworkRepository('%s/catalogo_de_redes' % self.path)
        self.name = name
        self.state = self.IDLE
        self.runner = True

    def _startNet(self, name):
        os.chdir(self.path)
        try:
            os.system('rm -rf lab')
        except:
            pass

        parser = nkparser.NetkitParser('%s.conf' % name)
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

        self._changeVm()
        # cria o socket do terminal
        try:
            self.socket = self.context.socket(zmq.ROUTER)
            self.socket.bind("tcp://*:%d" % (self.port + 1))
        except:
            self.rede.stop()
            return False
        # registra o socket de terminal E o descritor da console da vm
        # no poller
        self.poller.register(self.socket, zmq.POLLIN)
        return True

    def _changeVm(self, arg=None):
        if self.state == self.STARTED:
            self.poller.unregister(self.fd)

        if arg: self.pool.set_active(arg)
        # obtem o descritor do terminal, modificando-o
        # para leitura nao-bloqueante
        self.fd = self.pool.active.getPty()
        print('fd:', self.fd)
        rfd_flags = fcntl.fcntl(self.fd, fcntl.F_GETFL) | os.O_NONBLOCK
        fcntl.fcntl(self.fd, fcntl.F_SETFL, rfd_flags)
        self.poller.register(self.fd, zmq.POLLIN)

    # para essa rede *falar com o Sobral*
    def stop(self):
        self.state = self.IDLE
        self.rede.stop()
        time.sleep(1)
        self.poller.unregister(self.fd)
        self.poller.unregister(self.socket)
        addr = self.socket.getsockopt(zmq.LAST_ENDPOINT)
        self.socket.unbind(addr)
        self.runner = False
        return True

    # inicia uma rede dada pelo nome
    def start(self, name):
        if name in self.repositorio.set:
            conf = open('%s.conf' % name, 'w')
            network = self.repositorio.getNetwork(name)[5]
            for line in network:
                conf.write(line)
            conf.close()

        if self._startNet(name):
            self.state = self.STARTED
            self.atual = name
            return True
        else:
            return False

    # troca o terminal
    def getPC(self, pcname):
        try:
            self._changeVm(pcname)
            return True
        except Exception as e:
            print(e)
            print(traceback.format_exc())

        # retorna uma string com os terminais, a string eh uma lista
        # unida por ";-;"

    def getTerms(self):
        terms = list(self.pool.get_terms())
        terms = ';-;'.join(terms)
        return terms

    # gerencia os comandos do terminal, espera por algum evento, executa obtem a mensagem e envia para o cliente
    # sem a necessidade de passar pelo socket de controle
    def _handle(self, ev):
        if self.fd in ev:
            request = os.read(self.fd, 256)
            self.data += request
            if self.addr:
                self.socket.send_multipart([self.addr, self.data])
                self.data = b''
        if self.socket in ev:
            self.addr, message = self.socket.recv_multipart()
            os.write(self.fd, message)

    # auxilia na criacao de uma Daemon
    def _runTerm(self):
        while self.runner:
            ev = dict(self.poller.poll())
            self._handle(ev)

    def run(self):
        self.instanciaDaemon = Thread(target=self._runTerm)
        self.instanciaDaemon.daemon = True
        self.instanciaDaemon.start()


#######################################################################################

# gerencia as redes em execucao
class Dispatcher:
    def __init__(self, port):
        # cria o socket de controle
        self.port = port
        self.context = zmq.Context()
        self.socketCMD = self.context.socket(zmq.ROUTER)
        self.socketCMD.bind("tcp://*:%d" % port)
        # dicionario para as instancias
        self.instancias = {}

    def _processCmd(self):
        address, req = self.socketCMD.recv_multipart()
        req = req.decode('ascii').split()  # decodifica e quebra em lista
        instanciaID = req[0]  # pega a id da rede
        msg = req[1:]  # cria outra lista
        cmd = msg[0]  # obtem o cmd

        # se a instancia nao existir no dicionario interno, eh adicionada
        if not instanciaID in self.instancias.keys():
            instancia = Instancia(self.port, instanciaID)
            self.instancias[instanciaID] = instancia
            self.instancias[instanciaID].run()
            print(instanciaID)

        if cmd == 'start':
            name = msg[1]
            # se conseguir inicia a rede envia um ok
            if self.instancias[instanciaID].start(name):
                self.socketCMD.send_multipart([address, 'OK'.encode('ascii')])
            else:
                self.socketCMD.send_multipart([address, 'falhou ao iniciar a rede'.encode('ascii')])

        elif cmd == 'get':
            if self.instancias[instanciaID].getPC(msg[1]):
                self.socketCMD.send_multipart([address, 'OK'.encode('ascii')])
            else:
                self.socketCMD.send_multipart([address, 'Falhou ao trocar'.encode('ascii')])

        elif cmd == 'getTerms':
            ans = self.instancias[instanciaID].getTerms().encode('ascii')
            self.socketCMD.send_multipart([address, ans])

    def run(self):
        while True:
            self._processCmd()


####################################################################

try:
    dispatcher = Dispatcher(5555)
    dispatcher.run()
except Exception as e:
    print('erro', e)
    print(traceback.format_exc())
    sys.exit(0)
