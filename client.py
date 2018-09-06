import datetime
import fcntl
import sys

import zmq


class Terminal:

    def __init__(self, sock):
        self.sock = sock
        self.pid = 0
        self.fdr = -1
        self.fdw = -1

    def run(self):
        self.fdm, self.fde = pty.openpty()
        self.pid = os.fork()

        try:
            os.set_inheritable(self.fdm, True)
        except Exception as e:
            print('Erro: %s' % e)
        if not self.pid:
            os.execlp('xterm', 'xterm', '-Sptmx/%d' % self.fdm)
            raise RuntimeError('nao conseguiu executar xterm')

        # self.pid, self.fd = pty.fork()
        # if not self.pid:
        #  fcntl.fcntl(sys.stdout, fcntl.F_SETFL, os.O_NDELAY)
        #  fcntl.fcntl(sys.stdin, fcntl.F_SETFL, os.O_NDELAY)
        #  os.execlp('nc','nc')
        #  raise RuntimeError('nao conseguiu executar xterm')
        self.fdr = os.fdopen(self.fde, 'rb')  # cria um objeto pra ler o fd do escravo
        self.fdd = os.fdopen(0, 'r')
        self.fdw = os.fdopen(self.fde, 'wb')  # pra escrever

    # flag de leitura bloqueante
    def __get_block_flag__(self, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        flags = flags | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)
        return flags

    def relay(self):
        fd_flags = self.__get_block_flag__(self.fdr)
        poller = zmq.Poller()
        poller.register(self.fdd, zmq.POLLIN)
        poller.register(self.fdr, zmq.POLLIN)
        poller.register(self.sock, zmq.POLLIN)

        # \x08\n = tab
        while True:
            ev = dict(poller.poll())
            # verifica o que foi lido no x-term
            if self.fdr.fileno() in ev:
                print('Lendo do terminal')
                request = self.fdr.read()
                if request: self.sock.send(request)
                print('Leu:', request)

            # e o que foi lido no terminal
            if self.fdd.fileno() in ev:
                comando = self.fdd.readline()
                return comando

            if self.sock in ev:
                message = self.sock.recv()
                if message:
                    try:
                        self.fdw.write(message)
                        self.fdw.flush()
                    except IOError:
                        pass
                else:
                    break
        return False

    def stop(self):
        # mata o processo criado pelo cliente e fecha os fd
        if self.pid: os.kill(self.pid, 15)
        try:
            self.fdr.close()
            print('fdr %i have been killed' % self.pid)
        except:
            pass
        try:
            self.fdw.close()
            print('fdw have been killed')
        except Exception as e:
            print(e)


##############################################################################################

