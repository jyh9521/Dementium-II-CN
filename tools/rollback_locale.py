"""Restore both files into a separate directory, leaving the build unchanged."""
import argparse
import json
from pathlib import Path

from localize import apply_delta, digest
from executable_text import apply_executable_patch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.output.resolve()==args.build.resolve():raise ValueError('Rollback must use another output directory')
    args.output.mkdir(parents=True,exist_ok=True)
    hashes={}
    for filename,delta_name,apply in [('rom.zar','patch.json',apply_delta),('Dementium II.exe','exe-patch.json',apply_executable_patch)]:
        before=(args.build/filename).read_bytes()
        patch=json.loads((args.build/delta_name).read_text(encoding='utf-8'))
        restored=apply(before,patch,True)
        (args.output/filename).write_bytes(restored)
        assert (args.output/filename).read_bytes()==restored
        assert (args.build/filename).read_bytes()==before
        hashes[filename]=digest(restored)
    print('ROLLBACK_BUNDLE rom_sha256='+hashes['rom.zar']+' exe_sha256='+hashes['Dementium II.exe']+' modified_retained=YES result=PASS')


if __name__=='__main__':main()
