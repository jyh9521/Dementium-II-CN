"""Replay the shipped option-label getter without starting the game."""
import argparse, json, struct
from pathlib import Path
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_RSP, UC_X86_REG_RAX
from localize import Zar

def labels(exe, rom):
    pe=pefile.PE(data=exe); base=pe.OPTIONAL_HEADER.ImageBase
    image=pe.get_memory_mapped_image(); u=Uc(UC_ARCH_X86, UC_MODE_64)
    u.mem_map(base,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095);u.mem_write(base,image)
    u.mem_map(0x2000000,0x40000)
    context=0x2000000; table=0x2010000; stack=0x2020000; stop=0x2030000
    u.mem_write(context+0x18,struct.pack('<Q',table))
    rows=Zar(rom).read('EN/OPTIONSNEW.TBL').decode('utf8').splitlines()
    for i in range(len(rows)):u.mem_write(table+i*8,struct.pack('<Q',0x3000000+i*256))
    def call(option, flags=0, bob=0):
        u.mem_write(context+0x90,struct.pack('<II',flags,bob))
        u.mem_write(stack,struct.pack('<Q',stop));u.reg_write(UC_X86_REG_RCX,context);u.reg_write(UC_X86_REG_RDX,option);u.reg_write(UC_X86_REG_RSP,stack)
        u.emu_start(base+0x1251a0,stop,count=200)
        index=(u.reg_read(UC_X86_REG_RAX)-0x3000000)//256
        return rows[index]
    return {'head_bob':[call(10,bob=i) for i in range(3)],'minimap':[call(7,flags=f) for f in [1<<17,0,1<<20]]}

def main():
    p=argparse.ArgumentParser();p.add_argument('game',type=Path);a=p.parse_args()
    result=labels((a.game/'Dementium II.exe').read_bytes(),(a.game/'rom.zar').read_bytes())
    ok=result=={'head_bob':['普通','轻微','关'],'minimap':['关','半透明','不透明']}
    print('OPTION_CONTEXT '+json.dumps(result,ensure_ascii=False,separators=(',',':'))+' result='+('PASS' if ok else 'FAIL'))
    return int(not ok)
if __name__=='__main__':raise SystemExit(main())
