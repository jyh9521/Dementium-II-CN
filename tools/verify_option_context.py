"""Verify actual native OPTIONSNEW loader -> context getter without game launch."""
import argparse,json
from pathlib import Path
from replay_option_loader import replay_bytes


def labels(exe,rom):
    result=replay_bytes(exe,rom)
    return {key:result[key] for key in ('head_bob','minimap')}


def main():
    p=argparse.ArgumentParser();p.add_argument('game',type=Path);a=p.parse_args()
    loaded=replay_bytes((a.game/'Dementium II.exe').read_bytes(),(a.game/'rom.zar').read_bytes())
    result={key:loaded[key] for key in ('head_bob','minimap')}
    ok=(result=={'head_bob':['普通','轻微','关闭'],'minimap':['关','半透明','不透明']}
        and loaded['loader_rows']==loaded['resource_rows']==loaded['native_table_capacity']
        and loaded['backing_buffer_is_after_rows']
        and loaded['settings_preserved'])
    print('OPTION_CONTEXT '+json.dumps(result,ensure_ascii=False,separators=(',',':'))+' result='+('PASS' if ok else 'FAIL'))
    return int(not ok)

if __name__=='__main__':raise SystemExit(main())
