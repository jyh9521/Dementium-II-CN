"""Keep a byte-exact previous ZIP as a small, streaming COPY/ADD rollback recipe."""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from archive_increment import binary_ops, canonical, identity, no_links

FORMAT = 'zip-copy-add-rollback-v1'
CHUNK = 1024 * 1024
MAX_CHANGED_MEMBER = 128 * CHUNK


def ranges(path):
    with zipfile.ZipFile(path) as archive:
        entries = sorted(archive.infolist(), key=lambda row: row.header_offset)
        if len({row.filename for row in entries}) != len(entries):
            raise ValueError('Duplicate ZIP members')
        return {row.filename: (row.header_offset,
                (entries[i+1].header_offset if i+1 < len(entries) else archive.start_dir)-row.header_offset)
                for i,row in enumerate(entries)}, archive.start_dir


def equal_range(source, target, a, b, length):
    source.seek(a); target.seek(b)
    while length:
        size = min(CHUNK, length)
        if source.read(size) != target.read(size): return False
        length -= size
    return True


def create(source, target, output, member_map=None):
    source, target, output = (no_links(Path(p)).resolve() for p in (source,target,output))
    if output.exists(): raise FileExistsError(output)
    before, previous = identity(source), identity(target)
    sr, _ = ranges(source); tr, tail = ranges(target)
    ops = []; member_map = member_map or {}
    def add(raw):
        if raw: ops.append(['add', base64.b64encode(raw).decode('ascii')])
    with source.open('rb') as src, target.open('rb') as old:
        cursor = 0
        for name,(offset,length) in sorted(tr.items(), key=lambda item: item[1][0]):
            old.seek(cursor); add(old.read(offset-cursor))
            candidate = sr.get(member_map.get(name,name))
            if candidate and candidate[1] == length and equal_range(src,old,candidate[0],offset,length):
                ops.append(['copy',candidate[0],length])
            else:
                if length > MAX_CHANGED_MEMBER or candidate and candidate[1] > MAX_CHANGED_MEMBER:
                    raise ValueError('Changed ZIP member exceeds bounded matching size: '+name)
                old.seek(offset); raw = old.read(length)
                if candidate:
                    src.seek(candidate[0]); current = src.read(candidate[1])
                    for op in binary_ops(current,raw,block=1024):
                        ops.append(['copy',candidate[0]+op[1],op[2]] if op[0]=='copy' else op)
                else: add(raw)
            cursor = offset+length
        old.seek(cursor); add(old.read())
    recipe = dict(schema=1,format=FORMAT,source=before,target=previous,operations=ops)
    if identity(source)!=before or identity(target)!=previous:
        raise ValueError('ZIP input changed during delta construction')
    with output.open('xb') as stream: stream.write(gzip.compress(canonical(recipe),mtime=0))
    return dict(**identity(output),source=before,target=previous,
                copied_bytes=sum(op[2] for op in ops if op[0]=='copy'))


def restore(source, delta, output):
    source, delta, output = (no_links(Path(p)).resolve() for p in (source,delta,output))
    if output.exists(): raise FileExistsError(output)
    with gzip.open(delta,'rb') as stream: raw=stream.read(64*CHUNK+1)
    if len(raw)>64*CHUNK: raise ValueError('Rollback recipe exceeds limit')
    recipe=json.loads(raw)
    if recipe.get('schema')!=1 or recipe.get('format')!=FORMAT: raise ValueError('Unknown ZIP rollback recipe')
    if identity(source)!=recipe['source']: raise ValueError('ZIP rollback source identity mismatch')
    target=recipe['target']
    if type(target.get('bytes')) is not int or target['bytes']<0: raise ValueError('Invalid rollback target size')
    total=0
    for op in recipe['operations']:
        if op[0]=='copy' and len(op)==3:
            a,n=op[1:]
            if type(a) is not int or type(n) is not int or a<0 or n<=0 or a+n>recipe['source']['bytes']:
                raise ValueError('Rollback COPY bounds')
            total+=n
        elif op[0]=='add' and len(op)==2: total+=len(base64.b64decode(op[1],validate=True))
        else: raise ValueError('Invalid rollback operation')
    if total!=target['bytes']: raise ValueError('Rollback target length mismatch')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.zip-rollback-',dir=output.parent) as directory:
        staging=Path(directory)/'restored.zip'; h=hashlib.sha256()
        with source.open('rb') as src, staging.open('xb') as dst:
            for op in recipe['operations']:
                if op[0]=='add':
                    data=base64.b64decode(op[1],validate=True); dst.write(data); h.update(data)
                else:
                    src.seek(op[1]); left=op[2]
                    while left:
                        data=src.read(min(left,CHUNK))
                        if not data: raise ValueError('ZIP source truncated during rollback')
                        dst.write(data); h.update(data); left-=len(data)
        if h.hexdigest()!=target['sha256'] or identity(staging)!=target:
            raise ValueError('Rollback target identity mismatch')
        if identity(source)!=recipe['source']: raise ValueError('ZIP source changed during rollback')
        if output.exists(): raise FileExistsError(output)
        # Hard-link publication is atomic and rejects an existing output on every OS.
        output.hardlink_to(staging)
    return dict(**identity(output),source_unchanged=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('create');p.add_argument('--source',type=Path,required=True);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--member-map',action='append',default=[])
    p=sub.add_parser('restore');p.add_argument('--source',type=Path,required=True);p.add_argument('--delta',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='create': result=create(args.source,args.target,args.output,dict(x.split('=',1) for x in args.member_map))
    else: result=restore(args.source,args.delta,args.output)
    print('ZIP_ROLLBACK_'+args.command.upper()+' '+json.dumps(result,sort_keys=True)+' result=PASS')


if __name__=='__main__':main()
