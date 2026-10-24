"""Version/hash/consumer guards for the shipped 1.0.3 native profile."""
import copy,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import native_profile as profiles
from executable_text import build_executable
from debug_menu import config,build_menu
from menu_input import patch_menu_input
from localize import digest
SOURCE=ROOT/'build/inputs/26152271/Dementium II.exe'

class NativeProfileGuardTests(unittest.TestCase):
    def test_unknown_profile_and_unmapped_address_rejected(self):
        for build,address,pattern in [('unknown',0,'Unknown'),('26152271',0xdeadbeef,'Unmapped')]:
            token=profiles._ACTIVE.set(build)
            try:
                with self.assertRaisesRegex(ValueError,pattern):profiles.rva(address)
            finally:profiles.restore(token)

@unittest.skipUnless(SOURCE.is_file(),'requires clean build 26152271 PE')
class ShippedNativeGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=SOURCE.read_bytes()
        cls.recipe=json.loads((ROOT/'locales/zh-CN/executable-text.json').read_text(encoding='utf8'))
        cls.localized,_=build_executable(cls.original,cls.recipe)
    def test_unknown_full_source_hash_rejected(self):
        damaged=bytearray(self.original);damaged[-1]^=1
        with self.assertRaisesRegex(ValueError,'identity'):build_executable(bytes(damaged),self.recipe)
        with self.assertRaisesRegex(ValueError,'verified'):profiles.select(bytes(damaged),config())
    def test_new_build_cannot_bind_old_profile_even_with_caller_hash(self):
        recipe=copy.deepcopy(config());recipe['input_sha256_by_build']={'26123896':digest(self.localized)}
        with self.assertRaisesRegex(ValueError,'layout mismatch'):profiles.select(self.localized,recipe)
    def test_real_consumer_guard_rejects_mutated_held_key_array_reference(self):
        import pefile
        damaged=bytearray(self.localized);pe=pefile.PE(data=self.localized)
        damaged[pe.get_offset_from_rva(0x2dfd5a)+4]^=1
        token=profiles._ACTIVE.set('26152271')
        try:
            with self.assertRaisesRegex(ValueError,'provenance'):patch_menu_input(bytes(damaged))
        finally:profiles.restore(token)
    def test_native_hook_guard_rejects_mutated_unlock_branch(self):
        import pefile
        damaged=bytearray(self.localized);pe=pefile.PE(data=self.localized)
        damaged[pe.get_offset_from_rva(0x4fd18)]^=1
        # Isolate byte guards below full-identity selection. A production build
        # rejects this even earlier because config retains the shipped digest.
        recipe=copy.deepcopy(config());recipe['input_sha256_by_build']['26152271']=digest(damaged)
        with self.assertRaisesRegex(ValueError,'Unlock branch guard'):build_menu(bytes(damaged),recipe)

if __name__=='__main__':unittest.main()
