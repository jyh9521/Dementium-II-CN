#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
"${PYTHON_BIN:-python}" -X utf8 "$ROOT/tools/localize.py" patch \
  "$ROOT/build/smoke/rom.zar" "$ROOT/build/smoke/patch.json" \
  "$ROOT/build/rollback-shell/rom.zar" --reverse
