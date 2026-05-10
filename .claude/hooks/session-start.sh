#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Project pins Python 3.10. Use uv to manage the interpreter and venv.
PYTHON_VERSION="3.10"
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  uv venv --python "$PYTHON_VERSION" "$VENV_DIR"
fi

# Install runtime deps from requirements.txt and dev tools (ruff, mypy, pre-commit, pytest).
# Skip Windows-only entries from the rye lockfile (e.g. pywin32-ctypes) by installing
# from requirements.txt instead of requirements.lock.
uv pip install --python "$VENV_DIR/bin/python" -r requirements.txt
uv pip install --python "$VENV_DIR/bin/python" ruff mypy pre-commit pytest

# Persist venv on PATH so subsequent tool calls pick it up.
echo "export VIRTUAL_ENV=\"$CLAUDE_PROJECT_DIR/$VENV_DIR\"" >> "$CLAUDE_ENV_FILE"
echo "export PATH=\"$CLAUDE_PROJECT_DIR/$VENV_DIR/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
