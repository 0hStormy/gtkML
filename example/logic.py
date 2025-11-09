def nameSubmit(widget):
    app.nameLabel.set_text(f"Hello, {app.nameEntry.get_text()}!")

def cancel(widget):
    import sys
    sys.exit(0)