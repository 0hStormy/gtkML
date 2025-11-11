from gi.repository import Gtk

def create(app, element):
    widget = Gtk.Label(label=(element.text or "").strip())
    return widget