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
 static Payload Settings()=>new Payload {Settings=new Settings {archive_file="rom.zar",executable_file="Game.exe",backup_folder="cn-backup"},Archive=new Delta(),Executable=new Delta()};
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
 static string Receipt(string dir)=>Path.Combine(dir,"cn-backup/resource-state.json");
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
  test("backup names and complete restore cleanup",()=>{string d=Fixture();var p=Settings();p.Settings.backup_folder="cn-backup";var e=new ResourceEngine(p,Data());var id=Id(d);e.Operate(Rom(d),true,false);Assert(File.Exists(Path.Combine(d,"cn-backup/rom.zar")) && File.Exists(Path.Combine(d,"cn-backup/Game.exe")),"Backup filenames must match game filenames");e.Operate(Rom(d),true,true);Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Backup folder remains after verified restore");});
  test("legacy hashed backups migrate read-only inspect then clean restore",()=>{string d=Fixture();var id=Id(d);var old=Settings();old.Settings.backup_folder=".dementium-locale";var e=new ResourceEngine(old,Data());e.Operate(Rom(d),true,false);var options=new JsonSerializerOptions {IncludeFields=true};string receipt=Path.Combine(d,".dementium-locale/resource-state.json");var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(receipt),options);foreach(var f in state.files){string name="original-"+f.original+Path.GetExtension(f.name);File.Move(Path.Combine(d,".dementium-locale",f.backup),Path.Combine(d,".dementium-locale",name));f.backup=name;}File.WriteAllText(receipt,JsonSerializer.Serialize(state,options));var next=Engine();Assert(next.Inspect(Rom(d)).CanRestore,"Legacy inspect");Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Inspect migrated files");next.Operate(Rom(d),true,false);Assert(!Directory.Exists(Path.Combine(d,".dementium-locale")),"Legacy remains");Assert(File.Exists(Path.Combine(d,"cn-backup/rom.zar")),"Migration filename");next.Operate(Rom(d),true,true);Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Restore residue");});
  test("migration failed restore keeps backups and retry cleans both directories",()=>{string d=Fixture();var old=Settings();old.Settings.backup_folder=".dementium-locale";new ResourceEngine(old,Data()).Operate(Rom(d),true,false);var id=Id(d);var e=Engine();e.BeforeReplace=i=>{if(i==1)throw new IOException("restore injection");};Reject(()=>e.Operate(Rom(d),true,true));Same(d,id);Assert(File.Exists(Path.Combine(d,"cn-backup/rom.zar")),"Lost recovery backup");Engine().Operate(Rom(d),true,true);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")) && !Directory.Exists(Path.Combine(d,".dementium-locale")),"Retry residue");});
  test("partial restore retains remaining executable backup",()=>{string d=Fixture();var id=Id(d);var e=Engine();e.Operate(Rom(d),true,false);e.Operate(Rom(d),false,true);Assert(Directory.Exists(Path.Combine(d,"cn-backup")) && e.Inspect(Rom(d)).CanRestore,"Partial restore lost EXE backup");e.Operate(Rom(d),true,true);Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Complete restore residue");});
  test("successful restore removes entire backup folder only",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);Directory.CreateDirectory(Path.Combine(d,"cn-backup/nested"));File.WriteAllText(Path.Combine(d,"cn-backup/nested/extra.tmp"),"RESIDUE");Directory.CreateDirectory(Path.Combine(d,"other"));File.WriteAllText(Path.Combine(d,"other/keep.txt"),"KEEP");e.Operate(Rom(d),true,true);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")) && File.ReadAllText(Path.Combine(d,"other/keep.txt"))=="KEEP","Cleanup escaped backup folder");});
  test("resource payload embedded and not container-offset based",()=>{var p=ResourcePayload.Load();Assert(p.members.Length>200 && p.literals.Length==5,"Missing real members");new ResourceEngine(Payload.Load(),p);});
  test("resource inspect reads only",()=>{string d=Fixture();var before=Id(d);Assert(Engine().Inspect(Rom(d)).CanInstall,"Not installable");Same(d,before);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Inspect wrote files");});
  test("resource install and exact source restore",()=>{string d=Fixture();var id=Id(d);var e=Engine();Assert(e.Operate(Rom(d),true,false)=="INSTALLED","Not installed");Assert(e.Inspect(Rom(d)).CanRestore,"No restore");e.Operate(Rom(d),true,true);Same(d,id);});
  test("resource unrelated update and extra members preserved",()=>{string d=Fixture(4096,true);byte[] source=File.ReadAllBytes(Rom(d));var e=Engine();e.Operate(Rom(d),true,false);using(var a=new ResourceArchive(Rom(d))){Assert(a.Read("TEX/OTHER.BIN").SequenceEqual(new byte[4113]),"Unrelated changed");Assert(Encoding.ASCII.GetString(a.Read("OTHER/NEW.BIN"))=="NEW GAME UPDATE RESOURCE","New member lost");Assert(a.Read("EN/A.TBL").SequenceEqual(target),"Not translated");}e.Operate(Rom(d),true,true);Assert(File.ReadAllBytes(Rom(d)).SequenceEqual(source),"Update restore failed");});
  test("resource exe shifted section and changed file size",()=>{string d=Fixture(1536);byte[] before=File.ReadAllBytes(Program(d));Engine().Operate(Rom(d),true,false);byte[] after=File.ReadAllBytes(Program(d));Assert(after.AsSpan(528+1536,6).SequenceEqual(Encoding.UTF8.GetBytes("复古")),"Not relocated");for(int i=0;i<before.Length;i++)if(i<528+1536 || i>=540+1536)Assert(before[i]==after[i],"Nonliteral bytes changed");});
  test("resource target drift rejected without backup writes",()=>{string d=Fixture(text:Encoding.ASCII.GetBytes("CHANGED TEXT"));var id=Id(d);Reject(()=>Engine().Operate(Rom(d),true,false));Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Unexpected backup");});
  test("resource duplicate literal rejected before archive write",()=>{string d=Fixture();File.WriteAllBytes(Program(d),Exe(duplicate:true));var id=Id(d);Reject(()=>Engine().Operate(Rom(d),true,false));Same(d,id);});
  test("resource malformed archive rejected",()=>{string d=Fixture();File.WriteAllText(Rom(d),"bad archive");var id=Id(d);Reject(()=>Engine().Operate(Rom(d),true,false));Same(d,id);});
  test("resource damaged backup refuses restore",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);var c=e.Inspect(Rom(d)).components[0];File.AppendAllText(c.backup,"bad");var id=Id(d);Reject(()=>e.Operate(Rom(d),true,true));Same(d,id);});
  test("resource missing receipt does not invent backup",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);File.Delete(Path.Combine(d,"cn-backup/resource-state.json"));var id=Id(d);Reject(()=>e.Inspect(Rom(d)));Same(d,id);});
  test("resource receipt traversal rejected",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);string p=Path.Combine(d,"cn-backup/resource-state.json");var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(p),new JsonSerializerOptions {IncludeFields=true});state.files[0].backup="../outside.zar";File.WriteAllText(p,JsonSerializer.Serialize(state,new JsonSerializerOptions {IncludeFields=true}));Reject(()=>e.Inspect(Rom(d)));});
  test("resource second commit failure restores both and retry works",()=>{string d=Fixture();var id=Id(d);var e=Engine();e.BeforeReplace=i=>{if(i==1)throw new IOException("injected");};Reject(()=>e.Operate(Rom(d),true,false));Same(d,id);Engine().Operate(Rom(d),true,false);Engine().Operate(Rom(d),true,true);Same(d,id);});
  test("resource first commit failure leaves originals",()=>{string d=Fixture();var id=Id(d);var e=Engine();e.BeforeReplace=i=>throw new IOException("injected");Reject(()=>e.Operate(Rom(d),true,false));Same(d,id);});
  test("resource repeated install does not grow archive",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);long size=new FileInfo(Rom(d)).Length;var id=Id(d);Assert(e.Operate(Rom(d),true,false)=="ALREADY_INSTALLED","Not idempotent");Same(d,id);Assert(new FileInfo(Rom(d)).Length==size,"Grew archive");});
  test("resource repeated restore no rewrite",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);e.Operate(Rom(d),true,true);var time=File.GetLastWriteTimeUtc(Rom(d));Assert(e.Operate(Rom(d),true,true)=="ALREADY_RESTORED","Restore state");Assert(File.GetLastWriteTimeUtc(Rom(d))==time,"Rewrote original");});
  test("resource later original update creates fresh named backups",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);string old=e.Inspect(Rom(d)).components[0].backup;e.Operate(Rom(d),true,true);File.WriteAllBytes(Rom(d),Zar(new byte[777],true));File.WriteAllBytes(Program(d),Exe(1024));var id=Id(d);e.Operate(Rom(d),true,false);Assert(e.Inspect(Rom(d)).components[0].backup==old && LocalizationInstaller.Engine.Hash(old)==id[0],"Fresh original backup mismatch");e.Operate(Rom(d),true,true);Same(d,id);});
  test("resource interrupted mixed component state recovers",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);var c=e.Inspect(Rom(d)).components[1];File.Copy(c.backup,c.path,true);var inspect=e.Inspect(Rom(d));Assert(inspect.CanInstall && inspect.CanRestore,"Mixed unrecognized");e.Operate(Rom(d),true,false);Assert(!e.Inspect(Rom(d)).CanInstall,"Mixed not completed");});
  test("resource save and config untouched",()=>{string d=Fixture();File.WriteAllText(Path.Combine(d,"save.dat"),"SAVE");File.WriteAllText(Path.Combine(d,"settings.ini"),"CONFIG");var e=Engine();e.Operate(Rom(d),true,false);e.Operate(Rom(d),true,true);Assert(File.ReadAllText(Path.Combine(d,"save.dat"))=="SAVE" && File.ReadAllText(Path.Combine(d,"settings.ini"))=="CONFIG","User data changed");});
  test("resource writable PE section rejected",()=>{string d=Fixture();byte[] b=File.ReadAllBytes(Program(d));BitConverter.GetBytes((uint)0xC0000040).CopyTo(b,124);File.WriteAllBytes(Program(d),b);Reject(()=>Engine().Operate(Rom(d),true,false));});
  test("resource metadata duplicate members rejected",()=>{var p=Data();p.members=new[]{p.members[0],p.members[0]};Reject(()=>new ResourceEngine(Settings(),p));});
  test("resource restore second commit failure keeps installed files",()=>{string d=Fixture();var e=Engine();e.Operate(Rom(d),true,false);var installed=Id(d);e.BeforeReplace=i=>{if(i==1)throw new IOException("injected restore failure");};Reject(()=>e.Operate(Rom(d),true,true));Same(d,installed);Engine().Operate(Rom(d),true,true);});
  test("resource concurrent precommit change is preserved",()=>{string d=Fixture();byte[] before=File.ReadAllBytes(Rom(d));var e=Engine();e.BeforeReplace=i=>{if(i==0)using(var f=new FileStream(Rom(d),FileMode.Append))f.WriteByte(66);};Reject(()=>e.Operate(Rom(d),true,false));Assert(File.ReadAllBytes(Rom(d)).SequenceEqual(before.Concat(new byte[]{66})),"Concurrent source change lost");Assert(File.ReadAllBytes(Program(d)).SequenceEqual(Exe()),"Other component changed");});
  test("resource native PE exact bytes append and rollback",()=>{string d=Fixture();var id=Id(d);var p=NativeData();var e=new ResourceEngine(p.settings,p.data);Assert(e.Operate(Rom(d),true,false)=="INSTALLED","Native install");Assert(File.ReadAllBytes(Program(d)).SequenceEqual(p.output),"Native PE append lost");Assert(e.Operate(Rom(d),true,false)=="ALREADY_INSTALLED","Native idempotence");e.Operate(Rom(d),true,true);Same(d,id);});
  test("resource native guarded unknown identity installs preserves differences and rolls back",()=>{
   string d=Fixture();var p=NativeData();byte[] source=Exe();source[1800]=42;File.WriteAllBytes(Program(d),source);var id=Id(d);
   byte[] known=Exe();p.data.native_executable.hash_guards=new[]{
    new HashGuard {offset=0,length=128,sha256=Hash(known.Take(128).ToArray()),target_sha256=Hash(p.output.Take(128).ToArray())},
    new HashGuard {offset=240,length=32,sha256=Hash(known.Skip(240).Take(32).ToArray()),target_sha256=Hash(p.output.Skip(240).Take(32).ToArray())}};
   var e=new ResourceEngine(p.settings,p.data);Assert(e.Operate(Rom(d),true,false)=="INSTALLED","Guarded install");
   Assert(File.ReadAllBytes(Program(d))[1800]==42,"Unrelated difference lost");Assert(e.Operate(Rom(d),true,false)=="ALREADY_INSTALLED","Guarded idempotence");
   e.Operate(Rom(d),true,true);Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Guarded restore residue");
  });
  test("resource native guarded feature mismatch makes zero writes",()=>{
   foreach(int offset in new[]{60,70,108,250,256}) {
    string d=Fixture();var p=NativeData();byte[] known=Exe();p.data.native_executable.hash_guards=new[]{new HashGuard {offset=0,length=512,sha256=Hash(known.Take(512).ToArray()),target_sha256=Hash(p.output.Take(512).ToArray())}};
    byte[] source=Exe();source[offset]^=1;File.WriteAllBytes(Program(d),source);var id=Id(d);Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Mismatch wrote backup");
   }
  });
  test("resource native guards require complete header and edit coverage",()=>{
   foreach(bool missingHeader in new[]{true,false}) {
    string d=Fixture();var p=NativeData();byte[] source=Exe();source[1800]=42;File.WriteAllBytes(Program(d),source);var id=Id(d);
    p.data.native_executable.hash_guards=new[]{new HashGuard {offset=missingHeader?240:0,length=missingHeader?32:128,sha256=Hash(source.Skip(missingHeader?240:0).Take(missingHeader?32:128).ToArray()),target_sha256=new string('0',64)}};
    Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Incomplete guards wrote backup");
   }
  });
  test("resource multiple verified member sources install and restore",()=>{
   string d=Fixture(text:Encoding.ASCII.GetBytes("ORIGINAL2"));var p=Data();byte[] source=Encoding.ASCII.GetBytes("ORIGINAL2");
   p.members[0].source_variants=new[]{new MemberPatch {name="EN/A.TBL",source_size=source.Length,target_size=target.Length,source_sha256=Hash(source),target_sha256=Hash(target),runs=new[]{new PatchRun {offset=0,old=Convert.ToHexString(source.AsSpan(0,target.Length)),@new=Convert.ToHexString(target)}},tail=""}};
   var id=Id(d);var e=new ResourceEngine(Settings(),p);e.Operate(Rom(d),true,false);e.Operate(Rom(d),true,true);Same(d,id);
  });
  test("resource multiple verified executable sources install and restore",()=>{
   string d=Fixture();var p=NativeData();byte[] source=Exe();source[1800]=42;byte[] next=p.output.ToArray();next[1800]=42;File.WriteAllBytes(Program(d),source);var primary=p.data.native_executable;
   primary.source_variants=new[]{new MemberPatch {name=primary.name,source_size=source.Length,target_size=next.Length,source_sha256=Hash(source),target_sha256=Hash(next),runs=primary.runs,tail=primary.tail}};
   var id=Id(d);var e=new ResourceEngine(p.settings,p.data);e.Operate(Rom(d),true,false);Assert(File.ReadAllBytes(Program(d)).SequenceEqual(next),"Variant output");e.Operate(Rom(d),true,true);Same(d,id);
  });
  test("resource native PE unknown hash rejects before writes",()=>{string d=Fixture();var p=NativeData();byte[] b=Exe();b[300]=1;File.WriteAllBytes(Program(d),b);var id=Id(d);Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Native unknown source wrote backup");});
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
  test("resource upgrade corrupted or unsupported backup rejects",()=>{string d=Fixture();Engine().Operate(Rom(d),true,false);var id=Id(d);var options=new JsonSerializerOptions {IncludeFields=true};var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(Receipt(d)),options);string backup=Path.Combine(d,"cn-backup",state.files[0].backup);File.WriteAllBytes(backup,Zar(new byte[17],text:Encoding.ASCII.GetBytes("OTHER SOURCE")));state.files[0].original=LocalizationInstaller.Engine.Hash(backup);File.WriteAllText(Receipt(d),JsonSerializer.Serialize(state,options));var p=UpgradeData();Reject(()=>new ResourceEngine(p.settings,p.data).Operate(Rom(d),true,false));Same(d,id);});
  test("resource upgrade second commit failure retains old files and receipt",()=>{string d=Fixture();Engine().Operate(Rom(d),true,false);var old=Id(d);byte[] receipt=File.ReadAllBytes(Receipt(d));var p=UpgradeData();var e=new ResourceEngine(p.settings,p.data);e.BeforeReplace=i=>{if(i==1)throw new IOException("upgrade injection");};Reject(()=>e.Operate(Rom(d),true,false));Same(d,old);Assert(File.ReadAllBytes(Receipt(d)).SequenceEqual(receipt),"Old upgrade receipt changed");e.BeforeReplace=null;e.Operate(Rom(d),true,false);Assert(!e.Inspect(Rom(d)).CanInstall,"Upgrade retry failed");});
  test("resource postreceipt failure rolls back receipt and upgraded files",()=>{string d=Fixture();Engine().Operate(Rom(d),true,false);var old=Id(d);byte[] receipt=File.ReadAllBytes(Receipt(d));var p=UpgradeData();var e=new ResourceEngine(p.settings,p.data,(m,n)=>{if(n==100)throw new IOException("after receipt injection");});Reject(()=>e.Operate(Rom(d),true,false));Same(d,old);Assert(File.ReadAllBytes(Receipt(d)).SequenceEqual(receipt),"Committed receipt not reverted");});
  test("resource archive-only upgrade retains executable receipt",()=>{string d=Fixture();var originalId=Id(d);Engine().Operate(Rom(d),true,false);var p=UpgradeData();var e=new ResourceEngine(p.settings,p.data);e.Operate(Rom(d),false,false);var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(Receipt(d)),new JsonSerializerOptions {IncludeFields=true});Assert(state.files.Count==2 && e.Inspect(Rom(d)).components[1].upgrade,"Executable receipt lost");e.Operate(Rom(d),true,true);Same(d,originalId);});
 }
 static int SectionProbe(byte[] bytes,string section,MemberPatch patch,bool protectedRegion) {
  int pe=BitConverter.ToInt32(bytes,60),count=BitConverter.ToUInt16(bytes,pe+6),table=pe+24+BitConverter.ToUInt16(bytes,pe+20);
  for(int i=0;i<count;i++) {
   int row=table+i*40;if(Encoding.ASCII.GetString(bytes,row,8).TrimEnd('\0')!=section)continue;
   int start=checked((int)BitConverter.ToUInt32(bytes,row+20)),size=checked((int)BitConverter.ToUInt32(bytes,row+16));
   for(int offset=start+size/2;offset<start+size;offset++) {
    bool changed=patch.runs.Any(r=>offset>=r.offset && offset<r.offset+r.old.Length/2);
    bool guarded=(patch.hash_guards ?? Array.Empty<HashGuard>()).Any(g=>offset>=g.offset && offset<g.offset+g.length);
    if(!changed && guarded==protectedRegion)return offset;
   }
  }
  throw new Exception("No suitable compatibility probe in "+section);
 }
 public static void CompatibilityReal(string source,string targetDir) {
  Assert(!Directory.Exists(targetDir),"Compatibility output must not exist");
  var payload=Payload.Load();var resource=ResourcePayload.Load();var patch=resource.native_executable;
  Assert(patch?.hash_guards?.Length>0,"Real compatibility requires hash guards");
  string sourceRom=Path.Combine(source,payload.Settings.archive_file),sourceExe=Path.Combine(source,payload.Settings.executable_file);
  string sourceRomHash=LocalizationInstaller.Engine.Hash(sourceRom),sourceExeHash=LocalizationInstaller.Engine.Hash(sourceExe);
  Assert(sourceRomHash==payload.Archive.original_sha256 && sourceExeHash==patch.source_sha256,"Expected verified current build inputs");
  Directory.CreateDirectory(targetDir);
  string rom=Path.Combine(targetDir,payload.Settings.archive_file),exe=Path.Combine(targetDir,payload.Settings.executable_file),cache=Path.Combine(targetDir,payload.Settings.backup_folder);
  File.Copy(sourceRom,rom);File.Copy(sourceExe,exe);
  byte[] originalExe=File.ReadAllBytes(exe);int resourceOffset=SectionProbe(originalExe,".rsrc",patch,false);byte[] changed=originalExe.ToArray();changed[resourceOffset]^=1;File.WriteAllBytes(exe,changed);
  string mutatedHash=LocalizationInstaller.Engine.Hash(exe);Assert(mutatedHash!=patch.source_sha256,"Probe did not change identity");
  var engine=new ResourceEngine(payload,resource);Assert(engine.Inspect(rom).CanInstall,"Unknown harmless identity not accepted");
  Console.WriteLine("COMPAT_BASELINE section=.rsrc offset="+resourceOffset+" original_sha256="+sourceExeHash+" unknown_sha256="+mutatedHash+" checks=PASS writes=NONE result=PASS");
  Assert(engine.Operate(rom,true,false)=="INSTALLED","Unknown identity install failed");
  byte[] installed=File.ReadAllBytes(exe);Assert(installed[resourceOffset]==changed[resourceOffset],"Unknown resource difference lost");
  string installedRom=LocalizationInstaller.Engine.Hash(rom),installedExe=LocalizationInstaller.Engine.Hash(exe);
  Assert(engine.Operate(rom,true,false)=="ALREADY_INSTALLED","Unknown identity idempotence failed");
  Assert(LocalizationInstaller.Engine.Hash(rom)==installedRom && LocalizationInstaller.Engine.Hash(exe)==installedExe,"Idempotent operation changed bytes");
  Console.WriteLine("COMPAT_MODIFIED section=.rsrc difference=PRESERVED installed_sha256="+installedExe+" idempotence=PASS result=PASS");
  Assert(engine.Operate(rom,true,true)=="RESTORED","Unknown identity restore failed");
  Assert(LocalizationInstaller.Engine.Hash(rom)==sourceRomHash && LocalizationInstaller.Engine.Hash(exe)==mutatedHash && File.ReadAllBytes(exe).SequenceEqual(changed),"Unknown identity rollback differs");
  Assert(!Directory.Exists(cache),"Unknown identity rollback left backup directory");
  Console.WriteLine("COMPAT_ROLLBACK files=2 restored=BYTE_IDENTICAL restored_exe_sha256="+mutatedHash+" backup=REMOVED result=PASS");
  int textOffset=SectionProbe(originalExe,".text",patch,true);byte[] incompatible=originalExe.ToArray();incompatible[textOffset]^=1;File.WriteAllBytes(exe,incompatible);
  string badHash=LocalizationInstaller.Engine.Hash(exe);bool rejected=false;string reason="";
  try {engine.Operate(rom,true,false);}catch(InvalidDataException ex){rejected=true;reason=ex.Message;}
  Assert(rejected,"Changed dependent text section was accepted");
  Assert(LocalizationInstaller.Engine.Hash(rom)==sourceRomHash && LocalizationInstaller.Engine.Hash(exe)==badHash,"Rejected dependent change wrote game files");
  Assert(!Directory.Exists(cache),"Rejected dependent change wrote backup directory");
  Console.WriteLine("COMPAT_REJECT section=.text offset="+textOffset+" modified_run=NO unknown_sha256="+badHash+" originals=UNCHANGED backup=ABSENT reason="+reason+" result=PASS");
  Assert(LocalizationInstaller.Engine.Hash(sourceRom)==sourceRomHash && LocalizationInstaller.Engine.Hash(sourceExe)==sourceExeHash,"Source game installation changed");
  Console.WriteLine("COMPAT_REAL cases=2 source_files=UNCHANGED game_launch=NEVER result=PASS");
 }
 public static void Real(string source,string targetDir) {
  Assert(!Directory.Exists(targetDir),"Real output must not exist");Directory.CreateDirectory(targetDir);
  var payload=Payload.Load();var resource=ResourcePayload.Load();var e=new ResourceEngine(payload,resource,(m,n)=>Console.WriteLine(n+"% "+m));
  string rom=Path.Combine(targetDir,payload.Settings.archive_file),exe=Path.Combine(targetDir,payload.Settings.executable_file);
  File.Copy(Path.Combine(source,payload.Settings.archive_file),rom);File.Copy(Path.Combine(source,payload.Settings.executable_file),exe);
  string[] original={LocalizationInstaller.Engine.Hash(rom),LocalizationInstaller.Engine.Hash(exe)};
  e.Inspect(rom);Console.WriteLine("RESOURCE_BASELINE files=2 archive_match=NAMED_MEMBERS executable_match="+(resource.native_executable!=null?"GUARDED_NATIVE":"RELOCATED_LITERALS")+" result=PASS");e.Operate(rom,true,false);
  Assert(!e.Inspect(rom).CanInstall,"Real install state");
  if(original[0]==payload.Archive.original_sha256)Assert(LocalizationInstaller.Engine.Hash(rom)==payload.Archive.modified_sha256,"Reference archive output mismatch");
  if(original[1]==payload.Executable.original_sha256)Assert(LocalizationInstaller.Engine.Hash(exe)==payload.Executable.modified_sha256,"Reference executable output mismatch");
  Assert(e.Operate(rom,true,false)=="ALREADY_INSTALLED","Real idempotence");
  Console.WriteLine("RESOURCE_MODIFIED files=2 idempotence=PASS named_members=PASS executable_match="+(resource.native_executable!=null?"GUARDED_NATIVE":"RELOCATED_LITERALS")+" result=PASS");
  e.Operate(rom,true,true);Assert(LocalizationInstaller.Engine.Hash(rom)==original[0] && LocalizationInstaller.Engine.Hash(exe)==original[1],"Real restore failed");
  Assert(!Directory.Exists(Path.Combine(targetDir,payload.Settings.backup_folder)),"Backup directory remains");
  Console.WriteLine("RESOURCE_ROLLBACK files=2 restored=BYTE_IDENTICAL backup=REMOVED game_launch=NEVER result=PASS");
 }
}
