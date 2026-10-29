"""Build26286386 real49-row loader, melee option, and context isolation."""
import os,struct,sys,unittest
from pathlib import Path
import pefile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from replay_option_loader import replay_bytes
from native_replay import require_native_fixture
EXE=Path(os.environ.get('DEMENTIUM_26286386_TEST_EXE',ROOT/'build/full-zh-CN/Dementium II.exe'))
ROM=Path(os.environ.get('DEMENTIUM_PREVIEW_ROM',ROOT/'build/full-zh-CN/rom.zar'))
ORIGINAL=ROOT/'build/inputs/26286386'

class NativeOptionLoader26286386Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_native_fixture(EXE,'26286386')
        cls.exe=EXE.read_bytes();cls.rom=ROM.read_bytes();cls.pe=pefile.PE(data=cls.exe)
    def test_native49_rows_keep_melee_label_and_slot49_buffer(self):
        r=replay_bytes(self.exe,self.rom)
        self.assertEqual(r['loader_rows'],49);self.assertEqual(r['resource_rows'],49)
        self.assertEqual(r['native_table_capacity'],49)
        self.assertEqual(r['melee_option_label'],'近战准星')
        self.assertFalse(r['slot48_is_backing_buffer']);self.assertTrue(r['slot49_is_backing_buffer'])
        self.assertTrue(r['backing_buffer_is_after_rows'])
    def test_head_bob_and_melee_setting_bits_are_independent(self):
        r=replay_bytes(self.exe,self.rom)
        self.assertEqual(r['head_bob_all_states'],['普通','轻微','关闭']+['普通']*5)
        self.assertEqual(r['head_bob_with_melee_crosshairs'],r['head_bob_all_states'])
        self.assertEqual(r['melee_crosshairs'],['关','开'])
        self.assertEqual(r['minimap'],['关','半透明','不透明'])
        self.assertTrue(r['settings_preserved'])
    def test_same_rom_repurposed48th_and49th_indices_go_red(self):
        green=replay_bytes(self.exe,self.rom)
        for index,label in [(48,'近战准星'),(49,'反转')]:
            broken=bytearray(self.exe);at=self.pe.get_offset_from_rva(0x12b6da)
            broken[at:at+8]=bytes.fromhex('49 63 8c 83 70 0a 44 00')
            struct.pack_into('<I',broken,self.pe.get_offset_from_rva(0x440a70)+4,index)
            red=replay_bytes(bytes(broken),self.rom)
            self.assertEqual(red['head_bob'],['普通',label,'关'])
            self.assertEqual(green['head_bob'],['普通','轻微','关闭'])
            self.assertEqual(red['rom_sha256'],green['rom_sha256'])
            self.assertEqual(red['melee_option_label'],green['melee_option_label'])
            self.assertEqual(red['melee_crosshairs'],green['melee_crosshairs'])
            self.assertTrue(red['settings_preserved'])
    def test_real_loader_context_and_melee_survive_image_relocation(self):
        r=replay_bytes(self.exe,self.rom,image_base=0x180000000)
        self.assertEqual(r['head_bob'],['普通','轻微','关闭'])
        self.assertEqual(r['melee_crosshairs'],['关','开'])
        self.assertEqual(r['minimap'],['关','半透明','不透明'])
        self.assertTrue(r['settings_preserved'])
    def test_capacity_regression_to48_is_rejected(self):
        bad=bytearray(self.exe);bad[self.pe.get_offset_from_rva(0x12ebf9)+2]=48
        with self.assertRaisesRegex(ValueError,'loader source guard'):replay_bytes(bytes(bad),self.rom)
    def test_unknown_getter_jump_or_context_code_is_rejected(self):
        ui=next(s.VirtualAddress for s in self.pe.sections if s.Name.rstrip(b'\0')==b'.locui')
        for address in (0x12b6db,ui+0xe00):
            bad=bytearray(self.exe);bad[self.pe.get_offset_from_rva(address)]^=1
            with self.assertRaisesRegex(ValueError,'context (?:hook|code) guard'):replay_bytes(bytes(bad),self.rom)
    def test_context_rejects_table_row48_and49_repurposing(self):
        for index in (48,49):
            bad=bytearray(self.exe);struct.pack_into('<I',bad,self.pe.get_offset_from_rva(0x440a70)+4,index)
            with self.assertRaisesRegex(ValueError,'index table guard'):replay_bytes(bytes(bad),self.rom)
    def test_melee_getter_code_mutation_is_rejected(self):
        bad=bytearray(self.exe);bad[self.pe.get_offset_from_rva(0x12b6f4)]^=1
        with self.assertRaisesRegex(ValueError,'getter source guard'):replay_bytes(bytes(bad),self.rom)
    def test_original_loader_getter_and_melee_states_replay_english(self):
        r=replay_bytes((ORIGINAL/'Dementium II.exe').read_bytes(),(ORIGINAL/'rom.zar').read_bytes())
        self.assertEqual(r['head_bob'],['NORMAL','SUBTLE','OFF'])
        self.assertEqual(r['loader_rows'],49);self.assertEqual(r['melee_option_label'],'MELEE CROSSHAIRS')
        self.assertEqual(r['melee_crosshairs'],['OFF','ON']);self.assertEqual(r['row0'],'Inverted')
        self.assertTrue(r['settings_preserved'])

if __name__=='__main__':unittest.main()
