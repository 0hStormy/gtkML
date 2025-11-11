def nameSubmit(widget):
    app.nameLabel.set_text(f"Hello, {app.nameEntry.get_text()}!")

def cancel(widget):
    import sys
    sys.exit(0)

def showSource(widget):
    try:
        with open(app.ui_path, "r", encoding="utf-8") as f:
            sourceCode = f.read()
        buffer = app.sourceTextView.get_buffer()
        buffer.set_text(sourceCode)
    except Exception as e:
        app.warn(f"Could not open source file: {e}")
    buffer = app.sourceTextView.get_buffer()
    buffer.set_text(sourceCode)
