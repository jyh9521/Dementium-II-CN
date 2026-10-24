"""Bounded native overflow reader for the audited Steam 26099941 executable.

Text-only EXAMINE pages retain their original font and full UTF-8 source. A
visible-line window is drawn through the existing renderer; illustrated cards,
short notes and the letter puzzle keep the original path. Never launches game.
"""
from native_profile import rva as map_rva, guard
import struct
import pefile
from keystone import Ks, KS_ARCH_X86, KS_MODE_64

STATE_RVA=0xa68980
STATE_SIZE=0x440
STATE_FIELDS={'active':0,'wheel':4,'owner':8,'scroll_line':16,'previous_keys':20,
              'visible_lines':24,'repeat_counter':28,'viewport_height':32,'viewport_top':36,'resource_id':40,'stick_direction':44,'stick_repeat':48,'buffer':64}
HOOK_RVA=0x11b4f7
HOOK_BYTES=bytes.fromhex('44 2b c2 c6 05 fe 6c 3a 00 01')

def assemble(text,address):
    return bytes(Ks(KS_ARCH_X86,KS_MODE_64).asm(text,addr=address)[0])

def native_render_flag_rva(base=0x140000000):
    """Recover the exact displaced RIP target instead of retyping a global VA."""
    import capstone
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
    stores=[]
    for ins in md.disasm(guard(HOOK_BYTES,map_rva(HOOK_RVA)),base+map_rva(HOOK_RVA)):
        if ins.mnemonic=='mov' and ins.operands and ins.operands[0].type==capstone.x86.X86_OP_MEM:
            op=ins.operands[0]
            if op.mem.base==capstone.x86.X86_REG_RIP:
                stores.append(ins.address+ins.size+op.mem.disp-base)
    if len(stores)!=1:raise ValueError('Displaced native render-flag store is ambiguous')
    return stores[0]


