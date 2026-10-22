"""Audited native debug-menu unlock and locale data, locked to one shipped PE.

Locale strings remain in a read-only PE section. Native UI hooks use a separate
RX section and an audited new zero-fill RW data tail, never RWX or new imports.
The original checkbox/action implementations are kept.
"""
import io
import base64
import json
import os
import re
import struct
from pathlib import Path

from localize import digest, make_delta

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'native-menu-pe-v1'


def config(path=None):
    path=Path(path) if path else ROOT/'locales'/os.environ.get('DEMENTIUM_LOCALE','zh-CN')/'debug-menu.json'
    recipe=json.loads(path.read_text(encoding='utf-8'))
    if recipe.get('schema')!=1 or not recipe.get('labels'):
        raise ValueError('Unsupported debug-menu locale recipe')
    for source,target in recipe['labels'].items():
        if not source or not target or '\0' in source+target or any(ord(c)>65535 for c in target):
            raise ValueError('Debug-menu labels require nonempty BMP UTF-8 strings')
        if re.findall(r'%(?:\d+\$)?[dsuf]',source)!=re.findall(r'%(?:\d+\$)?[dsuf]',target):
            raise ValueError('Debug-menu printf placeholders differ')
    return recipe


def glyph_text(recipe):
    return ''.join(chr(c) for c in range(32,127)) + ''.join(sorted(set(''.join(recipe['labels'].values())) - set(chr(c) for c in range(32,127))))


def build_font(zar, font_path, recipe=None):
    from fontTools.ttLib import TTFont
    from fontTools import subset
    recipe = config() if recipe is None else recipe
    original = zar.read('TUFFY_BOLD.TTF')
    if digest(original) != recipe['font_source_sha256']:
        raise ValueError('Native debug font source differs')
    font = TTFont(font_path, recalcTimestamp=False)
    codes = set(map(ord,glyph_text(recipe)))
    if codes - font.getBestCmap().keys():
        raise ValueError('Debug menu font lacks required glyphs')
    options = subset.Options()
    options.recalc_timestamp = False
    sub = subset.Subsetter(options=options)
    sub.populate(unicodes=codes)
    sub.subset(font)
    if 'glyf' not in font:
        raise ValueError('Native debug rasterizer requires TrueType outlines')
    for code,name in font.getBestCmap().items():
        glyph=font['glyf'][name]
        if code!=32 and not glyph.isComposite() and glyph.numberOfContours==0:
            raise ValueError('Native debug font has an empty outline: '+hex(code))
    font['head'].created = font['head'].modified = 2082844800
    output = io.BytesIO(); font.save(output)
    return output.getvalue()


