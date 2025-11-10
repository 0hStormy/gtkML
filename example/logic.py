def nameSubmit(widget):
    app.nameLabel.set_text(f"Hello, {app.nameEntry.get_text()}!")

def cancel(widget):
    import sys
    sys.exit(0)

def showSource(widget):
    with open("ui.gtkm", "r") as f:
        sourceCode = f.read()
    buffer = app.sourceTextView.get_buffer()
    buffer.set_text(sourceCode)
