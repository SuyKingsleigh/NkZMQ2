#!/usr/bin/python

import os
import random
import re
import time

import uml_layer


#####################################################################################
def getpath():
  path = os.getcwd()
  if path[-4:] == '/lab':
    path = path[:-4]
  if not path: path='/tmp'
  #print ('cwd=%s' % path)
  return path
#####################################################################################
def appendToScript(arq, cmd=None):
    if not cmd:
        r = 'echo -n > "%s"\n'% arq
    else:
        r = 'echo "%s" >> "%s"\n' % (cmd, arq)
    return r
    
#####################################################################################
class IP:

  Masks = ['0.0.0.0', '128.0.0.0', '192.0.0.0', '224.0.0.0', '240.0.0.0', '248.0.0.0', '252.0.0.0', '254.0.0.0', '255.0.0.0', '255.128.0.0', '255.192.0.0', '255.224.0.0', '255.240.0.0', '255.248.0.0', '255.252.0.0', '255.254.0.0', '255.255.0.0', '255.255.128.0', '255.255.192.0', '255.255.224.0', '255.255.240.0', '255.255.248.0', '255.255.252.0', '255.255.254.0', '255.255.255.0', '255.255.255.128', '255.255.255.192', '255.255.255.224', '255.255.255.240', '255.255.255.248', '255.255.255.252', '255.255.255.254', '255.255.255.255']

  def __init__(self,  ip):
      if type(ip) == type(''):
        self.ip,  self.mask  = self.__parseIpString__(ip)
      elif type(ip) in [tuple, list]:
        self.ip,  self.mask  = self.__parseIp__(ip[0], ip[1])
      else:
        raise ValueError('ip must be string, tuple or list, and not %s' % type(ip))

  def __hash__(self):
    return hash(repr(self))

  def __parseIpString__(self, data):
     data = data.split('/')
     if len(data) == 2:
       ip, mask = data
     elif len(data) == 1:
       ip = data[0]
       mask = 32
     else:
       raise ValueError('invalid IP address: must be A.B.C.D/M or A.B.C.D')
     return self.__parseIp__(ip, mask)

  def __parseIp__(self, ip, mask):
     try:
        m = int(mask)
        if m < 0 or m > 32:
          raise ValueError('Invalid mask %s !' % mask)
        mask = self.Masks[m]
     except:
        if not mask in self.Masks:
          raise ValueError('Invalid mask %s !' % mask)
     test = list(map(int, ip.split('.')))
     if len(test) != 4: raise ValueError('IP must have exactly 4 octets')
     test = [x for x in test if x >= 0 and x < 256]
     if len(test) != 4: raise ValueError('IP octets must be in range (0,255)')    
     return ip,mask

  def __lastIp__(self, last=1):
    #m = map(int, self.mask.split('.'))
    m = self.Masks.index(self.mask)
    ml = (1<<(32-m))-1 # tamanho da rede - 1
    mask = ((1<<32) - 1) ^ ml # mascara em binario
    ip = int(self)
    base = ip & mask # prefixo da rede
    if last != None:
      nip = base + ml - last # ultimo IP da rede
    else:
      nip = base # prefixo da rede
    #print ('...',m,ml,mask,base,nip)
    ip = []
    ip.append((nip & (0xff << 24))>>24)
    ip.append((nip & (0xff << 16))>>16)
    ip.append((nip & (0xff << 8))>>8)
    ip.append(nip & 0xff)
    ip = '.'.join(list(map(str, ip)))
    return ip

  def getLastIP(self):
    return self.__lastIp__(1)

  def getBroadcast(self):
    return self.__lastIp__(0)
    
  def getPrefix(self):
    return self.__lastIp__(None)
  
  def getMask(self):
    return self.mask

  def getShortMask(self):
    return  self.Masks.index(self.mask)

  def getIp(self):
    return self.ip

  def __repr__(self):
    if self.getShortMask() < 32:
      return '%s/%s' % (self.ip,self.getShortMask())
    return self.ip

  def __int__(self):
    ip = [int(x) for x in self.ip.split('.')]
    return (ip[0]<<24)+(ip[1]<<16)+(ip[2]<<8)+ip[3]

  def __cmp__(self, o):
    ip1 = int(self)
    ip2 = int(o)
    if ip1 < ip2: return -1
    return ip1 > ip2
    
class IPv6(IP):

  Caso0 = re.compile('([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}')
  Caso1 = re.compile('(([0-9a-fA-F]{1,4}:)+)((:[0-9a-fA-F]{1,4})+)$')
  Caso2 = re.compile(':((:[0-9a-fA-F]{1,4})+)$')
  Caso3 = re.compile('(([0-9a-fA-F]{1,4}:)+):$')
  Caso4 = re.compile('(::)$')
  Zeros = re.compile('^((:?0+)+)|((0+:?)+)')

  def __parseIpString__(self, data):
     data = data.split('/')
     if len(data) == 2:
       ip, mask = data
     elif len(data) == 1:
       ip = data[0]
       mask = 128
     else:
       raise ValueError('invalid IPv6 address')
     return self.__parseIp__(ip, mask)

  def __parseIp__(self, ip, mask):
     try:
        m = int(mask)
        if m < 0 or m > 128:
          raise ValueError('Invalid mask %s !' % mask)
        mask = m
     except:
        raise ValueError('Invalid mask %s: must be a number between 0 and 128 !' % mask)

     m = self.Caso0.match(ip)
     if not m:
       m = self.Caso1.match(ip)
       if m:
         i1, i2 = m.group(1,3)
         n = i1.count(':') + i2.count(':')
       else:
         m = self.Caso2.match(ip)
         if m:
           i1 = ''
           i2 = m.group(1)
         else:
           m = self.Caso3.match(ip)
           if m:
             i1 = m.group(1)
             i2 = ''
           else:
             m = self.Caso4.match(ip)
             if m:
               i1 = ''
               i2 = ''
             else:
               raise ValueError('Invalid IPv6 address: %s' % ip) 
       n = 8 - (i1.count(':') + i2.count(':'))
       if n > 0:
         zeros = ':'.join(['0']*n)
         ip = i1+zeros+i2
       elif n < 0: ValueError('Invalid IPv6 address: %s' % ip)

     test = ip.split(':')
     try:
       test = [int(x, 16) for x in test]
     except:
       raise ValueError('Invalid IPv6 address: %s' % ip)
     #print (test)
     test = [x for x in test if x >= 0 and x < 0x10000]
     if len(test) != 8: raise ValueError('IP octets must be in range (0,ffff)')    
     #test = map(lambda x: '%x' % x, test)
     #ip = string.join(test, ':')
     return ip,mask    

  def __lastIp__(self, last=1):
    ml = (1<<(128-self.mask))-1 # tamanho da rede - 1
    mask = ((1<<128) - 1) ^ ml # mascara em binario
    ip = int(self)
    base = ip & mask # prefixo da rede
    if last != None:
      nip = base + ml - last # ultimo IP da rede
    else:
      nip = base # prefixo da rede
    #print ('...',m,ml,mask,base,nip)
    n = 7
    ip = []
    while n >= 0:
      ip.append((nip & (0xffff << (n*16))) >> (n*16))
      n -= 1
    ip = ':'.join(['%x' % x for x in ip])
    return ip

  def __repr__(self):
    if self.mask < 128:
      return '%s/%d' % (self.ip,self.mask)
    return self.ip

  def __int__(self):
    ip = [int(x,16) for x in self.ip.split(':')]
    n = 7
    r = 0
    for w in ip:
      r += (w << (n*16))
      n -= 1
    return r

  def __cmp__(self, o):
    ip1 = int(self)
    ip2 = int(o)
    if ip1 < ip2: return -1
    return ip1 > ip2

  def getCompactIp(self):
    estado = 0
    ip = [int(x,16) for x in self.ip.split(':')]
    s = ''
    for x in ip:
      if estado == 0: # primeira palavra
        if x == 0:
          s += '::'
          estado = 2
        else: 
          s += '%x:' % x
          estado = 1
      elif estado == 1: # palavra diferente de zero
        if x == 0:
          s += ':'
          estado = 2
        else: 
          s += '%x:' % x
          estado = 1
      elif estado == 2: # zero
        if x != 0:    
          s += '%x:' % x
          estado = 3
      elif estado == 3: # palavra qualquer depois de zeros
          s += '%x:' % x
    if estado == 3 or estado == 1: return s.rstrip(':')
    return s         

  def getCompact(self):
    return '%s/%d' % (self.getCompactIp(), self.mask)
    
