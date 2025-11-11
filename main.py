#!/usr/bin/env python3
import sys
import os
import json
import xml.etree.ElementTree as ET
import importlib.util
import importlib
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gio, Gdk, GdkPixbuf  # noqa: E402

DEFAULT_APP_ID = "com.zerostormy.gtkml"

def log(message):
    print(f"[gtkML:LOG] {message}")

def warn(message):
    print(f"[gtkML:WARN] {message}")

def error(message):
    print(f"[gtkML:ERROR] {message}")

def detect_app_root():
    if getattr(sys, "frozen", False) or getattr(sys, "compiled", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) > 1:
        app_root = os.path.abspath(sys.argv[1])
    else:
        example_dir = os.path.join(base_dir, "example")
        app_root = example_dir if os.path.exists(example_dir) else base_dir
    return app_root

APP_ROOT = detect_app_root()

class gtkMLApp:
    def log(self, message):
        print(f"[gtkML:LOG] {message}")

    def warn(self, message):
        print(f"[gtkML:WARN] {message}")

    def error(self, message):
        print(f"[gtkML:ERROR] {message}")

    def __getattr__(self, name):
        try:
            widgets = object.__getattribute__(self, "widgets")
        except Exception:
            widgets = {}

        if isinstance(widgets, dict):
            lname = name.lower()
            for key, widget in widgets.items():
                if key and key.lower() == lname:
                    return widget

        if name.startswith("Gtk_"):
            return getattr(Gtk, name[4:], None)
        if name.startswith("Gdk_"):
            return getattr(Gdk, name[4:], None)

        try:
            window = object.__getattribute__(self, "window")
        except Exception:
            window = None

        if window and hasattr(window, name):
            return getattr(window, name)

        def missing(*args, **kwargs):
            try:
                self.warn(f"Attempted to call unknown function or attribute: {name} (args={args}, kwargs={kwargs})")
            except Exception:
                print(f"[gtkML:WARN] Attempted to call unknown function or attribute: {name} (args={args}, kwargs={kwargs})")
            return None
        return missing

    def __init__(self, ui_path, logic_path=None, widgets_dir=None, application_id=None):
        ui_path = os.path.abspath(ui_path)
        self.ui_path = ui_path
        self.app_dir = os.path.dirname(self.ui_path)
        self.app_root = APP_ROOT
        self.assets_dir = os.path.join(self.app_root, "assets")

        if widgets_dir and os.path.isdir(widgets_dir):
            self.widgets_dir = os.path.abspath(widgets_dir)
        else:
            candidate_dirs = [
                os.path.join(self.app_root, "widgets"),
                os.path.join(os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__), "widgets"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "widgets"),
                os.path.join(os.getcwd(), "widgets"),
            ]
            self.widgets_dir = next((d for d in candidate_dirs if os.path.isdir(d)), candidate_dirs[0])


        self.widgets = {}
        self.app_info = {}
        self.logic = None
        self._widget_module_cache = {}

        app_id = application_id or DEFAULT_APP_ID
        self.app = Gtk.Application(application_id=app_id)
        self.app.connect("activate", self.on_activate)
        self.root = self.parse_markup(self.ui_path)

        if logic_path:
            self.logic = self.load_logic_module(logic_path)

    def load_logic_module(self, path):
        path = os.path.abspath(path)
        if not os.path.exists(path):
            self.warn(f"Logic file not found: {path}")
            return None

        spec = importlib.util.spec_from_file_location("gtkml_logic_module", path)
        module = importlib.util.module_from_spec(spec)

        import gi as _gi
        _gi.require_version("Gtk", "4.0")
        _gi.require_version("Gio", "2.0")
        _gi.require_version("Gdk", "4.0")
        _gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import Gtk as _Gtk, Gio as _Gio, Gdk as _Gdk, GdkPixbuf as _GdkPixbuf

        module.Gtk = _Gtk
        module.Gio = _Gio
        module.Gdk = _Gdk
        module.GdkPixbuf = _GdkPixbuf

        sys.modules["gtkml_logic_module"] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            self.warn(f"Failed to load logic module '{path}': {e}")
            return None

        module.app = self
        return module

    def parse_markup(self, file_path):
        try:
            tree = ET.parse(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to parse UI file '{file_path}': {e}")

        root = tree.getroot()
        self.app_info = {}

        logic_path = None
        for child in list(tree.iter()):
            tag = child.tag.lower()
            if tag == "head":
                for meta in child:
                    self.app_info[meta.tag.lower()] = (meta.text or "").strip()
            elif tag == "script" and child.attrib.get("src"):
                src = child.attrib["src"]
                candidate = os.path.join(self.app_dir, src)
                if os.path.exists(candidate):
                    logic_path = candidate
                else:
                    logic_path = src
        if logic_path:
            self.logic = self.load_logic_module(logic_path)
        return root

    def load_css(self, css_path):
        if css_path:
            if not os.path.isabs(css_path):
                css_path = os.path.join(self.app_dir, css_path)
        else:
            css_path = self.app_info.get("css")
            if css_path and not os.path.isabs(css_path):
                css_path = os.path.join(self.app_dir, css_path)

        if not css_path or not os.path.exists(css_path):
            self.warn(f"CSS not found or not provided: {css_path}")
            return

        try:
            provider = Gtk.CssProvider()
            provider.load_from_path(css_path)
            display = Gdk.Display.get_default()
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        except Exception as e:
            self.warn(f"Could not load CSS '{css_path}': {e}")

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
        win.set_title(self.root.attrib.get("title") or self.app_info.get("program_name", "gtkML Application"))
        win.set_default_size(640, 480)

        for element in self.root:
            if element.tag.lower() == "headerbar":
                headerbar = self.create_headerbar(element)
                if headerbar:
                    win.set_titlebar(headerbar)
                break

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_hexpand(True)
        vbox.set_vexpand(True)

        for element in self.root:
            if element.tag.lower() == "headerbar":
                continue
            widget = self.create_widget(element)
            if widget:
                if hasattr(vbox, "append"):
                    vbox.append(widget)
                else:
                    try:
                        vbox.add(widget)
                    except Exception:
                        pass

        win.set_child(vbox)
        self.window = win
        return win

    def get_app_root(self):
        return self._determine_app_root(preferred_app_dir=self.app_dir)

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
        attrib = {k.lower(): v for k, v in attrib.items()}

        def truthy(val):
            return str(val).lower() in ("1", "true", "yes", "on")

        margin_keys = {
            "margin": ("top", "bottom", "start", "end"),
            "margin-top": ("top",),
            "margin-bottom": ("bottom",),
            "margin-start": ("start",),
            "margin-end": ("end",),
        }

        for key, sides in margin_keys.items():
            if key in attrib:
                try:
                    value = int(attrib[key])
                    for side in sides:
                        setter = getattr(widget, f"set_margin_{side}", None)
                        if callable(setter):
                            setter(value)
                except Exception:
                    continue

        if "spacing" in attrib:
            try:
                spacing = int(attrib["spacing"])
                if hasattr(widget, "set_spacing"):
                    widget.set_spacing(spacing)
            except Exception:
                pass

        align_map = {
            "fill": Gtk.Align.FILL,
            "start": Gtk.Align.START,
            "center": Gtk.Align.CENTER,
            "end": Gtk.Align.END,
        }

        halign = attrib.get("halign", "").lower()
        valign = attrib.get("valign", "").lower()

        try:
            if halign in align_map:
                widget.set_halign(align_map[halign])
            if valign in align_map:
                widget.set_valign(align_map[valign])
        except Exception:
            pass

        if "expand" in attrib:
            try:
                val = truthy(attrib["expand"])
                widget.set_hexpand(val)
                widget.set_vexpand(val)
            except Exception:
                pass

        if "hexpand" in attrib:
            try:
                widget.set_hexpand(truthy(attrib["hexpand"]))
            except Exception:
                pass

        if "vexpand" in attrib:
            try:
                widget.set_vexpand(truthy(attrib["vexpand"]))
            except Exception:
                pass

        if "disabled" in attrib and truthy(attrib["disabled"]):
            try:
                widget.set_sensitive(False)
            except Exception:
                pass
        elif "enabled" in attrib:
            try:
                widget.set_sensitive(truthy(attrib["enabled"]))
            except Exception:
                pass

        try:
            ctx = widget.get_style_context()
        except Exception:
            ctx = None

        if ctx:
            classes = []
            if "class" in attrib:
                classes += attrib["class"].split()
            if "classes" in attrib:
                classes += attrib["classes"].split()
            for c in classes:
                try:
                    ctx.add_class(c)
                except Exception:
                    pass

        if "id" in attrib:
            wid = attrib["id"]
            self.widgets[wid] = widget
            try:
                setattr(self, wid, widget)
            except Exception:
                pass

    def _load_widget_module_from_file(self, tag):
        # Try several candidate directories for widget files. This is necessary
        # because when using Nuitka in onefile mode data directories may be
        # placed next to the executable or in other runtime locations.
        tried = []
        candidates = []
        if self.widgets_dir:
            candidates.append(self.widgets_dir)
        # app_dir (where ui.gtkm / logic.py live)
        try:
            candidates.append(os.path.join(self.app_dir, "widgets"))
        except Exception:
            pass
        # app_root (runtime base)
        try:
            candidates.append(os.path.join(self.app_root, "widgets"))
        except Exception:
            pass
        # dirname of the executable (useful for frozen / onefile builds)
        try:
            candidates.append(os.path.join(os.path.dirname(sys.executable), "widgets"))
        except Exception:
            pass
        # local repository layout
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "widgets"))
        candidates.append(os.path.join(os.getcwd(), "widgets"))

        # remove duplicates while preserving order
        seen = set()
        filtered = []
        for p in candidates:
            if not p:
                continue
            if p in seen:
                continue
            seen.add(p)
            filtered.append(p)

        for d in filtered:
            module_path = os.path.join(d, f"{tag}.py")
            tried.append(module_path)
            if os.path.exists(module_path):
                try:
                    name = f"gtkml_widget_{tag}"
                    spec = importlib.util.spec_from_file_location(name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    return module
                except Exception as e:
                    self.warn(f"Failed to load widget module file {module_path}: {e}")
                    return None

        # nothing found
        return None

    def _load_widget_module_via_import(self, tag):
        candidates = [
            f"gtkML.widgets.{tag}",
            f"widgets.{tag}",
            f"gtkml.widgets.{tag}",
            tag,
        ]
        for name in candidates:
            try:
                module = importlib.import_module(name)
                return module
            except ModuleNotFoundError:
                continue
            except Exception as e:
                self.warn(f"Error importing widget module '{name}': {e}")
        return None

    def create_widget(self, element):
        tag = element.tag.lower()

        module = self._widget_module_cache.get(tag)
        if not module:
            module = self._load_widget_module_from_file(tag)
            if module is None:
                module = self._load_widget_module_via_import(tag)

            if module is None:
                self.warn(f"No widget handler for <{tag}>")
                return None

            self._widget_module_cache[tag] = module

        if not hasattr(module, "create"):
            self.warn(f"Widget module '{tag}' missing create() function")
            return None

        try:
            widget = module.create(self, element)
            if widget:
                self.apply_common_properties(widget, element.attrib)
            return widget
        except Exception as e:
            self.warn(f"Error creating widget <{tag}>: {e}")
            return None

    def show_about(self, *_args):
        info = self.app_info
        dialog = Gtk.AboutDialog(
            transient_for=self.window,
            modal=True,
            program_name=info.get("program_name", "gtkML Application"),
            version=info.get("version", "1.0"),
            comments=info.get("comments", "No description provided."),
            website=info.get("website", "https://example.com"),
            authors=[a.strip() for a in info.get("authors", "Unknown").split(",")],
        )

        if info.get("icon"):
            icon_path = info.get("icon")
            icon_file = icon_path if os.path.isabs(icon_path) else os.path.join(self.app_dir, icon_path)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_file, 128, 128)
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                dialog.set_logo(texture)
            except Exception as e:
                self.warn(f"Could not load icon '{icon_path}': {e}")

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


