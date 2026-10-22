"""Native-reader CPU replay and paragraph-preservation regressions; no game."""
import ctypes
import json
import os
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from document_reader import build_reader_code,reset_code,assemble,STATE_RVA,HOOK_RVA,HOOK_BYTES,native_render_flag_rva
from font_pipeline import layout_document,glyph_width
ROOT=Path(__file__).resolve().parents[1]
BASE=0x140000000
CODE=0xaf2000
SIZE=0xb00000

class DocumentParagraphTests(unittest.TestCase):
    def test_long_prose_rules_never_join_authored_breaks(self):
        profile=json.loads((ROOT/'locales/zh-CN/font-profile.json').read_text('utf8'))
        self.assertEqual(profile['fonts']['body']['pixel_size'],12)
        self.assertEqual(profile['linefeed'],16)
        self.assertTrue(profile['document_defaults']['preserve_whitespace'])
        for resource,rule in profile['prose_layouts'].items():
            self.assertFalse(rule.get('soft_lines'),resource)
            self.assertFalse(rule.get('reflow'),resource)
        source='标题\n\n  第一段甲乙\n第二行甲乙\n\n  第二段甲乙'
        meta={'linefeed':16,'glyphs':{'0':{'logw':12}}}
        actual=layout_document(source,meta,profile,profile['document_defaults'])
        self.assertEqual(actual,source)

class NativeReaderPatchTests(unittest.TestCase):
    def test_displaced_native_render_flag_target_is_decoded_not_retyped(self):
        self.assertEqual(native_render_flag_rva(),0x4c21ff)
        self.assertEqual(native_render_flag_rva(0x180000000),0x4c21ff)

    def test_actual_shared_section_patch_guards_and_scope(self):
        import pefile
        from document_reader import patch_document_reader
        incoming=ROOT/'build/reader-input-fix/menu-patched.exe'
        if not incoming.is_file():self.skipTest('shared UI section local fixture required')
        source=incoming.read_bytes();result,report=patch_document_reader(source)
        a=pefile.PE(data=source);b=pefile.PE(data=result)
        self.assertEqual([(s.Name,s.Characteristics) for s in a.sections],[(s.Name,s.Characteristics) for s in b.sections])
        allowed=set()
        for rva,size in [(0x11b4f7,10),(0x11a7b0,5),(0x11af80,6),(0x123379,10),(0x121e50,5),(0x122a10,11)]:
            p=a.get_offset_from_rva(rva);allowed.update(range(p,p+size))
            self.assertEqual(result[p],0xe9)
        start=int(report['code_rva'],16);p=a.get_offset_from_rva(start)
        allowed.update(range(p,p+report['code_bytes']))
        self.assertEqual(result[p:p+len(build_reader_code(start))],build_reader_code(start))
        self.assertTrue(all(x==y or n in allowed for n,(x,y) in enumerate(zip(source,result))))
        broken=bytearray(source);broken[a.get_offset_from_rva(0x11b4f7)]^=1
        with self.assertRaisesRegex(ValueError,'guard mismatch'):patch_document_reader(bytes(broken))
        with self.assertRaisesRegex(ValueError,'guard mismatch'):patch_document_reader(result)

