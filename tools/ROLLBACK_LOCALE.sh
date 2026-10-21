#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python -X utf8 "$ROOT/tools/localize.py" patch "$ROOT/build/zh-CN/rom.zar" "$ROOT/build/zh-CN/patch.json" "$ROOT/build/zh-CN/rollback-shell/rom.zar" --reverse
