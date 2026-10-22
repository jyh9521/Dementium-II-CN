"""Native menu input ownership, wheel routing and Win32 cursor transitions.

Only menu-visible keyboard dispatch differs. Opening centers/clips a visible
system cursor to the game client; closing restores native capture. Win32 calls
are existing imports; generated x64 code uses relative branches/RIP addressing.
"""
from native_profile import rva as map_rva, guard
import struct
import pefile
from native_patch import BASE,READER_STATE,MENU_STATE,assemble,guarded_write,jump,prepare_ui_section


def native_f1_previous_rva(data):
    """Decode both native consumer accesses; never retype an adjacent byte."""
    import capstone
    pe=pefile.PE(data=data)
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
    targets=[]
    for rva,expected in [(map_rva(0x4fa2e),'cmp'),(map_rva(0x4fa60),'mov')]:
        ins=next(md.disasm(pe.get_data(rva,7),BASE+rva))
        if ins.mnemonic!=expected:raise ValueError('F1 consumer instruction guard mismatch')
        op=ins.operands[0]
        if op.type!=capstone.x86.X86_OP_MEM or op.mem.base!=capstone.x86.X86_REG_RIP:
            raise ValueError('F1 consumer RIP target guard mismatch')
        targets.append(ins.address+ins.size+op.mem.disp-BASE)
    if len(set(targets))!=1:raise ValueError('F1 consumer targets disagree')
    return targets[0]


