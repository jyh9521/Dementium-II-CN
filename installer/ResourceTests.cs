using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Collections.Generic;
using System.Security.Cryptography;
using LocalizationInstaller;

static class ResourceTests {
 static string root;
 static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 static void Assert(bool ok,string message){if(!ok)throw new Exception(message);}
 static void Reject(Action action){bool rejected=false;try{action();}catch(Exception){rejected=true;}Assert(rejected,"Expected rejection");}
 static byte[] original=Encoding.UTF8.GetBytes("ORIGINAL"),target=Encoding.UTF8.GetBytes("中文");
 static Payload Settings()=>new Payload {Settings=new Settings {archive_file="rom.zar",executable_file="Game.exe",backup_folder=".dementium-locale"},Archive=new Delta(),Executable=new Delta()};
 static ResourcePayload Data()=>new ResourcePayload {schema=1,members=new[]{new MemberPatch {name="EN/A.TBL",source_size=original.Length,target_size=target.Length,source_sha256=Hash(original),target_sha256=Hash(target),runs=new[]{new PatchRun {offset=0,old=Convert.ToHexString(original.AsSpan(0,target.Length)),@new=Convert.ToHexString(target)}},tail=""}},literals=new[]{new LiteralPatch {source="RETRO",target="复古",capacity=12}}};
 static ResourceEngine Engine()=>new ResourceEngine(Settings(),Data());
 static (Payload settings,ResourcePayload data,byte[] output) NativeData() {
  byte[] a=Exe(),b=a.Concat(Encoding.ASCII.GetBytes("NATIVE SECTION FIXTURE")).ToArray();b[256]=99;
  var runs=new[]{new PatchRun {offset=256,old=a[256].ToString("x2"),@new=b[256].ToString("x2")}};
  var p=Data();p.native_executable=new MemberPatch {name="Game.exe",source_size=a.Length,target_size=b.Length,source_sha256=Hash(a),target_sha256=Hash(b),runs=runs,tail=Convert.ToBase64String(b.Skip(a.Length).ToArray())};
  var settings=Settings();settings.Executable=new Delta {format="native-menu-pe-v1",original_size=a.Length,modified_size=b.Length,original_sha256=Hash(a),modified_sha256=Hash(b),runs=runs,append=p.native_executable.tail};
  return(settings,p,b);
 }
 static (Payload settings,ResourcePayload data,byte[] output) UpgradeData() {
  var p=NativeData();byte[] next=Encoding.UTF8.GetBytes("新版");
  p.data.members[0].target_sha256=Hash(next);p.data.members[0].target_size=next.Length;p.data.members[0].runs[0].@new=Convert.ToHexString(next);
  return p;
 }
 static string Receipt(string dir)=>Path.Combine(dir,".dementium-locale/resource-state.json");
 static byte[] Zar(byte[] unrelated,bool extra=false,byte[] text=null) {
  var files=new SortedDictionary<string,byte[]>(StringComparer.Ordinal){{"EN/A.TBL",text ?? original},{"TEX/OTHER.BIN",unrelated}};
  if(extra)files.Add("OTHER/NEW.BIN",Encoding.ASCII.GetBytes("NEW GAME UPDATE RESOURCE"));
  using(var index=new MemoryStream())using(var bw=new BinaryWriter(index,Encoding.ASCII,true)) {
   bw.Write((ulong)files.Count);long offset=0;foreach(var f in files){bw.Write((uint)f.Value.Length);bw.Write((uint)0);bw.Write((ulong)offset);offset+=f.Key.Length+2;}
   foreach(var f in files){bw.Write(Encoding.ASCII.GetBytes("/"+f.Key));bw.Write((byte)0);}files.Add("~INDEX",index.ToArray());
  }
  int names=32,strings=32+files.Count*4,pool=files.Keys.Sum(s=>s.Length+1),toc=strings+pool,header=((toc+files.Count*24+511)/512)*512;
  using var stream=new MemoryStream();using var writer=new BinaryWriter(stream,Encoding.ASCII,true);writer.Write(new byte[header]);
  stream.Position=0;writer.Write(Encoding.ASCII.GetBytes("ZAR1"));writer.Write(files.Count);writer.Write(header);writer.Write(0);writer.Write(names);writer.Write(strings);writer.Write(toc);writer.Write(0);
  int i=0,nameOffset=0;
  foreach(var f in files) {
   stream.Position=names+4*i;writer.Write(nameOffset);stream.Position=strings+nameOffset;writer.Write(Encoding.ASCII.GetBytes(f.Key));writer.Write((byte)0);nameOffset+=f.Key.Length+1;
   stream.Position=stream.Length;while(stream.Position%512!=0)writer.Write((byte)0);long start=stream.Position;writer.Write(f.Value);
   stream.Position=toc+24*i;writer.Write((ulong)start);writer.Write((ulong)f.Value.Length);writer.Write((ulong)0);i++;
  }
  return stream.ToArray();
 }
 static byte[] Exe(int shift=0,bool duplicate=false) {
  byte[] b=new byte[2048+shift];Encoding.ASCII.GetBytes("MZ").CopyTo(b,0);BitConverter.GetBytes(64).CopyTo(b,60);Encoding.ASCII.GetBytes("PE\0\0").CopyTo(b,64);BitConverter.GetBytes((ushort)1).CopyTo(b,70);
  Encoding.ASCII.GetBytes(".rdata").CopyTo(b,88);BitConverter.GetBytes((uint)128).CopyTo(b,104);BitConverter.GetBytes((uint)(512+shift)).CopyTo(b,108);BitConverter.GetBytes((uint)0x40000040).CopyTo(b,124);
  Encoding.ASCII.GetBytes("RETRO").CopyTo(b,528+shift);if(duplicate)Encoding.ASCII.GetBytes("RETRO").CopyTo(b,560+shift);b[b.Length-1]=77;return b;
 }
 static string Fixture(int shift=0,bool extra=false,byte[] text=null) {
  string dir=Path.Combine(root,Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);File.WriteAllBytes(Path.Combine(dir,"rom.zar"),Zar(new byte[17+shift],extra,text));File.WriteAllBytes(Path.Combine(dir,"Game.exe"),Exe(shift));return dir;
 }
 static string Rom(string dir)=>Path.Combine(dir,"rom.zar");
 static string Program(string dir)=>Path.Combine(dir,"Game.exe");
 static string[] Id(string dir)=>new[]{LocalizationInstaller.Engine.Hash(Rom(dir)),LocalizationInstaller.Engine.Hash(Program(dir))};
 static void Same(string dir,string[] id)=>Assert(Id(dir).SequenceEqual(id),"Source/restore changed");
 public static void Run(Action<string,Action> test,string output) {
  root=output;Directory.CreateDirectory(root);
  test("resource payload embedded and not container-offset based",()=>{var p=ResourcePayload.Load();Assert(p.members.Length>200 && p.literals.Length==5,"Missing real members");new ResourceEngine(Payload.Load(),p);});
  test("resource inspect reads only",()=>{string d=Fixture();var before=Id(d);Assert(Engine().Inspect(Rom(d)).CanInstall,"Not installable");Same(d,before);Assert(!Directory.Exists(Path.Combine(d,".dementium-locale")),"Inspect wrote files");});
  test("resource install and exact source restore",()=>{string d=Fixture();var id=Id(d);var e=Engine();Assert(e.Operate(Rom(d),true,false)=="INSTALLED","Not installed");Assert(e.Inspect(Rom(d)).CanRestore,"No restore");e.Operate(Rom(d),true,true);Same(d,id);});
  test("resource unrelated update and extra members preserved",()=>{string d=Fixture(4096,true);byte[] source=File.ReadAllBytes(Rom(d));var e=Engine();e.Operate(Rom(d),true,false);using(var a=new ResourceArchive(Rom(d))){Assert(a.Read("TEX/OTHER.BIN").SequenceEqual(new byte[4113]),"Unrelated changed");Assert(Encoding.ASCII.GetString(a.Read("OTHER/NEW.BIN"))=="NEW GAME UPDATE RESOURCE","New member lost");Assert(a.Read("EN/A.TBL").SequenceEqual(target),"Not translated");}e.Operate(Rom(d),true,true);Assert(File.ReadAllBytes(Rom(d)).SequenceEqual(source),"Update restore failed");});
  test("resource exe shifted section and changed file size",()=>{string d=Fixture(1536);byte[] before=File.ReadAllBytes(Program(d));Engine().Operate(Rom(d),true,false);byte[] after=File.ReadAllBytes(Program(d));Assert(after.AsSpan(528+1536,6).SequenceEqual(Encoding.UTF8.GetBytes("复古")),"Not relocated");for(int i=0;i<before.Length;i++)if(i<528+1536 || i>=540+1536)Assert(before[i]==after[i],"Nonliteral bytes changed");});
  test("resource target drift rejected without backup writes",()=>{string d=Fixture(text:Encoding.ASCII.GetBytes("CHANGED TEXT"));var id=Id(d);Reject(()=>Engine().Operate(Rom(d),true,false));Same(d,id);Assert(!Directory.Exists(Path.Combine(d,".dementium-locale")),"Unexpected backup");});
  test("resource duplicate literal rejected before archive write",()=>{string d=Fixture();File.WriteAllBytes(Program(d),Exe(duplicate:true));var id=Id(d);Reject(()=>Engine().Operate(Rom(d),true,false));Same(d,id);});
  test("resource malformed archive rejected",()=>{string d=Fixture();File.WriteAllText(Rom(d),"bad archive");var id=Id(d);Reject(()=>Engine().Operate(Rom(d),true,false));Same(d,id);});
  test("resource damaged backup refuses restore",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);var c=e.Inspect(Rom(d)).components[0];File.AppendAllText(c.backup,"bad");var id=Id(d);Reject(()=>e.Operate(Rom(d),true,true));Same(d,id);});
  test("resource missing receipt does not invent backup",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);File.Delete(Path.Combine(d,".dementium-locale/resource-state.json"));var id=Id(d);Reject(()=>e.Inspect(Rom(d)));Same(d,id);});
  test("resource receipt traversal rejected",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);string p=Path.Combine(d,".dementium-locale/resource-state.json");var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(p),new JsonSerializerOptions {IncludeFields=true});state.files[0].backup="../outside.zar";File.WriteAllText(p,JsonSerializer.Serialize(state,new JsonSerializerOptions {IncludeFields=true}));Reject(()=>e.Inspect(Rom(d)));});
  test("resource second commit failure restores both and retry works",()=>{string d=Fixture();var id=Id(d);var e=Engine();e.BeforeReplace=i=>{if(i==1)throw new IOException("injected");};Reject(()=>e.Operate(Rom(d),true,false));Same(d,id);Engine().Operate(Rom(d),true,false);Engine().Operate(Rom(d),true,true);Same(d,id);});
  test("resource first commit failure leaves originals",()=>{string d=Fixture();var id=Id(d);var e=Engine();e.BeforeReplace=i=>throw new IOException("injected");Reject(()=>e.Operate(Rom(d),true,false));Same(d,id);});
  test("resource repeated install does not grow archive",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);long size=new FileInfo(Rom(d)).Length;var id=Id(d);Assert(e.Operate(Rom(d),true,false)=="ALREADY_INSTALLED","Not idempotent");Same(d,id);Assert(new FileInfo(Rom(d)).Length==size,"Grew archive");});
  test("resource repeated restore no rewrite",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);e.Operate(Rom(d),true,true);var time=File.GetLastWriteTimeUtc(Rom(d));Assert(e.Operate(Rom(d),true,true)=="ALREADY_RESTORED","Restore state");Assert(File.GetLastWriteTimeUtc(Rom(d))==time,"Rewrote original");});
  test("resource later original update keeps historical backups",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);string old=e.Inspect(Rom(d)).components[0].backup;e.Operate(Rom(d),true,true);File.WriteAllBytes(Rom(d),Zar(new byte[777],true));File.WriteAllBytes(Program(d),Exe(1024));var id=Id(d);e.Operate(Rom(d),true,false);Assert(e.Inspect(Rom(d)).components[0].backup!=old && File.Exists(old),"Historical backup overwritten");e.Operate(Rom(d),true,true);Same(d,id);});
  test("resource interrupted mixed component state recovers",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);var c=e.Inspect(Rom(d)).components[1];File.Copy(c.backup,c.path,true);var inspect=e.Inspect(Rom(d));Assert(inspect.CanInstall && inspect.CanRestore,"Mixed unrecognized");e.Operate(Rom(d),true,false);Assert(!e.Inspect(Rom(d)).CanInstall,"Mixed not completed");});
  test("resource save and config untouched",()=>{string d=Fixture();File.WriteAllText(Path.Combine(d,"save.dat"),"SAVE");File.WriteAllText(Path.Combine(d,"settings.ini"),"CONFIG");var e=Engine();e.Operate(Rom(d),true,false);e.Operate(Rom(d),true,true);Assert(File.ReadAllText(Path.Combine(d,"save.dat"))=="SAVE" && File.ReadAllText(Path.Combine(d,"settings.ini"))=="CONFIG","User data changed");});
  test("resource writable PE section rejected",()=>{string d=Fixture();byte[] b=File.ReadAllBytes(Program(d));BitConverter.GetBytes((uint)0xC0000040).CopyTo(b,124);File.WriteAllBytes(Program(d),b);Reject(()=>Engine().Operate(Rom(d),true,false));});
  test("resource metadata duplicate members rejected",()=>{var p=Data();p.members=new[]{p.members[0],p.members[0]};Reject(()=>new ResourceEngine(Settings(),p));});
  test("resource restore second commit failure keeps installed files",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);var installed=Id(d);e.BeforeReplace=i=>{if(i==1)throw new IOException("injected restore failure");};Reject(()=>e.Operate(Rom(d),true,true));Same(d,installed);Engine().Operate(Rom(d),true,true);});
  test("resource concurrent precommit change is preserved",()=>{string d=Fixture();byte[] before=File.ReadAllBytes(Rom(d));var e=Engine();e.BeforeReplace=i=>{if(i==0)using(var f=new FileStream(Rom(d),FileMode.Append))f.WriteByte(66);};Reject(()=>e.Operate(Rom(d),true,false));Assert(File.ReadAllBytes(Rom(d)).SequenceEqual(before.Concat(new byte[]{66})),"Concurrent source change lost");Assert(File.ReadAllBytes(Program(d)).SequenceEqual(Exe()),"Other component changed");});
  test("resource native PE exact bytes append and rollback",()=>{string d=Fixture();var id=Id(d);var p=NativeData();var e=new ResourceEngine(p.settings,p.data);Assert(e.Operate(Rom(d),true,false)=="INSTALLED","Native install");Assert(File.ReadAllBytes(Program(d)).SequenceEqual(p.output),"Native PE append lost");Assert(e.Operate(Rom(d),true,false)=="ALREADY_INSTALLED","Native idempotence");e.Operate(Rom(d),true,true);Same(d,id);});
  test("resource native PE unknown hash rejects before writes",()=>{string d=Fixture();var p=NativeData();byte[] b=Exe();b[300]=1;File.WriteAllBytes(Program(d),b);var id=Id(d);Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);Assert(!Directory.Exists(Path.Combine(d,".dementium-locale")),"Native unknown source wrote backup");});
  test("resource native PE shifted literal match does not bypass lock",()=>{string d=Fixture(512);var p=NativeData();var id=Id(d);Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);});
  test("resource native archive-only works with another EXE",()=>{string d=Fixture(512);var p=NativeData();var id=Id(d);var e=new ResourceEngine(p.settings,p.data);e.Operate(Rom(d),false,false);Assert(LocalizationInstaller.Engine.Hash(Program(d))==id[1],"Archive-only changed program");e.Operate(Rom(d),false,true);Same(d,id);});
  test("resource native metadata disagreement rejected",()=>{var p=NativeData();p.data.native_executable.name="another.exe";Reject(()=>new ResourceEngine(p.settings,p.data));p=NativeData();p.settings.Executable.original_sha256=new string('0',64);Reject(()=>new ResourceEngine(p.settings,p.data));});
  test("resource native metadata missing sparse executable rejected",()=>{var p=NativeData();p.data.native_executable=null;Reject(()=>new ResourceEngine(p.settings,p.data));});
  test("resource native byte guard rejects and originals retained",()=>{string d=Fixture();var id=Id(d);var p=NativeData();p.data.native_executable.runs[0].old="ee";Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);});
  test("resource native second commit failure reverts archive",()=>{string d=Fixture();var id=Id(d);var p=NativeData();var e=new ResourceEngine(p.settings,p.data);e.BeforeReplace=i=>{if(i==1)throw new IOException("native injection");};Reject(()=>e.Operate(Rom(d),true,false));Same(d,id);e.BeforeReplace=null;e.Operate(Rom(d),true,false);e.Operate(Rom(d),true,true);Same(d,id);});
  test("resource native restore failure retains installed bytes",()=>{string d=Fixture();var p=NativeData();var e=new ResourceEngine(p.settings,p.data);e.Operate(Rom(d),true,false);var id=Id(d);e.BeforeReplace=i=>{if(i==1)throw new IOException("native restore injection");};Reject(()=>e.Operate(Rom(d),true,true));Same(d,id);e.BeforeReplace=null;e.Operate(Rom(d),true,true);});
  test("resource previous localization upgrades from verified originals",()=>{string d=Fixture();var originalId=Id(d);Engine().Operate(Rom(d),true,false);var oldId=Id(d);var p=UpgradeData();var e=new ResourceEngine(p.settings,p.data);var inspection=e.Inspect(Rom(d));Assert(inspection.CanInstall && inspection.CanRestore && inspection.components.All(c=>c.upgrade),"Older localization not recognized");Assert(e.Operate(Rom(d),true,false)=="INSTALLED","Upgrade failed");Assert(File.ReadAllBytes(Program(d)).SequenceEqual(p.output),"Upgraded native output");Assert(!e.Inspect(Rom(d)).CanInstall,"Upgraded still pending");e.Operate(Rom(d),true,true);Same(d,originalId);});
  test("resource old native version upgrades and restores original",()=>{string d=Fixture();var originalId=Id(d);var old=NativeData();new ResourceEngine(old.settings,old.data).Operate(Rom(d),true,false);var next=NativeData();next.output[256]=88;next.settings.Executable.modified_sha256=Hash(next.output);next.settings.Executable.runs[0].@new="58";next.data.native_executable.target_sha256=Hash(next.output);var e=new ResourceEngine(next.settings,next.data);Assert(e.Inspect(Rom(d)).components[1].upgrade,"Old native not upgradeable");e.Operate(Rom(d),true,false);Assert(File.ReadAllBytes(Program(d)).SequenceEqual(next.output),"Native upgrade bytes");e.Operate(Rom(d),true,true);Same(d,originalId);});
  test("resource upgrade mismatched receipt rejects without writes",()=>{string d=Fixture();Engine().Operate(Rom(d),true,false);var id=Id(d);var options=new JsonSerializerOptions {IncludeFields=true};var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(Receipt(d)),options);state.files[0].installed=new string('0',64);File.WriteAllText(Receipt(d),JsonSerializer.Serialize(state,options));var p=UpgradeData();Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);});
  test("resource upgrade corrupted or unsupported backup rejects",()=>{string d=Fixture();Engine().Operate(Rom(d),true,false);var id=Id(d);var options=new JsonSerializerOptions {IncludeFields=true};var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(Receipt(d)),options);string backup=Path.Combine(d,".dementium-locale",state.files[0].backup);File.WriteAllBytes(backup,Zar(new byte[17],text:Encoding.ASCII.GetBytes("OTHER SOURCE")));state.files[0].original=LocalizationInstaller.Engine.Hash(backup);File.WriteAllText(Receipt(d),JsonSerializer.Serialize(state,options));var p=UpgradeData();Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);});
  test("resource upgrade second commit failure retains old files and receipt",()=>{string d=Fixture();Engine().Operate(Rom(d),true,false);var old=Id(d);byte[] receipt=File.ReadAllBytes(Receipt(d));var p=UpgradeData();var e=new ResourceEngine(p.settings,p.data);e.BeforeReplace=i=>{if(i==1)throw new IOException("upgrade injection");};Reject(()=>e.Operate(Rom(d),true,false));Same(d,old);Assert(File.ReadAllBytes(Receipt(d)).SequenceEqual(receipt),"Old upgrade receipt changed");e.BeforeReplace=null;e.Operate(Rom(d),true,false);Assert(!e.Inspect(Rom(d)).CanInstall,"Upgrade retry failed");});
  test("resource postreceipt failure rolls back receipt and upgraded files",()=>{string d=Fixture();Engine().Operate(Rom(d),true,false);var old=Id(d);byte[] receipt=File.ReadAllBytes(Receipt(d));var p=UpgradeData();var e=new ResourceEngine(p.settings,p.data,(m,n)=>{if(n==100)throw new IOException("after receipt injection");});Reject(()=>e.Operate(Rom(d),true,false));Same(d,old);Assert(File.ReadAllBytes(Receipt(d)).SequenceEqual(receipt),"Committed receipt not reverted");});
  test("resource archive-only upgrade retains executable receipt",()=>{string d=Fixture();var originalId=Id(d);Engine().Operate(Rom(d),true,false);var p=UpgradeData();var e=new ResourceEngine(p.settings,p.data);e.Operate(Rom(d),false,false);var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(Receipt(d)),new JsonSerializerOptions {IncludeFields=true});Assert(state.files.Count==2 && e.Inspect(Rom(d)).components[1].upgrade,"Executable receipt lost");e.Operate(Rom(d),true,true);Same(d,originalId);});
 }
 public static void Real(string source,string targetDir) {
  Assert(!Directory.Exists(targetDir),"Real output must not exist");Directory.CreateDirectory(targetDir);
  var payload=Payload.Load();var resource=ResourcePayload.Load();var e=new ResourceEngine(payload,resource,(m,n)=>Console.WriteLine(n+"% "+m));
  string rom=Path.Combine(targetDir,payload.Settings.archive_file),exe=Path.Combine(targetDir,payload.Settings.executable_file);
  File.Copy(Path.Combine(source,payload.Settings.archive_file),rom);File.Copy(Path.Combine(source,payload.Settings.executable_file),exe);
  string[] original={LocalizationInstaller.Engine.Hash(rom),LocalizationInstaller.Engine.Hash(exe)};
  e.Inspect(rom);Console.WriteLine("RESOURCE_BASELINE files=2 archive_match=NAMED_MEMBERS executable_match="+(resource.native_executable!=null?"NATIVE_EXACT":"RELOCATED_LITERALS")+" result=PASS");e.Operate(rom,true,false);
  Assert(!e.Inspect(rom).CanInstall,"Real install state");
  if(original[0]==payload.Archive.original_sha256)Assert(LocalizationInstaller.Engine.Hash(rom)==payload.Archive.modified_sha256,"Reference archive output mismatch");
  if(original[1]==payload.Executable.original_sha256)Assert(LocalizationInstaller.Engine.Hash(exe)==payload.Executable.modified_sha256,"Reference executable output mismatch");
  Assert(e.Operate(rom,true,false)=="ALREADY_INSTALLED","Real idempotence");
  Console.WriteLine("RESOURCE_MODIFIED files=2 idempotence=PASS named_members=PASS executable_match="+(resource.native_executable!=null?"NATIVE_EXACT":"RELOCATED_LITERALS")+" result=PASS");
  e.Operate(rom,true,true);Assert(LocalizationInstaller.Engine.Hash(rom)==original[0] && LocalizationInstaller.Engine.Hash(exe)==original[1],"Real restore failed");
  Console.WriteLine("RESOURCE_ROLLBACK files=2 restored=BYTE_IDENTICAL backup=RETAINED game_launch=NEVER result=PASS");
 }
}
