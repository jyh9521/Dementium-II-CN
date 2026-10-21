"""Build a small native Windows GUI with embedded sparse deltas, never game files."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=Path('build/full-zh-CN'))
    p.add_argument('--output',type=Path,default=Path('dist/Dementium-II-zh-CN-Setup.exe'))
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    work=root/'build/installer';work.mkdir(parents=True,exist_ok=True)
    compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not compiler.is_file():raise FileNotFoundError('Windows .NET Framework C# compiler is required')
    resources=[];inputs={}
    identity=json.loads((root/'assets/supported-build.json').read_text(encoding='utf-8'))
    for src,name in [(a.build/'patch.json','patch.rom.gz'),(a.build/'exe-patch.json','patch.exe.gz')]:
        raw=src.read_text(encoding='utf-8').encode('utf-8');target=work/name
        delta=json.loads(raw);component='rom' if name=='patch.rom.gz' else 'exe'
        if (delta['original_sha256'],delta['original_size'])!=(identity[component+'_sha256'],identity[component+'_size']):
            raise ValueError('Installer payload differs from supported build identity')
        if len(raw)>64*1024*1024:raise ValueError('Installer delta JSON exceeds loader bound')
        target.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0));resources.append('/resource:'+str(target)+','+name)
        inputs[str(src)]=hashlib.sha256(raw).hexdigest()
    locale=root/'locales/zh-CN/installer.json';resources.append('/resource:'+str(locale)+',installer.json')
    for src in [locale,root/'installer/app.manifest',*(root/'installer').glob('*.cs')]:
        inputs[src.relative_to(root).as_posix()]=hashlib.sha256(src.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
    common=[str(compiler),'/nologo','/codepage:65001','/platform:x64','/optimize+',
            '/r:System.dll','/r:System.Core.dll','/r:System.Web.Extensions.dll',*resources]
    a.output=a.output.resolve();a.output.parent.mkdir(parents=True,exist_ok=True)
    engine=root/'installer/InstallerEngine.cs'
    commands=[common+['/target:winexe','/r:System.Windows.Forms.dll','/r:System.Drawing.dll',
        '/win32manifest:'+str(root/'installer/app.manifest'),'/out:'+str(a.output),str(engine),str(root/'installer/InstallerForm.cs'),str(root/'installer/AssemblyInfo.cs')],
        common+['/target:exe','/out:'+str(work/'InstallerTests.exe'),str(engine),str(root/'installer/InstallerTests.cs')]]
    for command in commands:subprocess.run(command,check=True,cwd=root)
    info=dict(installer=str(a.output),size=a.output.stat().st_size,sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),
              input_hashes=inputs,contains_full_game_files=False,requires_python=False,architecture='Windows x64',
              framework='.NET Framework 4.8 (Windows 10/11 system component)',compiler=str(compiler),game_launch='NEVER')
    (work/'build-report.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    print('GUI_INSTALLER bytes=%d sha256=%s full_game_files=NONE python=NOT_REQUIRED result=PASS'%(info['size'],info['sha256']))


if __name__=='__main__':main()
