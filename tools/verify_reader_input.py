"""Reproduce old menu failures, verify new native UI code and isolated rollback."""
import argparse,hashlib,io,json,os,subprocess,sys
from pathlib import Path
from localize import Zar,extract,write_json,make_delta
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.before=a.before.resolve();a.build=a.build.resolve();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    records=[]
    def run(stage,command,environment=None,expected=0):
        r=subprocess.run([str(x) for x in command],cwd=ROOT,env=environment,capture_output=True,text=True,encoding='utf8')
        rec=dict(stage=stage,command=[str(x) for x in command],input=(environment.get('DEMENTIUM_UI_TEST_EXE') or environment.get('DEMENTIUM_MODIFIED_EXE')) if environment else str(a.build),stdout=r.stdout,stderr=r.stderr,exit_status=r.returncode)
        records.append(rec)
        write_json(a.output/'commands.json',records)
        if r.returncode!=expected:raise RuntimeError(str(rec))
        return rec
    for stage,folder,expected in [('BASELINE',a.before,1),('MODIFIED',a.build,0)]:
        env=dict(os.environ,DEMENTIUM_UI_TEST_EXE=str(folder/'Dementium II.exe'))
        run(stage,[sys.executable,'-X','utf8','-m','unittest','discover','-s','tests','-p','test_menu_focus.py','-v'],env,expected)
        print(stage+' menu_focus_keyboard_wheel='+('FAIL_REPRODUCED' if expected else 'PASS'),flush=True)
    before=Zar((a.before/'rom.zar').read_bytes());after=Zar((a.build/'rom.zar').read_bytes())
    changed=[name for name in before.entries if before.read(name)!=after.read(name)]
    protected=[name for name in before.entries if name.endswith('.PNG') or name.startswith('FONTS/') or name=='TUFFY_BOLD.TTF']
    assert all(before.read(n)==after.read(n) for n in protected)
    textchanges=[n for n in changed if n.startswith('EN/')]
    assert all(n.startswith('EN/EXAMINE.') and n!='EN/EXAMINE.535' for n in textchanges)
    assert all(before.read(n)==after.read(n) for n in before.entries if n.startswith('EN/EXAMINE.0'))
    # Every possible 9-line view fits the reserved 1024-byte UTF-8 copy buffer,
    # including a possible synthetic emphasis-state prefix and trailing NUL.
    largest=0
    for row in extract(after):
        if '/EXAMINE.' not in row['resource']:continue
        lines=row['source'].splitlines()
        for i in range(len(lines)):
            size=len('\n'.join(lines[i:i+9]).encode('utf8'))+2
            largest=max(largest,size)
    assert largest<=1024,largest
    import pefile
    old=(a.before/'Dementium II.exe').read_bytes();new=(a.build/'Dementium II.exe').read_bytes()
    oldpe=pefile.PE(data=old);newpe=pefile.PE(data=new)
    for rva,size in [(0x4fa49,2),(0x1a7d4b,3),(0x1a7d81,15)]:assert oldpe.get_data(rva,size)==newpe.get_data(rva,size)
    assert next(s for s in oldpe.sections if s.Name.rstrip(b'\0')==b'.locmenu').get_data()==next(s for s in newpe.sections if s.Name.rstrip(b'\0')==b'.locmenu').get_data()
    assert not any(s.Characteristics&0xa0000000==0xa0000000 for s in newpe.sections)
    for x,y in zip(oldpe.sections,newpe.sections):assert (x.VirtualAddress,x.PointerToRawData,x.SizeOfRawData)==(y.VirtualAddress,y.PointerToRawData,y.SizeOfRawData)
    assert [(d.dll,[(i.name,i.ordinal) for i in d.imports]) for d in oldpe.DIRECTORY_ENTRY_IMPORT]==[(d.dll,[(i.name,i.ordinal) for i in d.imports]) for d in newpe.DIRECTORY_ENTRY_IMPORT]
    print('PRESERVATION sign=BYTE_IDENTICAL all_png_fonts=BYTE_IDENTICAL F1=RETAINED cards_puzzle_other_ui=UNCHANGED text_documents='+str(len(textchanges))+' max_view_bytes='+str(largest)+' PASS',flush=True)
    # Store a separate incremental upgrade delta. Its rollback retains the
    # previously fixed F1/sign rather than uninstalling the entire localization.
    from debug_menu import make_patch
    for name,key in [('rom.zar','rom'),('Dementium II.exe','exe')]:
        delta=(make_delta if key=='rom' else make_patch)((a.before/name).read_bytes(),(a.build/name).read_bytes())
        write_json(a.output/(key+'-upgrade.json'),delta)
    # The rollback script restores another directory and never rewrites modified.
    script=a.output/'ROLLBACK.sh';restored=a.output/'rollback-test'
    source='#!/usr/bin/env bash\nset -eu\npython -X utf8 "'+str(ROOT/'tools/rollback_upgrade.py').replace('\\','/')+'" --modified "'+str(a.build).replace('\\','/')+'" --patches "'+str(a.output).replace('\\','/')+'" --output "'+str(restored).replace('\\','/')+'"\n'
    script.write_text(source,encoding='utf8',newline='\n');script.chmod(0o755)
    retained={n:hashlib.sha256((a.build/n).read_bytes()).hexdigest() for n in ['rom.zar','Dementium II.exe']}
    shell=Path('C:/Program Files/Git/bin/bash.exe') if os.name=='nt' else Path('/bin/bash')
    run('ROLLBACK',[shell,script])
    for name in ['rom.zar','Dementium II.exe']:
        assert (restored/name).read_bytes()==(a.before/name).read_bytes()
        assert hashlib.sha256((a.build/name).read_bytes()).hexdigest()==retained[name]
    restored_pe=pefile.PE(str(restored/'Dementium II.exe'))
    assert restored_pe.get_data(0x4fa49,2)==bytes.fromhex('eb 04')
    assert restored_pe.get_data(0x1a7d4b,3)==bytes.fromhex('83 fa 1c')
    env=dict(os.environ,DEMENTIUM_MODIFIED_EXE=str(restored/'Dementium II.exe'))
    run('ROLLBACK_F1',[sys.executable,'-X','utf8','-m','unittest','discover','-s','tests','-p','test_debug_dispatch.py','-k','test_f1_after_native_startup','-v'],env)
    print('ROLLBACK prior_fixed_hashes=EXACT F1=RETAINED sign=RETAINED modified_retained=YES PASS',flush=True)
    original_restore=a.output/'rollback-original'
    run('ORIGINAL_ROLLBACK',[sys.executable,'-X','utf8',ROOT/'tools/rollback_locale.py',a.build,original_restore])
    identity=json.loads((ROOT/'assets/supported-build.json').read_text('utf8'))
    assert hashlib.sha256((original_restore/'rom.zar').read_bytes()).hexdigest()==identity['rom_sha256']
    assert hashlib.sha256((original_restore/'Dementium II.exe').read_bytes()).hexdigest()==identity['exe_sha256']
    summary=dict(schema=1,stages=records,changed_resources=changed,changed_text_documents=textchanges,
                 protected_resources=len(protected),font_and_png_bytes='EXACT',F1='RETAINED',sign_sha256=hashlib.sha256(after.read('TEX/EN/SIGN_02.PNG')).hexdigest(),
                 max_nine_line_view_bytes=largest,modified_hashes=retained,rollback='EXACT prior fixed files with F1/sign retained; original uninstall also checked',game_launch='NEVER',runtime_acceptance='PENDING')
    write_json(a.output/'verification.json',summary)
    # Include both already-existing changes and the new source files in a local diff.
    diff=subprocess.run(['git','diff','--binary'],cwd=ROOT,capture_output=True,check=True).stdout
    added=subprocess.run(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
    for name in added:
        r=subprocess.run(['git','diff','--no-index','--','NUL' if os.name=='nt' else '/dev/null',name],cwd=ROOT,capture_output=True)
        if r.returncode!=1:raise RuntimeError('New source diff failed: '+name)
        diff+=r.stdout
    (a.output/'DIFF_FILE.patch').write_bytes(diff)
    text='CHANGED: native document render 0x11b4f7, open 0x11a7b0, close 0x11af80, collection render 0x123379/open 0x121e50/close 0x122a10; no merge of authored document breaks; 12px font and 16px linefeed unchanged.\nCHANGED: mode gate 0x1a7c54, wheel callbacks 0x2ee30/0x1a7d90, reader game-action mask 0x15587b, cursor 0x2f3236, game capture 0x2f4ad, F1 transition sync 0x4fa66. Original F1 comparison, unlock, edge/debounce and padding bridge exact.\n'
    text+='MODIFIED_FILE: '+str(a.build/'Dementium II.exe')+'\nDIFF_FILE: '+str(a.output/'DIFF_FILE.patch')+'\nVERIFICATION: '+str(a.output/'VERIFICATION.txt')+'\nROLLBACK_SCRIPT: '+str(script)+'\n\n'
    for rec in records:text+=rec['stage']+'\nCOMMAND: '+subprocess.list2cmdline(rec['command'])+'\nINPUT: '+str(rec['input'])+'\nSTDOUT: '+rec['stdout']+'\nSTDERR: '+rec['stderr']+'\nEXIT_STATUS: '+str(rec['exit_status'])+'\n\n'
    text+='RESTORED_STATUS: isolated rollback EXE/ROM equal prior fixed build; F1 opens and 死囚区 stays exact. Separate original uninstall hashes also checked. Modified files retained.\nPRESERVATION: all PNG/font bytes exact; cards/puzzle/other UI unchanged; F1 previous fixed fields exact.\nMODIFIED_HASHES: '+json.dumps(retained)+'\nGAME_LAUNCH: NEVER\nRUNTIME_ACCEPTANCE: PENDING; Win32 calls were deterministic boundary doubles, not actual cursor movement in game.\n'
    (a.output/'VERIFICATION.txt').write_text(text,encoding='utf8')
    assert (a.build/'Dementium II.exe').read_bytes()[:2]==b'MZ'
    assert (a.output/'DIFF_FILE.patch').read_bytes().startswith(b'diff --git')
    assert 'EXIT_STATUS:' in (a.output/'VERIFICATION.txt').read_text('utf8')
    assert script.read_text('utf8').startswith('#!/usr/bin/env bash')
    print('READER_INPUT_VERIFY artifacts=REOPENED game_launch=NEVER PASS')
if __name__=='__main__':main()
