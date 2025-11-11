from gi.repository import Gtk

def create(app, element):
    label = element.attrib.get("label")
    widget = Gtk.Frame(label=label)

    children = [app.create_widget(child) for child in element if app.create_widget(child)]
    children = [c for c in children if c is not None]

    if len(children) == 1:
        child_widget = children[0]
        if isinstance(child_widget, (Gtk.Image, Gtk.Label)):
            child_widget.set_halign(Gtk.Align.CENTER)
            child_widget.set_valign(Gtk.Align.CENTER)
            child_widget.set_hexpand(True)
            child_widget.set_vexpand(True)
        widget.set_child(child_widget)
    elif len(children) > 1:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for child_widget in children:
            box.append(child_widget)
        widget.set_child(box)
    return widget
