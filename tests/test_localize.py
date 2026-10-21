"""Synthetic fixtures only: no installed game or copyrighted assets required."""
import copy
import json
from pathlib import Path
import random
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from localize import Zar, apply_delta, extract, import_text, make_delta, validate


def fixture(members=None):
    members = members or {'EN/GUI.TBL': b'\xef\xbb\xbfNew Game\r\n\r\nResume\n',
                          'EN/TEST.SUB': b'{1}{300}Hello|\x02$K\x01\r\n'}
    names = sorted(members)
    pool = bytearray()
    offsets = []
    for name in names:
        offsets.append(len(pool))
        pool.extend(name.encode('ascii') + b'\0')
    strings = 32 + 4 * len(names)
    toc = strings + len(pool)
    out = bytearray(1024)
    struct.pack_into('<8I', out, 0, int.from_bytes(b'ZAR1', 'little'), len(names), 1024, 0, 32, strings, toc, 0)
    struct.pack_into('<' + 'I' * len(names), out, 32, *offsets)
    out[strings:toc] = pool
    for i, name in enumerate(names):
        out.extend(b'\0' * (-len(out) % 512))
        struct.pack_into('<QQQ', out, toc + i * 24, len(out), len(members[name]), 0)
        out.extend(members[name])
    return bytes(out)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        self.zar = Zar(self.data)

    def test_noop_is_byte_identical(self):
        self.assertEqual(self.zar.rebuild({n: self.zar.read(n) for n in self.zar.entries}), self.data)

    def test_resize_preserves_other_members(self):
        after = Zar(self.zar.rebuild({'EN/GUI.TBL': '新游戏，123 ABC'.encode('utf-8') * 500}))
        self.assertEqual(after.read('EN/TEST.SUB'), self.zar.read('EN/TEST.SUB'))
        self.assertEqual(after.entries['EN/GUI.TBL'].offset % 512, 0)

    def test_unknown_replacement(self):
        with self.assertRaises(ValueError): self.zar.rebuild({'UNKNOWN': b'X'})

    def test_bad_magic(self):
        with self.assertRaises(ValueError): Zar(b'FAIL' + self.data[4:])

    def test_truncated(self):
        for size in [0, 4, 31, 32, 64, 1023, len(self.data) - 1]:
            with self.subTest(size=size), self.assertRaises(ValueError): Zar(self.data[:size])

    def test_header_variants(self):
        for offset, value in [(4, 0), (4, 0xffffffff), (12, 1), (28, 1), (16, 8), (20, 0), (24, 0xffffffff)]:
            bad = bytearray(self.data); struct.pack_into('<I', bad, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError): Zar(bytes(bad))

    def test_member_bounds_alignment_and_metadata(self):
        toc = self.zar.entries['EN/GUI.TBL'].toc
        for off, value in [(toc, 513), (toc, len(self.data) + 1), (toc + 8, len(self.data)), (toc + 16, 1)]:
            bad = bytearray(self.data); struct.pack_into('<Q', bad, off, value)
            with self.subTest(off=off, value=value), self.assertRaises(ValueError): Zar(bytes(bad))

    def test_duplicate_names_and_traversal(self):
        bad = bytearray(self.data); struct.pack_into('<I', bad, 36, 0)
        with self.assertRaises(ValueError): Zar(bytes(bad))
        for name in ['../X', '/ABS', 'C:/X', 'A\\B']:
            with self.subTest(name=name), self.assertRaises(ValueError): Zar(fixture({name: b'x'}))

    def test_overlap(self):
        bad = bytearray(self.data)
        struct.pack_into('<Q', bad, self.zar.entries['EN/TEST.SUB'].toc, 1024)
        with self.assertRaises(ValueError): Zar(bytes(bad))


