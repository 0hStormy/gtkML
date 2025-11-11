from gi.repository import Gtk

def create(app, element):
    label = (element.text or "").strip()
    button_type = element.attrib.get("type", "normal").lower()

    if button_type == "toggle":
        widget = Gtk.ToggleButton(label=label)
    elif button_type == "link":
        uri = element.attrib.get("href", "#")
        widget = Gtk.LinkButton(uri=uri, label=label)
    else:
        widget = Gtk.Button(label=label)

    # connect onclick handler if present
    if "onclick" in element.attrib and app.logic:
        func_name = element.attrib["onclick"]
        handler = getattr(app.logic, func_name, None)
        if callable(handler):
            widget.connect("clicked", handler)
        else:
            app.warn(f"No such handler in logic.py: {func_name}")

    return widget
