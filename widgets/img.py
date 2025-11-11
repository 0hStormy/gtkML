from gi.repository import Gtk, Gdk, GdkPixbuf
import os

def create(app, element):
    src = element.attrib.get("src")
    width = element.attrib.get("width")
    height = element.attrib.get("height")
    size = element.attrib.get("size")

    if not src:
        app.warn("<img> tag missing src attribute.")
        return Gtk.Image.new()

    try:
        candidates = []

        if hasattr(app, "app_root"):
            candidates.append(os.path.join(app.app_root, src))
            candidates.append(os.path.join(app.app_root, "assets", src))

        candidates.append(os.path.join(os.getcwd(), src))
        if not os.path.isabs(src):
            candidates.append(os.path.abspath(src))
        else:
            candidates.insert(0, src)

        resolved_path = next((p for p in candidates if os.path.exists(p)), None)

        if not resolved_path:
            app.warn(f"Image not found: {src}")
            return Gtk.Image.new()

        target_w = target_h = None
        if size:
            try:
                target_w = target_h = int(size)
            except Exception:
                pass
        else:
            if width:
                try: target_w = int(width)
                except Exception: pass
            if height:
                try: target_h = int(height)
                except Exception: pass

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
                texture = Gdk.Texture.new_from_filename(resolved_path)
                pic = Gtk.Picture()
                pic.set_paintable(texture)
                pic.set_size_request(target_w, target_h)
                widget = pic
        else:
            try:
                texture = Gdk.Texture.new_from_filename(resolved_path)
                pic = Gtk.Picture()
                pic.set_paintable(texture)
                pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                widget = pic
            except Exception:
                widget = Gtk.Image.new_from_file(resolved_path)

    except Exception as e:
        app.warn(f"Could not load image '{src}': {e}")
        widget = Gtk.Image.new()

    app.apply_common_properties(widget, element.attrib)
    return widget