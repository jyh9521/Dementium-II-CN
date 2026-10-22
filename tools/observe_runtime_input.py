"""Read-only, foreground-game-only input snapshots; never launches or writes game memory."""
import argparse,ctypes,json,os,struct,subprocess,time
from pathlib import Path
from ctypes import wintypes as W

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--wait',type=float,default=90);p.add_argument('--seconds',type=float,default=45);a=p.parse_args()
 if os.name!='nt':raise OSError('Windows runtime observation requires Windows')
 k=ctypes.WinDLL('kernel32',use_last_error=True);u=ctypes.WinDLL('user32',use_last_error=True)
 k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
 k.ReadProcessMemory.argtypes=[W.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.ReadProcessMemory.restype=W.BOOL
 k.CloseHandle.argtypes=[W.HANDLE];u.GetForegroundWindow.restype=W.HWND;u.GetAsyncKeyState.argtypes=[ctypes.c_int];u.GetAsyncKeyState.restype=ctypes.c_short
 u.GetCursorPos.argtypes=[ctypes.POINTER(W.POINT)];u.ScreenToClient.argtypes=[W.HWND,ctypes.POINTER(W.POINT)]
 command="Get-Process | Where-Object {$_.ProcessName -eq 'Dementium II'} | Select-Object -First 1 Id,@{N='Base';E={$_.MainModule.BaseAddress.ToInt64()}},@{N='Path';E={$_.MainModule.FileName}} | ConvertTo-Json -Compress"
 start=time.monotonic();meta=None
 print('WAITING game_launch=NEVER observer=READ_ONLY',flush=True)
 while time.monotonic()-start<a.wait:
  r=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,creationflags=0x08000000)
  if r.stdout.strip():meta=json.loads(r.stdout);break
  time.sleep(.6)
 if not meta:print('NO_RUNNING_GAME no_memory_observed=YES');return 2
 handle=k.OpenProcess(0x1010,False,meta['Id'])
 if not handle:raise ctypes.WinError(ctypes.get_last_error())
 base=meta['Base']
 def read(addr,n):
  b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
  if not k.ReadProcessMemory(handle,addr,b,n,ctypes.byref(got)) or got.value!=n:raise OSError('Target memory read ended')
  return b.raw
 def val(addr,fmt):return struct.unpack(fmt,read(addr,struct.calcsize(fmt)))[0]
 def ptr(rva):return val(base+rva,'<Q')
 a.output.parent.mkdir(parents=True,exist_ok=True);last=None;count=0;focused=0;begin=time.monotonic()
 try:
  with a.output.open('w',encoding='utf-8') as f:
   f.write(json.dumps(dict(schema=1,read_only=True,process=meta,scope='Mouse/E and native fields only while this game owns foreground; no other application input'))+'\n');f.flush()
   print('ATTACHED pid='+str(meta['Id'])+' base='+hex(base)+' output='+str(a.output),flush=True)
   while time.monotonic()-begin<a.seconds:
    try:
     obj,ctx,window=ptr(0x4c2228),ptr(0x4c2248),ptr(0xa312b0)
     if not obj or not ctx or not window:time.sleep(.02);continue
     hwnd=val(window+0x20,'<Q');foreground=int(u.GetForegroundWindow() or 0)==hwnd
     if not foreground:time.sleep(.02);continue
     focused+=1;point=W.POINT();u.GetCursorPos(ctypes.byref(point));u.ScreenToClient(hwnd,ctypes.byref(point))
     row=dict(menu=val(base+0x4a2f1d,'<B'),reader=val(base+0xa68980,'<I'),owned=val(base+0xa68e81,'<B'),capture=val(base+0x49f1a5,'<B'),window_flags=read(window+0x18,3).hex(),focus=read(window+0x79,2).hex(),input_flags=read(obj+0x218,3).hex(),direct_mode=val(obj+0x458,'<B'),keys=read(obj+0x221,18).hex(),input_xy=struct.unpack('<2i',read(obj+0x340,8)),raw_buttons=val(obj+0x350,'<I'),os_xy=(point.x,point.y),os_left=bool(u.GetAsyncKeyState(1)&0x8000),os_right=bool(u.GetAsyncKeyState(2)&0x8000),os_E=bool(u.GetAsyncKeyState(0x45)&0x8000),io_flags=val(ctx+8,'<I'),io_display=struct.unpack('<2f',read(ctx+0x10,8)),io_xy=struct.unpack('<2f',read(ctx+0x130,8)),io_down=read(ctx+0x138,5).hex(),io_clicked=read(ctx+0x430,5).hex(),io_released=read(ctx+0x43a,5).hex(),io_duration=struct.unpack('<f',read(ctx+0x44c,4))[0],hovered_window=hex(val(ctx+0x1ab0,'<Q')))
     if row!=last:
      f.write(json.dumps(dict(elapsed_ms=round((time.monotonic()-begin)*1000),**row))+'\n');f.flush();last=row;count+=1
     time.sleep(.01)
    except OSError as e:
     f.write(json.dumps(dict(end=str(e)))+'\n');break
 finally:k.CloseHandle(handle)
 print(f'OBSERVED records={count} foreground_samples={focused} game_launch=NEVER memory_writes=NONE',flush=True)
 return 0
if __name__=='__main__':raise SystemExit(main())
