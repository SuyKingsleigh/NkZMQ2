#!/usr/bin/python3

import os
import re
import sqlite3
import sys
import time

sys.path.append('%s/bin' % os.environ['NETKIT2_HOME'])
import nkparser, fcntl, traceback, zmq, tempfile

# um termpool simples para oferecer acesso as vms e seus terminais
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


####################################################################
class Controller:

  expr = re.compile('(?P<action>[a-zA-Z]+) +(?P<arg>.*)')
  IDLE = 1
  STARTED = 2
  STOPPED = 3

  def __init__(self, port):
    # cria o socket de controle
    self.port = port
    self.context = zmq.Context()
    self.sockcmd = self.context.socket(zmq.ROUTER)
    self.sockcmd.bind("tcp://*:%d" % port)
    # cria o poller ZMQ para monitorar o socket e o terminal
    self.poller = zmq.Poller()
    self.poller.register(self.sockcmd, zmq.POLLIN)
    self.state = self.IDLE
    self.data = b''
    self.addr = ''
    self.path = os.path.abspath(os.curdir)
    self.dir_orig = os.path.abspath(os.curdir)
    self.repositorio = NetworkRepository('%s/catalogo_de_redes' % self.dir_orig)
    self.atual = ''

  # inicia uma rede contida no arquivo de configuracao com prefixo dado por "name"
  def _startNet(self, name):
    # cria a rede a partir de uma configuracao
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

    self.changeVm()
    # cria o socket do terminal
    try:
      self.socket = self.context.socket(zmq.ROUTER)
      self.socket.bind("tcp://*:%d" % (self.port+1))
    except:
      self.rede.stop()
      return False

    # registra o socket de terminal E o descritor da console da vm
    # no poller
    #os.system('mv %s/lab %s' % (self.dir_orig, self.path)) #muda para o diretorio temporario
    self.poller.register(self.socket, zmq.POLLIN)
    return True

  def changeVm(self, arg=None):
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

  # processa um comando recebido do socket de controle
  def _processCmd(self):
    address, msg = self.sockcmd.recv_multipart()
    msg = msg.decode('ascii')
    cmd = msg.split()[0]
    print('cmd: ', cmd)
    print('msg: ', msg)

    if cmd == 'start':
      name = msg.split()[1]
      if name in self.repositorio.set:
        conf = open('%s.conf' % name, 'w')
        network = self.repositorio.getNetwork(name)[5]
        for line in network:
          conf.write(line)
        conf.close()

        if self._startNet(name):
          self.sockcmd.send_multipart([address,'OK'.encode('ascii')])
          self.state = self.STARTED
          self.atual = name
      else:
        self.sockcmd.send_multipart([address, 'rede nao existe no repositorio'.encode('ascii')])

    elif cmd == 'get':
      try:
        self.changeVm(msg.split()[1])
        self.sockcmd.send_multipart([address, 'OK'.encode('ascii')])
      except Exception as e:
        print(e)
        print(traceback.format_exc())
    
    elif cmd == 'get_network':
      flag, name = msg.split()[1], msg.split()[2]
      if name == 'atual': name = self.atual
      if(flag == 'all'):
        nwInfo = self.repositorio.getNetworkInfo(name,flag)  
        nwInfostr = ';-;'.join(nwInfo)      
        self.sockcmd.send_multipart([address, nwInfostr.encode('ascii')])
      else:
        nwInfo = self.repositorio.getNetworkInfo(name, flag)  
        self.sockcmd.send_multipart([address, nwInfo.encode('ascii')])        

    elif cmd == 'stop':
      self.stop()
      self.sockcmd.send_multipart([address,'OK'.encode('ascii')]) 

    elif msg[:11] == 'new_network':
      arglist = msg.split(';-;')
      #print('Name', arglist[1])
      #print('Author', arglist[2])
      #print('Desc', arglist[3])
      #print('pref', arglist[4])
      #print('data', arglist[5])
      #print('network', arglist[6])
      if self.repositorio.addNetwork(arglist[1:]):
        self.sockcmd.send_multipart([address, 'OK'.encode('ascii')])
      else:
        self.sockcmd.send_multipart([address, 'Name already in use'.encode('ascii')])

    elif cmd == 'list_networks':
      names = self.repositorio.listNetworks()
      self.sockcmd.send_multipart([address, names.encode('ascii')])

    elif cmd == 'rm_network':
      if self.repositorio.removeNetwork(msg.split()[1]):
        self.sockcmd.send_multipart([address, 'OK'.encode('ascii')])
      else: self.sockcmd.send_multipart([address, 'Falha ao remover'.encode('ascii')])

    elif cmd == 'get_terms':
      terms = list(self.pool.get_terms())
      terms = ';-;'.join(terms)
      self.sockcmd.send_multipart([address, terms.encode('ascii')]) 
  # trata um evento: algo recebido de algum dos socket ou da console da vm
  # isso depende do estado do Controller:
  # -- se IDLE: apenas trata o socket de controle
  # -- se STARTED: trata socket de controle, de terminal e console da vm
  def _handle(self, ev):
    if self.state == self.IDLE:
      # se ha algum comando a processar, executa-o
      if self.sockcmd in ev:
        self._processCmd()
    elif self.state == self.STARTED:
      # se ha algum comando a processar, executa-o
      if self.sockcmd in ev:
        self._processCmd()
      # se tem dados na console da vm
      if self.fd in ev:
        request = os.read(self.fd, 256)
        self.data += request
        # envia pro cliente somente se cliente for conhecido (coisa do ZMQ)
        if self.addr:
          self.socket.send_multipart([self.addr, self.data])
          self.data = b''
      # se tem dados para ler do socket, encaminha-os pro terminal
      if self.socket in ev:
        self.addr,message = self.socket.recv_multipart()
        #print("Received %d bytes" % len(message))
        os.write(self.fd, message)

  # trata eventos indefinidamente
  def run(self):
    nome_dir = tempfile.mkdtemp('', 'tmp-', '.')#cria um diretorio
    self.dir_orig = os.getcwd() #pego o nome do diretorio atual 
    os.chdir(nome_dir)#acesso esse diretorio novo
    self.path = os.path.abspath(os.curdir)
    #os.system('cp %s/catalogo_de_redes.db %s' % (self.dir_orig,self.path)) #e o banco de dados
    # executa a rede
    while True:
      ev = dict(self.poller.poll())
      self._handle(ev)
    #volta ao diretorio original
    os.chdir(self.dir_orig)
    self.path = self.dir_orig

  # para o controller
  def stop(self):
    self.state = self.IDLE
    self.rede.stop()
    time.sleep(1)
    # na duvida, forca matar VMs penduradas
    os.system('killall vmlinux')
    self.poller.unregister(self.fd)
    # OBS:
    self.poller.unregister(self.socket)
    addr = self.socket.getsockopt(zmq.LAST_ENDPOINT)
    self.socket.unbind(addr)



