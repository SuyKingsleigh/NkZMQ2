import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class InterfaceHandler(Gtk.Window):
    def __init__(self):
        # building a builder
        self.builder = Gtk.Builder()
        self.builder.add_from_file("interface-glade2.glade")

        # get main window
        self.mainWindow = self.builder.get_object("main-window")

        # get interface box
        self.interfaceBox = self.builder.get_object("interface-box")

        # get interface grid
        self.interfaceGrid = self.builder.get_object('interface-grid')
        self.menuBar = self.builder.get_object('menu-bar')



        # file-chooser
        self.fileChoser = self.builder.get_object('file-chooser')

        self.builder.connect_signals(self)
        # Gtk.main()

    def on_destroy(self, *args):
        Gtk.main_quit()


    def add_network_button(self):
        # abrir uma janela, extrair author, preferences e description
        # fechar a janela
        # abrir o file-chooser
        # abrir o arquivo
        # carrega-lo em algum lugar
        # envia-lo
        # imprimir uma mensagem q deu bom
        pass

    def get_grid(self):
        return self.interfaceGrid

    def get_user_data(self):
        # talvez seja melhor fazer isso com uma classe interna?
        self.user_input = Gtk.Builder()
        self.user_input.add_from_file('user_input.glade')

        self.name_input= self.user_input.get_object('name_input')
        self.author_input = self.user_input.get_object('author_input')
        self.description_input = self.user_input.get_object('description_input')
        self.preferences_input = self.user_input.get_object('preferences_input')



    def runMain(self):
        Gtk.main()

