"""Locale-neutral, explicitly audited native address profiles (offline only)."""
from contextvars import ContextVar
import struct
_ACTIVE=ContextVar('native_build',default='26099941')
# Each entry was matched to the corresponding instruction/function in build 26123896.
_MAP={
 0xb05c0:0xb0320,0x111800:0x111af0,0x1118e0:0x111bd0,0x111950:0x111c40,
 0x11b450:0x11b740,0x11b536:0x11b826,0x1232fc:0x12388c,0x1233bf:0x12394f,
 0x4c2158:0x4c4198,0x4c2200:0x4c4240,0xa68990:0xa6a9d0,0x1a7c50:0x1a8290,
 0x11a7b0:0x11aaa0,0x11af80:0x11b270,0x11b4f7:0x11b7e7,
 0x121e50:0x1223e0,0x122a10:0x122fa0,0x123379:0x123909,0x123383:0x123913,
 0x126da7:0x1273d7,0x126dac:0x1273dc,
 0x1557a5:0x155de5,0x15587b:0x155ebb,0x155882:0x155ec2,
 0x2f3236:0x2f4686,0x2f3241:0x2f4691,0x2f3250:0x2f46a0,0x2f34d0:0x2f4920,
 0x2f39cc:0x2f4e1c,0x2f39d2:0x2f4e22,0x2f39e3:0x2f4e33,
 0x2f3a3e:0x2f4e8e,0x2f3a45:0x2f4e95,
 0x2f537c:0x2f685c,0x2f5386:0x2f6866,0x2f5439:0x2f6919,
 0x31ad26:0x31c206,
 0xa68980:0xa6a9c0,0xa68e80:0xa6aec0,0xa69000:0xa6b000,
}
for _a in [0x1a7c54,0x1a7c5b,0x1a7c61,0x1a7d4b,0x1a7d50,0x1a7d57,0x1a7d81,0x1a7d90,0x1a7d9b,0x2dd940,0x2de833,0x2de83a,0x2deb38]:_MAP[_a]=_a+0x640
for _a in [0x37d6f0,0x37d748,0x37d758,0x37d760,0x37d7b0,0x37d818,0x3bebf0,0x3c08c0,0x3c09d0,0x3c0e30]:_MAP[_a]=_a+0x1000
for _a in [0x49f1a5,0x4a2f1d,0x4a4a58]:_MAP[_a]=_a+0x2000
for _a in [0x4c2228,0x4c2248,0xa121a0,0xa25e28,0xa2ca78,0xa30d20,0xa312b0,0xa314f0,0xa344f4,0xa34522,0x4c21ff]:_MAP[_a]=_a+0x2040

# Build 26152271: matched shipped functions, imported names, RIP targets and tables.
_MAP_26152271 = {
    0x2ed4d: 0x2ed4d,
    0x2ee30: 0x2ee30,
    0x2ee36: 0x2ee36,
    0x2f4ad: 0x2f4ca,
    0x2f4b3: 0x2f4d0,
    0x2f5a8: 0x2f5c5,
    0x2f5af: 0x2f5cc,
    0x2f5b5: 0x2f5d2,
    0x4e300: 0x4e3b0,
    0x4fa2e: 0x4fcf4,
    0x4fa49: 0x4fd18,
    0x4fa60: 0x4fb77,
    0x4fa66: 0x4fb7e,
    0x4fa6e: 0x4fb86,
    0x509ed: 0x50b66,
    0x66e70: 0x66fe0,
    0xb05c0: 0xb0560,
    0x111800: 0x111dd0,
    0x1118e0: 0x111eb0,
    0x111950: 0x111f20,
    0x11a7b0: 0x11add0,
    0x11af80: 0x11b5a0,
    0x11b450: 0x11ba70,
    0x11b4f7: 0x11bb17,
    0x11b536: 0x11bb56,
    0x121e50: 0x122790,
    0x122a10: 0x123350,
    0x1232fc: 0x123c3c,
    0x123379: 0x123cb9,
    0x123383: 0x123cc3,
    0x1233bf: 0x123cff,
    0x126da7: 0x127777,
    0x126dac: 0x12777c,
    0x1557a5: 0x1562d5,
    0x15587b: 0x1563ab,
    0x155882: 0x1563b2,
    0x1a7c50: 0x1a88e0,
    0x1a7c54: 0x1a88e4,
    0x1a7c5b: 0x1a88eb,
    0x1a7c61: 0x1a88f1,
    0x1a7d4b: 0x1a89db,
    0x1a7d50: 0x1a89e0,
    0x1a7d57: 0x1a89e7,
    0x1a7d81: 0x1a8a11,
    0x1a7d90: 0x1a8a20,
    0x1a7d9b: 0x1a8a2b,
    0x2dd940: 0x2decc0,
    0x2de833: 0x2dfd53,
    0x2de83a: 0x2dfd5a,
    0x2deb38: 0x2e0058,
    0x2f3236: 0x2f59e6,
    0x2f3241: 0x2f59f1,
    0x2f3250: 0x2f5a00,
    0x2f34d0: 0x2f5c80,
    0x2f39cc: 0x2f617c,
    0x2f39d2: 0x2f6182,
    0x2f39e3: 0x2f6193,
    0x2f3a3e: 0x2f61ee,
    0x2f3a45: 0x2f61f5,
    0x2f537c: 0x2f7bbc,
    0x2f5386: 0x2f7bc6,
    0x2f5439: 0x2f7c79,
    0x31ad26: 0x31e019,
    0x37d6f0: 0x380828,
    0x37d748: 0x380840,
    0x37d758: 0x380850,
    0x37d760: 0x380858,
    0x37d7b0: 0x3807c8,
    0x37d818: 0x380760,
    0x3bebf0: 0x3c1bf0,
    0x3c08c0: 0x3c38c0,
    0x3c09d0: 0x3c39d0,
    0x3c0e30: 0x3c3e30,
    0x49f1a5: 0x4a41a5,
    0x4a2f1d: 0x4a7f1d,
    0x4a4a58: 0x4a9a58,
    0x4c2158: 0x4c7198,
    0x4c21ff: 0x4c723f,
    0x4c2200: 0x4c7240,
    0x4c2228: 0x4c7268,
    0x4c2248: 0x4c7288,
    0xa121a0: 0xa171e0,
    0xa25e28: 0xa2ae68,
    0xa2ca78: 0xa31ab8,
    0xa30d20: 0xa35db0,
    0xa312b0: 0xa36340,
    0xa314f0: 0xa36560,
    0xa344f4: 0xa39564,
    0xa34522: 0xa39592,
    0xa68980: 0xa6da20,
    0xa68990: 0xa6da30,
    0xa68e80: 0xa6df20,
    0xa69000: 0xa6e000,
}

