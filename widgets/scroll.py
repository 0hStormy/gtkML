from gi.repository import Gtk

def create(app, element):
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    for attr, value in element.attrib.items():
        if attr.startswith("margin"):
            app.apply_margin(scroll, attr, value)
        elif attr == "class":
            for cls in value.split():
                scroll.get_style_context().add_class(cls)

    for child in element:
        child_widget = app.create_widget(child)
        if child_widget:
            scroll.set_child(child_widget)
            break

    widget = scroll
    return widget