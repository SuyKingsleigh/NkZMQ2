import sys
if sys.version_info.major < 3:
  from mydb import Record,MyDB
else:
  from mydb3 import Record,MyDB

class Dados(Record):

  Attrs = Record.init_attrs()
  Attrs['speed']=0
  Attrs['dir']=0
  Attrs['src']=0
  Attrs['timestamp']=0
  Index = ('speed','timestamp')

class Fonte(Record):

  Attrs = Record.init_attrs()
  Attrs['nome']=''
  Attrs['url']=''
  Index = ('nome',)

class Contatos(Record):

  Attrs = Record.init_attrs()
  Attrs['nome']=''
  Attrs['email']=''
  
class WindDB(MyDB):

  Tabelas = (Dados,Fonte, Contatos)