#####################################################################################
class NetkitInterface:

  Masks = ['128.0.0.0', '192.0.0.0', '224.0.0.0', '240.0.0.0', '248.0.0.0', '252.0.0.0', '254.0.0.0', '255.0.0.0', '255.128.0.0', '255.192.0.0', '255.224.0.0', '255.240.0.0', '255.248.0.0', '255.252.0.0', '255.254.0.0', '255.255.0.0', '255.255.128.0', '255.255.192.0', '255.255.224.0', '255.255.240.0', '255.255.248.0', '255.255.252.0', '255.255.254.0', '255.255.255.0', '255.255.255.128', '255.255.255.192', '255.255.255.224', '255.255.255.240', '255.255.255.248', '255.255.255.252', '255.255.255.254', '255.255.255.255']

  Attr=['link','ip', 'ipv6', 'rate', 'noipv6','down']

  Prefix = ''

  def __init__(self, num, link):
    self.num = num
    self.attrs = {}
    self.iplist = []
    self.ip = ''
    self.ipv6 = []
    self.__parse__(link)

  def __parseIp__(self, data):
    return data

  def __parse__(self, attrs):
    self.link = ''
    self.ip = ''
    #print (attrs)
    for attr in attrs:
      if not attr in self.Attr:
        raise ValueError('Unknown attribute to interface %s: "%s"' % (self.ifName(), attr))
      if attr == 'ip':
        iplist = attrs[attr]
        if type(iplist) == type(''):
          try:
            self.ip = self.IP(iplist)
            continue
          except:
            pass
        elif isinstance(iplist, IP):
          #print (self.ifName(), iplist)
          self.ip = iplist
        else:
          self.ip = iplist[0]
          self.iplist = iplist[1:]
          continue
          # abaixo ficou obsoleto ... o parser jah retorna objetos IP
          try:
            self.ip = self.__parseIp__(iplist[0])
            self.iplist = list(map(self.__parseIp__, iplist[1:]))
            continue
          except:
            pass
      if attr == 'ipv6':
        self.ipv6 += attrs[attr]
        continue
      if attr == 'link':
        self.link = attrs[attr]
        continue
      #self.attrs[attr] = attrs[attr]

  def getIfaces(self,  ifClass):
      if isinstance(self, ifClass): return [self]
      
  def ifName(self):
    raise ValueError('Abtract interface ... you should not use class NetkitInterface directly !')

  def toVM(self, vm):
    raise ValueError('Abtract interface ... you should not use class NetkitInterface directly !')

  def getBroadcast(self):
    return self.ip.getBroadcast()
    
  def getPrefix(self):
    return self.ip.getPrefix()
  
  def getMask(self):
    return self.ip.getShortMask()

  def getIp(self):
    return self.ip.getIp()

  def getIPv6(self, n=0):
    if not self.ipv6: return None
    try:
      return self.ipv6[n]
    except:
      return self.ipv6[0]

  def addRoutes(self, routes, routes6):
    s = ''
    for dest in routes:
      try:
        if route[dest]['dev'] == self.ifName():
          s += 'route add -net %s dev %s\n' % (dest, self.ifName())
      except:
        pass
    for dest in routes6:
      try:
        if route6[dest]['dev'] == self.ifName():
          s += 'route -A inet6 add %s dev %s\n' % (dest, self.ifName())
      except:
        pass
    return s

  def __repr__(self):
    #print (self.ifName(), self.ip)
    s = ''
    if not 'down' in self.attrs:
        s += 'ifconfig %s up\n' % self.ifName()
    else:
        s += 'ifconfig %s down\n' % self.ifName()        
    if self.ip:
      s += 'ifconfig %s %s netmask %s\n' % (self.ifName(), self.ip.getIp(), self.ip.getMask())
    if 'noipv6' in self.attrs:
      s += 'sysctl -w net.ipv6.conf.%s.disable_ipv6=1\n' % self.ifName()
    else:
      for ipv6 in self.ipv6:
        s += 'ifconfig %s inet6 add %s\n' % (self.ifName(), ipv6.getCompact())
    if 'rate' in self.attrs:
        s += 'tc qdisc add dev %s root handle 1: tbf rate %skbit burst 4096 limit 262144\n' % (self.ifName(),  self.attrs['rate'])
    return s

  def __cmp__(self, o):
    t1,n1 = self.ifType(),self.num
    t2,n2 = o.ifType(),o.num
    #print (t1, t2)
    if t1 == t2:
      if n1 < n2: return -1
      return n1 > n2
    if t1 < t2: return -1
    return t1 > t2
    
  def start(self):
    pass

class NetkitPPPInterface(NetkitInterface):

  Basic_Opts = 'ttyS%d %d unit %d ipcp-accept-remote local nocrtscts'
  PPP_Opts = 'persist lcp-echo-failure 10 noauth noccp nobsdcomp nodeflate'
  Prefix = 'ppp'

  Attr = NetkitInterface.Attr + ['ber','delay','rate', 'debug']

  def __init__(self, num, link, ppp_opts=''):
    NetkitInterface.__init__(self, num, link)
    if ppp_opts:
      self.opts = '%s %s' % (self.Basic_Opts, ppp_opts)
    else:
      self.opts = '%s %s' % (self.Basic_Opts, self.PPP_Opts)
    self.pty = ''

  def ifName(self):
    return 'ppp%d' % self.num

  def ifType(self):
    return 'ppp'

  def __addCommand__(self, cmd, ip='ip'):   
    ipup = '/etc/ppp/%s-up.d/%s' % (ip,self.ifName())
    s = 'echo "%s" >> %s\n' % (cmd, ipup)
    return s

  def addCommand(self, cmd):
    return self.__addCommand__(cmd)

  def addCommand6(self, cmd):
    return self.__addCommand__(cmd, 'ipv6')

  def addRoutes(self,  routes, routes6):
    #ipup = '/etc/ppp/ip-up.d/%s' % self.ifName()
    #ipup6 = '/etc/ppp/ipv6-up.d/%s' % self.ifName()
    s = ''
    for r in routes:
        dest = r
        try:
            dev = routes[r]['dev']
            if not dev: continue
        except:
            continue
        if dev == self.ifName():
            s += self.addCommand('route add -net %s dev %s' % (dest,  dev))
            #s += 'echo route add -net %s dev %s >> %s\n' % (dest,  dev,  ipup)
    for r in routes6:
        dest = r
        try:
            dev = routes6[r]['dev']
            if not dev: continue
        except:
            continue
        if dev == self.ifName():
          s += self.addCommand6('route -A inet6 add %s dev %s' % (dest,  dev))
          #s += 'echo route -A inet6 add %s dev %s >> %s\n' % (dest,  dev,  ipup6)
    return s

  def __parse__(self, attrs):
    NetkitInterface.__parse__(self, attrs)
    self.delay = 0
    self.speed = 115200
    self.ber = 0
    self.debug = False
    for item in attrs:
      data = attrs[item]
      if item == 'ber':
        self.ber = float(data)
      elif item == 'delay':
        self.delay = int(data)
      elif item == 'rate':
        self.speed = int(data)
      elif item == 'debug':
        self.debug = data

  def __repr__(self):
    s = 'if [ ! -c /dev/ttyS%d ]; then mknod /dev/ttyS%d c 4 %d;fi\n' % (self.num, self.num, self.num + 64)
    if not self.ip and not self.ipv6: return s
    ipup = '/etc/ppp/ip-up.d/%s' % self.ifName()
    ipup6 = '/etc/ppp/ipv6-up.d/%s' % self.ifName()
    for arq in (ipup, ipup6):
      s += 'cp /hostlab/shared/templates/ip-up.tmpl %s\n' % arq
      s += 'chmod +x %s\n' % arq
    opts = self.opts % (self.num, self.speed, self.num)
    if self.ip:
      opts += ' %s:' % self.ip.getIp()
    else:
      opts += ' noip'
    if self.ipv6:
      ipv6 = self.ipv6[0]
      opts += ' +ipv6'
      for ipv6 in self.ipv6:
        s += self.addCommand6('ifconfig %s inet6 add %s' % (self.ifName(), ipv6.getCompact()))
        #s += 'echo ifconfig %s inet6 add %s >> %s\n' % (self.ifName(), ipv6.getCompact(), ipup6)
    else:
      opts += ' noipv6'

    if self.debug:
      opts += ' record /hostlab/VM/%s.log' % self.ifName()

    s += 'pppd %s\n' % opts
    return s

  def setPty(self, pty):
    self.pty = pty

  def toVM(self, vm):
    vm.add_serial(self.num, self.pty)
        
