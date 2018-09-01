import hashlib
import os
import pty
import signal
import sys
import time


class VSwitch:

  ActivationWatchPeriod = 0.1

  def __init__(self, name):
    self.name = name
    self.pid = 0
    self.socket = ''
    self.cmd = self.__gen_cmd__()

  def __gen_cmd__(self):
    cmd = ['%s/bin/uml_switch' % os.environ['NETKIT2_HOME']]
    cmd.append('-hub')
    cmd.append('-unix')
    self.socket = '%s/.netkit/hubs/vhub_%s_%s.cnct' % (os.environ['HOME'], os.environ['USER'], self.name)
    cmd.append(self.socket)
    return cmd

  def getLink(self):
    return self.socket

  def start(self):
    if self.started():
      raise Exception('already started')
    try:
      os.remove(self.socket)
    except Exception as e:
      pass
    self.pid = os.fork()
    if self.pid == 0:
      fd = os.open('/dev/null',os.O_RDONLY)
      os.dup2(1, 2)
      os.dup2(fd, 0)
      os.close(fd)
      try:
        path = os.path.split(self.socket)[0]
        os.stat(path)
      except:
        os.makedirs(path, 0o700)
      print (self.cmd)
      os.execvp(self.cmd[0], self.cmd)
      sys.exit(0)
    # aguarda o switch ativar
    while 1:
      try:
        os.stat(self.socket)
        break
      except:
        time.sleep(self.ActivationWatchPeriod)

  def started(self):
    return self.pid != 0

  def stop(self):
    if self.started():
      os.kill(self.pid, 9)
      os.waitpid(self.pid, 0)
      pid = self.pid
      self.pid = 0
      self.socket = ''
      return pid

