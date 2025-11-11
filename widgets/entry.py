from gi.repository import Gtk

def create(app, element):
    widget = Gtk.Entry()
    if element.text:
        widget.set_placeholder_text(element.text.strip())
    return widget