def active_build():
    return _ACTIVE.get()

def rva(value):
    build=active_build()
    if build not in {'26099941','26123896','26152271'}:
        raise ValueError('Unknown native build profile: '+build)
    if build=='26099941' or value==0:return value
    mapping=_MAP if build=='26123896' else _MAP_26152271
    if value in mapping:return mapping[value]
    if 0xa121a0<=value<0xa121c8:return mapping[0xa121a0]+value-0xa121a0
    if build=='26123896' and value in {0x2ed4d,0x2ee30,0x2ee36,0x2f4ad,0x2f4b3,0x2f5a8,0x2f5af,0x2f5b5,0x4e300,0x509ed,0x4fa2e,0x4fa49,0x4fa60,0x4fa66,0x4fa6e,0x66e70}:return value
    raise ValueError('Unmapped native address: '+hex(value))

def select(data,recipe):
    from localize import digest
    identity=digest(data)
    if identity==recipe['input_sha256']:build='26099941'
    elif identity==recipe.get('input_sha256_by_build',{}).get('26123896'):build='26123896'
    elif identity==recipe.get('input_sha256_by_build',{}).get('26152271'):build='26152271'
    else:raise ValueError('Native menu requires a verified executable profile')
    # A caller-supplied recipe cannot silently bind one shipped layout to another.
    pe=struct.unpack_from('<I',data,60)[0]
    count=struct.unpack_from('<H',data,pe+6)[0]
    optional=struct.unpack_from('<H',data,pe+20)[0]
    sections=pe+24+optional
    actual=next((struct.unpack_from('<I',data,sections+i*40+12)[0]
                 for i in range(count) if data[sections+i*40:sections+i*40+8].rstrip(b'\0')==b'.data'),None)
    if actual!={'26099941':0x49f000,'26123896':0x4a1000,'26152271':0x4a4000}[build]:
        raise ValueError('Native executable identity/profile layout mismatch')
    return _ACTIVE.set(build)

def restore(token):_ACTIVE.reset(token)

def guard(expected,new_rva):
    """Re-encode displaced RIP/branch targets; every final byte remains guarded."""
    if _ACTIVE.get()=='26099941':return expected
    import capstone
    mapping=_MAP if active_build()=='26123896' else _MAP_26152271
    old=next((a for a,b in mapping.items() if b==new_rva),new_rva)
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
    out=bytearray(expected)
    for ins in md.disasm(expected,0x140000000+old):
        off=ins.address-(0x140000000+old)
        for op in ins.operands:
            if op.type==capstone.x86.X86_OP_MEM:
                disp=op.mem.disp
                if op.mem.base==capstone.x86.X86_REG_RIP:
                    target=ins.address+ins.size+disp-0x140000000
                    newdisp=rva(target)-(new_rva+off+ins.size)
                elif disp>=0x20000:newdisp=rva(disp)
                else:continue
                # Capstone 5 reports a 16-bit disp_size for 66 0F 6E RIP MOVD;
                # x64 RIP addressing still encodes the audited four-byte displacement.
                if ins.disp_size in (2,4):struct.pack_into('<i',out,off+ins.disp_offset,newdisp)
    return bytes(out)
