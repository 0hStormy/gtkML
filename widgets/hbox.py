from gi.repository import Gtk

def create(app, element):
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    for child in element:
        widget = app.create_widget(child)
        if widget:
            box.append(widget)

    return box
