# NkZMQ2 - Laboratorio Virtual de Redes - vNet 

Este projeto é uma bolsa de pesquisa com o objetivo de executar o software Netkit2 remotamente, para simplificar e ajudar no ensino
de redes. 

### Estrutura do projeto
Dividido em duas partes, cliente (Client2.py) e Servidor (Server2.py), além do repositório de redes. 
Para execução deve-se em uma máquina executar o Servidor e na outra o cliente. 

## Servidor: 
No lado do servidor usa-se, as classes: 
TermPool: Agrupador de terminais. 
Instancia: Representa uma instancia em execução 
Dispatcher: gerencia as instancias 

O diagrama a seguir é um breve representação do lado do servidor. 
![diagrama](vNet.png)

* Para obter a documentação da classe: pydoc3 server2



## Message: 
Protocolo criado para a comunicação entre servidor e cliente, todas as mensagens trocadas entre eles o utilizam. 
Formatos das mensagens recebidas do cliente: (cmd, data)
Formatos das mensagens recebidas do servidor: (status, data) 

* para obter a documentação da classe: pydoc3 nkmessage

## Cliente:
Gerencia as redes de um catalogo (podendo adicionar, remover e atualizar), além de criar e inicializar 
os pseudos terminais. 
