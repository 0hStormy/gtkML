from gi.repository import Gtk

def create(app, element):
    active = element.attrib.get("active", "false").lower() in ("1", "true", "yes")
    label = element.attrib.get("label")

    if label:
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.START)
        hbox.append(lbl)
        sw = Gtk.Switch()
        sw.set_active(active)
        hbox.append(sw)
        widget = hbox
        widget._inner_switch = sw
    else:
        sw = Gtk.Switch()
        sw.set_active(active)
        widget = sw

    if "onclick" in element.attrib and app.logic:
        func_name = element.attrib["onclick"]
        handler = getattr(app.logic, func_name, None)
        if callable(handler):
            sw.connect("state-set", lambda w, state: handler(w, state))
        else:
            app.warn(f"No such handler in logic.py: {func_name}")
    return widget