def get_runtime_dir():
    """Return the base directory where assets and examples live."""
    if getattr(sys, "frozen", False):
        # Nuitka onefile mode
        # sys._MEIPASS may exist, but with Nuitka, data dirs are next to the binary
        base = os.path.dirname(sys.executable)
    else:
        # Normal Python mode
        base = os.path.dirname(os.path.abspath(__file__))
    return base


def find_app_paths(start_path):
    # json and os are already imported at module level; avoid re-importing here
    start_path = os.path.abspath(start_path)

    # detect if we're running from a Nuitka binary
    if getattr(sys, "frozen", False):
        runtime_base = os.path.dirname(sys.executable)
    else:
        runtime_base = os.path.dirname(os.path.abspath(__file__))

    # ensure example/ is treated as part of the app root only if we’re inside it
    if os.path.basename(start_path) == "example" and os.path.isdir(start_path):
        app_dir = os.path.join(runtime_base, "example")
    else:
        app_dir = start_path if os.path.isdir(start_path) else os.path.dirname(start_path)

    ui_candidate = os.path.join(app_dir, "ui.gtkm")
    logic_candidate = os.path.join(app_dir, "logic.py")
    css_candidate = os.path.join(app_dir, "style.css")
    config_candidate = os.path.join(app_dir, "gtkml.json")

    ui_path = logic_path = css_path = None

    if os.path.exists(config_candidate):
        try:
            with open(config_candidate, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            ui_path = os.path.join(app_dir, cfg.get("main", "ui.gtkm"))
            logic_path = os.path.join(app_dir, cfg.get("logic", "logic.py")) if cfg.get("logic") else None
            css_path = os.path.join(app_dir, cfg.get("style", "style.css")) if cfg.get("style") else None
        except Exception as e:
            print(f"[gtkML:WARN] Failed to parse gtkml.json: {e}")

    if not ui_path:
        if os.path.exists(ui_candidate):
            ui_path = ui_candidate
        elif os.path.isfile(start_path) and start_path.lower().endswith(".gtkm"):
            ui_path = start_path

    if not logic_path and os.path.exists(logic_candidate):
        logic_path = logic_candidate

    if not css_path and os.path.exists(css_candidate):
        css_path = css_candidate

    return app_dir, ui_path, logic_path, css_path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        start_path = sys.argv[1]
    else:
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        start_path = os.path.join(base, "example")

    app_dir, ui_path, logic_path, css_path = find_app_paths(start_path)

    app = gtkMLApp(ui_path, logic_path)
    app.app_root = app_dir
    app.run(css_path)
