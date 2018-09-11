import os
import sys
import time

sys.path.append('%s/bin' % os.environ['NETKIT2_HOME'])
import nkparser
import fcntl
import traceback
import zmq
from nkmessage import Message,Response
from nkrepo import NetworkRepository

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


#############################################################################################
# gerencia as redes em execucao
      
class Dispatcher:
    '''Dispatcher: trata mensagens recebidas do socket, e dados recebidos das consoles das vms
Encaminha os dados para as instãncias correspondentes.

       Formatos das mensagens recebidas do cliente: (id, comando, dados)
             id: identificador de instância (int)
             comando: nome do comando (str)
             dados: depende do comando
             
             comando start: dados=nome da rede a ser iniciada (str)
             
             comando stop: dados=string vazia
             
             comando data: dados=(term, data)
               term: nome do terminal a que se destinam os dados (str)
               data: dados para enviar ao terminal (bytes)
               
             comando getTerms: dados=string vazia
             
             comando list: dados=string vazia
             
      Formato das mensagens enviadas para o cliente: {status:, data:}
        status: código numérico para o status de resposta (int)
        dados: atributos da resposta (dict)
        
        comando start:
            {status=200, {id:}}: id=identificador da instância criada (int)
            {status=400, {info:}}: info=informação sobre o erro (str)
            
        comando stop:
            {status=200, {id:}}: id=identificador da instância terminada (int)
            {status=400, {info:}}: info=informação sobre o erro (str)
            
        comando data: sem resposta
        
        comando getTerms:
            {status=200, {terms:}}: terms=lista de nomes de terminais da instância (list)
            {status=400, {info:}}: info=informação sobre o erro (str)
            
        comando list:
            {status=200, {networks:}}: networks=lista de nomes de redes do catálogo (list)
            
'''

    Dsn = 'catalogo_de_redes'

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
                resp = Response(status=200, id=inst.id)
                self.socket.send_multipart([msg.address, resp.serialize()])
            else:
                del self.instancias[inst.id]
                err = Response(status=400, info='falhou ao iniciar a rede')
                self.socket.send_multipart([msg.address, err.serialize()])

        elif msg.cmd == 'stop':
            if msg.id in self.instancias:
              inst = self.instancias[msg.id]
              for fd in inst.pool.fds:
                self.poller.unregister(fd)
              inst.stop()
              del self.instancias[msg.id]
              resp = Response(status=200, id=inst.id)
            else:
              resp = Response(status=400, info='instância inexistente')
            self.socket.send_multipart([msg.address, resp.serialize()])
                

        elif msg.cmd == 'data': # dados para um terminal ... não precisa de resposta
            if msg.id in self.instancias:
              inst = self.instancias[msg.id]
              term = inst.pool.get_term(msg.data.term)
              fd = term.getPty()
              os.write(fd, msg.data.data)

        elif msg.cmd == 'getTerms':
            if msg.id in self.instancia:
                ans = self.instancias[msg.id].getTerms()
                resp = Response(status=200, terms=ans)
            else:
              resp = Response(status=400, info='instância inexistente')
                
            self.socket.send_multipart([msg.address, resp.serialize()])

        elif msg.cmd == 'list': # lista redes do catálogo
            ans = self.repositorio.listNetworks()
            resp = Response(status=200, networks=ans)
            self.socket.send_multipart([msg.address, resp.serialize()])


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

if __name__ == '__main__':

    try:
        dispatcher = Dispatcher(5555)
        dispatcher.run()
    except Exception as e:
        print('erro', e)
        print(traceback.format_exc())
        sys.exit(0)

