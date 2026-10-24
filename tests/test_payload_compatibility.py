"""Version recipes remain explicit, with no inferred native compatibility."""
import copy
import json
import tempfile
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_resource_payload import add_compatibility, native_hash_guards, make_payload
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

    def test_multiple_builds_keep_all_resource_and_native_variants(self):
        current, middle, oldest = [self.payload(v) for v in ('current', 'middle', 'oldest')]
        add_compatibility(current, middle)
        add_compatibility(current, oldest)
        for patch in (current['members'][0], current['native_executable']):
            self.assertEqual([p['source_sha256'] for p in patch['source_variants']], ['middle', 'oldest'])

    def test_nested_compatibility_is_flattened_and_deduplicated(self):
        current, middle, oldest = [self.payload(v) for v in ('current', 'middle', 'oldest')]
        add_compatibility(middle, oldest)
        add_compatibility(current, oldest)
        add_compatibility(current, middle)
        for patch in (current['members'][0], current['native_executable']):
            self.assertEqual([p['source_sha256'] for p in patch['source_variants']], ['oldest', 'middle'])
            self.assertTrue(all('source_variants' not in p for p in patch['source_variants']))

    def test_compatibility_import_does_not_alias_inputs(self):
        current, previous = self.payload('current'), self.payload('previous')
        add_compatibility(current, previous)
        previous['native_executable']['source_sha256'] = 'changed'
        previous['members'][0]['source_sha256'] = 'changed'
        self.assertEqual(current['native_executable']['source_variants'][0]['source_sha256'], 'previous')
        self.assertEqual(current['members'][0]['source_variants'][0]['source_sha256'], 'previous')

    def test_resource_only_rebuild_does_not_require_current_native_identity(self):
        from test_localize import fixture as zar_fixture
        from localize import Zar, make_delta
        original = zar_fixture({'EN/A.TBL': b'New Game'})
        modified = Zar(original).rebuild({'EN/A.TBL': '新游戏'.encode()})
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            (build/'rom.zar').write_bytes(modified)
            (build/'patch.json').write_text(json.dumps(make_delta(original, modified)))
            (build/'exe-patch.json').write_text('INVALID NATIVE MANIFEST')
            recipe = build/'recipe.json'
            recipe.write_text(json.dumps({'entries': []}))
            payload = make_payload(build, recipe, include_native=False)
            self.assertNotIn('native_executable', payload)
            self.assertEqual(payload['members'][0]['source_sha256'], digest(b'New Game'))
            self.assertEqual(payload['members'][0]['target_sha256'], digest('新游戏'.encode()))

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