@unittest.skipUnless(os.name=='nt','bounded Windows x64 native replay')
class NativeReaderTests(unittest.TestCase):
    def setUp(self):
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.VirtualAlloc.restype=ctypes.c_void_p
        self.kernel.VirtualAlloc.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_ulong,ctypes.c_ulong]
        self.kernel.VirtualFree.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_ulong]
        self.mem=self.kernel.VirtualAlloc(None,SIZE,0x3000,0x40)
        self.assertTrue(self.mem)
        self.write(CODE,build_reader_code(CODE))
        self.write(HOOK_RVA+len(HOOK_BYTES),b'\xc3')
        self.input=ctypes.create_string_buffer(0x500)
        self.write(0x4c2228,struct.pack('<Q',ctypes.addressof(self.input)))
        self.font=ctypes.create_string_buffer(0x100)
        self.font[0x18]=16
        self.node=ctypes.create_string_buffer(0x100)
        struct.pack_into('<Q',self.node,0x68,ctypes.addressof(self.font))
        self.owner=ctypes.create_string_buffer(0x700)
        struct.pack_into('<h',self.owner,0x128,504)
        struct.pack_into('<h',self.owner,0x12a,-1)
        adapter=assemble(f"""
            push rdi;push rsi;push r12;push r15;push rbx
            mov rbx,rcx
            mov rdi,[rbx]
            lea r12,[rdi+0x12c]
            mov r15,[rbx+8]
            mov esi,[rbx+16]
            mov edx,[rbx+20]
            mov r8d,86
            mov eax,24
            call {hex(BASE+CODE)}
            mov [rbx+24],r8d
            mov rax,r12
            pop rbx;pop r15;pop r12;pop rsi;pop rdi;ret
        """,BASE+0x1000)
        self.write(0x1000,adapter)
        self.call=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_void_p)(self.mem+0x1000)

    def tearDown(self):
        self.kernel.VirtualFree(self.mem,0,0x8000)

    def write(self,rva,data):ctypes.memmove(self.mem+rva,data,len(data))
    def state(self,offset,value=None):
        v=ctypes.c_int32.from_address(self.mem+STATE_RVA+offset)
        if value is not None:v.value=value
        return v.value

    def render(self,text,card=False,puzzle=False,menu=False):
        raw=text.encode('utf8')+b'\0'
        self.assertLess(len(raw),1024)
        ctypes.memmove(ctypes.addressof(self.owner)+0x12c,raw,len(raw))
        struct.pack_into('<h',self.owner,0x12a,41 if card else -1)
        struct.pack_into('<h',self.owner,0x128,535 if puzzle else 504)
        self.write(0x4a2f1d,bytes([menu]))
        n=len(text.split('\n'))
        args=ctypes.create_string_buffer(32)
        struct.pack_into('<QQII',args,0,ctypes.addressof(self.owner),ctypes.addressof(self.node),n,n*16//2)
        ptr=self.call(ctypes.addressof(args))
        return ctypes.string_at(ptr).decode('utf8'),struct.unpack_from('<i',args,24)[0]

    def test_native_old_reader_overflows_but_modified_window_fits(self):
        text='\n'.join('第%d行'%i for i in range(20))
        # Replay exactly the original replaced instructions as the red baseline.
        import pefile
        source=ROOT/'build/text-layout-fix/original/Dementium II.exe'
        if not source.is_file():self.skipTest('locally supplied original executable required')
        p=pefile.PE(str(source));self.assertEqual(p.get_data(HOOK_RVA,10),HOOK_BYTES)
        self.write(CODE,HOOK_BYTES[:3]+b'\xc3')
        baseline,y=self.render(text)
        self.assertEqual(baseline,text);self.assertLess(y,24)
        self.write(CODE,build_reader_code(CODE))
        actual,y=self.render(text)
        self.assertEqual(actual,'\n'.join(text.split('\n')[:9]))
        self.assertEqual(y,24);self.assertEqual(self.state(0),1)
        self.assertEqual(self.state(24),9)

    def test_wheel_clamps_and_reaches_every_last_line(self):
        text='\n'.join('第%d行'%i for i in range(20))
        self.render(text)
        self.state(4,-1)
        actual,_=self.render(text)
        self.assertEqual(self.state(16),3);self.assertTrue(actual.startswith('第3行'))
        self.state(4,-100)
        actual,_=self.render(text)
        self.assertEqual(self.state(16),11);self.assertTrue(actual.endswith('第19行'))
        self.state(4,100)
        actual,_=self.render(text)
        self.assertEqual(self.state(16),0);self.assertTrue(actual.startswith('第0行'))
        self.assertEqual(self.state(4),0)

    def test_keyboard_press_release_hold_and_menu_input_isolation(self):
        text='\n'.join('第%d行'%i for i in range(25))
        self.render(text)
        self.input[0x22e]=1
        self.render(text);self.assertEqual(self.state(16),1)
        for _ in range(19):self.render(text)
        self.assertEqual(self.state(16),1)
        for _ in range(5):self.render(text)
        self.assertGreater(self.state(16),1)
        before=self.state(16)
        for _ in range(30):self.render(text,menu=True)
        self.assertEqual(self.state(16),before)
        self.input[0x22e]=0;self.render(text)
        self.input[0x22d]=1;self.render(text)
        self.assertEqual(self.state(16),before-1)

    def test_blank_lines_indentation_and_active_emphasis_are_preserved(self):
        text='\n'.join(['标题','','  第一段','第二行','', '\x02强调开始']+['延续%d'%i for i in range(8)]+['\x01末段'])
        actual,_=self.render(text)
        self.assertTrue(actual.startswith('标题\n\n  第一段\n第二行\n\n'))
        self.assertTrue(actual.endswith('\x01'))
        self.state(4,-2);actual,_=self.render(text)
        self.assertTrue(actual.startswith('\x02延续0'))
        self.assertEqual(actual.count('\x02'),actual.count('\x01'))
        self.assertIn('延续',actual)

    def test_short_postcard_and_puzzle_paths_stay_unmodified(self):
        self.assertEqual(self.render('短文')[0],'短文');self.assertEqual(self.state(0),0)
        text='\n'.join(['甲乙']*20)
        self.assertEqual(self.render(text,card=True)[0],text);self.assertEqual(self.state(0),0)
        self.assertEqual(self.render(text,puzzle=True)[0],text);self.assertEqual(self.state(0),0)

    def test_illustrated_letters_scroll_inside_72px_not_postcard_area(self):
        text='\n'.join('信件第%d行'%i for i in range(8))
        for resource in [78,90,91,92,93]:
            struct.pack_into('<h',self.owner,0x128,resource)
            # Render helper uses 504 normally; invoke the ABI adapter directly.
            raw=text.encode('utf8')+b'\0';ctypes.memmove(ctypes.addressof(self.owner)+0x12c,raw,len(raw))
            struct.pack_into('<h',self.owner,0x12a,78)
            args=ctypes.create_string_buffer(32)
            struct.pack_into('<QQII',args,0,ctypes.addressof(self.owner),ctypes.addressof(self.node),8,128)
            ptr=self.call(ctypes.addressof(args))
            self.assertEqual(ctypes.string_at(ptr).decode('utf8'),'\n'.join(text.split('\n')[:4]))
            self.assertEqual(struct.unpack_from('<i',args,24)[0],104)
            self.assertEqual(self.state(24),4)
            self.state(4,-100);ptr=self.call(ctypes.addressof(args))
            self.assertTrue(ctypes.string_at(ptr).decode('utf8').endswith('信件第7行'))

    def test_inventory_letters_and_item_id_mapping_have_independent_viewport(self):
        self.write(CODE+0x800,build_reader_code(CODE+0x800,inventory=True))
        self.write(0x123383,b'\xc3')
        adapter=assemble(f"""
            push rdi;push rsi;push r12;push r14;push r15;push rbx
            mov rbx,rcx
            mov r14,[rbx]
            add r14,0x1e0
            mov rsi,[rbx+8]
            mov edi,[rbx+16]
            mov ecx,[rbx+20]
            xor r8d,r8d
            mov eax,24
            call {hex(BASE+CODE+0x800)}
            mov [rbx+24],r8d
            mov rax,r14
            pop rbx;pop r15;pop r14;pop r12;pop rsi;pop rdi;ret
        """,BASE+0x3000)
        self.write(0x3000,adapter)
        call=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_void_p)(self.mem+0x3000)
        # Inventory font node stores font/spacing at +40/+3c, unlike field node.
        node=ctypes.create_string_buffer(0x100)
        struct.pack_into('<Q',node,0x40,ctypes.addressof(self.font))
        text='\n'.join('库存信件第%d行'%i for i in range(8));raw=text.encode('utf8')+b'\0'
        ctypes.memmove(ctypes.addressof(self.owner)+0x1e0,raw,len(raw))
        args=ctypes.create_string_buffer(32)
        struct.pack_into('<QQII',args,0,ctypes.addressof(self.owner),ctypes.addressof(node),8,128)
        for resource in [78,90,91,92,93]:
            struct.pack_into('<I',self.owner,0x1d0,resource)
            ptr=call(ctypes.addressof(args))
            self.assertEqual(ctypes.string_at(ptr).decode('utf8'),'\n'.join(text.split('\n')[:4]))
            self.assertEqual(struct.unpack_from('<i',args,24)[0],88)
            self.state(4,-100);ptr=call(ctypes.addressof(args))
            self.assertTrue(ctypes.string_at(ptr).decode('utf8').endswith('库存信件第7行'))
            self.assertEqual(self.state(16),4)
        for resource in [41,42,43,45,46,47,48,49,50,51,52,53,73,74,85]:
            struct.pack_into('<I',self.owner,0x1d0,resource)
            ptr=call(ctypes.addressof(args))
            self.assertEqual(ctypes.string_at(ptr).decode('utf8'),text)
            self.assertEqual(self.state(0),0)

    def test_native_collection_stores_only_direct_ids_41_through_99(self):
        import pefile
        source=ROOT/'build/text-layout-fix/original/Dementium II.exe'
        if not source.is_file():self.skipTest('locked original executable required')
        p=pefile.PE(str(source));code=p.get_data(0x1562b3,0x1562cd-0x1562b3)
        self.assertEqual(code[:5],bytes.fromhex('83 f8 3a 77 15'))
        self.write(0x1562b3,code);self.write(0x1562cd,b'\xc3')
        self.write(0x4000,assemble(f"""
            push rbp;push rdi
            mov rbp,rcx
            mov edi,edx
            lea eax,[rdi-41]
            call {hex(BASE+0x1562b3)}
            pop rdi;pop rbp;ret
        """,BASE+0x4000))
        callback=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_uint32)(self.mem+0x4000)
        world=ctypes.create_string_buffer(0x4300)
        for resource in [41,53,78,90,99,40,100,500,501,504,535]:
            callback(ctypes.addressof(world),resource)
        self.assertEqual(world.raw[0x41eb],5)
        self.assertEqual(list(world.raw[0x41b0:0x41b5]),[41,53,78,90,99])

    def test_native_open_and_close_clear_transient_state(self):
        for offset in range(0,32,4):self.state(offset,17)
        code=reset_code(BASE+0x2000,BASE+0x2100,bytes.fromhex('40 53 48 83 ec 20'))
        self.write(0x2000,code);self.write(0x2100,bytes.fromhex('48 83 c4 20 5b c3'))
        ctypes.CFUNCTYPE(None)(self.mem+0x2000)()
        self.assertEqual([self.state(o) for o in range(0,32,4)],[0]*8)

if __name__=='__main__':unittest.main(verbosity=2)
