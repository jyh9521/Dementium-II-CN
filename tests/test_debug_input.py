"""Offline CPU replay of bounded native input snippets; never starts the game.

The proprietary input is optional, ignored build data. Every copied instruction
is read from the SHA-256 locked original, with only the two documented changes.
No window, Steam API, save I/O, or native external call is executed.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import platform
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('DEMENTIUM_SOURCE_EXE', ROOT / 'build/text-layout-fix/original/Dementium II.exe'))
SOURCE_SHA = 'ea68364b72c7c1ef5b84d24990ddcab6090eedff752736d3ef3c634733351e56'
BASE = 0x140000000
VISIBLE = 0x4a2f1d
ALLOW = 0x4a2f1c
PREVIOUS = 0xa34527
SIZE = 0xb10000


@unittest.skipUnless(os.name == 'nt' and platform.machine().lower() in ('amd64', 'x86_64') and SOURCE.is_file(),
                     'native x64 Windows replay requires the locally supplied original EXE')
class NativeDebugInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_replay import require_native_fixture
        require_native_fixture(SOURCE)
        import pefile
        cls.original = SOURCE.read_bytes()
        if hashlib.sha256(cls.original).hexdigest() != SOURCE_SHA:
            raise ValueError('Native replay original SHA-256 mismatch')
        cls.pe = pefile.PE(data=cls.original)
        cls.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        cls.kernel.VirtualAlloc.restype = ctypes.c_void_p
        cls.kernel.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
        cls.kernel.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]

    @classmethod
    def source_bytes(cls, start, end):
        offset = cls.pe.get_offset_from_rva(start)
        return cls.original[offset:offset + end - start]

    def setUp(self):
        self.memory = self.kernel.VirtualAlloc(None, SIZE, 0x3000, 0x40)
        if not self.memory:
            raise ctypes.WinError(ctypes.get_last_error())

    def tearDown(self):
        self.kernel.VirtualFree(self.memory, 0, 0x8000)

    def write(self, rva, data):
        ctypes.memmove(self.memory + rva, data, len(data))

    def byte(self, rva, value=None):
        cell = ctypes.c_ubyte.from_address(self.memory + rva)
        if value is not None:
            cell.value = value
        return cell.value

    def word(self, rva):
        return ctypes.c_uint32.from_address(self.memory + rva).value

    def callable(self, rva, *args):
        return ctypes.CFUNCTYPE(ctypes.c_uint32, *args)(self.memory + rva)

    def install_toggle(self, modified):
        # Preserve RSI per the Windows x64 ABI. ECX is the supplied key state.
        self.write(0x4fa2a, bytes.fromhex('56 31 f6 90'))
        code = bytearray(self.source_bytes(0x4fa2e, 0x4fa66))
        self.assertEqual(code[0x4fa49 - 0x4fa2e:0x4fa4b - 0x4fa2e], bytes.fromhex('75 04'))
        if modified:
            code[0x4fa49 - 0x4fa2e] = 0xeb
        self.write(0x4fa2e, bytes(code))
        self.write(0x4fa66, bytes.fromhex('5e c3'))
        return self.callable(0x4fa2a, ctypes.c_uint32)

    def test_baseline_locked_gate_and_unlocked_gate(self):
        toggle = self.install_toggle(False)
        toggle(1)
        self.assertEqual(self.byte(VISIBLE), 0)
        self.byte(PREVIOUS, 0)
        self.byte(ALLOW, 1)
        toggle(1)
        self.assertEqual(self.byte(VISIBLE), 1)

    def test_modified_rising_edge_open_hold_release_close(self):
        toggle = self.install_toggle(True)
        result = []
        for key in (0, 1, 1, 0, 1, 1, 0, 1):
            toggle(key)
            result.append(self.byte(VISIBLE))
        self.assertEqual(result, [0, 1, 1, 1, 0, 0, 0, 1])
        self.assertEqual(self.byte(ALLOW), 0)

    def test_rollback_restores_locked_behavior(self):
        self.install_toggle(True)(1)
        self.assertEqual(self.byte(VISIBLE), 1)
        self.byte(VISIBLE, 0)
        self.byte(PREVIOUS, 0)
        self.install_toggle(False)(1)
        self.assertEqual(self.byte(VISIBLE), 0)

    def test_native_windows_key_mapping_f1_v_and_arrows(self):
        # This leaf uses only its ECX argument and local integer registers.
        self.write(0x2dd940, self.source_bytes(0x2dd940, 0x2ddd91))
        key = self.callable(0x2dd940, ctypes.c_uint32)
        self.assertEqual({vk: key(vk) for vk in (0x70, 0x56, 0x25, 0x26, 0x27, 0x28)},
                         {0x70: 0x1c, 0x56: 0x7e, 0x25: 0xe, 0x26: 0xf, 0x27: 0x10, 0x28: 0x11})

    def test_f1_field_updates_and_other_inactive_input_ignored(self):
        code = bytearray(self.source_bytes(0x1a7c50, 0x1a7d81))
        relative = 0x1a7d4b - 0x1a7c50
        self.assertEqual(code[relative:relative + 3], bytes.fromhex('83 fa 7e'))
        code[relative + 2] = 0x1c
        self.write(0x1a7c50, bytes(code))
        event = self.callable(0x1a7c50, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint8)
        obj = ctypes.create_string_buffer(0x500)
        address = ctypes.addressof(obj)
        obj[0x458] = 1
        event(address, 0x7e, 1)
        self.assertEqual(obj.raw[0x22c], 0)
        event(address, 0x1c, 1)
        self.assertEqual(obj.raw[0x22c], 1)
        event(address, 0x1c, 0)
        self.assertEqual(obj.raw[0x22c], 0)
        obj[0x458] = 0
        event(address, 0x1c, 1)
        self.assertEqual(obj.raw[0x22c], 0)

    def test_menu_visible_native_game_input_gate_zeros_actions(self):
        # EAX=current actions, EDX=pressed, DIL=0 as in the native caller.
        self.write(0x155875, bytes.fromhex('57 31 ff 89 c8 90'))
        self.write(0x15587b, self.source_bytes(0x15587b, 0x1558c7))
        self.write(0x1558c7, bytes.fromhex('5f c3'))
        update = self.callable(0x155875, ctypes.c_uint32, ctypes.c_uint32)
        self.byte(VISIBLE, 0)
        update(0xdead, 0xbeef)
        self.assertEqual(self.word(0xa121b8), 0xbeef)
        self.byte(VISIBLE, 1)
        update(0xdead, 0xbeef)
        for rva in (0xa121c4, 0xa121b4, 0xa121a8, 0xa121a4, 0xa121b0, 0xa121b8):
            self.assertEqual(self.word(rva), 0, hex(rva))
        self.assertEqual(self.word(0x49f1e4), 0xffffffff)

    def test_menu_visible_skips_native_cursor_capture_branch(self):
        self.write(0x2f3ac, self.source_bytes(0x2f3ac, 0x2f3b9))
        self.write(0x2f3b9, bytes.fromhex('b8 01 00 00 00 c3'))
        self.write(0x2f44b, bytes.fromhex('31 c0 c3'))
        capture_gate = self.callable(0x2f3ac)
        self.assertEqual(capture_gate(), 1)
        self.byte(VISIBLE, 1)
        self.assertEqual(capture_gate(), 0)

    def test_native_invulnerable_mask_on_off_encoded_health_update(self):
        # Entire audited leaf function, no external calls. Health is encoded as
        # 100 - native health units; this is not a screen HP percentage.
        self.write(0x1098b0, self.source_bytes(0x1098b0, 0x109998))
        player = ctypes.create_string_buffer(0x200)
        world = ctypes.create_string_buffer(0x5000)
        hud = ctypes.create_string_buffer(0x2000)
        hud_pointer = ctypes.c_void_p(ctypes.addressof(hud))
        self.write(0x4c2148, struct.pack('<Q', ctypes.addressof(world)))
        self.write(0xa344a8, struct.pack('<Q', ctypes.addressof(hud_pointer)))
        update = self.callable(0x1098b0, ctypes.c_void_p, ctypes.c_uint8)
        observed = []
        for flag in (0, 0x200, 0):
            struct.pack_into('<I', world, 0x40a4, flag)
            update(ctypes.addressof(player), 3)
            observed.append((world.raw[0x4098], hud.raw[0x1388]))
        self.assertEqual(observed, [(97, 3), (90, 10), (97, 3)])

    def test_native_infinite_ammo_mask_preserves_count_and_can_turn_off(self):
        world = ctypes.create_string_buffer(0x5000)
        address = ctypes.addressof(world)
        self.write(0x4c2148, struct.pack('<Q', address))
        # Both bounded native decrement blocks, stopping before shot effects or
        # sound callbacks. There are no stubs inside the copied blocks.
        self.write(0x147d3b, self.source_bytes(0x147d3b, 0x147d6e))
        self.write(0x147d6e, b'\xc3')
        clip = self.callable(0x147d3b)
        self.write(0x143828, bytes.fromhex('48 89 ca'))  # RDX = supplied RCX
        self.write(0x14382b, self.source_bytes(0x14382b, 0x143857))
        self.write(0x143857, b'\xc3')
        reserve = self.callable(0x143828, ctypes.c_void_p)
        observed = []
        for flag in (0, 0x400, 0):
            packed_clip = (5 << 8) | 0xa4000003
            packed_reserve = (5 << 20) | 0xa00000b3
            struct.pack_into('<III', world, 0x409c, packed_reserve, packed_clip, flag)
            clip()
            reserve(address)
            got_reserve, got_clip = struct.unpack_from('<II', world, 0x409c)
            observed.append(((got_clip & 0x1ff00) >> 8, (got_reserve & 0xff00000) >> 20))
            self.assertEqual(got_clip & ~0x1ff00, packed_clip & ~0x1ff00)
            self.assertEqual(got_reserve & ~0xff00000, packed_reserve & ~0xff00000)
        self.assertEqual(observed, [(4, 4), (5, 5), (4, 4)])

    @unittest.skipUnless(os.environ.get('DEMENTIUM_MODIFIED_EXE'), 'set DEMENTIUM_MODIFIED_EXE to validate the built EXE')
    def test_actual_built_executable_input_patches(self):
        data = Path(os.environ['DEMENTIUM_MODIFIED_EXE']).read_bytes()
        # The new section must preserve every preexisting code RVA/file mapping.
        self.assertEqual(data[0x4ee49:0x4ee4b], bytes.fromhex('eb 04'))
        self.assertEqual(data[0x1a714b:0x1a714e], bytes.fromhex('83 fa 1c'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
