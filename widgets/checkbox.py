from gi.repository import Gtk

def create(app, element):
    label = element.attrib.get("label", "").strip()
    active = element.attrib.get("active", "false").lower() in ("1", "true", "yes")
    widget = Gtk.CheckButton(label=label)
    widget.set_active(active)
    if "onclick" in element.attrib and app.logic:
        func_name = element.attrib["onclick"]
        handler = getattr(app.logic, func_name, None)
        if callable(handler):
            widget.connect("toggled", lambda w: handler(w, w.get_active()))
        else:
            app.warn(f"No such handler in logic.py: {func_name}")
    return widget