"""Guarded local pause-control legend coordinates; no shared font/global layout changes."""
import pefile
from native_patch import guarded_write

# Native pause draw FUN_140126a40.  The renderer subtracts (86,24).
# Y-axis bitmap itself is drawn at (-154,-24); localized label ink is
# texture (155,221)..(181,232).  Status (116,218) therefore starts three
# blank pixels after the colon and shares its visible top, with 12px font.
PAUSE_VALUE_X=116
PAUSE_VALUE_Y=218

def patch_pause_layout(data):
 pe=pefile.PE(data=data);out=bytearray(data)
 guarded_write(out,pe,0x126da7,bytes.fromhex('badc000000'),b'\xba'+PAUSE_VALUE_Y.to_bytes(4,'little'))
 guarded_write(out,pe,0x126dac,bytes.fromhex('b97d000000'),b'\xb9'+PAUSE_VALUE_X.to_bytes(4,'little'))
 return bytes(out),dict(scope='pause-control Y-axis status only',native_function='0x140126a40',
                       x=dict(rva='0x126dac',before=125,after=PAUSE_VALUE_X),
                       y=dict(rva='0x126da7',before=220,after=PAUSE_VALUE_Y),
                       font_size_unchanged=True,game_launch='NEVER')
