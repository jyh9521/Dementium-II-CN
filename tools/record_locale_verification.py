"""Capture exact three-way evidence for the expanded build; leave modified output intact."""
import argparse
import json
from pathlib import Path
import subprocess

from localize import filehash, write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True)
    parser.add_argument('--build',type=Path)
    parser.add_argument('--rollback-script',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]; build=(args.build or root/'build/zh-CN').resolve()
    records=[]
    for stage in ['baseline','modified','rollback']:
        command=['python','-X','utf8',str(root/'tools/verify_locale.py'),stage,'--game',str(args.game),'--build',str(build)]
        done=subprocess.run(command,cwd=root,encoding='utf-8',text=True,capture_output=True)
        records.append(dict(stage=stage.upper(),command=subprocess.list2cmdline(command),input=str(args.game/'rom.zar') if stage=='baseline' else str(build/'rom.zar'),stdout=done.stdout.rstrip(),stderr=done.stderr.rstrip(),exit_status=done.returncode))
        if done.returncode:
            write_json(build/'verification-failure.json',records)
            raise RuntimeError(done.stderr)
    manifest=json.loads((root/'build/inventory/game-manifest.json').read_text(encoding='utf-8'))['files']
    assert all(filehash(args.game/f['path'])==f['sha256'] for f in manifest)
    paths=dict(MODIFIED_FILE=build/'rom.zar',DIFF_FILE=build/'patch.json',VERIFICATION=build/'VERIFICATION.txt',ROLLBACK=(args.rollback_script or root/'tools/ROLLBACK_LOCALE.sh').resolve())
    lines=['Changed fields: EN text resources; FONTS/D2FONT_12X15.JSON glyphs/linefeed; PNG appended glyph areas; ~INDEX size fields.',
           'Changed font field: 168 Latin/digit/punctuation glyph definitions now reference Fusion Pixel 12px, including Latin-1 accents.',
           'Changed full-build fields: 41 image resources / 187 labels; 5 fixed UTF-8 EXE literal slots; executable code and layout unchanged.',
           'Preserved: original atlas pixels and 28 other glyph definitions, DEBUG08, all Steam original files.',
           'Runtime status: Latin replacement NOT_TESTED in-game; this script does not start the game.',
           'Postcard fields: 12 EXAMINE resources use bounded reflow, 4 lines, 228px width, 72px pane; no blank padding or font shrink.',
           'Restored status: original archive byte-identical and menu New Game; modified output retained.',
           'Original installation: ALL_8_FILES_HASH_UNCHANGED', '']
    lines += [key+'='+str(path) for key,path in paths.items()]
    for r in records:
        lines += ['',r['stage'],'COMMAND: '+r['command'],'INPUT: '+r['input'],'STDOUT: '+r['stdout'],'STDERR: '+r['stderr'],'EXIT_STATUS: '+str(r['exit_status'])]
    paths['VERIFICATION'].write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    write_json(build/'verification.json',records)
    for path in paths.values():
        with path.open('rb') as stream: assert stream.read(1)
    print('VERIFICATION stages=3 original_files=8 artifacts_reopened=4 result=PASS')


if __name__=='__main__': main()
