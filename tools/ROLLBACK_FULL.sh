#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python -X utf8 "$ROOT/tools/rollback_locale.py" "$ROOT/build/full-zh-CN" "$ROOT/build/full-zh-CN/rollback-shell"
