"""Version-locked full text, graphic-label and executable-literal build; no launch."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from localize import filehash, write_json
from executable_text import build_executable


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('build/full-zh-CN'))
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    game=args.game.resolve(strict=True); out=args.output.resolve()
    if out==game or out.is_relative_to(game):
        raise ValueError('Build output must be outside installed game')
    identity=json.loads((root/'assets/supported-build.json').read_text(encoding='utf-8'))
    assert filehash(game/'Dementium II.exe')==identity['exe_sha256']
    assert filehash(game/'rom.zar')==identity['rom_sha256']
    out.mkdir(parents=True,exist_ok=True)
    commands=[['tools/merge_locale.py',str(game/'rom.zar'),'locales/zh-CN',str(out/'text.json')],
              ['tools/localize.py','build',str(game/'rom.zar'),str(out/'text.json'),str(out),'--profile','locales/zh-CN/font-profile.json','--identity','assets/supported-build.json']]
    for command in commands:
        subprocess.run([sys.executable,'-X','utf8',*command],cwd=root,check=True)
    # Full-inventory gates, not screenshot-only spot checks. Failed audits stop
    # release generation and retain their per-record/per-image diagnostics.
    audits=[['tools/audit_text_layout.py','--archive',str(out/'rom.zar'),
             '--logical',str(out/'text.json'),'--output',str(out/'text-layout-audit.json')],
            ['tools/audit_image_alignment.py','--original',str(game/'rom.zar'),
             '--archive',str(out/'rom.zar'),'--output',str(out/'image-layout-audit.json')]]
    audits.append(['tools/audit_body_fallback.py','--archive',str(out/'rom.zar'),
                   '--report',str(out/'font-report.json'),'--logical',str(out/'text.json'),
                   '--output',str(out/'body-fallback-audit.json')])
    audits.append(['tools/audit_ui_corrections.py','--original',str(game/'rom.zar'),
                   '--archive',str(out/'rom.zar'),'--output',str(out/'ui-correction-audit.json')])
    for command in audits:
        subprocess.run([sys.executable,'-X','utf8',*command],cwd=root,check=True)
    recipe=json.loads((root/'locales/zh-CN/executable-text.json').read_text(encoding='utf-8'))
    original=(game/'Dementium II.exe').read_bytes()
    modified,delta=build_executable(original,recipe)
    from debug_menu import build_menu, make_patch
    modified,menu_report=build_menu(modified)
    delta=make_patch(original,modified)
    write_json(out/'debug-menu-report.json',menu_report)
    (out/'Dementium II.exe').write_bytes(modified)
    write_json(out/'exe-patch.json',delta)
    for path in game.iterdir():
        if path.is_file() and path.name not in ('rom.zar','Dementium II.exe'):
            shutil.copy2(path,out/path.name)
    (out/'steam_appid.txt').write_text(str(identity['appid'])+'\n',encoding='ascii')
    build=json.loads((out/'build-report.json').read_text(encoding='utf-8'))
    text=json.loads((out/'translation-report.json').read_text(encoding='utf-8'))
    images=json.loads((out/'image-report.json').read_text(encoding='utf-8')) if (out/'image-report.json').exists() else None
    fingerprints={}
    inputs=[root/'requirements.txt',root/'assets/supported-build.json',*(root/'tools').glob('*.py'),*(root/'locales/zh-CN').glob('*.json')]
    for path in sorted(inputs):
        fingerprints[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
    source_fingerprint=hashlib.sha256(json.dumps(fingerprints,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    write_json(out/'source-inputs.json',fingerprints)
    manifest=dict(schema=1,supported_build=identity,text=text,executable_labels=len(recipe['entries']),
                  graphics=images,modified_rom_sha256=build['modified_sha256'],modified_exe_sha256=filehash(out/'Dementium II.exe'),
                  patch_sha256=filehash(out/'patch.json'),exe_patch_sha256=filehash(out/'exe-patch.json'),
                  game_launch='NEVER',runtime_qa='PENDING',source_fingerprint=source_fingerprint)
    write_json(out/'release-manifest.json',manifest)
    print('FULL_BUILD records=%d translated=%d preserved=%d executable_labels=%d game_launch=NEVER result=PASS' %
          (text['total'],text['translated'],text['preserved'],len(recipe['entries'])))


if __name__=='__main__':main()
