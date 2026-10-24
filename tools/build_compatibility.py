"""Rebuild one verified compatibility native recipe using current locale labels."""
import argparse
import gzip
import json
from pathlib import Path
from build_resource_payload import native_executable_payload, native_hash_guards, make_payload, add_compatibility
from debug_menu import build_menu, make_patch
from executable_text import build_executable
from localize import digest

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable',type=Path,required=True)
    parser.add_argument('--build-id',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resource-build',type=Path,help='Verified current resource build, required for 26123896')
    args=parser.parse_args()
    identity=json.loads((ROOT/'assets/supported-builds'/f'{args.build_id}.json').read_text('utf-8'))
    original=args.executable.read_bytes()
    if len(original)!=identity['exe_size'] or digest(original)!=identity['exe_sha256']:
        raise ValueError('Compatibility executable identity mismatch; writes=NONE')
    legacy=ROOT/'build/installer/old-v1.0/resource-patches.gz'
    raw=legacy.read_bytes()
    from import_legacy_installer import RESOURCE_HASH
    if digest(raw)!=RESOURCE_HASH:raise ValueError('Legacy resource recipe identity mismatch')
    payload=json.loads(gzip.decompress(raw))
    if args.build_id == '26099941':
        if payload['native_executable']['source_sha256']!=identity['exe_sha256']:
            raise ValueError('Compatibility recipe source mismatch')
    elif args.build_id == '26123896':
        if args.resource_build is None:
            raise ValueError('26123896 requires --resource-build from the current verified resource build')
        compatibility=json.loads((ROOT/'assets/compatibility-payloads.json').read_text('utf-8'))
        item=next(p for p in compatibility['payloads'] if p['buildid']=='26099941')
        raw=(ROOT/item['path']).read_bytes()
        if digest(raw)!=item['sha256']:
            raise ValueError('Compatibility payload identity mismatch')
        previous=json.loads(gzip.decompress(raw))
        payload=make_payload(args.resource_build,ROOT/'locales/zh-CN/builds'/f'{args.build_id}-executable-text.json',include_native=False)
    else:
        raise ValueError('Unsupported compatibility build')
    recipe=json.loads((ROOT/'locales/zh-CN/builds'/f'{args.build_id}-executable-text.json').read_text('utf-8'))
    literal,_=build_executable(original,recipe)
    modified,report=build_menu(literal)
    patch=make_patch(original,modified)
    work=ROOT/'build/compatibility'/args.build_id
    work.mkdir(parents=True,exist_ok=True)
    (work/'Dementium II.exe').write_bytes(modified)
    payload['native_executable']=native_executable_payload(work,patch,identity)
    payload['native_executable']['hash_guards']=native_hash_guards(original,modified)
    if args.build_id == '26123896':
        add_compatibility(payload,previous)
    (work/'exe-patch.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8')
    (work/'debug-menu-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    output=gzip.compress(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8'),compresslevel=9,mtime=0)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(output)
    assert args.output.read_bytes()==output
    print(f'COMPATIBILITY build={args.build_id} sha256={digest(output)} native_sha256={digest(modified)} game_launch=NEVER result=PASS')

if __name__=='__main__':main()