class NetkitEthInterface(NetkitInterface):

  Prefix = 'eth'
  Config8021xPath = '/etc/wpa_supplicant'
  Config8021x = '%s/wpa.conf' % Config8021xPath
  Supplicant = '/hostlab/shared/templates/wpa/'
  Template8021x = '%s/wpa.conf' % Supplicant

  Attr = NetkitInterface.Attr + ['vlans_tagged', 'vlan_tagged','vlan_untagged',
           'stp_cost','max_age','hello_time','forward_delay', 'hostif','mode','pppoe_ac',
           'pppoe_user','pppoe_password','8021x_authenticator','8021x_user']

  def __init__(self, num, link):
    NetkitInterface.__init__(self, num, link)
    if not self.link:
      raise ValueError('link name (collision domain) must be defined on interface %d' % self.num)
    self.vlink = link

  def __parseIp__(self, data):
    r = None
    if data == 'dhcp':
      self.attrs['dhcp']=True
      return r
    return NetkitInterface.__parseIp__(self, data)

  def __parse__(self, attrs):    
    NetkitInterface.__parse__(self, attrs)
    self.vid = 0
    self.vlans = {}
    self.subif = []
    for item in attrs:
      data = attrs[item]
      if item == 'vlan_untagged':
        if self.vid:
          raise ValueError('Interface %s: only one untagged vlan allowed !' % self.ifName())
        self.vid = data
      elif item in ['vlans_tagged', 'vlan_tagged']:
        # interface vlan tagged como subinterface ???
        for vid,ip in data:
          if type(ip) == type([]): aip = ip[0]
          else: aip = ip
          if isinstance(aip, IPv6): attrs = {'ipv6': ip}
          elif isinstance(aip, IP): attrs = {'ip': ip}
          else: attrs = {}
          attrs.update({'vlan_untagged': vid, 'link': self.link, 'hostif': self})
          subif = NetkitEthInterface(self.num, attrs)
          self.subif.append(subif)
          #self.vlans[vid] = self.__parseIp__(ip)
      else:
        if not item in self.attrs: self.attrs[item] = data
    if not self.vid and len(self.subif) == 0:
      self.vid = 1

  def getStpCost(self):
    try:
      return int(self.attrs['stp_cost'])
    except:
      return 0

  def getStpPrio(self):
    try:
      return int(self.attrs['stp_prio'])
    except:
      return 0

  def vlanIface(self, vlan):
    # untagged
    if vlan == self.vid:
      return self.ifName()
    # tagged ?
    for subif in self.subif:
      iface = subif.vlanIface(vlan)
      if iface: return iface
    # nao tem vlan ...
    return ''

  def ifType(self):
    return self.Prefix

  def confDescription(self):
    return '[%d]=%s' % (self.num, self.link)

  def ifName(self):
    if self.isSubInterface():
      return '%s%d.%d' % (self.Prefix, self.num, self.vid)    
    else:
      return '%s%d' % (self.Prefix,self.num)

  def isAuthenticator(self):
    #print (self.ifName(), self.attrs)
    try:
        return int(self.attrs['8021x_authenticator'])
    except:
        return False

  def isSubInterface(self):
    return 'hostif' in self.attrs

  def addSubinterface(self, iface):
    for subif in self.subif:
      if subif.ifName() == iface.ifName():
        raise ValueError('Subinterface %s already exists in %s' % (iface.ifName(), self.ifName()))
    self.subif.append(iface)

  def __ifConfig__(self):
    r = ''
    iface = self.ifName()
    if self.isSubInterface():
      hostif = self.attrs['hostif'].ifName() 
      r += 'vconfig add %s %d\n' % (hostif, self.vid)

    r += NetkitInterface.__repr__(self)
    #if self.isSubInterface():
    #  print (iface, self.ip, self.ipv6, r)

    try:
      dhcp = (self.attrs['ip'] == 'dhcp')
      if dhcp:
        r += 'dhclient -nw %s\n' % iface
    except Exception as e:
      print (e)
      pass

    #if not self.ip:
    #  r += 'ifconfig %s up\n' % iface
    #  try:
    #    dhcp = int(self.attrs['dhcp'])
    #    if dhcp:
    #      r += 'dhclient -nw %s\n' % iface
    #  except:
    #    pass
    #  return r
    #else:
    #  r += 'ifconfig %s %s netmask %s\n' % (iface, self.ip.getIp(), self.ip.getMask())

    n = 0
    for ip in self.iplist:
      r += 'ifconfig %s:%d %s netmask %s\n' % (iface, n, ip.getIp(), ip.getMask())
      n += 1
    return r

  def __repr__(self):
    print(self.attrs)
    s = self.__ifConfig__()
    for subif in self.subif:
      s += repr(subif)
    try:
        user,password = self.attrs['8021x_user']
        s += 'mkdir -p %s\n' % self.Config8021xPath
        s += 'sed -e s/USER/%s/ -e s/PASSWORD/%s/ %s > %s-%s\n' % (user, password,  self.Template8021x,  self.Config8021x,  self.ifName())
        s += 'cp %s/* /usr/local/sbin/\n' % self.Supplicant
        s += 'wpa_supplicant -i %s -Dwired -c %s-%s -B\n' % (self.ifName(),  self.Config8021x,  self.ifName())
    except Exception as e:
        #print ('WARNING: could not run supplicant: ',  e)
        pass
    return s

  def getVlans(self):
    r = [subif.vid for subif in self.subif]
    if self.vid:
      r.append(self.vid)
    return r

  def setVLink(self, vlink):
    self.vlink = vlink

  def toVM(self, vm):
    vm.add_interface(self.num, self.vlink)

class NetkitPPPoEInterface(NetkitPPPInterface):

  PPPoE_Opts = 'pppd pty \"/usr/sbin/pppoe -I %s -T 80 -m 1452 -C %s\" noipdefault user %s usepeerdns defaultroute hide-password lcp-echo-interval 20 lcp-echo-failure 3 connect /bin/true noauth persist mtu 1492 noaccomp default-asyncmap unit %d\n'
  PPPoE_Op1 = 'pty \\"/usr/sbin/pppoe -I %s -T 80 -m 1452 -C %s\\"'
  PPPoE_Op2 = 'user %s unit %d'
  PPPoE_Ops = ['noipdefault', 'usepeerdns', 'defaultroute', 'hide-password', 'lcp-echo-interval 20', 'lcp-echo-failure 3', 'connect /bin/true', 'noauth', 'persist', 'mtu 1492', 'noaccomp', 'default-asyncmap']

  PPPoE_Attr = ['interface','user','password','type']
  Attr = NetkitPPPInterface.Attr + PPPoE_Attr

  def __init__(self, num, link):
    NetkitPPPInterface.__init__(self, num, link)
    #print (self.attrs)
    if self.attrs['type'] != 'pppoe':
      raise ValueError('%s: not a PPPoE interface' % self.ifName())
    if not 'user' in self.attrs:
      raise ValueError('Missing PPPoE user')
    if not 'password' in self.attrs:
      raise ValueError('Missing PPPoE password')
    if not 'interface' in self.attrs:
      raise ValueError('Missing PPPoE host interface')
        
  def __parse__(self, attrs):
    NetkitPPPInterface.__parse__(self, attrs)
    for item in attrs:
      data = attrs[item]
      if item in self.PPPoE_Attr: self.attrs[item] = data
      
  def __repr__(self):
    s = 'echo -n > /etc/ppp/chap-secrets\n'
    s += 'echo %s \* %s >> /etc/ppp/chap-secrets\n' % (self.attrs['user'], self.attrs['password'])
    s += 'sleep 2\n' 
    #s += self.PPPoE_Opts % (self.attrs['pppoe_ac'], self.attrs['pppoe_user'])
    echo = 'echo %s >> /etc/ppp/peers/adsl\n'
    s += echo % (self.PPPoE_Op1 % (self.attrs['interface'], self.link))
    s += echo % (self.PPPoE_Op2 % (self.attrs['user'], self.num))
    for linha in self.PPPoE_Ops:
      s += echo % linha
    s += 'pppd call adsl\n'
    return s

  def getHostInterface(self):
    return self.attrs['interface']

class NetkitBondingInterface(NetkitEthInterface):

  Prefix = 'bond'
  Attr = NetkitEthInterface.Attr + ['interfaces',  'mode', 'miimon',  'lacp_rate']
  Modes = {'round-robin': 0,  'backup': 1, 'xor':2, 'broadcast':3, '802.3ad':4,  '8023ad':4,   'tlb':5, 'alb':6}
  Defaults = {'mode': 0,  'miimon': 100}
  
  def __init__(self, num, link):
    NetkitEthInterface.__init__(self, num, link)

  def __parse__(self, link):    
    NetkitEthInterface.__parse__(self, link)
    self.interfaces = []
    for item in self.attrs:
      data = self.attrs[item]
      if item == 'interfaces':
        fac = NetkitInterfaceFactory()
        interfaces = [x.strip() for x in data]
        #print (interfaces)
        n = 0
        for iface in interfaces:
          link = '%s-%d' % (self.link,  n) 
          iface = fac.getNetkitInterface(iface, {'link':link})
          self.interfaces.append(iface)
          print(self.ifName(),  iface.link,  iface.attrs)
          n += 1
      elif item == 'mode':
          data = self.attrs[item].lower()
          if not data in self.Modes:
              raise ValueError('unknown bonding mode: %s' % data)
          self.attrs[item] = self.Modes[data]
      elif item == 'lacp_rate':
          data = self.attrs[item].lower()
          if data == 'slow': self.attrs['lacp_rate'] = 0
          elif data == 'fast': self.attrs['lacp_rate'] = 1
          else: raise ValueError('Invalid lacp_rate on %s' % self.ifName())
    if not self.interfaces:
      raise ValueError('Link-aggregation interface %s lacks slave interfaces' % self.ifName())
    if not 'mode' in self.attrs: self.attrs['mode'] = self.Defaults['mode']
    if not 'miimon' in self.attrs: self.attrs['miimon'] = self.Defaults['miimon']

  def __repr__(self):
    s = ''
    for iface in self.interfaces:
      s += 'ifconfig %s up\n' % iface.ifName()
    #s += 'modprobe bonding mode=%d miimon=%d -o %s\n' % (self.attrs['mode'],  self.attrs['miimon'],  self.ifName())
    s += 'modprobe bonding max_bonds=0\n'
    s += 'echo +%s > /sys/class/net/bonding_masters\n' % self.ifName()
    s += 'echo %d > /sys/class/net/%s/bonding/mode\n' % (self.attrs['mode'],  self.ifName())
    s += 'echo %d > /sys/class/net/%s/bonding/miimon\n' % (self.attrs['miimon'],  self.ifName())
    #s += 'echo 1 > /sys/class/net/%s/bonding/all_slaves_active\n' % self.ifName()
    try:
        s += 'echo %d > /sys/class/net/%s/bonding/lacp_rate\n' % (self.attrs['lacp_rate'],  self.ifName())
    except KeyError:
        pass
    s += NetkitEthInterface.__repr__(self)
    lif = [x.ifName() for x in self.interfaces]
    s += 'ifenslave %s %s\n' % (self.ifName(), ' '.join(lif))
    return s

  def getIfaces(self, ifClass):
      return [x for x in self.interfaces if isinstance(x, ifClass)]  

  def toVM(self, vm):
    n = 0
    for iface in self.interfaces:
      #vm.add_interface(iface, '%s-%d' % (self.link, n))
      iface.toVM(vm)
      #vm.add_interface(iface, '%s' % self.vlink)
      n += 1

