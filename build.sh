#!/usr/bin/env bash
set -e

APP_NAME="gtkml"
ENTRY="main.py"
OUTPUT_DIR="dist"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$BASE_DIR/.venv"

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

pip install --upgrade pip setuptools wheel
pip install nuitka pycairo PyGObject

export NUITKA_FORCE_DATA_FILES=1

DATA_ARGS=""

add_dir_recursive() {
    SRC="$1"
    DEST="$2"
    if [ -d "$SRC" ]; then
        while IFS= read -r -d '' file; do
            relpath="${file#$SRC/}"
            DATA_ARGS="$DATA_ARGS --include-data-file=$file=$DEST/$relpath"
        done < <(find "$SRC" -type f -print0)
    fi
}

add_dir_recursive "$BASE_DIR/widgets" "widgets"
add_dir_recursive "$BASE_DIR/assets" "assets"
add_dir_recursive "$BASE_DIR/example" "example"

NUITKA_OPTIMIZATION_LEVEL=3 python3 -m nuitka \
    --onefile \
    --follow-imports \
    --remove-output \
    --lto=no \
    --no-pyi-file \
    --python-flag=no_docstrings \
    --assume-yes-for-downloads \
    --nofollow-import-to=tests,unittest \
    --noinclude-default-mode=error \
    --output-dir="$OUTPUT_DIR" \
    --output-filename="$APP_NAME" \
    $DATA_ARGS \
    "$ENTRY"

echo
echo "Build complete: $OUTPUT_DIR/$APP_NAME"
