"""Reverse a hash-guarded two-component upgrade into a separate directory."""
import argparse,json
from pathlib import Path
from localize import apply_delta,digest
from executable_text import apply_executable_patch

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--modified',type=Path,required=True);p.add_argument('--patches',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve() in (a.modified.resolve(),a.patches.resolve()):raise ValueError('Rollback requires another output directory')
    a.output.mkdir(parents=True,exist_ok=True);hashes={}
    for name,key in [('rom.zar','rom'),('Dementium II.exe','exe')]:
        current=(a.modified/name).read_bytes();delta=json.loads((a.patches/(key+'-upgrade.json')).read_text('utf8'))
        restored=(apply_delta if key=='rom' else apply_executable_patch)(current,delta,True);target=a.output/name;target.write_bytes(restored)
        assert target.read_bytes()==restored and (a.modified/name).read_bytes()==current
        hashes[key]=digest(restored)
    print('ROLLBACK_UPGRADE rom_sha256='+hashes['rom']+' exe_sha256='+hashes['exe']+' prior_fixed_version=EXACT modified_retained=YES PASS')
if __name__=='__main__':main()