def build_reader_code(code_rva,base=0x140000000,inventory=False):
    state=base+map_rva(STATE_RVA)
    def mem(field): return hex(state+STATE_FIELDS[field])
    # All pointers use RIP-relative LEA/load: preferred image base is only an
    # assembly-time coordinate, never an absolute runtime pointer.
    text=f"""
        pushfq
        push rax
        push rcx
        push rdx
        push rbx
        push rbp
        push rsi
        push rdi
        push r9
        push r10
        push r11
        push r13
        push r14
        push r15
        sub r8d,edx
        lea r11,[rip + {state-(base+code_rva)}]
    """
    # Keystone's rip+expression is a displacement, not a target. Generate a
    # labelled assembly with data-relative operands patched below from tagged
    # absolute targets via the assembler at their actual instruction addresses.
    text=text[:text.index('        lea r11')]+"\nSTATE_LEA\n"+f"""
        READER_CLASSIFY
        mov rax,[r15+0x68]
        movsx ecx,byte ptr [rax+0x18]
        add ecx,[r15+0x64]
        test ecx,ecx
        jle inactive
        mov ebx,ecx
        mov eax,ecx
        imul eax,esi
        sub eax,[r15+0x64]
        cmp eax,[r11+32]
        jle inactive
        mov eax,[r11+32]
        add eax,[r15+0x64]
        xor edx,edx
        div ecx
        test eax,eax
        jz inactive
        mov [r11+24],eax
        mov r13d,esi
        sub r13d,eax
        jle inactive
        cmp [r11+8],rdi
        jne new_owner
        cmp [r11+40],r10d
        je same_owner
    new_owner:
        mov [r11+8],rdi
        mov [r11+40],r10d
        mov dword ptr [r11+16],0
        mov dword ptr [r11+20],0
        mov dword ptr [r11+28],0
        mov dword ptr [r11+4],0
        mov qword ptr [r11+44],0
    same_owner:
        mov dword ptr [r11],1
        mov ebx,[r11+16]
        xor eax,eax
        xchg eax,[r11+4]
        imul eax,eax,3
        sub ebx,eax
        MENU_VISIBLE
        jne stick_blocked
        INPUT_POINTER
        test rax,rax
        je stick_blocked
        mov r10,rax
        PAD_CONNECTED
        je stick_idle
        WINDOW_POINTER
        test rax,rax
        je stick_idle
        cmp byte ptr [rax+0x79],0
        je stick_idle
        cmp byte ptr [rax+0x7a],0
        je stick_idle
        mov ecx,[r10+0x2cc]
        mov edx,ecx
        and edx,0x7fffffff
        cmp edx,0x3eb33333
        jbe stick_idle
        cmp edx,0x3f800000
        ja stick_idle
        sar ecx,31
        and ecx,2
        dec ecx
        cmp ecx,[r11+44]
        jne stick_edge
        inc dword ptr [r11+48]
        cmp dword ptr [r11+48],24
        jb stick_done
        mov dword ptr [r11+48],12
        jmp stick_move
    stick_edge:
        mov [r11+44],ecx
        mov dword ptr [r11+48],0
    stick_move:
        imul ecx,ecx,3
        add ebx,ecx
        jmp stick_done
    stick_idle:
        mov qword ptr [r11+44],0
    stick_done:
        mov rax,r10
        jmp keyboard_input
    stick_blocked:
        mov qword ptr [r11+44],0
        jmp clamp
    keyboard_input:
        movzx ecx,byte ptr [rax+0x22d]
        movzx edx,byte ptr [rax+0x22e]
        shl edx,1
        or ecx,edx
        mov edx,[r11+20]
        mov [r11+20],ecx
        xor edx,ecx
        and edx,ecx
        test edx,edx
        jne key_edge
        test ecx,ecx
        je key_release
        inc dword ptr [r11+28]
        cmp dword ptr [r11+28],20
        jb clamp
        mov eax,[r11+28]
        and eax,3
        jne clamp
        mov edx,ecx
        jmp key_move
    key_edge:
        mov dword ptr [r11+28],0
    key_move:
        test edx,1
        jz key_down
        dec ebx
    key_down:
        test edx,2
        jz clamp
        inc ebx
        jmp clamp
    key_release:
        mov dword ptr [r11+28],0
    clamp:
        xor eax,eax
        test ebx,ebx
        cmovl ebx,eax
        cmp ebx,r13d
        cmovg ebx,r13d
        mov [r11+16],ebx
        mov rsi,r12
        xor r9d,r9d
        mov ecx,ebx
        test ecx,ecx
        je start_copy
    skip_line:
        mov al,[rsi]
        test al,al
        je start_copy
        inc rsi
        cmp al,2
        jne skip_reset
        mov r9d,1
    skip_reset:
        cmp al,1
        jne skip_lf
        xor r9d,r9d
    skip_lf:
        cmp al,10
        jne skip_line
        dec ecx
        jnz skip_line
    start_copy:
        lea rdi,[r11+64]
        mov r12,rdi
        lea r10,[r11+1086]
        mov ecx,[r11+24]
        test r9d,r9d
        je copy_byte
        mov byte ptr [rdi],2
        inc rdi
    copy_byte:
        cmp rdi,r10
        jae end_copy
        mov al,[rsi]
        test al,al
        je end_copy
        inc rsi
        cmp al,10
        jne save_byte
        dec ecx
        jz end_copy
    save_byte:
        cmp al,2
        jne copy_control_end
        mov r9d,1
    copy_control_end:
        cmp al,1
        jne copy_store
        xor r9d,r9d
    copy_store:
        mov [rdi],al
        inc rdi
        jmp copy_byte
    end_copy:
        test r9d,r9d
        je terminate_copy
        mov byte ptr [rdi],1
        inc rdi
    terminate_copy:
        mov byte ptr [rdi],0
        mov r8d,[r11+36]
        jmp finish
    inactive:
        cmp dword ptr [r11],0
        je inactive_reset
        INPUT_POINTER
        test rax,rax
        je inactive_reset
        mov word ptr [rax+0x22d],0
    inactive_reset:
        mov qword ptr [r11+44],0
        mov dword ptr [r11],0
        mov dword ptr [r11+4],0
        mov qword ptr [r11+8],0
        mov dword ptr [r11+16],0
        mov dword ptr [r11+20],0
        mov dword ptr [r11+28],0
    finish:
        INVENTORY_RESULT
        pop r15
        pop r14
        pop r13
        pop r11
        pop r10
        pop r9
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        pop rdx
        pop rcx
        pop rax
        popfq
        INVENTORY_RESTORE
        RENDER_FLAG
        jmp {hex(base+(map_rva(0x123383) if inventory else map_rva(HOOK_RVA)+len(HOOK_BYTES)))}
    """
    classify=("mov r10d,[rdi+0x1d0]" if inventory else "movsx r10d,word ptr [rdi+0x128]")+f"""
        cmp r10d,535
        je inactive
        mov dword ptr [r11+32],152
        mov dword ptr [r11+36],{8 if inventory else 24}
        cmp r10d,78
        je illustrated_letter
        lea eax,[r10-90]
        cmp eax,3
        jbe illustrated_letter
        NORMAL_GUARD
        jmp classify_done
    illustrated_letter:
        mov dword ptr [r11+32],72
        mov dword ptr [r11+36],{88 if inventory else 104}
        COLLECTION_CONTENT_EXTENT
    classify_done:
    """
    classify=classify.replace('NORMAL_GUARD',
        'cmp r10d,500; jl inactive' if inventory else
        'cmp word ptr [rdi+0x12a],0; jge inactive')
    if inventory:
        classify='xor r14d,r14d\n'+classify
    # Collection letters retain authored/native trailing padding for layout.
    # Only the overflow/scroll extent ends at the last nonblank content line;
    # do not delete source bytes or collapse internal paragraph separation.
    classify=classify.replace('COLLECTION_CONTENT_EXTENT',"""
        mov r14d,esi
        mov rax,r12
        mov edx,1
        xor ecx,ecx
    extent_byte:
        movzx r9d,byte ptr [rax]
        inc rax
        test r9b,r9b
        je extent_done
        cmp r9b,10
        je extent_newline
        cmp r9b,32
        je extent_byte
        cmp r9b,9
        je extent_byte
        cmp r9b,13
        je extent_byte
        cmp r9b,1
        je extent_byte
        cmp r9b,2
        je extent_byte
        mov ecx,edx
        jmp extent_byte
    extent_newline:
        inc edx
        jmp extent_byte
    extent_done:
        sub edx,ecx
        sub esi,edx
        jns extent_nonnegative
        xor esi,esi
    extent_nonnegative:
    """ if inventory else '')
    text=text.replace('READER_CLASSIFY',classify)
    if inventory:
        text=text.replace('cmp eax,[r11+32]\n        jle inactive',
                          'cmp eax,[r11+32]\n        jle collection_content_fits')
        text=text.replace('    inactive:',"""
    collection_content_fits:
        test r14d,r14d
        je inactive
        mov eax,ebx
        imul eax,r14d
        sub eax,[r15+0x64]
        cmp eax,[r11+32]
        jle inactive
        mov r8d,[r11+36]
        jmp inactive
    inactive:""")
        text='push r12\n'+text
        text=text.replace('sub r8d,edx','sub r8d,ecx; add r8d,160; mov r9d,edi; lea rdi,[r14-0x1e0]; mov r12,r14; mov r15,rsi; mov esi,r9d')
        text=text.replace('[r15+0x68]','[r15+0x40]').replace('[r15+0x64]','[r15+0x3c]')
        text=text.replace('INVENTORY_RESULT','mov [rsp+8],r12')
        text=text.replace('INVENTORY_RESTORE','pop r12')
        text=text.replace('RENDER_FLAG','')
    else:
        text=text.replace('INVENTORY_RESULT','').replace('INVENTORY_RESTORE','')
    # Fixed-width placeholder instruction encodings allow every label to be
    # assembled once; then replace only tagged RIP displacements.
    placeholders={
        'PAD_CONNECTED':('cmp byte ptr [rip+0x12345673],0',0x12345673,base+map_rva(0xa314f0)),
        'WINDOW_POINTER':('mov rax,[rip+0x12345674]',0x12345674,base+map_rva(0xa312b0)),
        'STATE_LEA':('lea r11,[rip+0x12345678]',0x12345678,state),
        'MENU_VISIBLE':('cmp byte ptr [rip+0x12345677],0',0x12345677,base+map_rva(0x4a2f1d)),
        'INPUT_POINTER':('mov rax,[rip+0x12345676]',0x12345676,base+map_rva(0x4c2228)),
        'RENDER_FLAG':('mov byte ptr [rip+0x12345675],1',0x12345675,base+native_render_flag_rva(base))}
    for tag,(ins,_,_) in placeholders.items():text=text.replace(tag,ins)
    code=bytearray(assemble(text,base+code_rva))
    import capstone
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
    for ins in md.disasm(bytes(code),base+code_rva):
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                for _,(_,marker,target) in placeholders.items():
                    if op.mem.disp==marker:
                        struct.pack_into('<i',code,ins.address-(base+code_rva)+ins.disp_offset,target-ins.address-ins.size)
    return bytes(code)


