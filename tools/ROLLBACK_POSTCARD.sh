#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python -X utf8 "$ROOT/tools/localize.py" patch "$ROOT/build/postcard-fix/rom.zar" "$ROOT/build/postcard-fix/patch.json" "$ROOT/build/postcard-fix/rollback-shell/rom.zar" --reverse