class NetkitUplinkInterface(NetkitEthInterface):

  Attr = NetkitEthInterface.Attr + ['bridge']

  def __init__(self, num, link):
    NetkitEthInterface.__init__(self, num, link)
    if self.link != 'uplink':
      raise ValueError('%s: not uplink interface' % self.ifName())

  def __parse__(self, link):
    NetkitEthInterface.__parse__(self, link)
    if self.ip:
      self.hostip = self.ip.getLastIP()
    else:
      self.hostip = ''

  def confDescription(self):
    try:
        ip = self.ip.getIp()
    except:
        ip = ''
    return '[%d]=tap,%s,%s' % (self.num, self.hostip, ip)

  def __genMac__(self, prefix='6e:5f:98'):
    mac=prefix
    n = 3
    while n > 0:
      b = random.randint(0,255)
      mac += ':%02x' % b
      n -= 1
    return mac

  def __repr__(self):
    r = 'ifconfig %s hw ether %s\n' % (self.ifName(), self.__genMac__())
    r += NetkitEthInterface.__repr__(self)
    return r

  def start(self):
    pass

  def toVM(self, vm):
    try:
        br = self.attrs['bridge']
    except:
        br = None
    
    if self.hostip: ip = '%s/%s' % (self.hostip, self.ip.getShortMask())
    else: ip = None
    vm.add_uplink(self.num, ip, br)

#####################################################################################
class NetkitObject:

  Kind = 'generic'

  Dhcp_params = {'default-lease': 600, 'max-lease': 3600}
  Attr = ['default_gateway','mem','preserve','route','dhcp','services',
          'radius','width','height','x','y']

  def __init__(self, name, data):
    self.name = name
    self.ifaces = []
    self.data = data
    self.routes = {}
    self.routes6 = {}

  def get_num_interfaces(self, ifClass=None):
      return len(self.getIfaces(ifClass))
  
  def addInterface(self, iface):
    if self.getIface(iface.ifName()):
      raise ValueError("%s already has interface %s" % (self.name, iface.ifName()))
    self.ifaces.append(iface)
    self.ifaces.sort()
  
  def getIface(self, ifname):
    r = [x for x in self.ifaces if x.ifName() == ifname]
    if r:
      return r[0]
    return None

  def getIfaces0(self, ifClass=None):
    if ifClass:
      return [x for x in self.ifaces if isinstance(x, ifClass)]
    return self.ifaces
  
  def getIfaces(self, ifClass=None):
    if ifClass:
      r = []
      for iface in self.ifaces:
          if isinstance(iface,  ifClass):
              r += iface.getIfaces(ifClass)
      return r
    return self.ifaces
  
  def __tryInt__(self, x):
    try:
      return int(x)
    except:
      return x

  def clear_routes(self):
      self.routes= {}
      
  def add_route(self, dest, gw, dev=None):
      self.routes[dest] = {}
      if dev:
          self.routes[dest]['dev'] = dev
      if gw:
          self.routes[dest]['gateway'] = gw
          
  def get_routes(self):
      r = []
      for dest in self.routes:
          rt = self.routes[dest]
          try:
              gw = rt['gateway']
          except:
              gw = ''
          try:
              dev = rt['dev']
          except:
              dev = ''
          r.append((dest,gw,dev))
      return r

  def __inet6route__ (self, data):
    if isinstance(data['default_item'], IPv6): return True
    try:
      ip = data['gateway']
      if isinstance(ip, IPv6): return True
    except:
      pass
    return False
      
  def setAttribute(self, attr, data):
    #print (self.name, attr, data)
    if not attr in self.Attr:
      raise ValueError('"%s" is %s and does not support attribute "%s"' % (self.name, self.Kind, attr))
    if attr == 'route':
      key = data['default_item']
      if self.__inet6route__(data):
        if type(key) == type(''):
          if key == 'default6': key = '::/0'
          else: raise ValueError('unknown destination format')
        else: key = repr(key)
        self.routes6[key] = data
      else:
        if type(key) == type(''):
          if key == 'default': key = '0.0.0.0/0'
          else: raise ValueError('unknown destination format')
        else: key = repr(key)
        self.routes[key] = data    
    elif attr == 'dhcp':
      iface = data['default_item']
      if not 'range' in data:
        raise ValueError('DHCP requires attribute "range"')
      d = {}
      d.update(self.Dhcp_params)
      d.update(data)
      ip1,  ip2 = data['range']
      if not isinstance(ip1,  IP): ip1 = IP(ip1)
      if not isinstance(ip2,  IP): ip2 = IP(ip2)
      #ip1, ip2 = map(IP, data['range'])
      if ip1 > ip2:  
        raise ValueError('first IP must precede second IP in range')
      try:
        self.data['dhcp'][iface] = d
      except:
        self.data['dhcp'] = {iface: d}
    elif attr == 'preserve': # diretorios a serem preservados (ex: /etc)
        self.data['preserve'] = data
    elif attr == 'services':
      try:
        self.data['services'] += data
      except:
        self.data['services'] = data
    elif attr == 'mem':
        self.data['mem'] = int(data)
    elif attr == 'radius':
        self.data['radius'] = {'enabled':True, 'users':[],'radius_clients': [],  'port':1812}
        self.data['radius'].update(data)
    elif attr in NetkitObject.Attr:
      self.data[attr] = data

  def __repr__(self):
    s = '%s: ' % self.name
    s += ','.join([x.ifName() for x in self.ifaces])
    return s

  def createStartup(self, path):
    try:
      os.mkdir('%s/%s' % (path, self.name))
    except:
      pass
    script = '%s-auto.sh' % self.name
    def_script = '%s/%s.startup' % (path, self.name)
    try:
      r = open(def_script).read()
    except:
      f = open(def_script, 'w')
      f.write('#!/bin/bash\n\n')
      f.close()
      r = ''
    if r.find('/hostlab/%s' % script) < 0:
      open(def_script, 'a').write('/hostlab/%s\n' % script)
      os.chmod(def_script, 0o700)
    # diretorio onde podem ser criados arquivos a serem usados pela vm
    self.tmplab = '%s/tmp'
    try:
        os.mkdir(self.tmplab)
    except:
        pass
    self.__createScript__('%s/%s' % (path, script))

  def __genScript__(self):
    s = '#!/bin/bash\n\n'
    #s += 'cp /hostlab/shared/templates/tc /usr/sbin\n'
    #s += 'cp /hostlab/shared/templates/sources.list /etc/apt\n'
    #s += 'cp /hostlab/shared/templates/netserver /etc/init.d/\n'
    #s += 'cp /hostlab/shared/templates/profile /etc/\n'
    #s += 'tar xCzf /usr/local /hostlab/shared/templates/pjsip.tgz\n'
    s += 'export PATH=/usr/sbin:${PATH}:/usr/local/bin:/usr/local/sbin\n'
    for iface in self.ifaces:
      r = repr(iface)
      r = r.replace('VM',self.name)
      s += '%s\n' % r
      s += iface.addRoutes(self.routes, self.routes6)
    try:
      s += 'route add default gw %s\n' % self.data['default_gateway']
    except:
      pass
    for dest in self.routes:
      try:
        s += 'route add -net %s gw %s ' % (dest,  self.routes[dest]['gateway'])
      except:
        pass
      s += '\n'
    for dest in self.routes6:
      try:
        s += 'route -A inet6 add %s gw %s ' % (dest, self.routes6[dest]['gateway'])
      except:
        pass
      s += '\n'
    s += self.__genDHCP__()
    try:
        dirs = self.data['preserve']
        tar_file = '/hostlab/%s/preserve.tgz' % self.name
        dirname = '/hostlab/%s/preserve' % self.name
        # removida a compactacaco dentro da VM ... apenas copia os arquivos.
        #s += 'if [ -f "%s" ]; then\n' % tar_file
        #s += '  tar xCzf / %s\n' % tar_file
        #s += 'fi\n'
        s += '#PRESERVE\nif [ -d "%s" ]; then\n' % dirname
        s += '  cd "%s"; cp -r * /\n' % dirname
        s += 'fi\n'
        s += 'cp -p /hostlab/shared/templates/K95preserve /etc/rc0.d\n'
        s += 'echo -n > /etc/default/preserve\n'
        for dir in dirs:
            s += 'echo "%s" >> /etc/default/preserve\n' % dir
        #print (self.name,  s)
    except:
        pass
    if 'services' in self.data:
        s += 'rm -f /etc/rc0.d/S80services\n'
        s += 'cp -a /etc/init.d/services /etc/rc0.d/S80services\n'
        for sv in self.data['services']:
            s += '/etc/init.d/%s start\n' % sv
            s += 'echo /etc/init.d/%s stop >> /etc/rc0.d/S80services\n' % sv
    s += 'sysctl -w net.ipv4.ip_forward=0\n'
    s += 'sysctl -w net.ipv6.conf.all.forwarding=0\n'
    return s

  def __genDHCP__(self):
    try:
      ifaces = self.data['dhcp']
    except:
      return ''
    s = ''
    dhcp_conf = '/etc/dhcp/dhcpd.conf'
    for iface in ifaces:
      ifobj = self.getIface(iface)
      if not ifobj: 
        print('WARNING: no such interface %s when configuring dhcp service ...' % iface)
        continue
      data = ifaces[iface]
      if not 'gateway' in data:
        try:
          data['gateway'] = ifobj.getIp()
        except:
          print('DHCP: could not define a gateway to leases on interface %s' % iface)
      s += "echo 'subnet %s netmask %s {' >> %s\n" % (ifobj.getPrefix(), ifobj.ip.getMask(), dhcp_conf)
      s += "echo '  range %s %s;'>> %s\n" % (data['range'][0], data['range'][1], dhcp_conf)
      try:
        s += "echo '  max-lease-time %s;'>> %s\n" % (data['max-lease'], dhcp_conf)
      except:
        pass
      try:
        s += "echo '  default-lease-time %s;'>> %s\n" % (data['default-lease'], dhcp_conf)
      except:
        pass
      s += "echo '  option subnet-mask %s;'>> %s\n" % (ifobj.ip.getMask(), dhcp_conf)
      s += "echo '  option broadcast-address %s;'>> %s\n" % (ifobj.getBroadcast(), dhcp_conf)
      try:
        s += "echo '  option routers %s;'>> %s\n" % (data['gateway'], dhcp_conf)
      except:
        pass
      s += "echo '}' >> %s\n" % dhcp_conf
    if s:
      s = 'echo -n > %s\n%s' % (dhcp_conf, s)
      s += 'touch /var/lib/dhcp/dhcpd.leases\n'
      s += 'chown dhcpd:dhcpd /var/lib/dhcp/dhcpd.leases\n'
      s += '/usr/sbin/dhcpd -q -4 -pf /run/dhcp-server/dhcpd.pid -cf /etc/dhcp/dhcpd.conf %s\n' % ' '.join(ifaces)
      #s += '/etc/init.d/isc-dhcp-server start\n' 
    return s

  def __createScript__(self, script):
    f = open(script, 'w')
    f.write(self.__genScript__())
    f.write('echo COMPLETE > /proc/mconsole\n')
    f.close()
    os.chmod(script, 0o700)

  def start(self, path):
    self.start2({'path':path})

  def start2(self, prefs):
    path = prefs['path']
    try:
        mem = self.data['mem']
    except:
        mem = prefs['mem']
    vm = uml_layer.VM(self.name, mem=mem, lab=path)
    for iface in self.ifaces:
      iface.toVM(vm)
    for iface in self.ifaces:
      iface.start()
    #print ('prefs=%s' % prefs)
    if prefs['rw']:
      vm.set_args(rw=1)
    return vm

