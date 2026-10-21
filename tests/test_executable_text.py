"""Synthetic PE fixtures; no game binaries or execution needed."""
import copy
import hashlib
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from executable_text import build_executable, apply_executable_patch


def fixture():
    data = bytearray(1024)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 70, 1)
    section = 88
    data[section:section+8] = b'.rdata\0\0'
    struct.pack_into('<II', data, section+16, 512, 512)
    struct.pack_into('<I', data, section+36, 0x40000040)
    data[600:605] = b'RETRO'
    data[612:616] = b'NEXT'
    data = bytes(data)
    recipe = dict(schema=1, encoding='utf-8', source_size=len(data),
                  source_sha256=hashlib.sha256(data).hexdigest(), entries=[
                      dict(id='retro', offset=600, slot_size=12,
                           source='RETRO', target='复古')])
    return data, recipe


class ExecutableTextTests(unittest.TestCase):
    def test_reordered_recipe_emits_canonical_offset_order(self):
        data, recipe = fixture()
        recipe['entries'].insert(0, dict(id='next', offset=612, slot_size=12, source='NEXT', target='下项'))
        modified, patch = build_executable(data, recipe)
        self.assertEqual([run['offset'] for run in patch['runs']], [600, 612])
        self.assertEqual(apply_executable_patch(data, patch), modified)
        self.assertEqual(apply_executable_patch(modified, patch, True), data)

    def setUp(self):
        self.data, self.recipe = fixture()

    def test_utf8_extends_only_into_audited_zeros(self):
        modified, patch = build_executable(self.data, self.recipe)
        self.assertEqual(len(modified), len(self.data))
        self.assertEqual(modified[:600], self.data[:600])
        self.assertEqual(modified[612:], self.data[612:])
        self.assertEqual(modified[600:612], '复古'.encode()+b'\0'*6)
        self.assertEqual(apply_executable_patch(self.data, patch), modified)
        self.assertEqual(apply_executable_patch(modified, patch, reverse=True), self.data)

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            build_executable(self.data+b'?', self.recipe)

    def test_oversized_utf8_rejected(self):
        self.recipe['entries'][0]['target'] = '超出固定槽的长文本'
        with self.assertRaises(ValueError):
            build_executable(self.data, self.recipe)

    def test_nonzero_padding_rejected_even_with_known_input(self):
        data = bytearray(self.data)
        data[608] = 1
        data = bytes(data)
        self.recipe['source_sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(ValueError):
            build_executable(data, self.recipe)

    def test_code_or_headers_cannot_be_patched(self):
        self.recipe['entries'][0].update(offset=400, source='', target='A')
        with self.assertRaises(ValueError):
            build_executable(self.data, self.recipe)

    def test_embedded_nul_rejected(self):
        self.recipe['entries'][0]['target'] = 'A\0B'
        with self.assertRaises(ValueError):
            build_executable(self.data, self.recipe)

    def test_overlapping_slots_rejected(self):
        self.recipe['entries'].append(copy.deepcopy(self.recipe['entries'][0]))
        with self.assertRaises(ValueError):
            build_executable(self.data, self.recipe)

    def test_tampered_patch_or_input_rejected(self):
        modified, patch = build_executable(self.data, self.recipe)
        for data in [self.data+b'!', modified]:
            with self.assertRaises(ValueError):
                apply_executable_patch(data, patch)
        patch['runs'][0]['new'] = (b'WRONG'+b'\0'*7).hex()
        with self.assertRaises(ValueError):
            apply_executable_patch(self.data, patch)

    def test_executable_section_rejected(self):
        data = bytearray(self.data)
        struct.pack_into('<I', data, 88+36, 0x60000040)
        data = bytes(data)
        self.recipe['source_sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(ValueError):
            build_executable(data, self.recipe)

    def test_truncated_pe_rejected(self):
        data = b'MZ'
        self.recipe['source_size'] = 2
        self.recipe['source_sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaises(ValueError):
            build_executable(data, self.recipe)


if __name__ == '__main__':
    unittest.main()