####################################################################

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
       
  #adiciona uma nova rede 
  def addNetwork(self, arglist):
    if not arglist[0] in self.set:
      self.set.add(arglist[0])
      self.cursor.execute("""INSERT INTO rep (name, author, description, preferences, published_date, value) VALUES (?, ?, ?, ?, ?, ?)""",
      (arglist[0], arglist[1], arglist[2], arglist[3], arglist[4], arglist[5]))
      self.connection.commit()
      return True
    else:
      return False
      #Rede ja existe

  #remove uma rede pelo nome
  def removeNetwork(self, name):
    if name in self.set:
      self.cursor.execute("""DELETE FROM rep WHERE name = ? """,(name,))
      self.connection.commit()
      self.set.remove(name)
      return True
    else:
      return False
      #rede nao existe

  #obtem uma rede pelo nome 
  def getNetwork(self, name):
    self.cursor.execute("""SELECT * FROM rep WHERE name=?""", [(name)])
    return self.cursor.fetchone()
  
  #atualiza ou adiciona uma rede
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

####################################################################
try:
  debug = sys.argv[1] == '-d'
except:
  debug = False

try:
  controller = Controller(5555)
  controller.run()  
except KeyboardInterrupt:
  controller.stop()
except Exception as e:
  print ('Ops:', e)
  print (traceback.format_exc())

sys.exit(0)
