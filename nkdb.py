import sys
if sys.version_info.major < 3:
  from mydb import Record,MyDB
else:
  from mydb3 import Record,MyDB

class Network(Record):

  Attrs = Record.init_attrs()
  Attrs['name']=''
  Attrs['author']=''
  Attrs['description']=''
  Attrs['preferences']=''
  Attrs['published']=0
  Attrs['value']=''
  Key = 'name'
  Index = ('name','author')

class NetkitDB(MyDB):

  Tabelas = (Network,)
