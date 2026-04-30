#!/bin/bash

ASKR_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/bin"
TARGET="$BIN_DIR/ask"

mkdir -p "$BIN_DIR"

cat > "$TARGET" <<EOF
#!/bin/bash
cd "\$PWD" && source "$ASKR_DIR/venv/bin/activate" && python "$ASKR_DIR/ask.py" "\$@"
EOF

chmod +x "$TARGET"

SHELL_RC="$HOME/.zshrc"
if ! grep -q '"$HOME/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_RC"
    echo "Added ~/bin to PATH in $SHELL_RC — restart your shell or run: source $SHELL_RC"
fi

echo "askr installed — type 'ask \"your question\"' from any directory."
