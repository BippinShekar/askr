#!/bin/bash
set -euo pipefail

ASKR_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/bin"
ASK_BIN="$BIN_DIR/ask"
ASKR_BIN="$BIN_DIR/askr"

fail() { echo "✗ $1" >&2; exit 1; }

# --- Preflight ---------------------------------------------------------

# Stock macOS ships /usr/bin/python3 at 3.9 — askr needs 3.10+ (uses `X | Y`
# union type syntax). Search candidates rather than assuming `python3`
# resolves to a new-enough interpreter; prefer the highest version found.
PYTHON=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
    command -v "$cand" >/dev/null 2>&1 || continue
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PYTHON="$cand"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    fail "no Python 3.10+ found (checked python3.13/3.12/3.11/3.10/python3). Install one, e.g. \`brew install python@3.11\`, and re-run."
fi

PY_VERSION=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "Using $PYTHON ($PY_VERSION)"

[ "$(uname -s)" = "Darwin" ] || echo "⚠ askr's daemon (launchd, caffeinate, Terminal.app spawn) is macOS-only — session orchestration will not work on $(uname -s). The ask/askr CLIs will still work."

mkdir -p "$BIN_DIR"

# --- venv + dependencies ------------------------------------------------

if [ ! -f "$ASKR_DIR/venv/bin/python" ]; then
    echo "Creating venv..."
    "$PYTHON" -m venv "$ASKR_DIR/venv" || fail "venv creation failed."
fi

echo "Installing dependencies..."
if ! "$ASKR_DIR/venv/bin/pip" install -q -r "$ASKR_DIR/requirements.txt"; then
    fail "pip install failed — check network access and requirements.txt, then re-run."
fi

# --- Wrapper scripts ------------------------------------------------------

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

# --- Smoke test -----------------------------------------------------------

if ! "$ASKR_DIR/venv/bin/python" -c "import anthropic, openai, dotenv, pathspec, rich, certifi" 2>/dev/null; then
    fail "dependency import check failed after install — venv may be corrupt. Try: rm -rf '$ASKR_DIR/venv' && re-run this script."
fi

# --- PATH setup (bash and zsh both, whichever rc files exist or match \$SHELL) ---

PATH_LINE='export PATH="$HOME/bin:$PATH"'
RC_FILES=()
case "$(basename "${SHELL:-}")" in
    zsh)  RC_FILES+=("$HOME/.zshrc") ;;
    bash) RC_FILES+=("$HOME/.bashrc" "$HOME/.bash_profile") ;;
    *)    RC_FILES+=("$HOME/.zshrc" "$HOME/.bashrc") ;;
esac

UPDATED_RC=()
for rc in "${RC_FILES[@]}"; do
    [ -f "$rc" ] || continue
    if ! grep -qF 'bin:$PATH' "$rc" 2>/dev/null; then
        echo "$PATH_LINE" >> "$rc"
        UPDATED_RC+=("$rc")
    fi
done

if [ "${#UPDATED_RC[@]}" -gt 0 ]; then
    echo "Added ~/bin to PATH in: ${UPDATED_RC[*]} — restart your shell or run: source ${UPDATED_RC[0]}"
fi

echo "✓ askr installed — ask for Q&A, askr for session management."