class Command:
    # inicia o socket de controel
    def __init__(self, ip, port):
        self.context = zmq.Context()
        self.ip = ip
        self.port = port
        self.socketCMD = self.context.socket(zmq.DEALER)
        self.socketCMD.connect("tcp://%s:%d" % (ip, port))
        self._started = False

    # nome do filename.conf
    # envia o arquivo pelo socket de controle
    # se tudo ocorrer bem, coloca status started=True
    def start(self, filename):
        request = 'start ' + filename
        self.socketCMD.send_string(request)
        resp = self.socketCMD.recv()
        resp = resp.decode('ascii')
        if resp != 'OK':
            print('Erro: %s' % resp)
            sys.exit(0)
        self._started = True

    # verifica se o objeto foi iniciado
    @property
    def started(self):
        return self._started

    def buildTerm(self):
        sockDEALER = self.context.socket(zmq.DEALER)
        sockDEALER.connect("tcp://%s:%d" % (self.ip, self.port + 1))
        self.term = Terminal(sockDEALER)
        self.term.run()

    # abre um socket dealer e cria um objeto terminal
    def run(self):
        if not self._started: raise Exception('not started')
        while self._started:
            action = self.term.relay()
            self._processCmd(action)

    def _processCmd(self, action):
        action = action.strip()
        if not action: return
        print('processando:', action)
        cmd = action.split()
        if cmd[0] == 'get':  # trocar de vm
            self._get(action)

        elif cmd[0] == 'stop':  # parar execucao
            self.stop_it(cmd[1])

        # obter informacoes de uma rede
        elif cmd[0] == 'get_network':
            self._getNetwork(action)

        elif cmd[0] == 'new_network':
            self._newNetwork(cmd[1])

        elif cmd[0] == 'list_networks':
            self._listNetworks()

        elif cmd[0] == 'rm_network':
            self._rmNetwork(cmd)

        elif cmd[0] == 'get_terms':
            self._getTerms()

    def _getTerms(self):
        self.socketCMD.send_string('get_terms')
        resp = self.socketCMD.recv_multipart()
        for term in resp[0].decode('ascii').split(';-;'):
            print(term)

    def _rmNetwork(self, cmd):
        self.socketCMD.send_string(cmd)
        resp = self.socketCMD.recv_multipart()
        print(resposta(resp))

    def _listNetworks(self):
        self.socketCMD.send_string('list_networks')
        resp = self.socketCMD.recv_multipart()
        for name in resp[0].decode('ascii').split(';-;'):
            print(name)

    def _newNetwork(self, name):
        new_network = open(name, 'r')
        parsed_network = pseudo_parser(new_network.readlines())
        new_network.close()
        if parsed_network:
            parsed_network = ';-;'.join(parsed_network)
            request = 'new_network;-;' + parsed_network
            self.socketCMD.send_string(request)
            resp = self.socketCMD.recv_multipart()
            print(resposta(resp))

    def _getNetwork(self, action):
        self.socketCMD.send_string(action)
        if action.split()[1] == 'all':
            try:
                resp = self.socketCMD.recv_multipart()
                resp = resp[0].decode('ascii').split(';-;')
                for data in resp:
                    print(data)
            except Exception as e:
                print(e)
        else:
            resp = self.socketCMD.recv_multipart()
            print('informacao da rede:  ', resp[0].decode('ascii'))

    def _get(self, action):
        self.socketCMD.send_string(action)
        resp = self.socketCMD.recv_multipart()
        print(resposta(resp))

    # para a execucao, e envia uma mesagem ao servidor informando a parada
    # altera started pra false
    def stop_it(self, name):
        if self._started:
            self.socketCMD.send_string('stop %s' % name)
            self.term.stop()
            resp = self.socketCMD.recv_multipart()
            if resp[0].decode('ascii') != 'OK':
                print('Ops:', resp)
            self._started = False


########################################################
def resposta(resp):
    resp = resp[0].decode('ascii')
    if resp != 'OK':
        return 'Ops:' % resp
    else:
        return 'OK'


########################################################
def pseudo_parser(arglist):
    name = arglist[0].strip('#')
    name = name.replace(' ', '_')
    if not name:
        print('rede deve ter um nome')
        return False

    author = arglist[1].strip('#')
    author = author.replace(' ', '_')
    if not author:
        print('rede deve ter um autor')
        return False

    desc = arglist[2].strip('#')
    desc = desc.replace(' ', '_')
    if not desc:
        print('rede deve ter uma descricao')
        return False

    pref = arglist[3].strip('#')
    pref = pref.replace(' ', '_')
    if not pref:
        print('Se nao possuir preferencias, escreva "Nenhuma"')
        return False

    now = datetime.datetime.now()
    published_date = str(now.day) + '-' + str(now.month) + '-' + str(now.year)

    network = arglist[4:]
    network = ''.join(network)
    return [name, author, desc, pref, published_date, network]


########################################################
if __name__ == '__main__':
    import gi

    gi.require_version('Gtk', '3.0')
    gi.require_version('Vte', '2.91')
    from gi.repository import Gtk, Vte
    import os
    import pty

    comando = Command('localhost', 5555)
    comando.start('teste')
    comando.buildTerm()


    # comando.run()
    # comando.stop_it('teste')
    # print('fim')

    def app():
        pid = os.fork()
        if pid:
            ptm = Vte.Pty.new_foreign_sync(comando.term.fdm)
            return ptm
        comando.run()


    # cria um vte
    terminal = Vte.Terminal()

    # obtém o pseudo-tty mestre
    pts = app()

    # vincula o pseudo-tty ao terminal
    terminal.set_pty(pts)

    # cria uma janela e associa o Vte a ela
    win = Gtk.Window()
    win.connect('delete-event', Gtk.main_quit)
    win.add(terminal)
    win.show_all()

    Gtk.main()
    comando.stop_it('teste')
    print('cabossi')
