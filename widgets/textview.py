from gi.repository import Gtk

def create(app, element):
    textview = Gtk.TextView()
    buffer = textview.get_buffer()
    if element.text and element.text.strip():
        buffer.set_text(element.text.strip())
    widget = textview
    return widget