class VM:

  #eth0=daemon,,,/home/msobral/.netkit/hubs/vhub_msobral_link1.cnct
  Disk = '*LAB*/*NAME*.disk'
  DiskRW = '*NKDIR*/fs/root.disk'
  Suffix = ['SELINUX_INIT=0']
  Cmd = ['*NKDIR*/fs/vmlinux', 'name=*NAME*', 'title=*NAME*', 'umid=*UMID*', 'mem=*MEM*M', 'uml_dir=*HOME*/.netkit/mconsole', 'root=*ROOT*', 'rw', 'quiet', 'con0=*CON0*', 'con1=*CON1*', 'hostlab=*LAB*', 'mconsole=notify:*NAME*.sock']
  #Cmd = ['sudo','ip', 'netns', 'exec', '*UMID*','*NKDIR*/fs/vmlinux', 'name=*NAME*', 'title=*NAME*', 'umid=*UMID*', 'mem=*MEM*M', 'uml_dir=*HOME*/.netkit/mconsole', 'root=*ROOT*', 'rw', 'quiet', 'con0=*CON0*', 'con1=*CON1*', 'hostlab=*LAB*', 'mconsole=notify:*NAME*.sock']
  Args = {'lab':'lab', 'mem':32, 'con0':'fd:0,fd:1','con1':'null','nkdir': os.environ['NETKIT2_HOME'], 'root': '98:0',
          'home': os.environ['HOME'], 'rw':0}
  Keys = {'*LAB*': 'lab', '*NKDIR*': 'nkdir','*ROOT*':'root', '*UMID*':'umid',
          '*NAME*':'name', '*MEM*': 'mem', '*HOME*':'home', '*CON0*':'con0', '*CON1*': 'con1'}

  Stopped = 0
  Running = 1
  Stopping = 2
  
  # Lista de numeros de interfaces: usados para gerar os nomes das interfaces tap ...
  N = []
  
  def __init__(self, name, **args):
    self.args={}
    self.args.update(self.Args)
    self.args.update(args)
    self.args['name'] = name
    self.__set_umid__()
    self.serial = {}
    self.ifaces = {}
    self.fd = -1
    self.pid = -1
    self.cow = False
    self.state = self.Stopped
    self.uplinks = {}

  def get_name(self):
    return self.args['name']

  def __set_umid__(self):
    try:
      self.args['umid'] = '%s_%s' % (self.args['net'], self.args['name'])
    except:
      self.args['umid'] = '%s' % self.args['name']

  def set_args(self, **args):
    self.args.update(args)
    self.__set_umid__()

  def add_interface(self, ifnum, link):
    self.ifaces[ifnum] = link

  def add_serial(self, n, port):
    self.serial['ssl%d' % n] = 'tty:%s' % port

  def add_uplink(self, ifnum, ip=None, bridge=None):
    self.uplinks[ifnum] = (self.__get_unique__(),  ip,bridge)

  def __get_unique__(self):
    n = 0
    while True:
      try:
        if self.N[n] != n:
          self.N.insert(n, n)
          return n
      except IndexError:
        self.N.append(n)
        return n
      n += 1

  # destructor: usado para remover numeros de interfaces tap da variavel de classe N
  def __del__(self):
    for n, ip, bridge in self.uplinks.values():
        self.N.remove(n)

  # gera o nome da interface tap. Precisa ser revisto, porque o nome depende do usuario que roda a rede e
  # do nome da vm. Se um usuario executar duas rees que tem uma vm com mesmo nome, nao conseguirah
  # criar interfaces tap em ambas. Em um cenario em que o netkit roda em um servidor de aplicacao, tal 
  # situacao poderia ocorrer ...
  def __tap_name__(self, n):
    suffix = '%s_%s_%d' % (os.environ['USER'], self.args['name'], n)
    m = hashlib.md5()
    m.update(suffix)
    ifname = 't_%s' % m.hexdigest()[:8]
    return ifname

  def __get_tap__(self, n):
    num, ip,bridge = self.uplinks[n]
    ifname = self.__tap_name__(num)
    if bridge:
      opts = '-b %s' % bridge
    else:
      if ip:
        opts = '-I %s' % ip
    os.system('sudo -A -E %s/bin/tap.py %s -i %s' % (os.environ['NETKIT2_HOME'], opts, ifname))
    return ifname

  def stop_uplinks(self):
    for iface in self.uplinks:
      num, ip,bridge = self.uplinks[iface]
      ifname = self.__tap_name__(num)
      if bridge:
        opts = '-b %s' % bridge
      else: opts = ''
      os.system('sudo -A -E %s/bin/tap.py %s -d -i %s' % (os.environ['NETKIT2_HOME'], opts, ifname))

  def __gen_cmd__(self):
    cmd = []
    Cmd = self.Cmd[:]
    self.disk = self.Disk.replace('*LAB*', self.args['lab'])
    self.disk = self.disk.replace('*NAME*', self.args['name'])
    self.rootdisk = self.DiskRW.replace('*NKDIR*', self.args['nkdir'])

    if self.args['rw']:
      Cmd.append('ubd0=%s' % self.rootdisk)
      self.cow = False
    else:
      Cmd.append('ubd0=%s' % self.disk)
      self.cow = True
    for x in Cmd:
      for k in self.Keys:
        k2 = self.Keys[k]
        x = x.replace(k, str(self.args[k2]))
      cmd.append(x)
    for serial in self.serial.keys():
      cmd.append('%s=%s' % (serial, self.serial[serial]))
    for ifnum in self.ifaces:
      cmd.append('eth%s=daemon,,,%s' % (ifnum, self.ifaces[ifnum]))
    for uplink in self.uplinks:
      tap = self.__get_tap__(uplink)
      cmd.append('eth%d=tuntap,%s' % (uplink, tap))
    return cmd+self.Suffix

  def __mkcow__(self):
    if not self.cow: return
    pid = os.fork()
    if not pid:
      os.execlp('uml_mkcow','uml_mkcow', self.disk, self.rootdisk)
      raise Exception('ao rodar uml_mkcow')
    os.waitpid(pid, 0)

  def start(self):
    cmd = self.__gen_cmd__()
    self.pid,self.fd = pty.fork()
    if self.pid == 0:
      self.__mkcow__()
      #os.system('sudo ip netns add %s' % self.args['umid'])
      os.execvp(cmd[0], cmd)
      sys.exit(0)
    self.state = self.Running
    return self.fd

  def startSimple(self):
    cmd = self.__gen_cmd__()
    self.pid = os.fork()
    if self.pid == 0:
      self.__mkcow__()
      os.execvp(cmd[0], cmd)
      sys.exit(0)
    self.state = self.Running
    return self.pid

  def startWithin(self, container=None):
    cmd = self.__gen_cmd__()
    container = container.split()
    cmd = container + cmd
    self.pid = os.fork()
    if self.pid == 0:
      self.__mkcow__()
      signal.signal(signal.SIGINT, signal.SIG_IGN)
      os.execvp(cmd[0], cmd)
      print ('???')
      sys.exit(0)
    self.state = self.Running
    return self.pid

  def getStartCommand(self):
    return self.__gen_cmd__()

  def stop(self):
    if not self.started(): return
    print ('parando', self.args['umid'])
    try:
      os.system('%s/bin/uml_mconsole %s cad > /dev/null 2>&1' % (os.environ['NETKIT2_HOME'], self.args['umid']))
      time.sleep(0.5)
      os.system('%s/bin/uml_mconsole %s cad > /dev/null 2>&1' % (os.environ['NETKIT2_HOME'], self.args['umid']))
      #os.waitpid(self.pid, 0)
    except Exception as e:
      print ('Ops ... could not halt vm %s:' % self.args['name'], e)
    #if self.fd > 0: os.close(self.fd)
    #pid = self.pid
    #self.pid = -1
    self.state = self.Stopping
    return self.pid

  def kill(self):
    if self.state == self.Stopped: return
    try:
      #os.kill(self.pid, 15)
      #time.sleep(0.5)
      os.system('%s/bin/uml_mconsole %s halt > /dev/null 2>&1' % (os.environ['NETKIT2_HOME'], self.args['umid']))
    except Exception as e:
      pass
    
  def started(self):
    return self.state == self.Running

  def getPty(self):
    return self.fd
    
  def wait(self):
    if self.state == self.Stopping:
      os.waitpid(self.pid, 0)
      try:
        if self.fd > 0: os.close(self.fd)
      except:
        pass
      self.pid = -1
      self.state = self.Stopped


### Terminais para usar em modo puramente texto.
## Dispara um xterm para cada vm

class TermPool:

  def __init__(self):
    self.terms = {}
  
  def addVM(self, vm):
    self.terms[vm.get_name()] = vm

  def start(self, term='xterm -hold -e'):
    for vm in self.terms:
      vm = self.terms[vm]
      vm.set_args(con0='fd:0,fd:1')
      #print (vm.get_name(), vm.__gen_cmd__(), vm.args)
      #print (string.join(vm.__gen_cmd__()))
      vm.startWithin(term)

  def stop(self):
    pids = []
    for vm in self.terms:
      pid = self.terms[vm].stop()
      if pid > 0: pids.append(pid)
    for pid in pids:
      try:
        os.waitpid(pid, 0)
      except:
        pass

  def get_term(self, name):
    return self.terms[name]

  def get_terms(self):
    return self.terms

  def wait(self):
    for vm in self.terms:
      self.terms[vm].wait()