def build_menu(data, recipe=None):
    import capstone
    import pefile
    recipe = config() if recipe is None else recipe
    # This hash is of the already validated five-literal localized executable.
    if digest(data) != recipe['input_sha256']:
        raise ValueError('Native menu requires its exact audited executable')
    pe = pefile.PE(data=data)
    if pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size:
        raise ValueError('Signed/overlaid executables are not supported')
    last = pe.sections[-1]
    if last.PointerToRawData + last.SizeOfRawData != len(data):
        raise ValueError('Unexpected executable overlay')
    align = lambda n,a:(n+a-1)//a*a
    va = align(last.VirtualAddress + max(last.Misc_VirtualSize,last.SizeOfRawData),pe.OPTIONAL_HEADER.SectionAlignment)
    raw = align(len(data),pe.OPTIONAL_HEADER.FileAlignment)
    table = last.get_file_offset()+40
    if table+40 > pe.OPTIONAL_HEADER.SizeOfHeaders or any(data[table:table+40]):
        raise ValueError('No audited section-header space')
    base = pe.OPTIONAL_HEADER.ImageBase
    payload = bytearray(); strings = {}
    for source,target in recipe['labels'].items():
        strings[source] = base+va+len(payload)
        payload.extend(target.encode('utf-8')+b'\0')
    glyph_va = base+va+len(payload)
    payload.extend(glyph_text(recipe).encode('utf-8')+b'\0')
    out = bytearray(data)
    md = capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64); md.detail=True
    redirected = []; hits=set()
    # Only native debug renderer/init/helpers. Other consumers retain originals.
    for ins in md.disasm(pe.get_data(0x4e300,0x509ed-0x4e300),base+0x4e300):
        for op in ins.operands:
            if op.type != capstone.x86.X86_OP_MEM or op.mem.base != capstone.x86.X86_REG_RIP:
                continue
            target = ins.address+ins.size+op.mem.disp
            if not (base+pe.sections[1].VirtualAddress <= target < base+pe.sections[1].VirtualAddress+pe.sections[1].Misc_VirtualSize):
                continue
            offset=pe.get_offset_from_rva(target-base)
            value=data[offset:offset+256].split(b'\0',1)[0]
            try: source=value.decode('ascii')
            except UnicodeDecodeError: continue
            new = glyph_va if target==0x1403bebf0 else strings.get(source)
            if new is None: continue
            if ins.disp_size!=4: raise ValueError('Unexpected RIP operand size')
            pos=pe.get_offset_from_rva(ins.address-base)+ins.disp_offset
            struct.pack_into('<i',out,pos,new-ins.address-ins.size)
            redirected.append(dict(instruction=hex(ins.address),source=source,target=hex(new)))
            if target!=0x1403bebf0: hits.add(source)
    # Existing entity name pointers already have IMAGE_REL_BASED_DIR64 entries.
    relocated={e.rva for b in pe.DIRECTORY_ENTRY_BASERELOC for e in b.entries if e.type==10}
    for rva,count,stride in [(0x3c08c0,12,16),(0x3c09d0,23,16),(0x3c0e30,7,24)]:
        for i in range(count):
            slot=rva+stride*i; pos=pe.get_offset_from_rva(slot)
            old=struct.unpack_from('<Q',data,pos)[0]
            off=pe.get_offset_from_rva(old-base)
            source=data[off:].split(b'\0',1)[0].decode('ascii')
            if source not in strings or slot not in relocated:
                raise ValueError('Untranslated/unrelocated entity table entry: '+source)
            struct.pack_into('<Q',out,pos,strings[source]); hits.add(source)
    # Unconditional branch into the existing rising-edge menu toggle.
    gate=pe.get_offset_from_rva(0x4fa49)
    if out[gate:gate+2]!=b'\x75\x04': raise ValueError('Unlock branch guard mismatch')
    out[gate]=0xeb
    key=pe.get_offset_from_rva(0x1a7d4b)
    if out[key:key+3]!=b'\x83\xfa\x7e': raise ValueError('Hotkey compare guard mismatch')
    out[key+2]=0x1c  # Native key translator maps Win32 VK_F1 to internal 0x1c.
    # Startup FUN_14002eee0 explicitly sets input object +458 to zero.
    # Only F1 must still reach +22c in that native mode. Preserve the mode
    # gate for every other key and use guarded adjacent INT3 padding for
    # relative branches only (no new section/import/absolute address).
    mode=pe.get_offset_from_rva(0x1a7c5b)
    cave=pe.get_offset_from_rva(0x1a7d81)
    if out[mode:mode+6]!=bytes.fromhex('0f 84 f6 00 00 00'):
        raise ValueError('Direct-input mode branch guard mismatch')
    if out[cave:cave+15]!=b'\xcc'*15:
        raise ValueError('F1 mode bridge padding guard mismatch')
    out[mode:mode+6]=b'\x0f\x84'+struct.pack('<i',0x1a7d81-(0x1a7c5b+6))
    bridge=(bytes.fromhex('83 fa 1c 0f 84')+
            struct.pack('<i',0x1a7d50-(0x1a7d81+9))+
            b'\xe9'+struct.pack('<i',0x1a7d57-(0x1a7d81+14))+b'\xcc')
    out[cave:cave+15]=bridge
    if not any(r['target']==hex(glyph_va) for r in redirected):
        raise ValueError('Glyph-range reference was not redirected')
    missing=set(recipe['labels'])-hits
    if missing: raise ValueError('Unused/unlocated debug translations: '+repr(sorted(missing)))
    raw_size=align(len(payload),pe.OPTIONAL_HEADER.FileAlignment)
    struct.pack_into('<8sIIIIIIHHI',out,table,b'.locmenu',len(payload),va,raw_size,raw,0,0,0,0,0x40000040)
    struct.pack_into('<H',out,pe.DOS_HEADER.e_lfanew+6,len(pe.sections)+1)
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(va+len(payload),pe.OPTIONAL_HEADER.SectionAlignment))
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfInitializedData'),pe.OPTIONAL_HEADER.SizeOfInitializedData+raw_size)
    struct.pack_into('<I',out,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),0)
    out.extend(b'\0'*(raw-len(out))); out.extend(payload); out.extend(b'\0'*(raw_size-len(payload)))
    result=bytes(out)
    parsed=pefile.PE(data=result)
    assert parsed.sections[-1].Characteristics==0x40000040
    from menu_input import patch_menu_input
    from document_reader import patch_document_reader
    result,input_report=patch_menu_input(result)
    result,reader_report=patch_document_reader(result)
    from pause_layout import patch_pause_layout
    result,pause_report=patch_pause_layout(result)
    return result,dict(input=input_report,document_reader=reader_report,pause_layout=pause_report,labels=len(hits),rip_references=len(redirected),entity_names=35,section_groups=7,
                       glyphs=len(set(glyph_text(recipe))),unlock_branch='0x14004fa49: 7504 -> eb04',
                       hotkey='F1 (VK 0x70 -> internal 0x1c), including native direct-input-disabled mode',
                       mode_bridge='0x1401a7c5b -> 0x1401a7d81; F1-only bypass of +458',
                       new_section='.locmenu read-only non-executable',references=redirected)


def make_patch(original, modified):
    patch=make_delta(original,modified); patch['format']=FORMAT
    return patch


def apply_patch(data,patch,reverse=False):
    if patch.get('format')!=FORMAT: raise ValueError('Not a native-menu PE patch')
    before='modified' if reverse else 'original'
    after='original' if reverse else 'modified'
    if len(data)!=patch[before+'_size'] or digest(data)!=patch[before+'_sha256']:
        raise ValueError('Native-menu patch input identity differs')
    append=base64.b64decode(patch['append'],validate=True)
    if patch['modified_size']-patch['original_size']!=len(append):
        raise ValueError('Native-menu patch tail length differs')
    out=bytearray(data);end=0
    for run in patch['runs']:
        old,new=bytes.fromhex(run['old']),bytes.fromhex(run['new'])
        offset=run['offset']
        if not old or len(old)!=len(new) or offset<end or offset+len(old)>patch['original_size']:
            raise ValueError('Invalid native-menu patch range')
        expected,replacement=(new,old) if reverse else (old,new)
        if data[offset:offset+len(expected)]!=expected:
            raise ValueError('Native-menu patch bytes differ')
        out[offset:offset+len(expected)]=replacement;end=offset+len(expected)
    if reverse: del out[patch['original_size']:]
    else: out.extend(append)
    result=bytes(out)
    if len(result)!=patch[after+'_size'] or digest(result)!=patch[after+'_sha256']:
        raise ValueError('Native-menu patch result identity differs')
    # Applying a prebuilt delta must remain standard-library-only for the
    # portable installer. Validate its existing PE section table defensively.
    from executable_text import _rdata
    _rdata(result)
    return result
