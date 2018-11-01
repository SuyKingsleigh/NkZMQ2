import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class Handler:
    def __init__(self):
        # building a builder
        self.builder = Gtk.Builder()
        self.builder.add_from_file("interface-glade.glade")

        # get main window
        self.mainWindow = self.builder.get_object("main-window")

        # get interface box
        self.interfaceBox = self.builder.get_object("interface-box")

        self.mainWindow.show_all()

        self.builder.connect_signals(self)

    def on_destroy(self):
        Gtk.main_quit()


a = Handler()
Gtk.main()

