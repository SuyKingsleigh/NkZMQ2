#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 16:51:11 2018
@author: msobral
"""
import os
import pty
import sys
import time
import tty
from threading import Thread

import gi
import zmq

from nkmessage import Message

gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Vte, GLib, Gtk


class Client:

    # inicia o socket de controel
    def __init__(self, ip, port):
        self.context = zmq.Context()
        self.ip = ip
        self.port = port
        self.socketCMD = self.context.socket(zmq.DEALER)
        self.socketCMD.connect("tcp://%s:%d" % (ip, port))
        self._started = False
        self.terminaisDict = dict()
        self.daemonStarted = False
        self.buttonDict = dict()  # key->win, bucket->button

    def start(self, netname):
        '''Inicia uma rede, definida por netname'''
        request = Message(cmd='start', data=netname)
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        self._started = True
        self.terminais = resp.data['terms']

    # verifica se o objeto foi iniciado
    @property
    def started(self):
        return self._started

    @property
    def networks(self):
        '''lista as redes no catalogo'''
        request = Message(cmd='list')
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        return resp.get('networks')

    def get_network(self, name):
        '''obtem informacoes sobre a rede especificada por nome'''
        request = Message(cmd='get', data=name)
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            raise Exception('Erro: %s' % resp.get('info'))
        return resp.get('network')

    # retorna um dicionario [terminal]->dado(str)
    def get_data(self):
        '''Obtem uma mensagem de dados de terminal. Deve ser chamado somente se houver uma mensagem
        pendente no socket. Depende portanto de previamente se usar um poller ou IOChannel para
        verificar o socket.'''
        msg = self.socketCMD.recv()
        resp = Message(0, msg)
        if resp.cmd != 'data':
            raise Exception('Erro: %s' % msg.decode('ascii'))
        return resp.data

    # comunicacao entre servidor e cliente
    def _exchangeData(self, chan, cond, fdout, termName):
        if not self.daemonStarted: self._daemon()  # se a daemon nao foi iniciada, inicia.
        # depois simplesmente le o que fora escrito no terminal, a daemon se responsabiliza pelo que veio do servidor
        payload = {'term': termName, 'data': chan.read(128).decode('ascii')}
        request = Message(cmd='data', data=payload)
        self.socketCMD.send(request.serialize())
        return True

    def _daemon(self):
        self.instanciaDaemon = Thread(target=self._readMessage)
        self.instanciaDaemon.daemon = True
        self.instanciaDaemon.start()
        self.daemonStarted = True

    def _buildTerm(self):
        for term in self.terminais:
            terminal = Vte.Terminal()
            ptm, pts = pty.openpty()

            # põe o lado mestre do terminal em modo "raw", para que não
            # interprete caracteres especiais digitados
            tty.setraw(ptm)

            terminal.set_pty(Vte.Pty.new_foreign_sync(ptm))  # sincroniza com o master
            terminal.set_name(term)  # da um nome para o terminal

            chanDoCliente = GLib.IOChannel(pts)  # canal para obter mensagens escritas no vte e envia-las pro socket
            # chanDoServidor = GLib.IOChannel(self.socketCMD.fileno())  # recebidas do servidor

            # define flags para leitura nao bloqueante
            chanDoCliente.set_flags(GLib.IO_FLAG_NONBLOCK)
            # chanDoServidor.set_flags(GLib.IO_FLAG_NONBLOCK)

            # define condicao
            condition = GLib.IOCondition(GLib.IOCondition.IN)

            # chanDoServidor.add_watch(condition, self._exchangeData, 1, term)  # escreve e manda pro servidor //Funciona
            chanDoCliente.add_watch(condition, self._exchangeData, pts, term)  # deve escrever no vte //fuck
            self.terminaisDict[term] = (terminal, ptm, pts)
            os.write(pts, "Pressione a tecla ENTER".encode('ascii'))

    def _buildWindow(self, terminal, pc):
        '''Metodo para criar uma janela, agrega a ela um terminal e o nome do mesmo(pc)'''
        win = Gtk.Window()
        win.set_title(pc)
        win.add(terminal)
        win.show_all()
        return win

    def on_button_clicked(self, button, win):
        """
        Se o botao for clicado, torna a janela visivel
        :param button: Gtk.ToggleButton
        :type win: Gtk.Window
        """
        if button.get_active():
            win.set_visible(True)
        else:
            win.set_visible(False)

    def on_close_clicked(self, win, *args):
        """
        :param win: Gtk.Window
        :type button: Gtk.ToggleButton
        """
        win.set_visible(False)
        button = self.buttonDict[win]
        status = button.get_active()
        status = not status
        button.set_active(status)
        return True

    def connect_main_win(self, win):
        self.gtkMainWin = win

    def _buildTermWindow(self):
        # self.gtkMainWin = InterfaceHandler(self)
        grid = self.gtkMainWin.get_grid()
        self._buildTerm()
        top = 0
        for termName in self.terminaisDict.keys():
            win = self._buildWindow(self.terminaisDict[termName][0], termName)
            # self.gtkMainWin.add(win)
            button = Gtk.ToggleButton(termName)
            self.buttonDict[win] = button
            button.connect("toggled", self.on_button_clicked, win)
            win.connect("delete-event", self.on_close_clicked)
            # grid.attach(button, 0, top, 3, 5)
            grid.add(button)
            top += 6
            win.set_visible(False)

        self.gtkMainWin.mainWindow.show_all()
        self.gtkMainWin.runMain()

    def _readMessage(self):
        while self.socketCMD.poll() == zmq.POLLIN:
            resp = self.socketCMD.recv()
            if resp:
                resp = Message(0, resp)
                if (resp.cmd == 'data'):
                    term = resp.data['term']
                    data = resp.data['data']
                    print("recebeu", term, data)
                    os.write(self.terminaisDict[term][2], data.encode('ascii'))

    def run(self):
        '''Constroi as janelas dos pseudo-terminais e executa'''
        self._buildTermWindow()
        # ao fechar as janelas, envia um sinal de stop para o servidor
        self.stop()

    def stop(self):
        request = Message(cmd='stop', data='')
        self.socketCMD.send(request.serialize())

    def addNetwork(self, **args):
        '''Adiciona uma rede no repositorio
        "name"=Nome da rede
        "author"=Autor da rede
        "description"=Descricao da rede
        "preferences"=Preferencias da rede
         "value"=nome do arquivo contendo a configuracao'''
        with open(args['filename'], 'r') as confFile:
            value = confFile.read()

        payload = {
            'name': args['name'],
            'author': args['author'],
            'description': args['description'],
            'preferences': args['preferences'],
            'published': time.asctime(),
            'value': value
        }
        request = Message(cmd='addNetwork', data=payload)
        self.socketCMD.send(request.serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        print('>>>', resp.data)
        print('recebeu do servidor: ', resp.get('status'))
        if resp.get('status') != 200:
            return False
        else:
            return True

    def updateNetwork(self, **args):
        '''Atualiza uma rede, o parametro nome="" eh obrigatorio, os outros sao opcionais
        author = new author
        description=new description
        preferences = new preference
        value = new value'''
        self.socketCMD.send(Message(cmd='update', data=args).serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            return False
        else:
            return True

    def updateNetwork(self, args):
        '''Atualiza uma rede, o parametro nome="" eh obrigatorio, os outros sao opcionais
        author = new author
        description=new description
        preferences = new preference
        value = new value'''
        self.socketCMD.send(Message(cmd='update', data=args).serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            return False
        else:
            return True

    def removeNetwork(self, name):
        '''Remove uma rede de acordo com o nome da mesma
        True se removeu False se falhou'''
        self.socketCMD.send(Message(cmd='remove', data=name).serialize())
        resp = self.socketCMD.recv()
        resp = Message(0, resp)
        if resp.get('status') != 200:
            False
        else:
            return True


#####################################################################################

class InterfaceHandler(Gtk.Window):
    image = ...  # type: Gtk.Image
    start_dialog_box = ...  # type: Gtk.Box
    start_dialog = ...  # type: Gtk.Dialog
    netname = ...  # type: Gtk.Entry
    input_dialog = ...  # type: Gtk.Dialog
    IP = '127.0.0.1'
    PORT = 5555

    def __init__(self):
        # client data
        self.client = Client(InterfaceHandler.IP, InterfaceHandler.PORT)

        # building a builder
        self.builder = Gtk.Builder()
        self.builder.add_from_file("interface-glade.glade")

        # get main window
        self.mainWindow = self.builder.get_object("main-window")
        self.mainWindow.connect("destroy", self.on_destroy)

        # get interface box
        self.interfaceBox = self.builder.get_object("interface-box")

        # get interface grid
        self.interfaceGrid = self.builder.get_object('interface-grid')
        self.menuBar = self.builder.get_object('menu-bar')

        # input dialog
        # self.input_dialog = self.builder.get_object("input")

        # image box
        self.image_box = self.builder.get_object("imagem_box")
        self.image = Gtk.Image().new_from_file('ifsc.png')
        self.image_box.add(self.image)
        # todo Carregar uma imagem qualquer, e ao iniciar a rede carregar o diagrama da rede

        # entry
        self.netname = self.builder.get_object("input_name")
        self.netauthor = self.builder.get_object("input_author")
        self.netdescription = self.builder.get_object("input_description")
        self.netpreferences = self.builder.get_object("input_preferences")

        # start dialog
        self.start_dialog = self.builder.get_object("start_dialog")
        self.start_dialog_box = self.builder.get_object("start_dialog_box")

        self.builder.connect_signals(self)

        # atributes
        self.name = ''
        self.author = ''
        self.description = ''
        self.preferences = ''
        self.filename = ''

    def _load_image(self):
        self.image_box.remove(self.image)
        self.image = Gtk.Image().new_from_file('teste.jpg')
        self.image_box.add(self.image)

    def on_network_button_clicked(self, widget):
        """

        :type widget: Gtk.Button
        """
        self.network_name = widget.get_name()
        print('o nome da rede eh ', self.network_name)
        self.start_dialog.set_visible(False)
        self.start_dialog.close()
        self.client.start(self.network_name)
        self.client.connect_main_win(self)
        self._load_image()
        self.client.run()
        self.start_dialog.set_visible(False)
        self.start_dialog.close()
        return True

    def on_start_button_clicked(self, *args):
        if not self.client.started:
            self.networks = self.client.networks
            for network in self.networks:
                button = Gtk.Button(network)
                button.set_name(network)
                button.connect("clicked", self.on_network_button_clicked)
                button.set_visible(True)
                self.start_dialog_box.add(button)
                print(network)

            self.start_dialog.run()
            self.start_dialog.show_all()

    def on_destroy(self, *args):
        Gtk.main_quit()

    def on_dialog_destroy(self, *args):
        """
        :type widget: Gtk.Dialog
        """
        # widget.destroy()
        # self.input_dialog.close()
        self.input_dialog.destroy()
        # self.input_dialog = self.builder.get_object("input")
        return True

    def on_name_input_changed(self, *args):
        self.name = self.netname.get_text()

    def on_author_input_changed(self, *args):
        self.author = self.netauthor.get_text()

    def on_description_input_changed(self, *args):
        self.description = self.netdescription.get_text()

    def on_preferences_input_changed(self, *args):
        self.preferences = self.netpreferences.get_text()

    def on_conf_file_clicked(self, *args):
        dialog = Gtk.FileChooserDialog("Open .conf file", None,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.filename = dialog.get_filename()

        dialog.destroy()

    def add_network_button(self, *args):
        self._clearData()
        self.input_dialog = self.builder.get_object("input")
        self.input_dialog.run()
        cliente = Client(InterfaceHandler.IP, InterfaceHandler.PORT)
        # se algum dos valores for nulo, nao faz nada
        if (not (self.name == '' or
                 self.author == '' or
                 self.description == '' or
                 self.preferences == ''
                 or self.filename == '')):
            # caso todos tenham sido preenchidos, ele adiciona a rede
            if cliente.addNetwork(
                    name=self.name,
                    author=self.author,
                    description=self.description,
                    preferences=self.preferences,
                    filename=self.filename
            ):
                print('Funcionou')
                # adicionar uma janelinha pra aparecer q adicionou
                self._ok_dialog("rede adicionada com sucesso")

        else:
            print('deu ruim lek')
            self._ok_dialog("fracassou ao adicionar a rede")
            # pop up pra avisar q deu ruim

        self.input_dialog.destroy()

    def on_update_button(self, *args):
        self._clearData()
        self.input_dialog = self.builder.get_object("input")
        self.input_dialog.run()
        novos_dados = {}

        # todo quando tiver tempo implementar isso de forma menos bosta
        if self.name != '': novos_dados['name'] = self.name
        if self.author != '': novos_dados['author'] = self.author
        if self.preferences != '': novos_dados['preferences'] = self.preferences
        if self.description != '': novos_dados['description'] = self.description
        if self.filename != '': novos_dados['filename'] = self.filename

        cliente = Client(InterfaceHandler.IP, InterfaceHandler.PORT)
        if cliente.updateNetwork(novos_dados): print('ok')
        else: print('deu ruim')

    def _clearData(self):
        pass

    def on_remove_button(self, *args):
        pass

    def on_info_button(self, *args):
        pass

    def on_cancel_button_clicked(self):
        self.input_dialog.close()

    def get_grid(self):
        return self.interfaceGrid

    def _ok_dialog(self, label):
        dialog = OkDialog(label)

    def runMain(self):
        Gtk.main()


#####################################################################################

class OkDialog(Gtk.Dialog):

    def __init__(self, label):
        Gtk.Dialog.__init__(self, "My Dialog", None, 0)
        self.set_default_size(150, 100)

        label = Gtk.Label(label)

        ok_button = Gtk.Button("OK")
        # ok_button.set_tooltip_text("OK")
        ok_button.connect("clicked", self.on_ok)

        box = self.get_content_area()
        box.add(label)
        box.add(ok_button)
        self.show_all()

    def on_ok(self, widget):
        self.destroy()
        return True


#####################################################################################
if __name__ == '__main__':
    app = InterfaceHandler()
    app.mainWindow.show_all()
    Gtk.main()
    sys.exit(0)

    # c = Client(InterfaceHandler.IP, 5555)
    # n = {'name' : 'rede3', 'author':'pudim'}
    # c.updateNetwork(n)
