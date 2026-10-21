import struct
import unittest

from test_localize import fixture
from localize import Zar
from check_runtime_assets import index_rows


def indexed_fixture():
    names = ['EN/GUI.TBL', 'FONT.PNG']
    values = [b'New Game', b'SYNTHETIC PNG BUFFER']
    pool = b''
    rows = bytearray(struct.pack('<Q', len(names)))
    for name, value in zip(names, values):
        rows.extend(struct.pack('<IIQ', len(value), 0, len(pool)))
        pool += ('/' + name.lower()).encode() + b'\0'
    return fixture(dict(zip(names, values)) | {'~INDEX': bytes(rows) + pool})


class VfsIndexTests(unittest.TestCase):
    def test_bad_index_rejected(self):
        for data in [b'', struct.pack('<Q', 100), struct.pack('<QIIQ', 1, 2, 0, 999) + b'/a\0']:
            with self.subTest(data=data), self.assertRaises(ValueError): list(index_rows(data))

    def test_unterminated_and_duplicate_index_names(self):
        for data in [struct.pack('<QIIQ', 1, 2, 0, 0) + b'/a',
                     struct.pack('<QIIQIIQ', 2, 1, 0, 0, 2, 0, 0) + b'/a\0']:
            with self.assertRaises(ValueError): list(index_rows(data))

    def test_resize_updates_secondary_size_manifest(self):
        zar = Zar(indexed_fixture())
        result = Zar(zar.rebuild({'FONT.PNG': b'LARGER SYNTHETIC IMAGE' * 12}))
        manifest = {name: size for name, size, _, _ in index_rows(result.read('~INDEX'))}
        self.assertEqual(manifest['FONT.PNG'], result.entries['FONT.PNG'].size)

    def test_table_growth_updates_secondary_size_manifest(self):
        zar = Zar(indexed_fixture())
        result = Zar(zar.rebuild({'EN/GUI.TBL': '新游戏'.encode('utf-8')}))
        manifest = {name: size for name, size, _, _ in index_rows(result.read('~INDEX'))}
        self.assertEqual(manifest['EN/GUI.TBL'], 9)

    def test_noop_keeps_index_byte_identical(self):
        data = indexed_fixture()
        self.assertEqual(Zar(data).rebuild({}), data)

    def test_only_size_fields_change(self):
        zar = Zar(indexed_fixture())
        result = Zar(zar.rebuild({'FONT.PNG': b'X' * 300}))
        old, new = zar.read('~INDEX'), result.read('~INDEX')
        slot = next(offset for name, _, _, offset in index_rows(old) if name == 'FONT.PNG')
        self.assertEqual(old[:slot], new[:slot])
        self.assertEqual(old[slot + 4:], new[slot + 4:])

    def test_manually_replaced_index_rejected(self):
        zar = Zar(indexed_fixture())
        with self.assertRaises(ValueError): zar.rebuild({'~INDEX': b'X'})

    def test_flagged_entry_resize_rejected(self):
        source = Zar(indexed_fixture())
        index = bytearray(source.read('~INDEX'))
        struct.pack_into('<I', index, 12, 1)
        members = {n: source.read(n) for n in source.entries}
        members['~INDEX'] = bytes(index)
        zar = Zar(fixture(members))
        with self.assertRaises(ValueError): zar.rebuild({'EN/GUI.TBL': b'X' * 30})