NetkitGeneric = NetkitObject

class NetkitGateway(NetkitObject):

  Kind = 'gateway'
  Attr = NetkitObject.Attr + ['nat', 'radvd']
  Radvd_Attrs = {'min_interval': 3,  'max_interval': 10, 'rdnss': None, 
                 'stateful':False, 'stateless':True}

  def __init__(self, name, data):
    NetkitObject.__init__(self, name, data)
    self.nat_iface = ''
    self.radvd = {}

  def setAttribute(self, attr, data):
    if attr == 'nat':
      self.nat_iface = data
    elif attr == 'radvd':
        ifname = data['default_item']
        try:
            iface = self.getIface(ifname)
        except:
            raise ValueError('unknown interface %s' % ifname)            
        d = {}
        d.update(self.Radvd_Attrs)
        d.update(data)
        self.radvd[ifname] = d
        
    else:
      NetkitObject.setAttribute(self, attr, data)

  def __genScript__(self):
    s = NetkitObject.__genScript__(self)
    radvd = False
    radvd_conf = '/etc/radvd.conf'
    s += appendToScript(radvd_conf)
    for ifname in self.radvd:
        data = self.radvd[ifname]
        try:
            iface = self.getIface(ifname)
        except:
            print('Erro: interface %s desconhecida ao configurar radvd em %s' % (ifname,  self.name))
            continue
        try:
            ipv6 = iface.getIPv6()
        except:
            print('Erro: interface %s em %s nao tem endereco IPv6 ao ativar radvd' % (ifname,  self.name))
            continue
        radvd = True
        s += appendToScript(radvd_conf, 'interface %s {'% ifname)
        s += appendToScript(radvd_conf, '  AdvSendAdvert on;')
        s += appendToScript(radvd_conf, '  MinRtrAdvInterval %d;' % data['min_interval'])
        s += appendToScript(radvd_conf, '  MaxRtrAdvInterval %d;' % data['max_interval'])
        if data['stateful']:
            s += appendToScript(radvd_conf, '  AdvManagedFlag on;')
        else:
            s += appendToScript(radvd_conf, '  prefix %s/%d {' % (ipv6.getPrefix(),  ipv6.getMask()))
            s += appendToScript(radvd_conf, '  AdvOnLink on;')
            s += appendToScript(radvd_conf, '  AdvAutonomous on')
            s += appendToScript(radvd_conf, '  };')
        if data['rdnss']:
            s += appendToScript(radvd_conf, '  RDNSS %s {};' % data['rdnss'].getCompactIp())
        s += appendToScript(radvd_conf, '};')
    s += 'sysctl -w net.ipv4.ip_forward=1\n'
    s += 'sysctl -w net.ipv6.conf.all.forwarding=1\n'
    if radvd:
      s += '/etc/init.d/radvd start\n'
    if self.nat_iface:
      s += 'iptables -t nat -A POSTROUTING -o %s -j MASQUERADE\n' % self.nat_iface
    return s

  def __condCopy__(self,  src,  target):
      try:
          os.stat(target)
      except:
          cmd = 'cp -ar %s %s' % (src,  target)
          os.system(cmd)

class NetkitPBX(NetkitGateway):

  Kind = 'pbx'
  Memory = 64
  
  def __init__(self, name, data):
      NetkitGateway.__init__(self, name, data)
      try:
        if self.data['mem'] < self.Memory:
          self.data['mem'] = self.Memory
      except:
        self.data['mem'] = self.Memory
  
  def start2(self, prefs):
      #self.__condCopy__('"%s"/contrib/asterisk.tar.gz' % os.environ['NETKIT2_HOME'],  '"%s"/shared/asterisk.tar.gz' % prefs['path'])
      #self.__condCopy__('"%s"/contrib/libtinfo.tar.gz' % os.environ['NETKIT2_HOME'],  '"%s"/shared/libtinfo.tar.gz' % prefs['path'])
      #self.__condCopy__('"%s"/contrib/nc.tar.gz' % os.environ['NETKIT2_HOME'],  '"%s"/shared/nc.tar.gz' % prefs['path'])
      return NetkitGateway.start2(self,  prefs)
      
  def __genScript__(self):
     s = NetkitGateway.__genScript__(self)
     #r = 'tar xCzf /usr/local /hostlab/shared/asterisk.tar.gz\n'
     #r += 'tar xCzf / /hostlab/shared/libtinfo.tar.gz\n'
     #r += 'tar xCzf / /hostlab/shared/nc.tar.gz\n'
     #r += 'rm -f /etc/asterisk; ln -s /usr/local/asterisk/etc/asterisk /etc/asterisk\n'
     r = 'echo "export PATH+=:/usr/local/asterisk/sbin" >> /etc/profile\n'
     pos = s.find('#PRESERVE')
     if pos < 0:
       s += r
     else:
       s = s[:pos] + r + s[pos:]
     return s
     
class NetkitPPPoE(NetkitGateway):

  Kind = 'pppoe'
  PPPoE_Opts = 'require-chap noauth login lcp-echo-interval 10 lcp-echo-failure 2 ms-dns 200.135.37.65 netmask 255.255.255.0 noipdefault debug kdebug 4'
  Attr = NetkitGateway.Attr + ['pppoe']

  def setAttribute(self, attr, data):
    if attr == 'pppoe':
      self.data.update(data)
      #print (self.data)
    else:
      NetkitGateway.setAttribute(self, attr, data)
  
  def __genUsers__(self):
    if not 'users' in self.data:
      return ''
    s = 'echo -n > /etc/ppp/chap-secrets\n'
    for user,password in self.data['users']:
      s += 'echo %s \* %s >> /etc/ppp/chap-secrets\n' % (user,password)
    return s

  def __genRate__(self):
     if not 'rate' in self.data: return ''
     s = 'cp /hostlab/shared/templates/rate-limit /etc/ppp/ip-up.d\n'
     s += 'echo %d > /etc/default/rate-limit\n' % self.data['rate']
     return s


  def __genScript__(self):
    s = NetkitGateway.__genScript__(self)
    try:
      ip1,ip2 = self.data['range']
      s += self.__genUsers__()
      s += self.__genRate__()
      s += 'echo %s-%s > /etc/ppp/faixa-ip\n' % (ip1, ip2)
      s += 'echo %s > /etc/ppp/pppoe-server-options\n' % self.PPPoE_Opts
      s += 'ebtables -A INPUT -i %s -p 0x0800 -j DROP\n' % self.data['interface'] 
      s += 'ebtables -A FORWARD -i %s -p 0x0800 -j DROP\n' % self.data['interface'] 
      s += 'pppoe-server -C %s -L %s -p /etc/ppp/faixa-ip -I %s\n' % (self.data['pppoe_ac'], self.data['ip'], self.data['interface'])
    except KeyError:
      pass
    return s
    
