import xml.etree.ElementTree as ET
import importlib.util
import sys
import os
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gio, Gdk, GdkPixbuf  # noqa: E402

def log(message):
    print(f"[gtkML:LOG] {message}")

def warn(message):
    print(f"[gtkML:WARN] {message}")

def error(message):
    print(f"[gtkML:ERROR] {message}")

class gtkMLApp:
    def __getattr__(self, name):
        for key, widget in self.widgets.items():
            if key.lower() == name.lower():
                return widget

        if name.startswith("Gtk_"):
            return getattr(Gtk, name[4:], None)
        if name.startswith("Gdk_"):
            return getattr(Gdk, name[4:], None)

        if self.window and hasattr(self.window, name):
            return getattr(self.window, name)

        def missing(*args, **kwargs):
            warn(f"Attempted to call unknown function or attribute: {name} (args={args}, kwargs={kwargs})")
            return None
        return missing
    
    def __init__(self, markup_path, logic_path=None):
        self.window = None
        self.widgets = {}
        self.app_info = {}
        self.logic = None

        self.root = self.parse_markup(markup_path)
        self.app = Gtk.Application(application_id="com.example.gtkm")
        self.app.connect("activate", self.on_activate)

        if logic_path:
            self.logic = self.load_logic_module(logic_path)

    def load_logic_module(self, path):
        spec = importlib.util.spec_from_file_location("logic_module", path)
        module = importlib.util.module_from_spec(spec)

        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gio", "2.0")
        gi.require_version("Gdk", "4.0")
        gi.require_version("GdkPixbuf", "2.0")

        from gi.repository import Gtk, Gio, Gdk, GdkPixbuf

        module.Gtk = Gtk
        module.Gio = Gio
        module.Gdk = Gdk
        module.GdkPixbuf = GdkPixbuf

        sys.modules["logic_module"] = module
        spec.loader.exec_module(module)

        module.app = self
        return module

    def parse_markup(self, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()

        logic_path = None

        for child in list(tree.iter()):
            tag = child.tag.lower()

            if tag == "head":
                for meta in child:
                    self.app_info[meta.tag.lower()] = (meta.text or "").strip()

            elif tag == "script" and "src" in child.attrib:
                logic_path = child.attrib["src"]

        if logic_path:
            self.logic = self.load_logic_module(logic_path)

        return root


    def load_css(self, css_path):
        try:
            provider = Gtk.CssProvider()
            provider.load_from_path(css_path)
            display = Gdk.Display.get_default()
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )
            log(f"Loaded CSS: {css_path}")
        except Exception as e:
            warn(f"[Warning] Could not load CSS '{css_path}': {e}")

    def build_ui(self):
        if self.logic:
            setattr(self.logic, "app", self)

        if self.root.tag.lower() == "gtkm":
            window_elem = next((child for child in self.root if child.tag.lower() == "window"), None)
        else:
            window_elem = self.root

        if window_elem is None or window_elem.tag.lower() != "window":
            raise ValueError("Markup must contain a <window> element")

        self.root = window_elem
        win = Gtk.ApplicationWindow(application=self.app)
        win.set_title(
            self.root.attrib.get("title") or self.app_info.get("program_name", "My GTK App")
        )
        win.set_default_size(640, 480)

        for element in self.root:
            if element.tag.lower() == "headerbar":
                headerbar = self.create_headerbar(element)
                win.set_titlebar(headerbar)
                break

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for element in self.root:
            if element.tag.lower() == "headerbar":
                continue
            widget = self.create_widget(element)
            if widget:
                vbox.append(widget)

        win.set_child(vbox)
        self.window = win
        return win

    def create_headerbar(self, element):
        headerbar = Gtk.HeaderBar()
        if "title" in element.attrib:
            headerbar.set_title_widget(Gtk.Label(label=element.attrib["title"]))

        for child in element:
            tag = child.tag.lower()
            if tag == "menu" and child.attrib.get("include") == "default":
                menu_button = self.create_hamburger_menu()
                headerbar.pack_end(menu_button)
                continue

            widget = self.create_widget(child)
            if widget:
                headerbar.pack_start(widget)
        return headerbar

    def create_hamburger_menu(self):
        menu_button = Gtk.MenuButton()
        icon = Gtk.Image.new_from_icon_name("open-menu-symbolic")
        menu_button.set_child(icon)

        # Menu model
        menu_model = Gio.Menu()
        menu_model.append("About", "app.about")
        menu_model.append("Quit", "app.quit")

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.show_about)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.app.quit())

        self.app.add_action(about_action)
        self.app.add_action(quit_action)

        menu_button.set_menu_model(menu_model)
        return menu_button
    
    def apply_common_properties(self, widget, attrib):
        margin_map = {
            "margin": ("top", "bottom", "start", "end"),
            "margin-top": ("top",),
            "margin-bottom": ("bottom",),
            "margin-start": ("start",),
            "margin-end": ("end",),
        }

        for key, sides in margin_map.items():
            if key in attrib:
                value = int(attrib[key])
                for side in sides:
                    getattr(widget, f"set_margin_{side}")(value)

        align_map = {
            "fill": Gtk.Align.FILL,
            "start": Gtk.Align.START,
            "center": Gtk.Align.CENTER,
            "end": Gtk.Align.END,
        }

        if "halign" in attrib:
            widget.set_halign(align_map.get(attrib["halign"].lower(), Gtk.Align.FILL))
        if "valign" in attrib:
            widget.set_valign(align_map.get(attrib["valign"].lower(), Gtk.Align.FILL))
        if "expand" in attrib:
            expand = attrib["expand"].lower() in ("1", "true", "yes")
            widget.set_hexpand(expand)
            widget.set_vexpand(expand)

        if "hexpand" in attrib:
            widget.set_hexpand(attrib["hexpand"].lower() in ("1", "true", "yes"))
        if "vexpand" in attrib:
            widget.set_vexpand(attrib["vexpand"].lower() in ("1", "true", "yes"))
        if "disabled" in attrib:
            widget.set_sensitive(False)
        if "class" in attrib:
            class_list = attrib["class"].split()
            for cls in class_list:
                widget.get_style_context().add_class(cls)
        elif "classes" in attrib:
            class_list = attrib["classes"].split()
            for cls in class_list:
                widget.get_style_context().add_class(cls)
        if "id" in attrib:
            wid = attrib["id"]
            self.widgets[wid] = widget
            setattr(self, wid, widget)


    def create_widget(self, element):
        tag = element.tag.lower()
        widget = None

        if tag == "button":
            label = (element.text or "").strip()
            button_type = element.attrib.get("type", "normal").lower()

            if button_type == "toggle":
                widget = Gtk.ToggleButton(label=label)
            elif button_type == "link":
                uri = element.attrib.get("href", "#")
                widget = Gtk.LinkButton(uri=uri, label=label)
            else:
                widget = Gtk.Button(label=label)

            if "onclick" in element.attrib:
                func_name = element.attrib["onclick"]
                handler = getattr(self.logic, func_name, None) if hasattr(self, "logic") else None
                if handler is None:
                    import logic
                    handler = getattr(logic, func_name, None)

                if callable(handler):
                    widget.connect("clicked", lambda w: handler(w))
                else:
                    warn(f"No such handler in logic.py: {func_name}")
        
        elif tag == "checkbox":
            label = element.attrib.get("label", "").strip()
            active = element.attrib.get("active", "false").lower() in ("1", "true", "yes")
            widget = Gtk.CheckButton(label=label)
            widget.set_active(active)
            if "onclick" in element.attrib and self.logic:
                func_name = element.attrib["onclick"]
                handler = getattr(self.logic, func_name, None)
                if callable(handler):
                    widget.connect("toggled", lambda w: handler(w, w.get_active()))
                else:
                    warn(f"No such handler in logic.py: {func_name}")

        elif tag == "switch":
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

            if "onclick" in element.attrib and self.logic:
                func_name = element.attrib["onclick"]
                handler = getattr(self.logic, func_name, None)
                if callable(handler):
                    sw.connect("state-set", lambda w, state: handler(w, state))
                else:
                    warn(f"No such handler in logic.py: {func_name}")

        elif tag == "label":
            widget = Gtk.Label(label=(element.text or "").strip())

        elif tag == "textview":
            textview = Gtk.TextView()
            buffer = textview.get_buffer()
            if element.text and element.text.strip():
                buffer.set_text(element.text.strip())
            widget = textview

        elif tag == "scroll":
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            for attr, value in element.attrib.items():
                if attr.startswith("margin"):
                    self.apply_margin(scroll, attr, value)
                elif attr == "class":
                    for cls in value.split():
                        scroll.get_style_context().add_class(cls)

            for child in element:
                child_widget = self.create_widget(child)
                if child_widget:
                    scroll.set_child(child_widget)
                    break

            widget = scroll

        elif tag == "entry":
            widget = Gtk.Entry()
            if element.text:
                widget.set_placeholder_text(element.text.strip())

        elif tag in ("vbox", "hbox"):
            orientation = (
                Gtk.Orientation.VERTICAL
                if tag == "vbox"
                else Gtk.Orientation.HORIZONTAL
            )
            widget = Gtk.Box(orientation=orientation)
            spacing = element.attrib.get("spacing")
            if spacing:
                widget.set_spacing(int(spacing))
            for child in element:
                child_widget = self.create_widget(child)
                if child_widget:
                    widget.append(child_widget)

        elif tag == "frame":
            label = element.attrib.get("label")
            widget = Gtk.Frame(label=label)

            children = [self.create_widget(child) for child in element if self.create_widget(child)]
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

        elif tag in ("img", "image"):
            src = element.attrib.get("src")
            width = element.attrib.get("width")
            height = element.attrib.get("height")
            size = element.attrib.get("size")

            if not src:
                warn("<img> tag missing src attribute.")
                widget = Gtk.Image.new()
            else:
                try:
                    base_dir = os.path.dirname(os.path.abspath(sys.argv[1])) if len(sys.argv) > 1 else os.getcwd()
                    resolved_path = os.path.normpath(os.path.join(base_dir, src))
                    target_w = target_h = None
                    if size:
                        try:
                            target_w = target_h = int(size)
                        except Exception:
                            target_w = target_h = None
                    else:
                        if width:
                            try:
                                target_w = int(width)
                            except Exception:
                                target_w = None
                        if height:
                            try:
                                target_h = int(height)
                            except Exception:
                                target_h = None
                    orig_pb = None
                    try:
                        orig_pb = GdkPixbuf.Pixbuf.new_from_file(resolved_path)
                        orig_w = orig_pb.get_width()
                        orig_h = orig_pb.get_height()
                    except Exception:
                        orig_pb = None
                        orig_w = orig_h = None

                    if target_w and not target_h and orig_w and orig_h:
                        target_h = int(target_w * (orig_h / orig_w))
                    elif target_h and not target_w and orig_w and orig_h:
                        target_w = int(target_h * (orig_w / orig_h))

                    if target_w and target_h:
                        try:
                            scaled_pb = GdkPixbuf.Pixbuf.new_from_file_at_size(resolved_path, target_w, target_h)
                        except Exception:
                            if orig_pb:
                                scaled_pb = orig_pb.scale_simple(target_w, target_h, GdkPixbuf.InterpType.BILINEAR)
                            else:
                                scaled_pb = None

                        if scaled_pb:
                            try:
                                texture = Gdk.Texture.new_for_pixbuf(scaled_pb)
                                pic = Gtk.Picture()
                                pic.set_paintable(texture)
                                pic.set_size_request(target_w, target_h)
                                pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                                pic.set_halign(Gtk.Align.CENTER)
                                pic.set_valign(Gtk.Align.CENTER)
                                widget = pic
                            except Exception:
                                widget = Gtk.Image.new_from_pixbuf(scaled_pb)
                        else:
                            try:
                                texture = Gdk.Texture.new_from_filename(resolved_path)
                                pic = Gtk.Picture()
                                pic.set_paintable(texture)
                                pic.set_size_request(target_w, target_h)
                                widget = pic
                            except Exception:
                                warn(f"Could not load image '{resolved_path}' (scaled fallback).")
                                widget = Gtk.Image.new()
                    else:
                        try:
                            texture = Gdk.Texture.new_from_filename(resolved_path)
                            pic = Gtk.Picture()
                            pic.set_paintable(texture)
                            pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                            widget = pic
                        except Exception:
                            try:
                                widget = Gtk.Image.new_from_file(resolved_path)
                            except Exception as e:
                                warn(f"Could not load image '{resolved_path}': {e}")
                                widget = Gtk.Image.new()
                except Exception as e:
                    warn(f"Could not load image '{src}': {e}")
                    widget = Gtk.Image.new()

            if widget:
                self.apply_common_properties(widget, element.attrib)

        elif tag == "notebook":
            widget = Gtk.Notebook()
            for tab_elem in element.findall("tab"):
                label = tab_elem.attrib.get("label", "Tab")

                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                for child in tab_elem:
                    child_widget = self.create_widget(child)
                    if child_widget:
                        vbox.append(child_widget)

                widget.append_page(vbox, Gtk.Label(label=label))

        elif tag == "script":
            return None

        else:
            warn(f"Unknown tag: <{tag}>")
            return None

        if widget:
            self.apply_common_properties(widget, element.attrib)

        return widget

    def show_about(self, *_args):
        info = self.app_info
        dialog = Gtk.AboutDialog(
            transient_for=self.window,
            modal=True,
            program_name=info.get("program_name", "gtkML Application"),
            version=info.get("version", "1.0"),
            comments=info.get("comments", "No discription provided."),
            website=info.get("website", "https://example.com"),
            authors=[a.strip() for a in info.get("authors", "Unknown").split(",")],
        )

        icon_path = info.get("icon")
        if icon_path:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 128, 128)
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                dialog.set_logo(texture)
            except Exception as e:
                warn(f"Could not load icon '{icon_path}': {e}")

        dialog.present()

    def on_activate(self, app):
        win = self.build_ui()
        app.add_window(win)
        win.present()

    def run(self, css_path=None):
        css_path = css_path or self.app_info.get("css")
        if css_path:
            self.load_css(css_path)
        self.app.run(None)


if __name__ == "__main__":
    app = gtkMLApp("ui.gtkm")
    app.run()
