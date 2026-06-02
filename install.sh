#!/bin/bash

ASKR_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/bin"
ASK_BIN="$BIN_DIR/ask"
ASKR_BIN="$BIN_DIR/askr"

mkdir -p "$BIN_DIR"

cat > "$ASK_BIN" <<EOF
#!/bin/bash
cd "\$PWD" && source "$ASKR_DIR/venv/bin/activate" && python "$ASKR_DIR/ask.py" "\$@"
EOF
chmod +x "$ASK_BIN"

cat > "$ASKR_BIN" <<EOF
#!/bin/bash
cd "\$PWD" && source "$ASKR_DIR/venv/bin/activate" && python -c "
import sys, os
sys.path.insert(0, '$ASKR_DIR')
from askr.cli.askr import main
main()
" "\$@"
EOF
chmod +x "$ASKR_BIN"

SHELL_RC="$HOME/.zshrc"
if ! grep -q '"$HOME/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_RC"
    echo "Added ~/bin to PATH in $SHELL_RC  - restart your shell or run: source $SHELL_RC"
fi

echo "askr installed  - ask for Q&A, askr for session management."