class NetkitMpls(NetkitPPPoE):

  Kind = 'mpls'
  Attr = NetkitPPPoE.Attr + ['fec','ilm','labelspace','nhlfe']

  def __init__(self, name, data):
    NetkitPPPoE.__init__(self, name, data)
    self.ilm = []
    self.nhlfe = {}
    self.fec = {}
    self.labelspace = {}

  def setAttribute(self, attr, data):
    NetkitPPPoE.setAttribute(self, attr, data)
    print (data)
    if attr == 'ilm':
      if not 'label' in data:
        raise ValueError('Missing label number when configuring ILM on MPLS router %s' % self.name)
      self.ilm.append(data)
    elif attr == 'fec':
      try:
         self.fec[data['fec']] = data
      except Exception as e:
         raise ValueError('Error when configuring FEC on MPLS router %s: %s' % (self.name, repr(e)))
    elif attr == 'nhlfe':
      try:
         self.nhlfe[data['nhlfe']] = data
      except:
         raise ValueError('Missing NHLFE key when configuring MPLS router %s' % self.name)
    elif attr == 'labelspace':
      try:
         self.labelspace[data['labelspace']] = data['interfaces']
      except:
         raise ValueError('Error when configuring labelspace on MPLS router %s' % self.name)

  def __getNhlfe__(self, nhlfe_id, label=None):
    nhlfe = self.nhlfe[nhlfe_id]
    # se nao informou label de entrada (ilm), entao deve ser
    # nhlfe interna de tunel
    if label == None:
      s = 'push %d ' % nhlfe['label']
    elif label != nhlfe['label']:
      # soh faz swap se label de saida for diferente ...
      s = 'swap %d ' % nhlfe['label']
    else: 
      s= ''
    try:
      # se for tunel, gera a proxima nhlfe
      s += self.__getNhlfe__(nhlfe['nhlfe_fwd'])
    except KeyError:
      s += 'dev %s %s' % (nhlfe['interface'], nhlfe['ip'])
      #s += '%s' % nhlfe['ip']
    return s

  def __genNhlfe__(self, nhlfe_id, label):
    try:
      cmd = 'ip -M route add %d mpls %s' % (label, self.__getNhlfe__(nhlfe_id, label))
      return self.__addCommand__(cmd, self.__getNhlfeInterface__(nhlfe_id))
    except KeyError:
      print('Ops: unknown NHLFE %d when setting ILM for label %d on Mpls %s: ignoring ...' % (nhlfe_id, label, self.name))

  def __getNhlfeInterface__(self, nhlfe_id):
    l = [nhlfe_id]
    while True:
      nhlfe = self.nhlfe[nhlfe_id]
      try:
        return nhlfe['interface']
      except KeyError:
        pass
      nhlfe_id = nhlfe['nhlfe']
      if nhlfe_id in l: break
      l.append(nhlfe_id)
    return None

  def __addCommand__(self, cmd, iface):
    out_if = self.getIface(iface)
    if isinstance(out_if, NetkitPPPInterface):
      return out_if.addCommand(cmd)
    else:
      return '%s\n' % cmd           

  def __labelspaceHasEthif__(self, labelspace):
    for iface in self.labelspace[labelspace]:
      iface = self.getIface(iface)
      if isinstance(iface, NetkitEthInterface): return True
    return False

  def __getLabelspacePPPif__(self, labelspace):
    for ifname in self.labelspace[labelspace]:
      iface = self.getIface(ifname)
      if isinstance(iface, NetkitPPPInterface): return ifname
    return None

  def __genIlm__(self):
    s = '# ILM\n'
    for attrs in self.ilm:
      # ignora labelspace, porque no momento ha apenas labelspace global
      label = attrs['label']
      try:
        nhlfe_id = attrs['nhlfe']
        s += self.__genNhlfe__(nhlfe_id, label)
      except KeyError:
        labelspace = attrs['labelspace']
        ilm = 'ip -M route add %d mpls pop 1' % label
        if self.__labelspaceHasEthif__(labelspace): 
          s += '%s\n' % ilm
        else: 
          s += self.__addCommand__(ilm, self.__getLabelspacePPPif__(labelspace))
    s += '\n'
    return s

  def __genLabelspace__(self):
    s = '# Labelspace\n'
    for key in self.labelspace:
      attrs = self.labelspace[key]
      # por enquanto ha apenas labelspace global ...      
      for iface in attrs:
        #s += 'mpls labelspace set dev %s labelspace %d\n' % (iface, key)
        labelspace = 'ip link set %s mpls on' % iface
        s += self.__addCommand__(labelspace, iface)
    s += '\n'
    return s

  def __getNhlfeIp__(self, key):
    try:
      return self.nhlfe[key]['ip']
    except:
      #print (key, self.nhlfe[key])
      key = self.nhlfe[key]['nhlfe']
      return self.__getNhlfeIp__(key)

  def __genFec__(self):
    s = '# FEC\n'
    for key in self.fec:
      attrs = self.fec[key]
      #nhlfe = self.nhlfe[attrs['nhlfe']]['default_item']
      nhlfe = attrs['nhlfe']
      fec = 'ip route add %s mpls %s' % (key, self.__getNhlfe__(nhlfe))
      s += self.__addCommand__(fec, self.__getNhlfeInterface__(nhlfe))
    s += '\n'
    return s

  def __genScript__(self):
    s = NetkitPPPoE.__genScript__(self)
    #s += 'echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter\n'
    s += 'ifconfig mpls0 up\n'
    s += self.__genLabelspace__()
    #s += self.__genNhlfe__()
    s += self.__genIlm__()
    s += self.__genFec__()
    return s

class NetkitRouter(NetkitMpls):

  Kind = 'router'
  Attr = NetkitMpls.Attr + ['router']

  def __genScript__(self):
    s = NetkitMpls.__genScript__(self)
    try:
      expr = ''
      for proto in self.data['protos']:
        expr += ' -e s/%sd=no/%sd=yes/ ' % (proto, proto)
      if expr:
        s += 'sed %s /etc/quagga/daemons.template > /etc/quagga/daemons\n' % expr
    except KeyError:
      pass
    s += '/etc/init.d/quagga start\n'
    if not 'services' in self.data:
      s += 'cp -a /etc/init.d/services /etc/rc0.d/S80services\n'
    s += 'echo /etc/init.d/quagga stop >> /etc/rc0.d/S80services\n'    
    s += 'echo export VTYSH_PAGER=more >> /root/.bashrc\n'
    s += 'grep vtysh /root/.bashrc || (echo /usr/local/bin/vtysh >> /root/.bashrc;'
    s += 'echo echo >> /root/.bashrc; echo echo Se quiser voltar ao menu do roteador, execute vtysh >> /root/.bashrc)\n'
    #s += 'echo /usr/bin/vtysh >> /root/.bashrc\n'
    #s += 'usermod -s /usr/bin/vtysh root\n'
    return s

  def setAttribute(self, attr, data):
    if attr == 'router':
      self.data.update(data)
      #print (self.data)
    else:
      NetkitMpls.setAttribute(self, attr, data)

