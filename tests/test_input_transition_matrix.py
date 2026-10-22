"""Native translator/reader/close/action collector press-release matrix.

This is CPU replay, not OS/device acceptance. It covers every Win32 virtual-key
value, including unrecognized values, in both original direct-input modes.
"""
import unittest
import test_reader_key_lifecycle as lifecycle


@unittest.skipUnless(lifecycle.EXE.is_file(), 'locally supplied patched PE required')
class InputTransitionMatrixTests(unittest.TestCase):
    def test_all_virtual_keys_release_after_both_reader_close_paths(self):
        count = 0
        for mode in (0, 1):
            for inventory in (False, True):
                fixture = lifecycle.ReaderKeyLifecycleTests()
                fixture.setUp()
                v = fixture.v
                v.uc.mem_write(v.obj + 0x458, bytes([mode]))
                for vk in range(256):
                    with self.subTest(mode=mode, inventory=inventory, vk=vk):
                        # Isolate each pair without substituting for either
                        # event; the native key translator and event wrappers run.
                        v.uc.mem_write(v.obj + 0x221, b'\0' * 0x12)
                        fixture.open_read()
                        fixture.key(vk, 1)
                        fixture.close(inventory)
                        fixture.key(vk, 0)
                        self.assertEqual(bytes(v.uc.mem_read(v.obj + 0x221, 0x12)), b'\0' * 0x12)
                        self.assertEqual(fixture.field(0x458), mode)
                        self.assertEqual(fixture.collect()[0] & 0xc0, 0)
                        count += 1
        print('INPUT_TRANSITION_MATRIX virtual_keys=256 modes=2 close_paths=2 pairs=%d stuck_fields=0 PASS' % count)


if __name__ == '__main__':
    unittest.main(verbosity=2)