def reset_code(address,resume,displaced,base=0x140000000,clear_reader_arrows=False):
    state=base+map_rva(STATE_RVA)
    # No general-purpose register or flags changes; initialization and closing
    # both clear the shared active/wheel/owner/scroll state before original code.
    result=bytearray()
    if clear_reader_arrows:
        # Only a previously active reader owns these borrowed arrow fields.
        # Cleanup precedes active reset, including native open/reinitialize paths.
        result.extend(bytes.fromhex('9c 50'))
        here=address+len(result)
        result.extend(bytes.fromhex('83 3d')+struct.pack('<i',state-(here+7))+b'\0')
        result.extend(bytes.fromhex('74 15'))
        here=address+len(result)
        result.extend(bytes.fromhex('48 8b 05')+struct.pack('<i',base+map_rva(0x4c2228)-(here+7)))
        result.extend(bytes.fromhex('48 85 c0 74 09 66 c7 80 2d 02 00 00 00 00 58 9d'))
    for offset in [0,4,8,12,16,20,24,28,32,36,40,44,48]:
        here=address+len(result)
        result.extend(bytes.fromhex('c7 05')+struct.pack('<i',state+offset-(here+10))+b'\0'*4)
    result.extend(displaced)
    here=address+len(result)
    result.extend(b'\xe9'+struct.pack('<i',resume-(here+5)))
    return bytes(result)


