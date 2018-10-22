# NkZMQ2 - Laboratorio Virtual de Redes - vNet 

## Introdução
  O emulador de redes Netkit2 apresenta-se como um ambiente para experimentos com redes de computadores, para torna-lo mais acessível, este projeto propõe estendê-lo para que seja executado em um servidor de aplicação, ou mesmo em nuvem, sendo acessado através de uma interface web. Nesse modelo, chamado de vNet, estudantes podem criar, executar e investigar suas redes, que podem ficar ativas e operantes pelo tempo que for necessário. O novo serviço possui também um catálogo de experimentos e a possibilidade de interligar redes de diversos experimentos. O vNet assim facilitaria a experimentação com redes de computadores e a criação de aulas práticas em cursos de redes em modalidade EaD.

## Netkit2 
  Netkit2 é um ambiente para experimentos com redes de computadores desenvolvido pela Área de Telecomunicações do IFSC (Câmpus São José), e que se inspirou no Netkit[1], uma ferramenta semelhante (mas mais simplificada) desenvolvida pela Universidade de Roma, na Itália.
  Ele se compõe de máquinas virtuais Linux (implementadas com kernel Linux UML – User Mode Linux)[2], que funcionam como roteadores ou computadores, e hubs Ethernet virtuais (UML switch) para interligar as máquinas virtuais. Para todos os efeitos, cada máquina virtual funciona como se fosse um computador real, possuindo uma ou mais interfaces de rede. Com esses recursos é possível criar redes de configurações arbitrárias para estudar protocolos de comunicação e serviços de rede.
  
As principais diferenças entre o Netkit e o Netkit2 são: 
* A definição de tipos de equipamentos a serem usados no experimento, tais como roteadores, switches, e computadores de uso geral: cada máquina virtual pode assim ser especializada para facilitar sua configuração.
  
* A possibilidade de definir diversos parâmetros de configuração de rede (ex: endereços de interfaces, rotas, VLANs, ...) diretamente no arquivo de configuração de um experimento.
  
* A possibilidade de criar enlaces ponto-a-ponto via links seriais virtuais, que podem ter configurados suas taxas de bits, taxas de erro (BER) e atraso de propagação.
  
* Uma interface gráfica para a execução de experimentos. Esse aplicativo concentra as telas de terminal das máquinas virtuais e provê diversas funções auxiliares para ajudar na realização dos experimentos. A figura abaixo mostra um exemplo dessa interface em ação:

![ilustracao](https://wiki.sj.ifsc.edu.br/wiki/images/thumb/3/31/Netkit-vlsm1.png/640px-Netkit-vlsm1.png)

## Estrutura do projeto
O projeto adota uma estrutura Cliente-Servidor, utilizando os sockets providos pela API zeroMQ[3] com os mesmos numa arquitetura dealer-router[4].
Devido a propriedade de multiplexação destes sockets, é necessário apenas um socket para cada cliente. 

Para simplificar a comunicação entre ambos os lados e torna-la mais eficiente, foi necessário desenvolver um protocolo próprio, uma vez que o HTTP demonstrou-se ineficiente para tal, este novo protocolo é demonstrado na figura a seguir:

![protocolo](protocolo.png)

O servidor também responde com status=400 caso haja algum erro e data= Descrição do erro ocorrido. 


> para obter a documentação da classe: **pydoc3 nkmessage**

## Servidor 
No lado do servidor usa-se as classes: 

* TermPool: Um agrupador dos terminais de cada instância, inicia as VMs (Virtual Machine) de cada instância, configurando-as para leitura não bloqueante. 

* Instancia: Representa uma rede em execução, cada objeto instância contém um TermPool, inicia de fato a rede e trata eventos vindos dos terminais do cliente.

* Dispatcher: Gerencia as requisições vindas dos clientes, caso a requisição seja do tipo "data", é executado direto no objeto instância, caso contrário, ele acessa o repositório de redes, possui multiplos objetos instâncias, as identifica de acordo com o endereço do cliente. 

O diagrama a seguir é um breve representação do lado do servidor. 
![diagrama](vNet.png)

> Para obter a documentação da classe: **pydoc3 server2**


## Cliente:
Gerencia as redes de um catalogo (podendo adicionar, remover e atualizar), além de criar e inicializar 
os pseudos terminais. 

* O diagrama a seguir demonstra de forma extremamente simplificada a interação entre ambas partes. 
![diagrama-cliente-servidor](client-server.png)

## Referencias: 
[1] http://wiki.netkit.org/index.php/Main_Page

[2] http://user-mode-linux.sourceforge.net/

[3] http://zeromq.org/

[4] http://zeromq.org/tutorials:dealer-and-router
