"""Replay native startup-disable -> key callback -> input field -> menu edge.

This catches the missed +458=0 mode; no game or window is launched.
"""
import ctypes
import os
from pathlib import Path
import struct
import unittest
from test_debug_input import NativeDebugInputTests, VISIBLE, PREVIOUS

class NativeDispatchTests(NativeDebugInputTests):
    def test_f1_after_native_startup_disables_direct_input(self):
        data=Path(os.environ['DEMENTIUM_MODIFIED_EXE']).read_bytes()
        import pefile
        pe=pefile.PE(data=data)
        for section in pe.sections:
            if section.Name.rstrip(b"\0")==b".locui":
                self.write(section.VirtualAddress,section.get_data())
        for start,end in [(0x1a7c50,0x1a7d90),(0x1a7dc0,0x1a7df3),
                          (0x2dd940,0x2ddd91),(0x4fa2e,0x4fa66),
                          (0x2f171,0x2f199)]:
            self.write(start,pe.get_data(start,end-start))
        self.write(0x2f199,b'\xc3')
        self.write(0x4fa2a,bytes.fromhex('56 31 f6 90'))
        self.write(0x4fa66,bytes.fromhex('5e c3'))
        obj=ctypes.create_string_buffer(0x500)
        ptr=ctypes.addressof(obj)
        # Rebase only the native vtable and two global object pointers.
        struct.pack_into('<Q',obj,0,self.memory+0x3bb4d8)
        self.write(0x3bb4d8+0x48,struct.pack('<Q',self.memory+0x1a7c50))
        self.write(0x3bb4d8+0x70,struct.pack('<Q',self.memory+0x2eb90))
        for rva in [0x4c2228,0xa2ca78]:self.write(rva,struct.pack('<Q',ptr))
        obj[0x458]=1
        self.callable(0x2f171)()
        self.assertEqual(obj.raw[0x458],0,'native startup must reproduce disabled direct-input mode')
        translate=self.callable(0x2dd940,ctypes.c_uint32)
        down=self.callable(0x1a7dc0,ctypes.c_uint32)
        up=self.callable(0x1a7de0,ctypes.c_uint32)
        toggle=self.callable(0x4fa2a,ctypes.c_uint32)
        observed=[]
        for pressed in [0,1,1,0,1,1,0,1]:
            (down if pressed else up)(translate(0x70))
            toggle(obj.raw[0x22c]);observed.append(self.byte(VISIBLE))
        print('NATIVE_DISPATCH direct_input=0 F1='+str(observed),flush=True)
        self.assertEqual(observed,[0,1,1,1,0,0,0,1])
        # Non-F1 input still obeys the native mode gate.
        self.byte(VISIBLE,0)
        down(translate(0x56));down(translate(0x26))
        self.assertEqual(obj.raw[0x22d],0)

if __name__=='__main__':unittest.main(verbosity=2)
