"""Locale-neutral native context literals; fixed-capacity table layouts stay intact."""
import json,os,struct
from pathlib import Path
import pefile
from native_profile import active_build
from native_patch import assemble,jump
ROOT=Path(__file__).resolve().parents[1]
# These are the already-normalized HEAD BOB getter branches of each shipped PE.
_PROFILES={
 '26123896':(0x1252ca,0x1252d2,0x41aa90),
 '26152271':(0x12566a,0x125672,0x41cd00),
 '26260428':(0x12b6fa,0x12b702,0x440a80),
 '26286386':(0x12b6da,0x12b6e2,0x440a70),
}

def configured_literals():
    if active_build()=='26099941':return {}
    path=ROOT/'locales'/os.environ.get('DEMENTIUM_LOCALE','zh-CN')/'executable-text.json'
    config=json.loads(path.read_text(encoding='utf8')).get('context_literals',{})
    if not config:return {}
    if set(config)!={'head_bob'} or set(config['head_bob'])!={'1','2'}:
        raise ValueError('Unknown/incomplete native context literal configuration')
    for value in config['head_bob'].values():
        if not isinstance(value,str) or not value or any(c in value for c in '\0\r\n') or len(value.encode('utf8'))>128:
            raise ValueError('Invalid native context literal')
    return config


def patch_context_literals(data,pointers):
    if not pointers:return data,{'contexts':0}
    build=active_build()
    if build not in _PROFILES:raise ValueError('Unknown native context getter profile')
    hook,rejoin,indices=_PROFILES[build]
    pe=pefile.PE(data=data);base=pe.OPTIONAL_HEADER.ImageBase;out=bytearray(data)
    expected=bytes.fromhex('49 63 8c 83')+struct.pack('<I',indices)
    source=pe.get_offset_from_rva(hook)
    if out[source:source+8]!=expected:raise ValueError('Context getter source guard mismatch')
    # Index-array values remain the shipped [16,41,18]; no table slot is repurposed.
    if pe.get_data(indices,12)!=struct.pack('<III',16,41,18):
        raise ValueError('Context getter index table guard mismatch')
    section=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.locui')
    if section.Characteristics!=0x60000020:raise ValueError('Context code section permissions differ')
    entry=base+section.VirtualAddress+0xe00
    values=pointers['head_bob'];symbols={'VALUE1':values['1'],'VALUE2':values['2']}
    code=assemble(f'''
        cmp eax,1
        je value1
        cmp eax,2
        je value2
        movsxd rcx,dword ptr [r11+rax*4+{indices}]
        jmp {base+rejoin}
    value1:
        lea rax,[rip + @VALUE1]
        ret
    value2:
        lea rax,[rip + @VALUE2]
        ret
    ''',entry,symbols)
    if len(code)>0x100:raise ValueError('Context literal code exceeds reservation')
    position=pe.get_offset_from_rva(entry-base)
    if out[position:position+len(code)]!=b'\xcc'*len(code):raise ValueError('Context literal reservation overlap')
    out[position:position+len(code)]=code;out[source:source+8]=jump(base+hook,entry,8)
    return bytes(out),{'contexts':1,'context':'head_bob','getter_hook':hex(hook),'code_rva':hex(entry-base),'code_bytes':len(code),'values':{k:hex(v-base) for k,v in values.items()},'native_table_capacity':49 if build=='26286386' else 48,'settings_writes':0}