def patch_document_reader(data):
    pe=pefile.PE(data=data)
    base=pe.OPTIONAL_HEADER.ImageBase
    # Bind axis index 3 / pad 0 and connection gate to audited native consumers.
    for rva,expected in [(map_rva(0x1557a5),bytes.fromhex('f3 45 0f 10 81 cc 02 00 00')),
                         (map_rva(0x2ed4d),bytes.fromhex('f3 41 0f 11 9c 89 c0 02 00 00')),
                         (map_rva(0x31ad26),bytes.fromhex('41 80 bc bc f0 14 a3 00 00'))]:
        from native_profile import active_build
        if active_build()=='26152271' and rva==map_rva(0x31ad26):
            # 1.0.3 copies controller packets to stack; the native consumer
            # uses RDX, while reader disconnect gating retains the source flag.
            expected=bytes.fromhex('80 3a 00')
            if pe.get_data(0x31df43,7)!=bytes.fromhex('0f 28 05 06 86 71 00') or pe.get_data(0x31df4a,7)!=bytes.fromhex('0f 28 0d 0f 86 71 00'):
                raise ValueError('Reader controller packet provenance guard mismatch')
        else:expected=guard(expected,rva)
        if pe.get_data(rva,len(expected))!=expected:
            raise ValueError('Reader gamepad axis/connection guard mismatch at '+hex(rva))
    section=next((s for s in pe.sections if s.Name.rstrip(b'\0')==b'.locui'),None)
    if section is None or section.SizeOfRawData<0x2000:
        raise ValueError('Reader requires shared .locui RX section of at least 8 KiB')
    if section.Characteristics & 0xa0000000 != 0x20000000:
        raise ValueError('Reader code section must be executable and non-writable')
    start=section.VirtualAddress+0x1000
    code=build_reader_code(start,base)
    entries={'render':start}
    body=bytearray(code)
    hooks=[(map_rva(HOOK_RVA),HOOK_BYTES,start)]
    while len(body)%16:body.append(0xcc)
    inventory_entry=start+len(body);entries['inventory_render']=inventory_entry
    body.extend(build_reader_code(inventory_entry,base,True))
    hooks.append((map_rva(0x123379),bytes.fromhex('44 2b c1 41 81 c0 a0 00 00 00'),inventory_entry))
    for key,rva,expected in [('open',map_rva(0x11a7b0),bytes.fromhex('44 88 4c 24 20')),
                             ('close',map_rva(0x11af80),bytes.fromhex('40 53 48 83 ec 20')),
                             ('inventory_open',map_rva(0x121e50),bytes.fromhex('48 89 5c 24 10')),
                             ('inventory_close',map_rva(0x122a10),bytes.fromhex('48 83 ec 28 48 8b 89 c8 01 00 00'))]:
        while len(body)%16:body.append(0xcc)
        entry=start+len(body);entries[key]=entry
        body.extend(reset_code(base+entry,base+rva+len(expected),expected,base,clear_reader_arrows=True))
        hooks.append((rva,expected,entry))
    if len(body)>0x1000:raise ValueError('Reader code exceeds reserved shared RX page')
    out=bytearray(data)
    for rva,expected,target in hooks:
        expected=guard(expected,rva)
        pos=pe.get_offset_from_rva(rva)
        if out[pos:pos+len(expected)]!=expected:
            raise ValueError('Native reader instruction guard mismatch at '+hex(rva))
        out[pos:pos+len(expected)]=b'\xe9'+struct.pack('<i',target-rva-5)+b'\x90'*(len(expected)-5)
    position=pe.get_offset_from_rva(start)
    if any(b not in (0,0xcc) for b in out[position:position+len(body)]):raise ValueError('Reader RX reservation is not empty')
    out[position:position+len(body)]=body
    dat=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.data')
    end=map_rva(STATE_RVA)+STATE_SIZE
    next_rva=min(s.VirtualAddress for s in pe.sections if s.VirtualAddress>dat.VirtualAddress)
    if not(dat.VirtualAddress+dat.SizeOfRawData<=map_rva(STATE_RVA) and end<=next_rva):
        raise ValueError('Reader state is outside audited .data zero-fill tail')
    struct.pack_into('<I',out,dat.get_field_absolute_offset('Misc_VirtualSize'),max(dat.Misc_VirtualSize,end-dat.VirtualAddress))
    report=dict(code_rva=hex(start),code_bytes=len(body),entries={k:hex(v) for k,v in entries.items()},
                state={k:map_rva(STATE_RVA)+v for k,v in STATE_FIELDS.items()},state_size=STATE_SIZE,native_render_flag_rva=hex(native_render_flag_rva(base)),
                gamepad_scroll={'axis':'input+0x2cc (pad 0 right Y)', 'deadzone':0.35,'lines_per_notch':3,'repeat_delay_frames':24,'repeat_interval_frames':12,'gates':['overflow reader','menu hidden','window active/focused','valid input','pad 0 connected'],'preserves':['axis values','gameplay input mode','ordinary look']},
                viewport=[0,24,256,176],illustrated_letter_viewports={'field':[0,104,256,176],'collection':[0,88,256,160]},font_scale=1,applies_to='overflow text-only EXAMINE plus illustrated letters 78/90..93 in field and collection readers, except letter puzzle 535',
                postcard_collection='12 postcard resources and their original branches unchanged; illustrated letters scroll only over nonblank content extent',
                collection_letter_extent='Ignore trailing blank padding only for overflow/scroll limits; preserve source, internal blanks and the previous fitting viewport anchor',short_documents='native paths retained; collection-letter padding alone never enables scrolling',
                close_input_cleanup={'fields':['input+0x22d','input+0x22e'],'when':'previous reader active; all open/close and render deactivation paths','preserved':['input+0x458','ordinary gameplay keys','native render flag']},
                source='native initialization 0x14011a7b0; per-frame renderer 0x14011b000; close 0x14011af80',
                validation='guarded machine code plus isolated CPU replay; not an in-game rendering claim')
    return bytes(out),report
