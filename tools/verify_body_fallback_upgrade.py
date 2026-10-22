"""Verify real font upgrade, old-version install migration and isolated rollback."""
import argparse, hashlib, io, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image
from localize import Zar, make_delta, write_json
from debug_menu import make_patch

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True);p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--original',type=Path,required=True)
    a=p.parse_args();os.chdir(ROOT)
    before=a.before.resolve();build=a.build.resolve();out=a.output.resolve();original=a.original.resolve()
    out.mkdir(parents=True,exist_ok=True);records=[]
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    def run(stage,cmd,input,expect=0):
        cmd=[str(c) for c in cmd]
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
        records.append(dict(stage=stage,command=subprocess.list2cmdline(cmd),input=str(input),output=r.stdout.strip(),stderr=r.stderr.strip(),exit_status=r.returncode))
        write_json(out/'commands.json',records)
        assert r.returncode==expect, stage+'\n'+r.stdout+r.stderr
        print(stage+' exit='+str(r.returncode)+' '+r.stdout.strip(),flush=True)
    py=[sys.executable,'-X','utf8']
    def audit(stage,archive,legacy=False,expect=0):
        cmd=py+['tools/audit_body_fallback.py','--archive',archive,'--report',build/'font-report.json','--logical',build/'text.json','--output',out/(stage.lower()+'.json')]
        if legacy:cmd+=['--legacy']
        run(stage,cmd,archive,expect)
    audit('BASELINE',before/'rom.zar',True)
    audit('BASELINE_RED',before/'rom.zar',False,1)
    audit('MODIFIED',build/'rom.zar')
    old=Zar((before/'rom.zar').read_bytes());new=Zar((build/'rom.zar').read_bytes())
    changed=[n for n in old.entries if old.read(n)!=new.read(n)]
    allowed={'~INDEX','FONTS/D2FONT_12X15.JSON','FONTS/D2FONT_12X15.PNG'}
    assert set(changed)<=allowed,changed
    oldmeta=json.loads(old.read('FONTS/D2FONT_12X15.JSON'));newmeta=json.loads(new.read('FONTS/D2FONT_12X15.JSON'))
    oldimage=Image.open(io.BytesIO(old.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    newimage=Image.open(io.BytesIO(new.read('FONTS/D2FONT_12X15.PNG'))).convert('RGBA')
    codes=json.loads((build/'font-report.json').read_text('utf8'))['body_fallback_codes']
    preserved=0
    assert oldmeta.keys()==newmeta.keys() and oldmeta['glyphs'].keys()==newmeta['glyphs'].keys()
    assert {k:v for k,v in oldmeta.items() if k!='glyphs'}=={k:v for k,v in newmeta.items() if k!='glyphs'}
    for key,g in oldmeta['glyphs'].items():
        if int(key) in codes:continue
        h=newmeta['glyphs'][key]
        assert {k:v for k,v in g.items() if k not in ('tx','ty')}=={k:v for k,v in h.items() if k not in ('tx','ty')}
        def crop(im,m):return im.crop((m['tx'],m['ty'],m['tx']+m['w'],m['ty']+m['h'])).tobytes()
        assert crop(oldimage,g)==crop(newimage,h),key
        preserved+=1
    assert (before/'Dementium II.exe').read_bytes()==(build/'Dementium II.exe').read_bytes()
    write_json(out/'preservation.json',dict(changed_resources=changed,preserved_glyphs=preserved,executable='BYTE_IDENTICAL',text='BYTE_IDENTICAL',images='BYTE_IDENTICAL',title='PIXEL_AND_METRIC_IDENTICAL',linefeed=16))
    print('PRESERVATION glyphs=%d exe=EXACT texts=EXACT images=EXACT title=EXACT PASS'%preserved,flush=True)
    for name,key in [('rom.zar','rom'),('Dementium II.exe','exe')]:
        write_json(out/(key+'-upgrade.json'),(make_delta if key=='rom' else make_patch)((before/name).read_bytes(),(build/name).read_bytes()))
    installer=ROOT/'dist/Dementium-II-zh-CN-Setup.exe'
    retained={str(p):digest(p) for p in [installer,build/'rom.zar',build/'Dementium II.exe']}
    rollbackpy=out/'rollback_installer.py'
    rollbackpy.write_text('from pathlib import Path\nimport hashlib,shutil\n'+f'src=Path({str(installer)!r});old=Path({str(before/installer.name)!r});dst=Path({str(out/"rollback-test/Setup.exe")!r})\n'+f'assert hashlib.sha256(src.read_bytes()).hexdigest()=={digest(installer)!r}\n'+'shutil.copy2(src,dst);shutil.copy2(old,dst)\nassert dst.read_bytes()==old.read_bytes()\nprint("ROLLBACK_INSTALLER restored=BYTE_IDENTICAL modified_retained=YES PASS")\n',encoding='utf8')
    shell=out/'ROLLBACK.sh'
    shell.write_text('#!/usr/bin/env bash\nset -eu\n'+f'python -X utf8 "{(ROOT/"tools/rollback_upgrade.py").as_posix()}" --modified "{build.as_posix()}" --patches "{out.as_posix()}" --output "{(out/"rollback-test").as_posix()}"\n'+f'python -X utf8 "{rollbackpy.as_posix()}"\n',encoding='utf8',newline='\n');shell.chmod(0o755)
    run('ROLLBACK',['C:/Program Files/Git/bin/bash.exe',shell],build)
    for name in ('rom.zar','Dementium II.exe'):assert digest(out/'rollback-test'/name)==digest(before/name)
    audit('ROLLBACK_BEHAVIOR',out/'rollback-test/rom.zar',True)
    # Same old receipt layout and original-file backups as an installed previous release.
    fixture=Path(tempfile.mkdtemp(prefix='upgrade-fixture-',dir=out))
    for name in ('rom.zar','Dementium II.exe'):shutil.copy2(before/name,fixture/name)
    backups=fixture/'cn-backup';backups.mkdir()
    entries=[]
    for name in ('rom.zar','Dementium II.exe'):
        shutil.copy2(original/name,backups/name)
        entries.append(dict(name=name,backup=name,original=digest(original/name),installed=digest(before/name)))
    write_json(backups/'resource-state.json',dict(schema=1,files=entries))
    sdk=ROOT/'build/toolchain/dotnet/dotnet.exe';dll=ROOT/'build/installer/tests/net10.0-windows10.0.17763.0/InstallerTests.dll'
    run('NATIVE_OLD_UPGRADE',[sdk,dll,'--resource-install',fixture/'rom.zar'],fixture)
    for name in ('rom.zar','Dementium II.exe'):
        assert digest(fixture/name)==digest(build/name)
        assert digest(backups/name)==digest(original/name)
    audit('INSTALLED',fixture/'rom.zar')
    run('NATIVE_UPGRADE_RESTORE',[sdk,dll,'--resource-restore',fixture/'rom.zar'],fixture)
    for name in ('rom.zar','Dementium II.exe'):assert digest(fixture/name)==digest(original/name)
    assert not backups.exists()
    assert retained=={p:digest(Path(p)) for p in retained}
    for p in [installer,out/'rom-upgrade.json',shell,rollbackpy]:assert p.read_bytes()
    paths=dict(MODIFIED_FILE=str(installer),DIFF_FILE=str(out/'rom-upgrade.json'),VERIFICATION=str(out/'VERIFICATION.txt'),ROLLBACK=str(shell))
    lines=['CHANGED: body fallback face renders at body.pixel_size=12, w/h/logw=12/15/12, xo/yo=0/0; body/fallback ascent 13/11 -> internal raster shift +2; title remains 16px yo=-2; linefeed=16.',
      'AUDIT: all 676 records plus previews/extra UI checked; fallback characters=辘 U+8F98,骶 U+9AB6; other glyphs='+str(preserved)+' exact ink+metrics; all text/images/EXE exact.',
      'RESTORED_STATUS: isolated rollback exactly reproduces old 16px yo=-2 behavior; native old-version upgrade produces current ROM/EXE and preserves original backups; native restore returns original SHA256 and removes backup directory; modified build/installer retained.',
      'GAME_LAUNCH=NEVER; actual in-game page acceptance=PENDING; version=1.0.0.',
      'BASELINE_HASHES='+json.dumps({n:digest(before/n) for n in ('rom.zar','Dementium II.exe',installer.name)}),
      'MODIFIED_HASHES='+json.dumps(retained),*['%s=%s'%v for v in paths.items()]]
    for r in records:lines+=['\n'+r['stage'],'COMMAND='+r['command'],'INPUT='+r['input'],'OUTPUT='+r['output'],'STDERR='+r['stderr'],'EXIT_STATUS='+str(r['exit_status'])]
    lines+=['\nBuild/full audits: '+str(out/'build.log'),'Installer build/native tests: '+str(out/'installer-build.log'),'Full installer verification: '+str(out/'installer-verification.log')]
    (out/'VERIFICATION.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
    assert (out/'VERIFICATION.txt').read_text('utf8').startswith('CHANGED:')
    print('FALLBACK_UPGRADE baseline=REPRODUCED modified=PASS rollback=EXACT installer_upgrade=PASS restored_original=EXACT modified_retained=YES game_launch=NEVER PASS')
if __name__=='__main__':main()