class NetkitSwitch(NetkitObject):

  Kind = 'switch'
  StpAttrs = {'bridge_priority': 4000,'ageing_time': 5,'forward_delay': 1, 'hello_time':2, 'max_age':10,
              'vlan': 1, 'on': 0}
  ConfigHostapdPath = '/etc/hostapd'
  ConfigHostapd = '%s/hostapd.conf' % ConfigHostapdPath
  HostapdUsers = '%s/hostapd.eap_user' % ConfigHostapdPath
  RadiusClients = '%s/hostapd.radius_clients' % ConfigHostapdPath
  RadiusSecret = 'ifsc2011'
  Attr = NetkitObject.Attr + ['stp','8021x','management_ip']
  
  def setAttribute(self, attr, data):
    #print (attr, data)
    if attr == 'stp':
      if not 'stp' in self.data:        
        self.data['stp'] = {}
        vlans = self.getVlans()
        if not vlans: vlans = [1]
        for vlan in vlans:
          self.data['stp'][vlan] = {}
          self.data['stp'][vlan].update(self.StpAttrs)
      # se ha somente uma vlan, define-a como default
      attrs = {}
      if len(self.data['stp']) == 1:
        attrs['vlan'] = list(self.data['stp'].keys())[0]      
      #data = map(lambda x: x.strip().split('='), data.split(':'))
      else: 
        attrs['vlan'] = 1
      for item in data:        
        #item = map(lambda x: x.strip(), item)
        if not item in self.StpAttrs:
          raise ValueError('Unknown attribute "%s" when configuring stp on %s' % (item, self.name))
      attrs.update(data)
      if not 'vlan' in attrs:
        raise ValueError('Missing vlan when configuring stp on %s' % self.name)
      data = {attrs['vlan']: attrs}
      self.data['stp'].update(data)
    elif attr == '8021x':
        self.data['8021x'] = {}
        self.data['8021x'].update(data)
    elif attr == 'management_ip':
        self.data['management_ip'] = {}
        try:
          self.data['management_ip']['ip'] = IP(data['ip'])
        except:
          raise ValueError("switch %s: invalid management IP" % self.name)
        try:
          self.data['management_ip']['vlan'] = data['vlan']
        except:
          raise ValueError("switch %s: must specify vlan number for management IP !" % self.name)
    else:
      NetkitObject.setAttribute(self, attr, data)

  def getVlans(self):
    vlans = {}
    for iface in self.ifaces:
      for vlan in iface.getVlans():
         vlans[vlan] = 0
    return vlans

  def enabled8021x(self,  vlan=0):
    #print (self.data['8021x'])
    try:
        if self.data['8021x']['enabled']:
            try:
              if len(self.data['8021x']['radius_clients']) > 0: return True
            except:
              pass
            for iface in self.ifaces:
                #print (iface.ifName(), iface.isAuthenticator())
                if iface.isAuthenticator() and (not vlan or vlan in iface.getVlans()): return True
        return False
    except Exception as e:
        return False

  def __genScript__(self):
    s = NetkitObject.__genScript__(self)
    vlans = self.getVlans()
    gen8021x_users = False
    #print ('8021X:',  self.enabled8021x())
    if self.enabled8021x():
        s += 'ebtables -A FORWARD -p 0x888e -j DROP\n'
        for iface in self.ifaces:
            if not iface.isAuthenticator():
                s += 'ebtables -A INPUT -i %s -p 0x888e -j DROP\n' % iface.ifName()
                s += 'ebtables -A INPUT -i %s -j ACCEPT\n' % iface.ifName()
                s += 'ebtables -A FORWARD -i %s -j ACCEPT\n' % iface.ifName()
    for vlan in vlans:
      s += 'brctl addbr vlan%d\n' % vlan
      for iface in self.ifaces:
        vif = iface.vlanIface(vlan)
        if vif:
          s += 'brctl addif vlan%d %s\n' % (vlan, vif)
      s += 'ifconfig vlan%d up\n' % vlan
      # 8021.x stuff
      if self.enabled8021x(vlan):
         #s += 'mkdir -p %s\n' % self.ConfigHostapdPath
         #s += 'cp /hostlab/shared/templates/hostapd.* %s\n' % self.ConfigHostapdPath
         #s += 'cp /hostlab/shared/templates/{hostapd,hostapd_*} /usr/local/bin/\n'
         # substituir os parametros: IFACE, NAS_IDENTIFIER, MANAGEMENT_IP, RADIUS_IP, RADIUS_SECRET
         if 'radius_server' in self.data['8021x']:
             hapd_config = '%s.radius' % self.ConfigHostapd
             ip = self.data['management_ip']['ip']
             s += r'sed -r -e s/IFACE/vlan%d/ -e s/NAS_IDENTIFIER/vlan%d/ -e s/RADIUS_IP/%s/ -e s/RADIUS_SECRET/%s/ -e s/MANAGEMENT_IP/%s/ -e "s/^(eap_user_file)/\#\1/" %s > %s-vlan%d'   % \
                      (vlan,  vlan,  self.data['8021x']['radius_server'], self.RadiusSecret,  ip.getIp(),  hapd_config,  self.ConfigHostapd,  vlan)
             s += '\n'
         else:
            try:
              mgt_vlan = self.data['management_ip']['vlan']
            except:
              mgt_vlan = 0
            if vlan == mgt_vlan:
                s += 'sed -e s/IFACE/vlan%d/ -e s/RADIUS_OK// %s > %s-vlan%d\n'   % (vlan,  self.ConfigHostapd,  self.ConfigHostapd,  vlan)
                s += 'rm -f %s\n' % self.RadiusClients
                try:
                  for client in self.data['8021x']['radius_clients']:
                      s += 'echo %s\t%s >> %s\n' % (client,  self.RadiusSecret,  self.RadiusClients)
                except:
                  pass
                s += 'echo 0.0.0.0/0\tdjknj@klmsc0jm >> %s\n' % self.RadiusClients
            else:
                s += 'sed -e s/IFACE/vlan%d/ -e s/RADIUS_OK/\#/ %s > %s-vlan%d\n'   % (vlan,  self.ConfigHostapd,  self.ConfigHostapd,  vlan)                
            if not gen8021x_users:
              s += 'cp %s.template %s\n' % (self.HostapdUsers,  self.HostapdUsers)
              for user, password in self.data['8021x']['users']:
                s += 'sed -r s/\'#"user(.*)password\'/\'"%s\\1%s"\\n&\'/ %s > /tmp/hostapd.conf\n' % (user, password, self.HostapdUsers)
                s += 'mv /tmp/hostapd.conf %s\n' % self.HostapdUsers
              gen8021x_users = True
         s += '/usr/local/bin/hostapd -B %s-vlan%d\n' % (self.ConfigHostapd,  vlan)
    # STP stuff
    try:
      stp = self.data['stp']
      #print (stp)
      for vlan in stp:
        for attr in stp[vlan]:
          data = stp[vlan][attr]
          if attr == 'bridge_priority':
            s += 'brctl setbridgeprio vlan%d %d\n' % (vlan, data)
          elif attr == 'ageing_time':
            s += 'brctl setageing vlan%d %d\n' % (vlan, data)
          elif attr == 'hello_time':
            s += 'brctl sethello vlan%d %d\n' % (vlan, data)
          elif attr == 'max_age':
            s += 'brctl setmaxage vlan%d %d\n' % (vlan, data)
          elif attr == 'forward_delay':
            s += 'brctl setfd vlan%d %d\n' % (vlan, data)
        if stp[vlan]['on']:
          s += 'brctl stp vlan%d on\n' % vlan
        else:
          s += 'brctl stp vlan%d off\n' % vlan
        for iface in self.ifaces:
          #print ('...', iface.vlanIface(vlan))
          if vlan in iface.getVlans():
            cost = iface.getStpCost()            
            if cost > 0:
              s += 'brctl setpathcost vlan%d %s %d\n' % (vlan, iface.vlanIface(vlan), cost)
            prio = iface.getStpPrio()
            if prio > 0:
              s += 'brctl setportprio vlan%d %s %d\n' % (vlan, iface.vlanIface(vlan), prio)
    except Exception as e:
      #print ('ops', e)
      pass
    # Management IP
    try:
        data = self.data['management_ip']
        ipmask = data['ip']
        ip = ipmask.getIp()
        mask = ipmask.getMask()
        try:
            vlan = data['vlan']
        except:
            vlan = 1
        s += 'ifconfig vlan%d %s netmask %s\n' % (vlan,  ip,  mask)
        try:
            s += 'route add default gw %s\n' % data['default_gateway']
        except:
            pass
    except:
        print('... no configured management IP on switch %s' % self.name)
        pass
    return s

#####################################################################################
class NetkitObjectFactory:

  Templates = {NetkitObject.Kind: NetkitObject, NetkitSwitch.Kind: NetkitSwitch, 
               NetkitGateway.Kind: NetkitGateway, NetkitRouter.Kind: NetkitRouter,
               NetkitPPPoE.Kind: NetkitPPPoE, NetkitMpls.Kind: NetkitMpls,  NetkitPBX.Kind:NetkitPBX}
  
  def getNetkitObject(self, name, data):
    attrs = self.__parse__(data)
    #print (attrs)
    try:
      template = self.Templates[attrs['type']]
      obj = template(name, attrs)
      return obj
    except Exception as e:
      print (e)
      return None

  def __parse__(self, data):
    attrs = {}
    if type(data) == type({}):
      attrs.update(data)
      return attrs
    for item in data.split(':'):
      item = item.strip()
      item = [x.lower() for x in item.split('=')]
      if len(item) > 1:
        item, data = item
        attrs[item] = data
      else:
        attrs['type'] = item[0]
    return attrs

class NetkitInterfaceFactory:

  Ifs = [NetkitUplinkInterface, NetkitPPPoEInterface, NetkitEthInterface,
         NetkitPPPInterface, NetkitBondingInterface]
  ExprIface = re.compile('(?P<prefix>[a-zA-Z]+)(?P<num>[0-9]+)')

  def getNetkitInterface(self, name, data):
     m = self.ExprIface.match(name)
     if m:
       m = m.groupdict()     
       prefix = m['prefix']
       num = int(m['num'])
       for IfaceClass in self.Ifs:
         if prefix == IfaceClass.Prefix:
           #print (name, IfaceClass.Prefix,IfaceClass.__name__)
           try:
              iface = IfaceClass(num, data)
              #print ('ok:', name, IfaceClass.__name__)
              return iface
           except Exception as e:              
              #traceback.print_exc(file=sys.stdout)
              #print (e)
              pass
     raise ValueError
#####################################################################################
import tempfile

