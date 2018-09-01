#!/usr/bin/python

import traceback

import ply.lex as lex
import ply.yacc as yacc

import netkit


class SemanticError(Exception):

  def __init__(self, lineno, value, line=''):
    self.value = value
    self.n = lineno
    self.line = line

  def __str__(self):
      return 'Semantic error: %s' % self.value

class ParseError (Exception):

  def __init__(self, lineno, column, value, line=''):
    self.column = column
    self.value = value
    self.line = line
    self.n = lineno

  def __str__(self):
    if self.column < 0:
      return 'Parse error: %s' % self.value
    else:
      return 'Parse error at column %d: %s' % (self.column, self.value)

class NetkitParser:

  start = 'statement'
  t_ignore = ' \t'
  precedence = ()
  literals = ''

  t_COLON  = r':'
  t_EQUALS  = r'='
  t_LBRACK  = r'\['
  t_RBRACK  = r'\]'
  t_VIRG    = r','
  t_FLOATNUMBER = r'[0-9]*\.[0-9]+'
  t_LPAR = r'\('
  t_RPAR = r'\)'
  #t_NODE = r'[a-zA-Z_.0-9][-a-zA-Z_. 0-9]*'

  reserved = {'ip': 'IPATTR', 'dhcp': 'DHCP', 'generic': 'GENERIC',
              'type': 'TYPE', 'gateway': 'GATEWAY', 'route': 'ROUTE',
              'default_gateway': 'DEFAULTGW', 'uplink':'UPLINK', 'default':'DEFAULT','default6':'DEFAULT6',
              'dev': 'DEV', 'interfaces':'INTERFACES', 'services':'SERVICES',
              'rate':'RATE', 'preserve':'PRESERVE', 'ber':'BER', 'delay':'DELAY', 
              'vlan_untagged':'UNTAGGED', 'vlan_tagged':'TAGGED', 
              'vlans_tagged':'TAGGEDS', 'bridge':'BRIDGE',
              'range': 'RANGE', 'default-lease':'DEFLEASE', 'max-lease':'MAXLEASE',
              'switch':'SWITCH', 'router':'ROUTER', 'pppoe':'PPPOE', 'mpls':'MPLS',
              'pbx':'PBX', 'nat':'NAT', 'bridge_priority':'BRPRIO', 'stp':'STP',
              'on': 'ON', 'off':'OFF', 'stp_cost':'STPCOST', 'stp_prio':'STPPRIO',
              'max_age':'BRAGE', 'hello_time':'BRHELLO', 'forward_delay':'BRDELAY',
              'users':'USERS', 'interface':'INTERFACE', 'pppoe_ac':'PPPOEAC',
              'pppoe_user':'PPPOEUSER', 'pppoe_password':'PPPOEPASSWD',
              'mode':'MODE','pppoe':'PPPOE','user':'USER','password':'PASSWORD',
              'label':'LABEL', 'fec':'FEC', 'labelspace':'LABELSPACE',
              'ilm':'ILM', 'nhlfe':'NHLFE', 'netmask':'NETMASK', 'global':'GLOBAL',
              'path':'PATH', 'mem':'MEM', 'rw':'RW', 'clean':'CLEAN','vm':'VM',
              'clean':'CLEAN','compact':'COMPACT', 'ipv6':'IPV6ATTR', 'ieee8021x':'IEEE8021X',
              'radius_clients':'RADIUS_CLIENTS', 'radius_server':'RADIUS_SERVER',
              'ieee8021x_auth': 'IEEE8021X_AUTH', 'ieee8021x_user': 'IEEE8021X_USER',
              'management_ip':'MGMT_IP', 'vlan':'VLAN','port':'PORT', 'name':'NAME',
              'debug':'DEBUG', 'rip':'RIP', 'ripng':'RIPNG', 'ospf':'OSPF', 
              'ospf6':'OSPF6', 'bgp':'BGP', 'isis':'ISIS',  'radvd': 'RADVD',  'min_interval': 'MIN_INTERVAL', 
              'max_interval':'MAX_INTERVAL', 'round-robin':'RR',  'tlb': 'TLB',  'alb':'ALB', 
              'backup':'BACKUP', 'xor':'XOR',  'miimon': 'MIIMON',  'lacp_rate': 'LACP_RATE', 
              'slow':'SLOW',  'fast':'FAST', 'rdnss':'RDNSS', 'noipv6':'NOIPV6',
              'stateless':'STATELESS', 'stateful':'STATEFUL', 'down':'DOWN'}

  tokens = (
    'COLON','LBRACK', 'RBRACK','EQUALS','IP','IPMASK','NUMBER', 'VIRG',
    'ETHIF', 'PPPIF', 'BONDIF', 'LPAR','RPAR','FLOATNUMBER', 
    'COMMENT','BOOL','IPV6','IPV6MASK','ID','PATHNAME',
    'USERPAIR',  '8023AD')


  def __init__(self, conf):
    self.tokens += tuple(self.reserved.values())
    self.vms = {}
    self.prefs = {}
    self.lineno = 1
    self.line = ''
    self.vmFactory = netkit.NetkitObjectFactory()
    self.ifFactory = netkit.NetkitInterfaceFactory()
    self.conf = conf
    self.__built = False

  def build(self, **args):
    self.lex = lex.lex(module=self, **args)
    self.yacc = yacc.yacc(module=self)
    self.__built = True

  def get_network(self):
    network = netkit.Network(self.vms, self.prefs)
    network.update_prefs(self.prefs)
    return network


  def get_reserved(self, token):
    it = iter(self.reserved.items())
    while True:
      try:
        key,val = next(it)
        if val == token: return key
      except StopIteration:
        return None

  def t_COMMENT(self, t):
    r'\#.*'
    pass

  def t_newline(self, t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")
    
  def t_error(self, t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

  def parse(self):
    if not self.__built: self.build()
    f=open(self.conf)
    self.lineno = 0
    while 1:
      self.line = f.readline()
      if not self.line: break
      self.line = self.line.strip()
      self.lineno += 1
      if not self.line: continue
      #print p.tokenize(x)
      r = self.yacc.parse(self.line, lexer=self.lex)
      #print 'resultado:', r
    f.close()
    return True

  def update_prefs(self, prefs):
    # modificar o constructor, que recebe um file object representando esse arquivo.
    # mas agora precisa grava-lo ... ou o file object deve ter sido aberto em modo 
    # leitura e escrita, ou deve-se passar o PATHNAME para poder ser aberto exclusivamente
    # para atualizacao. Acho melhor a 1a opcao ...
    f = open(self.conf,'r+')
    f.seek(0)
    novo = ['# Global attributes: these values are obtained automatically from menu General->Preferences']
    for k in list(prefs.keys()):
      novo.append('global[%s]=%s' % (k, prefs[k]))
    for l in f.readlines():
      l = l.strip()
      if l.find('global[') < 0 and l.find('# Global') < 0:
        novo.append(l)
    novo = [x + '\n' for x in novo]
    f.truncate()
    f.seek(0)
    f.writelines(novo)
    f.flush()
    f.close()

  def p_error(self,p):
    if not p:
      raise ParseError(self.lineno, 0, "Unknown or incomplete declaration", self.line)
    raise ParseError(self.lineno, p.lexpos, p.value, self.line)

  def tokenize(self, x=''):
    lexer = lex.lex(module=self)
    lexer.input(x)
    #print self.tokens, tokens, t_ID
    r = []
    while True:
      tok = lexer.token()
      if not tok: break
      r.append(tok)
    return r

  def get_vm(self, name):
    try:
      vm = self.vms[name]
    except KeyError:
      raise SemanticError(self.lineno, 'vm "%s" does not exist !' % name, self.line)
    return vm

  def t_BOOL(self, t):
    r'[Tt][Rr][Uu][Ee]|[Ff][Aa][Ll][Ss][Ee]'
    t.value = eval(t.value)
    return t

  def t_ETHIF(self, t):
    r'eth[0-9]+'
    return t

  def t_PPPIF(self, t):
    r'ppp[0-9]+'
    return t

  def t_BONDIF(self, t):
    r'bond[0-9]+'
    return t

  def t_IPMASK(self, t):
    r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}'
    try:
      t.value = netkit.IP(t.value)
    except ValueError as e:
      raise ParseError(self.lineno, t.lexpos, e, self.line)
    return t

  def t_IPV6MASK(self, t):
    r'(([0-9a-fA-F]{1,4}:)+(:[0-9a-fA-F]{1,4})+|(([0-9a-fA-F]{1,4}:)+):|([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|:((:[0-9a-fA-F]{1,4})+)|(::))/[0-9]{1,3}'
    try:
      t.value = netkit.IPv6(t.value)
    except ValueError as e:
      raise ParseError(self.lineno, t.lexpos, e, self.line)
    return t

  def t_IPV6(self, t):
    r'([0-9a-fA-F]{1,4}:)+(:[0-9a-fA-F]{1,4})+|(([0-9a-fA-F]{1,4}:)+):|([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|:((:[0-9a-fA-F]{1,4})+)'
    try:
      t.value = netkit.IPv6(t.value)
    except ValueError as e:
      raise ParseError(self.lineno, t.lexpos, e, self.line)
    return t

  def t_IP(self, t):
    r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
    try:
      t.value = netkit.IP(t.value)
    except ValueError as e:
      raise ParseError(self.lineno, t.lexpos, e, self.line)
    return t

  def t_8023AD(self,  t):
      r'8023.?[aAdD]'
      return t

  def t_NUMBER(self, t):
    r'\d+'
    t.value = int(t.value)
    return t

  def t_PATHNAME(self, t):
    r'(/[-_a-zA-Z.+0-9]+)+/?'
    return t

  def t_USERPAIR(self, t):
    r'[-_a-zA-Z0-9]+/[-_a-zA-Z0-9]+'
    t.value = tuple(t.value.split('/'))
    return t

  def t_ID(self, t):
    r'[a-zA-Z_]([a-zA-Z_0-9.]+-)?[a-zA-Z_0-9.]*'
    #r'[a-zA-Z_][-a-zA-Z_0-9]*'
    t.type = self.reserved.get(t.value,'ID')    # Check for reserved words
    return t

  def p_statement_comment(self, p):
    '''statement : COMMENT
             | '''
    p[0] = None
    return p[0]

  def p_statement_vmif(self, p):
    'statement : vmif'
    p[0] = p[1]
    return p[0]

  def p_statement_vmdef(self, p):
    'statement : vmdef'
    p[0] = p[1]
    return p[0]

  def p_statement_vmroute(self, p):
    'statement : vmroute'
    p[0] = p[1]
    return p[0]

  def p_statement_vmdefgw(self, p):
    'statement : vmdefgw'
    p[0] = p[1]
    return p[0]

  def p_statement_vmservices(self, p):
    'statement : vmservices'
    p[0] = p[1]
    return p[0]

  def p_statement_vmpreserve(self, p):
    'statement : vmpreserve'
    p[0] = p[1]
    return p[0]

  def p_statement_vmmem(self, p):
    'statement : vmmem'
    p[0] = p[1]
    return p[0]

  def p_statement_vmdhcp(self, p):
    'statement : vmdhcp'
    p[0] = p[1]
    return p[0]

  def p_statement_vmnat(self, p):
    'statement : vmnat'
    p[0] = p[1]
    return p[0]

  def p_statement_vmstp(self, p):
    'statement : vmstp'
    p[0] = p[1]
    return p[0]

  def p_statement_vmradvd(self,  p):
      'statement : vmradvd'
      p[0] = p[1]
      return p[0]
      
  def p_statement_vmpppoe(self, p):
    'statement : vmpppoe'
    p[0] = p[1]
    return p[0]

  def p_statement_vmfec(self, p):
    'statement : vmfec'
    p[0] = p[1]
    return p[0]

  def p_statement_vmilm(self, p):
    'statement : vmilm'
    p[0] = p[1]
    return p[0]

  def p_statement_vmnhlfe(self, p):
    'statement : vmnhlfe'
    p[0] = p[1]
    return p[0]

  def p_statement_vmlabelspace(self, p):
    'statement : vmlabelspace'
    p[0] = p[1]
    return p[0]

  def p_statement_prefs(self, p):
    'statement : prefs'
    p[0] = p[1]
    return p[0]
    
  def p_statement_8021x(self, p):
    'statement : vm8021x'
    p[0] = p[1]
    return p[0]

  def p_statement_mgmtip(self, p):
    'statement : vmmgmtip'
    p[0] = p[1]
    return p[0]

  def p_statement_vmrouter(self, p):
    'statement : vmrouter'
    p[0] = p[1]
    return p[0]

  def p_vmradvd_decl(self,  p):
      r'vmradvd : ID LBRACK RADVD RBRACK EQUALS radvdexpr'
      vm = self.get_vm(p[1])
      if not isinstance(vm,  netkit.NetkitGateway):
          raise SemanticError(self.lineno,  '%s must be a gateway !' % p[1],  self.line)
      try:
          vm.setAttribute(p[3],  p[6])
      except ValueError as e:
          raise SemanticError(self.lineno, e, self.line)

  def p_radvdexpr_decl1(self,  p):
      r'''radvdexpr : ETHIF
                             | ETHIF COLON radvdattrs'''
      p[0] = {'default_item': p[1]}
      try:
          p[0].update(p[3])
      except:
          pass

  def p_radvdattrs_decl(self,  p):
      r'radvdattrs : radvdpair'
      p[0] = p[1]

  def p_radvdattrs_decl2(self, p):
    'radvdattrs : radvdpair COLON radvdattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_radvdattrs_decl3(self, p):
    'radvdattrs : radvdsingle COLON radvdattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_radvdattrs_decl4(self, p):
    'radvdattrs : radvdsingle'
    p[0] = p[1]

  def p_radvdsingle_decl1(self, p):
    '''radvdsingle : STATELESS
                   | STATEFUL'''
    p[0] = {p[1]:True}

  def p_radvdpair_decl1(self,  p):
      r'''radvdpair : MIN_INTERVAL EQUALS NUMBER
                        | MAX_INTERVAL EQUALS NUMBER
                        | RDNSS EQUALS IPV6'''
      p[0] = {p[1]: p[3]}
      
  def p_vmrouter_decl(self, p):
    r'vmrouter : ID LBRACK ROUTER RBRACK EQUALS rtlist'
    p[0] = {'protos': p[6]}
    vm = self.get_vm(p[1])
    if vm.Kind != p[3]: 
      raise SemanticError(self.lineno, '%s must be a router !' % p[1], self.line)
    try:
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)
  
  def p_rtlist_decl1(self, p):
    r'rtlist : rtproto VIRG rtlist'
    p[0] = p[3]
    p[0].append(p[1])

  def p_rtlist_decl2(self, p):
    r'rtlist : rtproto'
    p[0] = [p[1]]

  def p_rtproto_decl(self, p):
    r'''rtproto : RIP
              | RIPNG
              | OSPF
              | BGP
              | OSPF6
              | ISIS'''
    p[0] = p[1]

  def p_prefs_decl(self, p):
    '''prefs : GLOBAL LBRACK PATH RBRACK EQUALS PATHNAME
             | GLOBAL LBRACK MEM RBRACK EQUALS NUMBER
             | GLOBAL LBRACK VM RBRACK EQUALS NUMBER
             | GLOBAL LBRACK CLEAN RBRACK EQUALS BOOL
             | GLOBAL LBRACK COMPACT RBRACK EQUALS BOOL
             | GLOBAL LBRACK PRESERVE RBRACK EQUALS BOOL
             | GLOBAL LBRACK RW RBRACK EQUALS BOOL
             | GLOBAL LBRACK NAME RBRACK EQUALS ID'''
    d = {p[3]: p[6]}
    self.prefs.update(d)
    return d

  def p_vmmgmtip_decl(self, p):
    r'vmmgmtip : ID LBRACK MGMT_IP RBRACK EQUALS IPMASK COLON VLAN EQUALS NUMBER'
    vm = self.get_vm(p[1])
    d = {'ip': p[6]}
    d[p[8]] = p[10]
    try:
      vm.setAttribute(p[3], d)
    except ValueError as e :
      raise SemanticError(self.lineno, e, self.line)

  def p_vm8021x_decl(self, p):
    r'vm8021x : ID LBRACK IEEE8021X RBRACK EQUALS ON COLON expr8021x'
    vm = self.get_vm(p[1])
    data = p[8]
    data['enabled']=True
    try:
      vm.setAttribute('8021x',data)
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.lineno)

  def p_expr8021x_decl(self, p):
    r'''expr8021x : expr8021xsv
                | expr8021xcl'''
    p[0] = p[1]

  def p_expr8021xcl_decl(self, p):
    r'expr8021xcl : RADIUS_SERVER EQUALS IP'
    p[0] = {p[1]: p[3]}

  def p_expr8021xsv_decl1(self, p):
    r'expr8021xsv : attr8021x COLON expr8021xsv'
    p[0] = p[3]
    p[0].update(p[1])

  def p_expr8021xsv_decl2(self, p):
    r'expr8021xsv : attr8021x'
    p[0] = p[1]

  def p_attr8021x_decl(self, p):
    r'''attr8021x : USERS EQUALS userlist
                  | RADIUS_CLIENTS EQUALS ipaddrlist
                  | PORT EQUALS NUMBER'''
    p[0] = {p[1]: p[3]}

  def p_ipaddrlist_decl1(self, p):
    r'ipaddrlist : IP VIRG ipaddrlist'
    p[0] = p[3]
    p[0].append(p[1])

  def p_ipaddrlist_decl2(self, p):
    r'ipaddrlist : IP'
    p[0] = [p[1]]

  def p_vmdef_decl(self, p):
    'vmdef : ID LBRACK TYPE RBRACK EQUALS types'
    if p[1] in self.vms:
      raise SemanticError(self.lineno, 'vm "%s" already declared !' % p[1], self.line)
    vm = self.vmFactory.getNetkitObject(p[1], p[6])
    p[0] = vm
    self.vms[p[1]] = vm 

  def p_types_decl(self, p):
    '''types : GENERIC
           | GATEWAY
           | ROUTER
           | SWITCH
           | PPPOE
           | MPLS
           | PBX'''
    p[0] = {'type': p[1]}

  def p_vmroute_decl(self, p):
    r'''vmroute : ID LBRACK ROUTE RBRACK EQUALS IPMASK COLON gwspec
                | ID LBRACK ROUTE RBRACK EQUALS IPV6MASK COLON gwspecng
                | ID LBRACK ROUTE RBRACK EQUALS DEFAULT COLON gwspec
                | ID LBRACK ROUTE RBRACK EQUALS DEFAULT6 COLON gwspecng'''
    vm = self.get_vm(p[1])
    p[0] = {'default_item': p[6]}
    p[0].update(p[8])
    try:
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      print(traceback.format_exc())
      raise SemanticError(self.lineno, e, self.line)