def patch_menu_input(data):
    data,report=prepare_ui_section(data)
    pe=pefile.PE(data=data);out=bytearray(data);code=BASE+report['code_rva']
    symbols=dict(VISIBLE=BASE+map_rva(0x4a2f1d),INPUT=BASE+map_rva(0x4c2228),IO=BASE+map_rva(0x4c2248),
                 READER=BASE+map_rva(READER_STATE),WHEEL=BASE+map_rva(READER_STATE)+4,
                 WINDOW=BASE+map_rva(0xa312b0),PREV=BASE+map_rva(MENU_STATE),OWNED=BASE+map_rva(MENU_STATE)+1,
                 CAPTURE=BASE+map_rva(MENU_STATE)+2,FRAME_RATE=BASE+map_rva(0x4a4a58),
                 CURSOR_HIDDEN=BASE+map_rva(0xa344f4),GAME_CAPTURE=BASE+map_rva(0x49f1a5),
                 LOAD_CURSOR=BASE+map_rva(0x37d818),SET_CURSOR=BASE+map_rva(0x37d758),
                 CLIP_CURSOR=BASE+map_rva(0x37d760),GET_CLIENT=BASE+map_rva(0x37d748),
                 CLIENT_SCREEN=BASE+map_rva(0x37d7b0),SET_POS=BASE+map_rva(0x37d6f0))
    symbols.update(VK_HELD=BASE+map_rva(0xa30d20),KEY_UP=BASE+map_rva(0xa25e28),KEY_INPUT=BASE+map_rva(0xa2ca78),IMAGE_BASE=BASE)
    symbols['F1_PREVIOUS']=BASE+native_f1_previous_rva(data)
    symbols.update({f'ACTION{i}':BASE+map_rva(0xa121a0)+4*i for i in range(10)})
    blocks={}
    def put(offset,text):
        body=assemble(text,code+offset,symbols)
        if offset+len(body)>0x1000:raise ValueError('Menu code exceeds reserved region')
        pos=pe.get_offset_from_rva(report['code_rva']+offset)
        if bytes(out[pos:pos+len(body)])!=b'\xcc'*len(body):raise ValueError('Menu code overlap')
        out[pos:pos+len(body)]=body;blocks[hex(offset)]=len(body)
        return code+offset
    key=put(0,f"""
        cmp byte ptr [rip + @VISIBLE],0
        jne menu_keys
        cmp dword ptr [rip + @READER],0
        je original_key_mode
        cmp edx,0xf
        je normal_keys
        cmp edx,0x11
        je normal_keys
    original_key_mode:
        cmp byte ptr [rcx+0x458],0
        jne normal_keys
        cmp edx,0x1c
        je {BASE+map_rva(0x1a7d50)}
        jmp {BASE+map_rva(0x1a7d57)}
    menu_keys:
        cmp edx,5
        je activate
        cmp edx,1
        je cancel
    normal_keys:
        jmp {BASE+map_rva(0x1a7c61)}
    activate:
        mov byte ptr [rcx+0x221],r8b
        jmp {BASE+map_rva(0x1a7d57)}
    cancel:
        mov byte ptr [rcx+0x222],r8b
        jmp {BASE+map_rva(0x1a7d57)}
    """)
    wheel=put(0x100,f"""
        cmp byte ptr [rip + @VISIBLE],0
        jne menu_wheel
        cmp dword ptr [rip + @READER],0
        jne reader_wheel
        sub rsp,0x28
        test edx,edx
        jmp {BASE+map_rva(0x2ee36)}
    reader_wheel:
        add dword ptr [rip + @WHEEL],edx
        ret
    menu_wheel:
        push rax
        mov rax,qword ptr [rip + @IO]
        test rax,rax
        je wheel_done
        sub rsp,0x10
        movdqu xmmword ptr [rsp],xmm0
        cvtsi2ss xmm0,edx
        addss xmm0,dword ptr [rax+0x140]
        movss dword ptr [rax+0x140],xmm0
        movdqu xmm0,xmmword ptr [rsp]
        add rsp,0x10
    wheel_done:
        pop rax
        ret
    """)
    cursor=put(0x200,f"""
        cmp byte ptr [rip + @VISIBLE],0
        je original_cursor
        cmp byte ptr [rdi+0x79],0
        je original_cursor
        cmp byte ptr [rdi+0x7a],0
        je original_cursor
        mov byte ptr [rdi+0x19],0
        mov al,1
        jmp {BASE+map_rva(0x2f3250)}
    original_cursor:
        cmp byte ptr [rdi+0x7a],0
        movzx eax,byte ptr [rip + @CURSOR_HIDDEN]
        jmp {BASE+map_rva(0x2f3241)}
    """)
    capture=put(0x280,f"""
        cmp byte ptr [rip + @VISIBLE],0
        je store_capture
        xor bl,bl
    store_capture:
        mov byte ptr [rip + @GAME_CAPTURE],bl
        jmp {BASE+map_rva(0x2f4b3)}
    """)
    raw_wheel=put(0x300,f"""
        cmp byte ptr [rip + @VISIBLE],0
        jne raw_done
        cmp dword ptr [rip + @READER],0
        jne raw_done
        sub rsp,0x28
        mov rcx,qword ptr [rcx+0x450]
        jmp {BASE+map_rva(0x1a7d9b)}
    raw_done:
        ret
    """)
    masks='\n'.join(f'and dword ptr [rip + @ACTION{i}],0xffffff3f' for i in range(10))
    reader_actions=put(0x340,f"""
        cmp dword ptr [rip + @READER],0
        je native_menu_gate
        and eax,0xffffff3f
        and edx,0xffffff3f
        and ebx,0xffffff3f
        {masks}
    native_menu_gate:
        cmp byte ptr [rip + @VISIBLE],dil
        jmp {BASE+map_rva(0x155882)}
    """)
    # Native window-message dispatch uses the same +19 capture request which
    # must be cleared to show/release the OS cursor. Keep its focus checks,
    # but allow menu-owned pointer messages past ONLY this capture gate.
    pointer=put(0x900,f"""
        cmp byte ptr [rip + @VISIBLE],0
        jne pointer_ready
        cmp byte ptr [rcx+0x19],0
        je {BASE+map_rva(0x2f5439)}
    pointer_ready:
        jmp {BASE+map_rva(0x2f5386)}
    """)
    # Engine UpdateInput synthesizes gameplay mouse state AFTER the platform
    # queue. With capture released its neutral raw values would erase queued UI
    # clicks before DrawDebugMenu copies +231. Preserve both native queue fields
    # only while the menu owns input; ordinary gameplay keeps the exact writes.
    pointer_poll=put(0x940,f"""
        cmp byte ptr [rip + @VISIBLE],0
        jne {BASE+map_rva(0x2f5b5)}
        mov byte ptr [rax+0x231],r8b
        jmp {BASE+map_rva(0x2f5af)}
    """)
    # The REGISTERED Win32 WndProc has an outer first-click-to-capture gate,
    # before the common message translator and the inner dispatch fixed above.
    # Releasing capture for the menu made every click take that return path.
    # Skip only recapture while visible; rejoin BEFORE native focus checks.
    window_click=put(0xa00,f"""
        cmp byte ptr [rip + @VISIBLE],0
        jne {BASE+map_rva(0x2f39e3)}
        cmp byte ptr [rbx+0x19],r14b
        jne {BASE+map_rva(0x2f39e3)}
        jmp {BASE+map_rva(0x2f39d2)}
    """)
    save='\n'.join(f'movdqu xmmword ptr [rsp+{0x60+i*16}],xmm{i}' for i in range(6))
    restore='\n'.join(f'movdqu xmm{i},xmmword ptr [rsp+{0x60+i*16}]' for i in range(6))
    focus=put(0x400,f"""
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp,0xc0
        {save}
        mov rcx,qword ptr [rip + @WINDOW]
        test rcx,rcx
        je focus_done
        mov qword ptr [rsp+0x20],rcx
        cmp byte ptr [rip + @VISIBLE],0
        je close_menu
        cmp byte ptr [rcx+0x79],0
        je lose_focus
        cmp byte ptr [rcx+0x7a],0
        je lose_focus
        cmp byte ptr [rip + @OWNED],0
        jne focus_done
        cmp byte ptr [rip + @PREV],0
        jne open_menu
        mov al,byte ptr [rcx+0x19]
        mov byte ptr [rip + @CAPTURE],al
    open_menu:
        mov byte ptr [rip + @PREV],1
        mov byte ptr [rip + @OWNED],1
        mov byte ptr [rcx+0x19],0
        call {BASE+map_rva(0x2f34d0)}
        xor ecx,ecx
        mov edx,0x7f00
        call qword ptr [rip + @LOAD_CURSOR]
        mov rcx,rax
        call qword ptr [rip + @SET_CURSOR]
        mov rcx,qword ptr [rsp+0x20]
        mov byte ptr [rcx+0x18],1
        mov rcx,qword ptr [rcx+0x20]
        lea rdx,[rsp+0x30]
        call qword ptr [rip + @GET_CLIENT]
        test eax,eax
        je focus_done
        mov eax,dword ptr [rsp+0x38]
        sub eax,dword ptr [rsp+0x30]
        sar eax,1
        mov dword ptr [rsp+0x40],eax
        mov edx,dword ptr [rsp+0x3c]
        sub edx,dword ptr [rsp+0x34]
        sar edx,1
        mov dword ptr [rsp+0x44],edx
        mov rcx,qword ptr [rip + @INPUT]
        test rcx,rcx
        je no_input_point
        mov dword ptr [rcx+0x340],eax
        mov dword ptr [rcx+0x344],edx
    no_input_point:
        mov rcx,qword ptr [rsp+0x20]
        mov rcx,qword ptr [rcx+0x20]
        lea rdx,[rsp+0x40]
        call qword ptr [rip + @CLIENT_SCREEN]
        test eax,eax
        je focus_done
        mov ecx,dword ptr [rsp+0x40]
        mov edx,dword ptr [rsp+0x44]
        call qword ptr [rip + @SET_POS]
        mov rcx,qword ptr [rsp+0x20]
        mov rcx,qword ptr [rcx+0x20]
        lea rdx,[rsp+0x30]
        call qword ptr [rip + @CLIENT_SCREEN]
        test eax,eax
        je focus_done
        mov rcx,qword ptr [rsp+0x20]
        mov rcx,qword ptr [rcx+0x20]
        lea rdx,[rsp+0x38]
        call qword ptr [rip + @CLIENT_SCREEN]
        test eax,eax
        je focus_done
        lea rcx,[rsp+0x30]
        call qword ptr [rip + @CLIP_CURSOR]
        jmp focus_done
    lose_focus:
        cmp byte ptr [rip + @OWNED],0
        je focus_done
        mov byte ptr [rip + @OWNED],0
        mov byte ptr [rcx+0x19],0
        xor ecx,ecx
        call qword ptr [rip + @CLIP_CURSOR]
        call clear_input
        jmp focus_done
    close_menu:
        cmp byte ptr [rip + @PREV],0
        je focus_done
        mov byte ptr [rip + @PREV],0
        mov byte ptr [rip + @OWNED],0
        call clear_input
        xor ecx,ecx
        call qword ptr [rip + @CLIP_CURSOR]
        mov rcx,qword ptr [rsp+0x20]
        mov al,byte ptr [rip + @CAPTURE]
        cmp byte ptr [rcx+0x79],0
        je no_capture
        cmp byte ptr [rcx+0x7a],0
        jne restore_capture
    no_capture:
        xor al,al
    restore_capture:
        mov byte ptr [rcx+0x19],al
        call {BASE+map_rva(0x2f34d0)}
        mov rcx,qword ptr [rsp+0x20]
        cmp byte ptr [rcx+0x19],0
        je focus_done
        mov byte ptr [rcx+0x18],0
        xor ecx,ecx
        call qword ptr [rip + @SET_CURSOR]
    focus_done:
        {restore}
        add rsp,0xc0
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        movd xmm0,dword ptr [rip + @FRAME_RATE]
        jmp {BASE+map_rva(0x4fa6e)}
    clear_input:
        mov rax,qword ptr [rip + @INPUT]
        test rax,rax
        je clear_io
        mov qword ptr [rax+0x221],0
        mov word ptr [rax+0x229],0
        mov byte ptr [rax+0x22b],0
        mov dword ptr [rax+0x22d],0
        mov word ptr [rax+0x231],0
    clear_io:
        mov rax,qword ptr [rip + @IO]
        test rax,rax
        je clear_done
        mov word ptr [rax+0x138],0
        mov dword ptr [rax+0x140],0
        sub rsp,0x28
        xor ecx,ecx
        xor edx,edx
        call {BASE+map_rva(0x66e70)}
        add rsp,0x28
    clear_done:
        ret
    """)
    # WM_KILLFOCUS / WM_ACTIVATEAPP(false) do not receive keys released in
    # another application. Release the native Win32 repeat-suppression latches
    # through the SAME translator/up callback as WM_KEYUP, before forwarding
    # the focus message. A later frame-only reset would miss immediate refocus.
    focus_release=put(0xb00,f"""
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp,0xc0
        {save}
        cmp r13d,8
        je check_lost_focus
        cmp r13d,0x1c
        jne release_done
    check_lost_focus:
        cmp byte ptr [rbx+0x79],0
        je release_keys
        cmp byte ptr [rbx+0x7a],0
        jne release_done
    release_keys:
        mov dword ptr [rsp+0x20],0
    next_key:
        lea rax,[rip + @VK_HELD]
        mov ecx,dword ptr [rsp+0x20]
        cmp byte ptr [rax+rcx],0
        je advance_key
        mov byte ptr [rax+rcx],0
        cmp ecx,0x70
        jne key_callback
        mov byte ptr [rip + @F1_PREVIOUS],0
    key_callback:
        cmp qword ptr [rip + @KEY_INPUT],0
        je advance_key
        cmp qword ptr [rip + @KEY_UP],0
        je advance_key
        xor r9d,r9d
        call {BASE+map_rva(0x2dd940)}
        mov ecx,eax
        xor edx,edx
        call qword ptr [rip + @KEY_UP]
    advance_key:
        inc dword ptr [rsp+0x20]
        cmp dword ptr [rsp+0x20],256
        jb next_key
    release_done:
        {restore}
        add rsp,0xc0
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        mov rdi,qword ptr [rbp+0x1e0]
        jmp {BASE+map_rva(0x2f3a45)}
    """)
    # After a lost-focus release, an OS auto-repeat is still not a fresh press.
    # Both native WM_KEYDOWN/WM_SYSKEYDOWN paths enter this exact point with
    # lParam in RSI. Preserve flags for the displaced LEA and native gate.
    key_repeat=put(0xd00,f"""
        pushfq
        test esi,0x40000000
        je fresh_key
        popfq
        jmp {BASE+map_rva(0x2deb38)}
    fresh_key:
        popfq
        lea rcx,[rip + @IMAGE_BASE]
        jmp {BASE+map_rva(0x2de83a)}
    """)
    # Intercept the common mode gate, so menu keys work in BOTH native modes.
    # The earlier F1 compare/unlock/debounce and padding bridge stay exact.
    hooks=[(map_rva(0x1a7c54),bytes.fromhex('80 b9 58 04 00 00 00'),key),(map_rva(0x2ee30),bytes.fromhex('48 83 ec 28 85 d2'),wheel),
           (map_rva(0x1a7d90),bytes.fromhex('48 83 ec 28 48 8b 89 50 04 00 00'),raw_wheel),
           (map_rva(0x2f3236),bytes.fromhex('80 7f 7a 00 0f b6 05 b3 12 74 00'),cursor),
           (map_rva(0x2f537c),bytes.fromhex('80 79 19 00 0f 84 b3 00 00 00'),pointer),
           (map_rva(0x2f5a8),bytes.fromhex('44 88 80 31 02 00 00'),pointer_poll),
           (map_rva(0x2f39cc),bytes.fromhex('44 38 73 19 75 11'),window_click),
           (map_rva(0x2f3a3e),bytes.fromhex('48 8b bd e0 01 00 00'),focus_release),
           (map_rva(0x2de833),bytes.fromhex('48 8d 0d c6 17 d2 ff'),key_repeat),
           (map_rva(0x2f4ad),bytes.fromhex('88 1d f2 fc 46 00'),capture),
           (map_rva(0x15587b),bytes.fromhex('40 38 3d 9b d6 34 00'),reader_actions),
           (map_rva(0x4fa66),bytes.fromhex('66 0f 6e 05 ea 4f 45 00'),focus)]
    for rva,expected,target in hooks:guarded_write(out,pe,rva,expected,jump(BASE+rva,target,len(expected)))
    report.update(blocks=blocks,key_hook=hex(key),wheel_hook=hex(wheel),raw_wheel_hook=hex(raw_wheel),reader_actions_hook=hex(reader_actions),focus_hook=hex(focus),
                  cursor_hook=hex(cursor),capture_hook=hex(capture),pointer_dispatch_hook=hex(pointer),pointer_poll_hook=hex(pointer_poll),window_click_hook=hex(window_click),focus_release_hook=hex(focus_release),key_repeat_hook=hex(key_repeat),state=hex(BASE+map_rva(MENU_STATE)),
                  input_policy='F1 always; visible menu accepts native navigation; long-reader bypasses mode gate only for Up/Down',
                  wheel_policy='menu ImGui IO +140; otherwise active long-reader wheel; otherwise original game callback',
                  focus_policy='show/center/client-clip on open, native capture restore on close; focus loss releases clip',
                  pointer_policy='visible menu bypasses outer first-click recapture and inner capture gate with native focus checks retained; queued buttons survive gameplay polling; native widgets unchanged')
    return bytes(out),report
