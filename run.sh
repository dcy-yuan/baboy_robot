#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON=python3
[ -f "$SCRIPT_DIR/venv/bin/python" ] && PYTHON="$SCRIPT_DIR/venv/bin/python"
$PYTHON -m src.main "$@"
