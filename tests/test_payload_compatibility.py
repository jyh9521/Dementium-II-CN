"""Version recipes remain explicit, with no inferred native compatibility."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_resource_payload import add_compatibility, native_hash_guards
from localize import digest
from test_executable_text import fixture


class CompatibilityPayloadTests(unittest.TestCase):
    def payload(self, version):
        return dict(schema=1,members=[dict(name='EN/OPTIONSNEW.TBL',source_sha256=version)],
                    native_executable=dict(name='Dementium II.exe',source_sha256=version))

    def test_different_resource_preimage_is_preserved_as_variant(self):
        new,old=self.payload('new'),self.payload('old')
        add_compatibility(new,old)
        self.assertEqual(new['members'][0]['source_variants'],old['members'])
        self.assertEqual(new['native_executable']['source_variants'],[old['native_executable']])

    def test_same_resource_source_uses_current_target(self):
        new,old=self.payload('new'),self.payload('old')
        old['members'][0]['source_sha256']='new'
        add_compatibility(new,old)
        self.assertNotIn('source_variants',new['members'][0])

    def test_unmapped_old_resource_rejected(self):
        new,old=self.payload('new'),self.payload('old')
        old['members'].append(dict(name='OLD_ONLY',source_sha256='old'))
        with self.assertRaisesRegex(ValueError,'Unmapped legacy'):add_compatibility(new,old)

    def test_duplicate_executable_is_not_a_second_verified_build(self):
        with self.assertRaisesRegex(ValueError,'duplicates'):add_compatibility(self.payload('same'),self.payload('same'))

    def test_native_guards_record_both_preimage_and_target_hashes(self):
        original,_=fixture()
        import struct
        data=bytearray(original)
        pe=struct.unpack_from('<I',data,60)[0]
        struct.pack_into('<I',data,pe+24+60,512)
        target=bytearray(data);target[-1]^=1
        guards=native_hash_guards(bytes(data),bytes(target))
        self.assertEqual(guards[0]['offset'],0)
        self.assertGreaterEqual(guards[0]['length'],512)
        self.assertTrue(all(g['sha256']==digest(data[g['offset']:g['offset']+g['length']]) for g in guards))
        self.assertTrue(all(g['target_sha256']==digest(target[g['offset']:g['offset']+g['length']]) for g in guards))


if __name__=='__main__':unittest.main()