class TextTests(unittest.TestCase):
    def setUp(self):
        self.zar = Zar(fixture())
        self.rows = extract(self.zar)

    def test_bom_blank_rows_and_exact_offsets(self):
        self.assertEqual([r['line'] for r in self.rows[:2]], [0, 2])
        self.assertEqual(self.rows[0]['offset'], 3)
        self.assertEqual(self.rows[2]['prefix'], '{1}{300}')
        self.assertEqual(self.rows[2]['source'], 'Hello|\x02$K\x01')

    def test_unicode_and_newlines_preserved(self):
        self.rows[0]['target'] = '新游戏'
        changes = import_text(self.zar, self.rows)
        self.assertEqual(changes['EN/GUI.TBL'], '\ufeff新游戏\r\n\r\nResume\n'.encode('utf-8'))
        self.assertEqual(extract(Zar(self.zar.rebuild(changes)))[0]['source'], '新游戏')

    def test_accent_json_roundtrip(self):
        zar = Zar(fixture({'EN/GUI.TBL': 'MARÍA / HÖNOW / INÊS'.encode('utf-8')}))
        rows = json.loads(json.dumps(extract(zar), ensure_ascii=False))
        validate(rows, extract(zar))

    def test_placeholder_loss_and_order(self):
        for text in ['你好|$K', '你好|\x01$K\x02', '你好\x02$K\x01']:
            rows = copy.deepcopy(self.rows); rows[2]['target'] = text
            with self.subTest(text=text), self.assertRaises(ValueError): validate(rows, self.rows)

    def test_row_injection_nul_bom_and_surrogate(self):
        for text in ['新\n游戏', '新\r游戏', '新\0游戏', '\ufeff新', '\ud800']:
            rows = copy.deepcopy(self.rows); rows[0]['target'] = text
            with self.subTest(text=repr(text)), self.assertRaises((ValueError, UnicodeError)): validate(rows, self.rows)

    def test_duplicate_missing_unknown_and_stale(self):
        cases = [self.rows[:-1], self.rows + [self.rows[0]]]
        for field in ['id', 'source', 'resource', 'prefix', 'resource_sha256']:
            rows = copy.deepcopy(self.rows); rows[0][field] += 'X'; cases.append(rows)
        rows = copy.deepcopy(self.rows); rows[0]['offset'] += 1; cases.append(rows)
        for rows in cases:
            with self.subTest(rows=rows[0]['id']), self.assertRaises(ValueError): validate(rows, self.rows)

    def test_document_control_codes(self):
        zar = Zar(fixture({'EN/EXAMINE.001': b'\xef\xbb\xbf\r\nIt is \x02a key\x01. $Lock,1$\r\n'}))
        rows = extract(zar); rows[0]['target'] = '\r\n这是\x02钥匙\x01。$Lock,1$\r\n'
        import_text(zar, rows)
        rows[0]['target'] = '钥匙。'
        with self.assertRaises(ValueError): import_text(zar, rows)

    def test_puzzle_guard(self):
        zar = Zar(fixture({'EN/ALPHA.TBL': b'HATE\nFEAR'})); rows = extract(zar)
        rows[0]['target'] = '憎恨'
        with self.assertRaises(ValueError): import_text(zar, rows)

    def test_bad_subtitle_and_encoding(self):
        for name, data in [('EN/TEST.SUB', b'Hello'), ('EN/GUI.TBL', b'\xff')]:
            with self.subTest(name=name), self.assertRaises((ValueError, UnicodeError)): extract(Zar(fixture({name: data})))


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.original = fixture()
        self.modified = Zar(self.original).rebuild({'EN/GUI.TBL': '新游戏'.encode('utf-8')})
        self.patch = make_delta(self.original, self.modified)

    def test_apply_and_rollback(self):
        self.assertEqual(apply_delta(self.original, self.patch), self.modified)
        self.assertEqual(apply_delta(self.modified, self.patch, reverse=True), self.original)

    def test_wrong_build_and_double_apply(self):
        for data in [self.original + b'X', b'FAIL' + self.original[4:], self.modified]:
            with self.assertRaises(ValueError): apply_delta(data, self.patch)

    def test_tampered_append_runs_and_hash(self):
        for field in ['append', 'modified_sha256']:
            patch = copy.deepcopy(self.patch); patch[field] += 'A'
            with self.assertRaises(ValueError): apply_delta(self.original, patch)
        patch = copy.deepcopy(self.patch); patch['runs'][0]['old'] = '00'
        with self.assertRaises(ValueError): apply_delta(self.original, patch)

    def test_noop(self):
        patch = make_delta(self.original, self.original)
        self.assertEqual(apply_delta(self.original, patch), self.original)

    def test_seeded_payload_sizes(self):
        rng = random.Random(5342930)
        for size in [1, 511, 512, 513, 65535, 65536, 65537]:
            payload = rng.randbytes(size)
            modified = Zar(self.original).rebuild({'EN/GUI.TBL': payload})
            patch = make_delta(self.original, modified)
            self.assertEqual(apply_delta(modified, patch, reverse=True), self.original)


if __name__ == '__main__':
    unittest.main()
