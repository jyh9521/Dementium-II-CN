"""Real table-loader regression: pointer slot 48 is the backing buffer, not a row."""
import json,os,struct,sys,unittest
from pathlib import Path
import pefile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from replay_option_loader import replay_bytes
EXE=Path(os.environ.get('DEMENTIUM_MODIFIED_EXE',ROOT/'build/full-zh-CN/Dementium II.exe'))
ROM=Path(os.environ.get('DEMENTIUM_PREVIEW_ROM',ROOT/'build/full-zh-CN/rom.zar'))

@unittest.skipUnless(EXE.is_file() and ROM.is_file(),'requires supplied native current build and ROM')
class NativeOptionLoaderV104Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe=EXE.read_bytes();cls.rom=ROM.read_bytes();cls.pe=pefile.PE(data=cls.exe)
        data=next(s.VirtualAddress for s in cls.pe.sections if s.Name.rstrip(b'\0')==b'.data')
        if data!=0x4cd000:raise unittest.SkipTest('requires build 26260428 option fixture')
    def test_same_real_rom_old_49th_index_goes_red_then_context_hook_goes_green(self):
        broken=bytearray(self.exe)
        at=self.pe.get_offset_from_rva(0x12b6fa);broken[at:at+8]=bytes.fromhex('49 63 8c 83 80 0a 44 00')
        struct.pack_into('<I',broken,self.pe.get_offset_from_rva(0x440a80)+4,48)
        red=replay_bytes(bytes(broken),self.rom);green=replay_bytes(self.exe,self.rom)
        self.assertEqual(red['head_bob'],['普通','反转','关'])
        self.assertEqual(green['head_bob'],['普通','轻微','关闭'])
        self.assertEqual(red['rom_sha256'],green['rom_sha256'])
        self.assertEqual(red['loader_rows'],48);self.assertTrue(red['slot48_is_backing_buffer'])
        self.assertEqual(green['resource_rows'],48)
        self.assertEqual(green['minimap'],red['minimap'])
        self.assertEqual(green['row0'],red['row0']);self.assertEqual(green['row0'],'反转')
        self.assertTrue(red['settings_preserved']);self.assertTrue(green['settings_preserved'])
    def test_all_settings_states_normalize_without_mutation(self):
        result=replay_bytes(self.exe,self.rom)
        self.assertEqual(result['head_bob_all_states'],['普通','轻微','关闭']+['普通']*5)
        self.assertEqual(result['minimap'],['关','半透明','不透明'])
        self.assertTrue(result['settings_preserved'])
    def test_actual_loader_and_context_literals_survive_image_relocation(self):
        result=replay_bytes(self.exe,self.rom,image_base=0x180000000)
        self.assertEqual(result['head_bob'],['普通','轻微','关闭'])
        self.assertEqual(result['minimap'],['关','半透明','不透明'])
        self.assertTrue(result['settings_preserved'])
    def test_native_loader_capacity_mutation_is_rejected(self):
        bad=bytearray(self.exe);bad[self.pe.get_offset_from_rva(0x12ebb9)+2]=49
        with self.assertRaisesRegex(ValueError,'loader source guard'):replay_bytes(bytes(bad),self.rom)
    def test_unknown_getter_jump_or_context_code_is_rejected(self):
        ui=next(s.VirtualAddress for s in self.pe.sections if s.Name.rstrip(b'\0')==b'.locui')
        for address in (0x12b6fb,ui+0xe00):
            bad=bytearray(self.exe);bad[self.pe.get_offset_from_rva(address)]^=1
            with self.assertRaisesRegex(ValueError,'context (?:hook|code) guard'):replay_bytes(bytes(bad),self.rom)
    def test_context_stub_rejects_reintroduced_table_extension_index(self):
        bad=bytearray(self.exe);struct.pack_into('<I',bad,self.pe.get_offset_from_rva(0x440a80)+4,48)
        with self.assertRaisesRegex(ValueError,'index table guard'):replay_bytes(bytes(bad),self.rom)
    def test_unmodified_current_loader_and_getter_replay_english_baseline(self):
        original=ROOT/'build/original'
        if not (original/'Dementium II.exe').is_file() or not (original/'rom.zar').is_file():
            self.skipTest('requires preserved current original inputs')
        result=replay_bytes((original/'Dementium II.exe').read_bytes(),(original/'rom.zar').read_bytes())
        self.assertEqual(result['head_bob'],['NORMAL','SUBTLE','OFF'])
        self.assertEqual(result['loader_rows'],48)
        self.assertEqual(result['row0'],'Inverted')
        self.assertTrue(result['settings_preserved'])

if __name__=='__main__':unittest.main()