class Network:

  Serialemu = 'serialemu -B %d -a %d -b %.9f'
  exprLink = re.compile('ttyS[0-9]+')
  Globals = {'mem':32, 'rw': False}

  def __init__(self, objs, prefs=None, serialemu=Serialemu):
    self.objs = objs
    self.serialemu=serialemu
    self.vms = {}
    self.vs = {}
    self.pool = None
    self.globals = {}
    self.globals.update(self.Globals)
    if prefs:
        for k in prefs:
            #prefs[k] = self.globals[k]
            self.globals[k] = prefs[k]
    if not 'path' in self.globals:
        try:
            prefix = 'lab-%s-' % self.globals['name']
        except KeyError:
            prefix = 'lab-'            
        self.globals['path'] = tempfile.mkdtemp('', prefix, '.')
        os.rmdir(self.globals['path'])
        print('path:', self.globals['path'])
    #print (self.objs.values()[1])

  def get_pool(self):
     return self.pool

  @property    
  def path(self):
    return self.globals['path']
    
  @property    
  def prefs(self):
    d = {}
    d.update(self.globals)
    return d

  def get_nodes(self):
        return list(self.objs.keys())
      
  def set_rw(self,  rw=False):
      self.globals['rw'] = rw
      
  def update_prefs(self, prefs):
    for k in list(prefs.keys()):
      #if not k in ['path','rw']:
      if not k in ['rw']:
        self.globals[k] = prefs[k]
    return

  def get_prefs(self):
    return self.globals
          
  def __repr__(self):
    s = ''
    for obj in list(self.objs.values()):
      s += '%s\n' % obj
    return s

  def createNetwork(self):
    try:
      os.makedirs(self.globals['path'])
    except:
      pass
    try:
      os.mkdir('%s/shared' % self.globals['path'])
    except:
      pass
    open('%s/lab.dep' % self.globals['path'],'w')
    #f = open('%s/lab.conf' % self.path,'w')
    #f.write(repr(self))
    #f.close()
    for obj in list(self.objs.values()):
      obj.createStartup(self.globals['path'])

  def __getSerialLinks__(self):
    links = {}
    for obj in list(self.objs.values()):
       ifaces = obj.getIfaces(NetkitPPPInterface)
       for iface in ifaces:
         if self.exprLink.match(iface.link): continue
         try:
           links[iface.link].append(iface)
         except:
           links[iface.link] = [iface]
    for link in links:
      if len(links[link]) != 2:
        raise ValueError('Link "%s" must apear exactly twice !' % link)
    return links

  def __getSerialUplinks__(self):
    links = {}
    for obj in list(self.objs.values()):
       ifaces = obj.getIfaces(NetkitPPPInterface)
       for iface in ifaces:
         if self.exprLink.match(iface.link):
           if iface.link in links:
             raise ValueError('Serial "%s" can be used only once !' % iface.link)
           else:
             links[iface.link] = iface
    res = []
    for link in links:
      res.append((links[link], '/dev/%s' % link))
    return res

  def __getEthLinks__(self):
    links = {}
    for obj in list(self.objs.values()):
       ifaces = obj.getIfaces(NetkitEthInterface)
       for iface in ifaces:
         if iface.link == 'uplink': continue
         try:
           links[iface.link].append(iface)
         except:
           links[iface.link] = [iface]
    return links
    
  def __getUplinks__(self):
    links = []
    for obj in list(self.objs.values()):
       ifaces = obj.getIfaces(NetkitUplinkInterface)
       for iface in ifaces:
         links.append(iface)
    return links

  def get_pty(self, rate, ber, delay):
    try:
      p = os.popen(self.serialemu % (rate, delay, ber))
      l = p.readline()
      p.close()
      l = l.strip()
      return l.split()
    except:
      return None  

  def __startNetwork__(self):
    # iniciar os links seriais por portas seriais fisicas ...
    links = self.__getSerialUplinks__()
    for iface,serial in links:
      # configura o pty da interface 
      iface.setPty(serial)
    # iniciar os links seriais por portas seriais emuladas ...
    links = self.__getSerialLinks__()
    for link in links:
      if1, if2 = links[link]
      p = self.get_pty(if1.speed, if1.ber, if1.delay)
      if1.setPty(p[0])
      if2.setPty(p[1])
    # criar os links ethernet
    links = self.__getEthLinks__()    
    #print ('links:', links)
    # ... criar os uml_switch
    for link in links:     
      ifaces = links[link]
      vs=uml_layer.VSwitch(link)
      vs.start()
      self.vs[link] = vs
      for iface in ifaces:
        iface.setVLink(vs.getLink())
    # cria o diretorio de trabalho e os scripts de boot das vms
    self.createNetwork()
    os.system('cp -ar "%s"/contrib/templates "%s"/shared/' % (os.environ['NETKIT2_HOME'],  self.globals['path']))
    #os.chdir(self.globals['path'])

  def start(self, pool=None):
    if self.globals['rw']:
      if len(self.objs) > 1:
        raise ValueError('Only one VM allowed in read-write disk mode !')      
    self.__startNetwork__()
    # removida a opcao de compactar dentro da VM
    #if not term.prefs['compact']:
    #    os.system('mv "%s"/shared/templates/K95preserve.no-compact "%s"/shared/templates/K95preserve' % (term.prefs['path'],  term.prefs['path']))

    # Executa as VMs se nao foi passado um TermPool
    # Nesse caso, usa o TermPool default disponivel em uml_layer.
    # Tal TermPool executa cada VM em um xterm.
    # No caso do gnome-netkit, um objeto NetkitTerminal funciona como TermPool
    do_start = not pool
    if do_start:
        self.pool = uml_layer.TermPool()
    else:
        self.pool = pool  
    lmaq = list(self.objs.keys())
    lmaq.sort()
    for maq in lmaq:
      obj = self.objs[maq]
      # cria uma uml_layer.VM
      vm = obj.start2(self.globals)
      try:
        vm.set_args(net=self.globals['name'])
      except:
        pass
      self.vms[vm.get_name()] = vm
      self.pool.addVM(vm)
    if do_start:
      self.pool.start()
    return self.pool

  def stop(self):
    pids = []
    vpids = []
    for vm in self.vms:
      pid = self.vms[vm].stop()
      if pid > 0: pids.append(pid)
    for vs in list(self.vs.values()):
      pid = vs.stop()
      if pid > 0: vpids.append(pid)
    os.system('killall -9 serialemu > /dev/null 2>&1')
    print(pids,vpids)
    for pid in vpids:
      try:
        os.waitpid(pid, 0)
      except:
        pass
    for vm in self.vms:
      self.vms[vm].stop_uplinks()

    print('... confirmando a morte das vms:', pids)
    time.sleep(2)
    for vm in self.vms:
      self.vms[vm].kill()
      self.vms[vm].wait()
      print('...morreu', vm)
    self.vms = {}
    self.vs = {}
    self.pool.stop()


#####################################################################################
class NetkitGrapher:

  Expr = re.compile('(?P<vm>[-A-Za-z0-9_]+).*pos="(?P<x>[0-9.]+),(?P<y>[0-9.]+)"')
  Exprw = re.compile('width="?(?P<width>[0-9.]+)"?')
  Exprh = re.compile('height="?(?P<height>[0-9.]+)"?')

  def __init__(self, network):
    self.net = network
    self.img_path = '%s/contrib' % os.environ['NETKIT2_HOME']
    self.dot = None

  def __links__(self):
    l = []
    lnodes = list(self.net.objs.values())
    i = 0
    nuvem = 0
    hubs = []
    links = {}
    while i < len(lnodes):
      node = lnodes[i]
      ifaces = node.getIfaces()
      uplink = [x for x in ifaces if x.link == 'uplink']
      if uplink:
        ifaces = [x for x in ifaces if x.link != 'uplink']
        for sif in uplink:
          l.append((node.name.replace('-','_'),sif.ifName(),'nuvem',''))
        nuvem = 1
      node_name = node.name.replace('-','_')
      for sif in ifaces:
        #try:
        #  ip = IP(sif.ip)
        #  data = (node_name, '%s:%s' % (sif.ifName(), ip))
        #except Exception as e:
        #  data = (node_name, sif.ifName())
        data = (node_name, sif.ifName())
        #print (data)
        try:
          links[sif.link].append(data)
        except:
          links[sif.link] = [data]
      i += 1    
    for link in links:
      data = links[link]
      if len(data) == 2:
        l.append((data[0][0], data[0][1], data[1][0], data[1][1]))
      elif len(data) > 2:
        for node, iface in data:
          l.append((node, iface, link, ''))
        hubs.append(link)        
    return (l, nuvem, hubs)

  def __normalize__(self, r):
    l=[]
    s = ''
    for lin in r:
      if lin.find('[') >= 0:
        s = lin.strip()
      if lin.find(']') >= 0:
        l.append(s+lin)
        s = ''
      elif len(s) > 0:
        s += lin.strip()
      else:
        l.append(lin)
    return l

  def get_coords(self):
    if not self.dot: self.gen_dot()
    open('/tmp/.xxx.dot', 'w').write(self.dot)
    p = os.popen('neato /tmp/.xxx.dot')
    r = self.__normalize__(p.readlines())
    p.close()    
    #print (r)
    lr = []
    for l in r:
      m = self.Expr.search(l)
      #print (l, m)
      if m:
        d = m.groupdict()
        d.update(self.Exprw.search(l).groupdict())
        d.update(self.Exprh.search(l).groupdict())
        lr.append(d)
    #print (lr)
    for d in lr:
      x = float(d['x'])
      y = float(d['y'])
      width = float(d['width'])
      height = float(d['height'])
      vm = d['vm']
      #print (vm, x, y, width, height)
      try:
        self.net.objs[vm].setAttribute('x', x)
        self.net.objs[vm].setAttribute('y', y)
        self.net.objs[vm].setAttribute('width', width)
        self.net.objs[vm].setAttribute('height', height)
      except KeyError as e:
        #print (vm, e)
        continue
       

  def gen_image(self, path):
    if not self.dot: self.gen_dot()
    open('%s.dot' % path,'w').write(self.dot)
    os.system('neato -Tpng %s.dot > %s' % (path, path))  
    
  def gen_dot(self):
    r = 'graph rede {\n'
    for obj in list(self.net.objs.values()):
      name = obj.name.replace('-','_')
      if obj.Kind == 'switch':
        loc='c'
      else:
        loc='b'
      r += '%s [shape=none, image="%s/%s.png", fontsize=11, labelloc=%s];\n' % (name, self.img_path, obj.Kind,loc)
    links, nuvem, hubs = self.__links__()
    #print (links, nuvem, hubs)
    if nuvem:
      r += 'nuvem [shape=none, image="%s/nuvem.png"];\n' % self.img_path
    for hub in hubs:
      r += '%s [shape=none, image="%s/hub.png"];\n' % (hub, self.img_path)
    for link in links:
      r += '%s -- %s [len=1.5,labelangle=90,labelfontsize=10,taillabel="%s",headlabel="%s"];\n' % (link[0],link[2],link[1],link[3])
    r += '}\n'
    self.dot = r
    return r

#####################################################################################
# Para desenhar a rede virtual (de acordo com as VLANs)
# - cada vlan ser composta por um switch (ou mais ?)
# - em interfaces tagged, a cada uma corresponde uma interface

#class NetkitVirtualGrapher:

#  def __links__(self):
#####################################################################################
def check_workdir(path):
  ls = os.listdir(path)
  if not ('shared' in ls and 'lab.dep' in ls):
    t = time.localtime()
    temp = 'tmp-%d-%02d%02d%02d' % (os.getpid(), t.tm_hour, t.tm_min, t.tm_sec)
    path = os.path.join(path, temp)
  return os.path.abspath(path)
  
