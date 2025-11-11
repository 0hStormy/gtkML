from gi.repository import Gtk

def create(app, element):
    widget = Gtk.Notebook()
    for tab_elem in element.findall("tab"):
        label = tab_elem.attrib.get("label", "Tab")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for child in tab_elem:
            child_widget = app.create_widget(child)
            if child_widget:
                vbox.append(child_widget)

        widget.append_page(vbox, Gtk.Label(label=label))
    return widget
