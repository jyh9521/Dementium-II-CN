"""Build a small native Windows GUI with embedded sparse deltas, never game files."""
import argparse
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import struct
from build_resource_payload import write_payload


def verify_version(root):
    policy=json.loads((root/'assets/release-policy.json').read_text(encoding='utf-8'))
    source=(root/'installer/AssemblyInfo.cs').read_text(encoding='utf-8')
    version=policy['installer_version']
    expected={'AssemblyVersion':version+'.0','AssemblyFileVersion':version,'AssemblyInformationalVersion':version}
    for field,value in expected.items():
        match=re.search(r'\b'+field+r'\("([^"]+)"\)',source)
        if not match or match.group(1)!=value:
            raise ValueError('Installer version differs from explicit release policy: '+field)
    window=(root/'installer/MaterialWindow.xaml').read_text(encoding='utf-8')
    title=re.search(r'\bTitle="([^"]+)"',window)
    if not title or not title.group(1).endswith(' v'+version):
        raise ValueError('Installer version differs from visible window title')
    code=(root/'installer/MaterialWindow.xaml.cs').read_text(encoding='utf-8')
    footer=re.search(r'BuildLabel\.Text\s*=([^;]+);',code)
    if not footer or (' · v'+version+'"') not in footer.group(1):
        raise ValueError('Installer version differs from visible build footer')
    return version


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=Path('build/full-zh-CN'))
    p.add_argument('--output',type=Path,default=Path('dist/Dementium-II-zh-CN-Setup.exe'))
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    version=verify_version(root)
    work=root/'build/installer';work.mkdir(parents=True,exist_ok=True)
    compiler=Path(os.environ.get('DOTNET_EXE',str(root/'build/toolchain/dotnet/dotnet.exe')))
    if not compiler.is_file():raise FileNotFoundError('Set DOTNET_EXE to a .NET 10 SDK dotnet.exe')
    inputs={'assets/release-policy.json':hashlib.sha256((root/'assets/release-policy.json').read_bytes()).hexdigest()}
    identity=json.loads((root/'assets/supported-build.json').read_text(encoding='utf-8'))
    for src,name in [(a.build/'patch.json','patch.rom.gz'),(a.build/'exe-patch.json','patch.exe.gz')]:
        raw=src.read_text(encoding='utf-8').encode('utf-8');target=work/name
        delta=json.loads(raw);component='rom' if name=='patch.rom.gz' else 'exe'
        if (delta['original_sha256'],delta['original_size'])!=(identity[component+'_sha256'],identity[component+'_size']):
            raise ValueError('Installer payload differs from supported build identity')
        if len(raw)>64*1024*1024:raise ValueError('Installer delta JSON exceeds loader bound')
        target.write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
        inputs[str(src)]=hashlib.sha256(raw).hexdigest()
    locale=root/'locales/zh-CN/installer.json'
    inputs['resource-patches.json']=write_payload(a.build,root/'locales/zh-CN/executable-text.json',work/'resource-patches.gz')
    if json.loads(locale.read_text(encoding='utf-8')).get('build_label')!='2026 build '+identity['buildid']:
        raise ValueError('Installer build label differs from supported source identity')
    for src in [locale,root/'installer/app.manifest',*(root/'installer').glob('*.cs')]:
        inputs[src.relative_to(root).as_posix()]=hashlib.sha256(src.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
    for src in [*(root/'installer').glob('*.xaml'),*(root/'installer').glob('*.csproj'),*(root/'installer').glob('*.props'),*(root/'installer').glob('*.json'),*(root/'installer/licenses').glob('*.txt'),*(root/'installer/branding').glob('*')]:
        inputs[src.relative_to(root).as_posix()]=hashlib.sha256(src.read_bytes()).hexdigest()
    a.output=a.output.resolve();a.output.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    publish=work/'publish'
    subprocess.run([str(compiler),'publish',str(root/'installer/Installer.csproj'),'-c','Release','-p:RestoreLockedMode=true','-o',str(publish)],check=True,cwd=root,env=env)
    subprocess.run([str(compiler),'build',str(root/'installer/Tests.csproj'),'-c','Release'],check=True,cwd=root,env=env)
    subprocess.run([str(compiler),str(work/'tests/net10.0-windows10.0.17763.0/InstallerTests.dll'),str(work/'build-smoke-fixtures')],check=True,cwd=root,env=env)
    import shutil
    shutil.copyfile(publish/'Dementium-II-zh-CN-Setup.exe',a.output)
    # Preserve the separately validated startup compatibility in source builds.
    # This only changes this installer apphost, never system or game settings.
    import pefile
    pe=pefile.PE(str(a.output))
    cet=[entry.struct for entry in pe.DIRECTORY_ENTRY_DEBUG if entry.struct.Type==20]
    if len(cet)!=1 or cet[0].SizeOfData<4:
        raise ValueError('Installer extended DLL characteristics missing or ambiguous')
    cet_flags=struct.unpack_from('<I',a.output.read_bytes(),cet[0].PointerToRawData)[0]
    if cet_flags & 1:
        raise ValueError('Installer CET compatibility setting was not applied by SDK')
    pe.close()
    info=dict(installer=str(a.output),installer_version=version,size=a.output.stat().st_size,sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),
              input_hashes=inputs,contains_full_game_files=False,requires_python=False,architecture='Windows x64',
              framework='.NET 10 self-contained WPF; no separately installed runtime required',material_design='MaterialDesignThemes 5.3.2 / Material Design 3',compiler=str(compiler),game_launch='NEVER',cet_compat=False)
    (work/'build-report.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    print('MATERIAL_INSTALLER bytes=%d sha256=%s full_game_files=NONE python=NOT_REQUIRED result=PASS'%(info['size'],info['sha256']))


if __name__=='__main__':main()