#  def p_routedest_decl(self, p):
#    'routedest : IPMASK'
#    p[0] = {'default_item': p[1]}
#
#  def p_routedestng_decl(self, p):
#    'routedestng : IPV6MASK'
#    p[0] = {'default_item': p[1]}

  def p_gwspec_gw(self, p):
    '''gwspec : GATEWAY EQUALS IP
              | DEV EQUALS PPPIF'''
    p[0] = {p[1]: p[3]}

  def p_gwspecng_gw(self, p):
    '''gwspecng : GATEWAY EQUALS IPV6
              | DEV EQUALS PPPIF'''
    p[0] = {p[1]: p[3]}

  def p_vmdefgw_decl(self, p):
    'vmdefgw : ID LBRACK DEFAULTGW RBRACK EQUALS gwdef'
    vm = self.get_vm(p[1])
    if isinstance(p[6], netkit.IPv6):
      p[0] = {'default_item': netkit.IPv6('::/0'), 'gateway': p[6]}
    else:
      p[0] = {'default_item': netkit.IP('0.0.0.0/0'), 'gateway': p[6]}
    try:
      vm.setAttribute('route', p[0])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_gwdef_decl(self, p):
    '''gwdef : IP
             | IPV6'''
    p[0] = p[1]

  def p_vmmem_decl(self, p):
    'vmmem : ID LBRACK MEM RBRACK EQUALS NUMBER'
    vm = self.get_vm(p[1])
    p[0] = {'default_item': p[6]}
    try:
      vm.setAttribute(p[3], p[6])
    except ValueError as e:
      raise SemanticError(e)

  def p_vmservices_decl(self, p):
    'vmservices : ID LBRACK SERVICES RBRACK EQUALS servlist'
    vm = self.get_vm(p[1])
    p[0] = {'default_item': p[6]}
    try:
      vm.setAttribute(p[3], p[6])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_servlist_decl1(self, p):
    'servlist : servid VIRG servlist'
    p[0] = [p[1]] + p[3]

  def p_servlist_decl2(self, p):
    'servlist : servid'
    p[0] = [p[1]]

  def p_serviceid_decl(self,  p):
      '''servid : ID
                      | RADVD'''
      p[0] = p[1]

  def p_vmpreserve_decl(self, p):
    'vmpreserve : ID LBRACK PRESERVE RBRACK EQUALS pathlist'
    vm = self.get_vm(p[1])
    p[0] = {'default_item': p[6]}
    try:
      vm.setAttribute(p[3], p[6])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)
 
  def p_pathlist_decl1(self, p):
    'pathlist : PATHNAME COLON pathlist'
    p[0] = [p[1]]
    p[0] += p[3]

  def p_pathlist_decl2(self, p):
    'pathlist : PATHNAME'
    p[0] = [p[1]]

  #def p_PATHNAME_decl1(self, p):
  #  r'''PATHNAME : PATHSEP NODE PATHNAME
  #               | PATHSEP ID PATHNAME'''
  #  p[0] = '/%s%s' % (p[2], p[3])

  #def p_PATHNAME_decl2(self, p):
  #  '''PATHNAME : PATHSEP NODE
  #              | PATHSEP ID'''
  #  p[0] = '/%s' % p[2]

  def p_vmdhcp_decl(self, p):
    'vmdhcp : ID LBRACK DHCP RBRACK EQUALS dhcpexpr'
    vm = self.get_vm(p[1])
    p[0] = p[6]
    try:
      #print p[3],  p[0]
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_dhcpexpr_decl(self, p):
    'dhcpexpr : ETHIF COLON dhcpattrs'
    p[0] = {'default_item': p[1]}
    p[0].update(p[3])

  def p_dhcpattrs_decl1(self, p):
    'dhcpattrs : dhcppair COLON dhcpattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_dhcpattrs_decl2(self, p):
    'dhcpattrs : dhcppair'
    p[0] = p[1]

  def p_dhcppair_decl1(self, p):
    'dhcppair : RANGE EQUALS IP VIRG IP'
    p[0] = {p[1]: (p[3], p[5])}

  def p_dhcppair_decl2(self, p):
    '''dhcppair : DEFLEASE EQUALS NUMBER
              | MAXLEASE EQUALS NUMBER
              | GATEWAY EQUALS IP
              | NETMASK EQUALS IP'''
    p[0] = {p[1]: p[3]}

  def p_vmif_eth(self, p):
    'vmif : ID LBRACK ETHIF RBRACK EQUALS ethexpr'
    vm = self.get_vm(p[1])
    p[0] = p[6]
    #print p[3], p[6]
    iface = self.ifFactory.getNetkitInterface(p[3], p[6])
    try:
      vm.addInterface(iface)
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_ethexpr_decl1(self, p):
    'ethexpr : UPLINK COLON uplinkattrs'
    p[0] = {'link': p[1]}
    p[0].update(p[3])

  def p_ethexpr_decl2(self, p):
    'ethexpr : ID COLON ethattrs'
    p[0] = {'link': p[1]}
    p[0].update(p[3])

  def p_ethexpr_decl3(self, p):
    'ethexpr : ID'
    p[0] = {'link': p[1]}

  def p_ethattrs_decl1(self, p):
    'ethattrs : ethpair COLON ethattrs'
    p[0] = p[3]
    p[0].update(p[1])

  def p_ethattrs_decl2(self, p):
    'ethattrs : ethpair'
    p[0] = p[1]

  def p_ethpair_decl1(self, p):
    '''ethpair : IPATTR EQUALS iplist
               | IPATTR EQUALS DHCP'''
    p[0] = {p[1]: p[3]}

  def p_ethpair_decl2(self, p):
    'ethpair : RATE EQUALS NUMBER'
    p[0] = {p[1]: p[3]}

  def p_ethpair_decl3(self, p):
    'ethpair : UNTAGGED EQUALS NUMBER'
    p[0] = {p[1]: p[3]}

  def p_ethpair_decl4(self, p):
    'ethpair : tagged EQUALS taglist'
    p[0] = {p[1]: p[3]}

  def p_ethpair_decl5(self, p):
    r'ethpair : IPV6ATTR EQUALS ipv6list'
    p[0] = {p[1]: p[3]}

  def p_ethpair_decl50(self, p):
    r'ethpair : NOIPV6'
    p[0] = {p[1]: True}

  def p_ethpair_decl51(self, p):
    r'ethpair : DOWN'
    p[0] = {p[1]: True}

  def p_ipv6list_decl1(self, p):
    r'ipv6list : IPV6MASK VIRG ipv6list'
    p[0] = p[3]
    p[0].append(p[1])

  def p_ipv6list_decl2(self, p):
    r'ipv6list : IPV6MASK'
    p[0] = [p[1]]

  def p_ethpair_decl6(self, p):
    r'ethpair : IEEE8021X_AUTH EQUALS NUMBER'
    p[0] = {'8021x_authenticator': p[3]}

  def p_ethpair_decl9(self, p):
    r'ethpair : IEEE8021X_USER EQUALS USERPAIR'
    p[0] = {'8021x_user': p[3]}

  def p_iplist_decl1(self, p):
    'iplist : IPMASK VIRG iplist'
    p[0] = [p[1]]
    p[0] += p[3]

  def p_iplist_decl2(self, p):
    'iplist : IPMASK'
    p[0] = [p[1]]
     
  def p_tagged_decl(self, p):
    '''tagged : TAGGED
              | TAGGEDS'''
    p[0] = 'vlans_tagged'

  def p_ethpair_decl7(self, p):
    '''ethpair : STPCOST EQUALS NUMBER
               | STPPRIO EQUALS NUMBER'''
    p[0] = {p[1]: p[3]}

  def p_ethpair_decl8(self, p):
    '''ethpair : PPPOEAC EQUALS ID
               | PPPOEUSER EQUALS ID
               | PPPOEPASSWD EQUALS ID
               | MODE EQUALS PPPOE'''
    p[0] = {p[1]: p[3]}

  def p_taglist_decl1(self, p):
    'taglist : NUMBER VIRG taglist'
    p[0] = [(p[1], None)]
    p[0] += p[3]

  def p_taglist_decl2(self, p):
    'taglist : NUMBER'
    p[0] = [(p[1], None)]

  def p_taglist_decl3(self, p):
    'taglist : tagpair VIRG taglist'
    p[0] = [p[1]]
    p[0] += p[3]

  def p_taglist_decl4(self, p):
    'taglist : tagpair'
    p[0] = [p[1]]

  def p_tagpair_decl1(self, p):
    'tagpair : LPAR NUMBER VIRG iplist RPAR'
    p[0] = (p[2], p[4])

  def p_tagpair_decl2(self, p):
    'tagpair : LPAR NUMBER VIRG IPATTR EQUALS iplist RPAR'
    p[0] = (p[2], p[6])

  def p_tagpair_decl3(self, p):
    'tagpair : LPAR NUMBER VIRG ipv6list RPAR'
    p[0] = (p[2], p[4])

  def p_tagpair_decl4(self, p):
    'tagpair : LPAR NUMBER VIRG IPV6ATTR EQUALS ipv6list RPAR'
    p[0] = (p[2], p[6])

  def p_uplinkattrs_decl1(self, p):
    'uplinkattrs : ethattrs'
    p[0] = p[1]

  def p_uplinkattrs_decl2(self, p):
    'uplinkattrs : uplinkpair COLON ethattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_uplinkattrs_decl3(self, p):
    'uplinkattrs : uplinkpair'
    p[0] = p[1]

  def p_uplinpair_decl1(self, p):
    'uplinkpair : BRIDGE EQUALS ETHIF'
    p[0] = {p[1]: p[3]}

  def p_vmif_ppp(self, p):
    'vmif : ID LBRACK PPPIF RBRACK EQUALS pppexpr'
    vm = self.get_vm(p[1])
    p[0] = p[6]
    iface = self.ifFactory.getNetkitInterface(p[3], p[6])
    if isinstance(iface, netkit.NetkitPPPoEInterface):
      hname = iface.getHostInterface()
      try:
        hostif = vm.getIface(hname)
        hostif.addSubinterface(iface)
      except:
        raise SemanticError(self.lineno, '%s is subinterface of %s, but %s does not exit !' % (p[3],hname, hname), self.line)
    else:
      try:
        vm.addInterface(iface)
      except ValueError as e:
        raise SemanticError(self.lineno,e,self.line)

  def p_pppexpr_decl1(self, p):
    'pppexpr : ID COLON pppattrs'
    p[0] = {'link': p[1]}
    p[0].update(p[3])
     
  def p_pppexpr_decl2(self, p):
    'pppexpr : ID'
    p[0] = {'link': p[1]}

  def p_pppattrs_decl1(self, p):
    'pppattrs : ppppair COLON pppattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_pppattrs_decl2(self, p):
    'pppattrs : ppppair'
    p[0] = p[1]

  def p_ppppair_decl1(self, p):
    r'''ppppair : IPATTR EQUALS IPMASK
                | IPV6ATTR EQUALS IPV6MASK'''
    p[0] = {p[1]: [p[3]]}

  def p_ppppair_decl2(self, p):
    '''ppppair : RATE EQUALS NUMBER
               | BER EQUALS FLOATNUMBER
               | DELAY EQUALS NUMBER'''
    p[0] = {p[1]: p[3]}

  def p_ppppair_decl3(self, p):
    '''ppppair : INTERFACE EQUALS ETHIF
               | USER EQUALS ID
               | PASSWORD EQUALS ID
               | TYPE EQUALS PPPOE'''
    p[0] = {p[1]:p[3]}

  def p_ppppair_decl4(self, p):
    '''ppppair : DEBUG
               | DEBUG EQUALS BOOL'''
    try:
      p[0] = {p[1]: p[3]}
    except:
      p[0] = {p[1]: True}

  def p_vmif_bond(self, p):
    'vmif : ID LBRACK BONDIF RBRACK EQUALS bondexpr'
    vm = self.get_vm(p[1])
    p[0] = p[6]
    iface = self.ifFactory.getNetkitInterface(p[3], p[6])
    try:
      vm.addInterface(iface)
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_bondexpr_decl1(self, p):
    'bondexpr : ID COLON bondattrs'
    p[0] = {'link': p[1]}
    p[0].update(p[3])

  def p_bondexpr_decl2(self, p):
    'bondexpr : ID'
    p[0] = {'link': p[1]}

  def p_bondattrs_decl1(self, p):
    'bondattrs : bondpair COLON bondattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_bondattrs_decl2(self, p):
    'bondattrs : bondpair'
    p[0] = p[1]

  def p_bondpair_decl1(self, p):
    '''bondpair : IPATTR EQUALS iplist
                 | IPV6ATTR EQUALS ipv6list
                 | IPATTR EQUALS DHCP
                 | MODE EQUALS bondmode
                 | LACP_RATE EQUALS SLOW
                 | LACP_RATE EQUALS FAST
                 | RATE EQUALS NUMBER
                 | MIIMON EQUALS NUMBER'''
    p[0] = {p[1]: p[3]}

  def p_bondmode_decl(self,  p):
     '''bondmode : RR
                            | 8023AD
                            | BACKUP
                            | XOR
                            | TLB
                            | ALB'''
     p[0] = p[1]

  def p_bondpair_decl2(self, p):
    'bondpair : INTERFACES EQUALS iflist'
    p[0] = {p[1]: p[3]}

  def p_iflist_decl1(self, p):
    'iflist : ETHIF VIRG iflist'
    p[0] = [p[1]]
    p[0] += p[3]

  def p_iflist_decl2(self, p):
    'iflist : ETHIF'
    p[0] = [p[1]]

  def p_vmnat_decl(self, p):
    'vmnat : ID LBRACK NAT RBRACK EQUALS interface'
    vm = self.get_vm(p[1])    
    p[0] = {'default_item': p[6]}
    try:
      vm.setAttribute(p[3], p[6])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.lineno)

  def p_interface_decl(self, p):
    r'''interface : ETHIF
                | PPPIF
                | BONDIF'''
    p[0] = p[1]

  def p_vmstp_decl(self, p):
    'vmstp : ID LBRACK STP RBRACK EQUALS stpexpr'
    vm = self.get_vm(p[1])
    try:
      vm.setAttribute(p[3], p[6])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)
    p[0] = p[6]

  def p_vmstpexpr_decl1(self, p):
    'stpexpr : ON COLON stpattrs'
    p[0] = {'on': True}
    p[0].update(p[3])

  def p_vmstpexpr_decl2(self, p):
    'stpexpr : ON'
    p[0] = {'on': True}

  def p_vmstpexpr_decl3(self, p):
    'stpexpr : OFF'
    p[0] = {'on': False}

  def p_vmstpattrs_decl1(self, p):
    'stpattrs : stppair COLON stpattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_vmstpattrs_decl2(self, p):
    'stpattrs : stppair'
    p[0] = p[1]

  def p_vmstppair_decl1(self, p):
    '''stppair : BRPRIO EQUALS NUMBER
             | BRHELLO EQUALS NUMBER
             | BRAGE EQUALS NUMBER
             | BRDELAY EQUALS NUMBER
             | VLAN EQUALS NUMBER'''
    p[0] = {p[1]: p[3]}

  def p_vmpppoe_decl(self, p):
    'vmpppoe : ID LBRACK PPPOE RBRACK EQUALS ID COLON pppoeattrs'
    vm = self.get_vm(p[1])
    p[0] = {'pppoe_ac': p[6]}
    p[0].update(p[8])
    try:
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_pppoeattrs_decl1(self, p):
    'pppoeattrs : pppoepair COLON pppoeattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_pppoeattrs_decl2(self, p):
    'pppoeattrs : pppoepair'
    p[0] = p[1]

  def p_pppoepair_decl1(self, p):
    'pppoepair : RANGE EQUALS IP VIRG IP'
    p[0] = {p[1]: (p[3], p[5])}

  def p_pppoepair_decl2(self, p):
    'pppoepair : IPATTR EQUALS IP'
    p[0] = {p[1]: p[3]}

  def p_pppoepair_decl3(self, p):
    'pppoepair : INTERFACE EQUALS ETHIF'
    p[0] = {p[1]: p[3]}
    
  def p_pppoepair_decl4(self, p):
    'pppoepair : USERS EQUALS userlist'
    p[0] = {p[1]: p[3]}

  def p_pppoepair_decl5(self, p):
    'pppoepair : RATE EQUALS NUMBER'
    p[0] = {p[1]: p[3]}

  def p_userlist_decl1(self, p):
    'userlist : USERPAIR VIRG userlist'
    p[0] = p[3]
    p[0] += [p[1]]

  def p_userlist_decl3(self, p):
    'userlist : USERPAIR'
    p[0] = [p[1]]

  #def p_userpair_decl(self, p):
  #  'userpair : ID PATHSEP ID'
  #  p[0] = (p[1], p[3])

  def p_vmfec_decl(self, p):
    'vmfec : ID LBRACK FEC RBRACK EQUALS IPMASK COLON NHLFE EQUALS NUMBER'
    vm = self.get_vm(p[1])
    p[0] = {'fec': p[6], p[8]: p[10]}
    try:
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_vmnhlfe_decl(self, p):
    'vmnhlfe : ID LBRACK NHLFE RBRACK EQUALS NUMBER COLON nhlfeattrs'
    vm = self.get_vm(p[1])
    p[0] = {'nhlfe': p[6]}
    p[0].update(p[8])
    try:
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      raise SemanticError(self.lineno, e, self.line)

  def p_nhlfeattrs_decl1(self, p):
    'nhlfeattrs : nhlfepair COLON nhlfeattrs'
    p[0] = p[1]
    p[0].update(p[3])

  def p_nhlfeattrs_decl2(self, p):
    'nhlfeattrs : nhlfepair'
    p[0] = p[1]

  def p_nhlfepair_decl1(self, p):
    '''nhlfepair : INTERFACE EQUALS ETHIF
                 | INTERFACE EQUALS PPPIF'''
    p[0] = {p[1]: p[3]}

  def p_nhlfepair_decl2(self, p):
    'nhlfepair : LABEL EQUALS NUMBER'
    p[0] = {p[1]: p[3]}

  def p_nhlfepair_decl3(self, p):
    'nhlfepair : IPATTR EQUALS IP'
    p[0] = {p[1]: p[3]}

  def p_nhlfepair_decl4(self, p):
    'nhlfepair : NHLFE EQUALS NUMBER'
    p[0] = {'nhlfe_fwd': p[3]}

  def p_vmilm_decl1(self, p):
    'vmilm : ID LBRACK ILM RBRACK EQUALS NUMBER COLON ilmattrs'
    vm = self.get_vm(p[1])
    p[0] = {'label': p[6]}
    p[0].update(p[8])
    try:
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      raise SemanticError(self.lineno,e, self.line)

  #def p_vmilm_decl2(self, p):
  #  'vmilm : ID LBRACK ILM RBRACK EQUALS NUMBER'
  #  vm = self.get_vm(p[1])
  #  p[0] = {'label': p[6]}
  #  try:
  #    vm.setAttribute(p[3], p[0])
  #  except ValueError as e:
  #    raise SemanticError(self.lineno,e, self.line)

  def p_ilmattrs_decl1(self, p):
    'ilmattrs : ilmpair COLON ilmpair'
    p[0] = p[1]
    p[0].update(p[3])

  def p_ilmattrs_decl2(self, p):
    'ilmattrs : ilmpair'
    p[0] = p[1]

  def p_ilmpair_decl1(self, p):
    '''ilmpair : LABELSPACE EQUALS NUMBER
             | NHLFE EQUALS NUMBER'''
    p[0] = {p[1]: p[3]}

  def p_vmlabelspace_decl(self, p):
    'vmlabelspace : ID LBRACK LABELSPACE RBRACK EQUALS NUMBER COLON INTERFACES EQUALS anyiflist'
    vm = self.get_vm(p[1])
    p[0] = {'labelspace':p[6], p[8]: p[10]}
    try:
      vm.setAttribute(p[3], p[0])
    except ValueError as e:
      raise SemanticError(self.lineno,e, self.line)

  def p_anyiflist_decl1(self, p):
    r'''anyiflist : ETHIF VIRG anyiflist
                  | PPPIF VIRG anyiflist'''
    p[0] = p[3]
    p[0].append(p[1])

  def p_anyiflist_decl2(self, p):
    r'''anyiflist : ETHIF
                  | PPPIF'''
    p[0] = [p[1]]

