using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace LocalizationInstaller {
 public sealed class MemberPatch {
  public string name,source_sha256,target_sha256,tail;
  public int source_size,target_size;
  public PatchRun[] runs;
 }
 public sealed class LiteralPatch { public string source,target; public int capacity; }
 public sealed class ResourcePayload {
  public int schema;
  public MemberPatch[] members;
  public LiteralPatch[] literals;
  public MemberPatch native_executable;
  public static ResourcePayload Load()=>Payload.Read<ResourcePayload>("resource-patches.gz",true);
 }
 public sealed class ResourceState {
  public int schema=1;
  public List<SavedComponent> files=new List<SavedComponent>();
 }
 public sealed class SavedComponent { public string name,backup,original,installed; }
 public sealed class ResourceComponent {
  public string path,current,backup,original;
  public bool installed,upgrade;
 }
 public sealed class ResourceInspection {
  public List<ResourceComponent> components=new List<ResourceComponent>();
  public bool NativeExecutable;
  public bool CanInstall=>components.Any(c=>!c.installed || c.upgrade);
  public bool CanRestore=>components.Any(c=>c.installed);
  public string Summary=>components.Any(c=>c.upgrade) ? "已核对旧版安装记录及原版备份，可以升级或恢复原版" : CanInstall ? (NativeExecutable ? "资源匹配、原生菜单程序精确校验通过，可以安装" : "资源可匹配，可以安装（不限制整包哈希或 build）") : "汉化已安装，可恢复安装前文件";
 }
 sealed class ArchiveMember { public string name; public long offset,size,toc; }
 // Strict structure/target-resource checks, not a whole-file version allow-list.
 sealed class ResourceArchive : IDisposable {
  public readonly FileStream stream;
  public readonly Dictionary<string,ArchiveMember> members=new Dictionary<string,ArchiveMember>(StringComparer.Ordinal);
  public ResourceArchive(string path) {
   stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);
   try {
    byte[] h=ReadAt(0,32);
    long count=U32(h,4),header=U32(h,8),names=U32(h,16),strings=U32(h,20),toc=U32(h,24);
    if(Encoding.ASCII.GetString(h,0,4)!="ZAR1" || count<1 || U32(h,12)!=0 || U32(h,28)!=0 ||
      names<32 || names>strings || strings>toc || toc>header || header>stream.Length || header>64*1024*1024 ||
      count>(strings-names)/4 || count>(header-toc)/24)throw new InvalidDataException("归档头结构不匹配");
    byte[] all=ReadAt(0,(int)header);string previous="";
    for(int i=0;i<count;i++) {
     long n=strings+U32(all,(int)names+4*i);string name=Name(all,n,toc);
     long row=toc+24*i,offset=I64(all,(int)row),size=I64(all,(int)row+8);
     if(String.CompareOrdinal(previous,name)>=0 || name.StartsWith('/') || name.Contains('\\') || name.Contains(':') || name.Split('/').Contains("..") ||
       offset<header || offset%512!=0 || size<0 || offset>stream.Length-size || I64(all,(int)row+16)!=0)throw new InvalidDataException("归档成员结构不匹配："+name);
     members.Add(name,new ArchiveMember {name=name,offset=offset,size=size,toc=row});previous=name;
    }
    long end=header;foreach(var m in members.Values.OrderBy(m=>m.offset)){if(m.offset<end)throw new InvalidDataException("归档成员重叠");end=m.offset+m.size;}
   }catch{stream.Dispose();throw;}
  }
  internal static long U32(byte[] b,int p)=>BitConverter.ToUInt32(b,p);
  internal static long I64(byte[] b,int p)=>checked((long)BitConverter.ToUInt64(b,p));
  internal static string Name(byte[] b,long p,long end) {
   if(p<0 || p>=end || end>b.Length)throw new InvalidDataException("资源名称越界");
   int start=(int)p;while(p<end && b[(int)p]!=0){if(b[(int)p]<32 || b[(int)p]>126)throw new InvalidDataException("资源名称编码不匹配");p++;}
   if(p==end || p==start)throw new InvalidDataException("资源名称未终止");return Encoding.ASCII.GetString(b,start,(int)p-start);
  }
  byte[] ReadAt(long offset,int size) {byte[] b=new byte[size];stream.Position=offset;stream.ReadExactly(b);return b;}
  public byte[] Read(string name) {
   if(!members.TryGetValue(name,out var m))throw new InvalidDataException("缺少汉化所需资源："+name);
   if(m.size>64*1024*1024)throw new InvalidDataException("待修改资源过大："+name);
   return ReadAt(m.offset,(int)m.size);
  }
  public byte[] Index(Dictionary<string,int> replacements) {
   byte[] b=Read("~INDEX");long count=I64(b,0),pool=checked(8+count*16);
   if(count<1 || pool>b.Length)throw new InvalidDataException("VFS目录结构不匹配");
   var seen=new HashSet<string>(StringComparer.Ordinal);
   for(int i=0;i<count;i++) {
    int row=8+i*16;string raw=Name(b,checked(pool+I64(b,row+8)),b.Length);
    if(!raw.StartsWith('/') || raw.Contains('\\') || raw.Contains(':') || raw.Split('/').Contains(".."))throw new InvalidDataException("VFS名称不匹配");
    string name=raw.TrimStart('/').ToUpperInvariant();if(!seen.Add(name))throw new InvalidDataException("VFS资源重复");
    long flags=U32(b,row+4),size=U32(b,row);
    if(members.TryGetValue(name,out var m) && flags==0 && size!=m.size)throw new InvalidDataException("VFS资源尺寸不一致："+name);
    if(replacements.TryGetValue(name,out int desired)) {
     if(flags!=0)throw new InvalidDataException("VFS压缩资源尚未适配："+name);
     BitConverter.GetBytes((uint)desired).CopyTo(b,row);
    }
   }
   if(replacements.Keys.Any(n=>!seen.Contains(n)))throw new InvalidDataException("VFS缺少汉化成员");
   return b;
  }
  public void Dispose()=>stream.Dispose();
 }
 public sealed class ResourceEngine {
  readonly Payload legacy;
  readonly ResourcePayload data;
  readonly Action<string,int> report;
  internal Action<int> BeforeReplace=null;
  const string Receipt="resource-state.json";
  static readonly JsonSerializerOptions Json=new JsonSerializerOptions {IncludeFields=true,WriteIndented=true};
  public ResourceEngine(Payload settings,ResourcePayload patches,Action<string,int> progress=null) {
   legacy=settings;data=patches;report=progress ?? ((s,n)=>{});
   if(data?.schema!=1 || data.members==null || data.members.Length<1 || data.literals==null || (data.literals.Length<1 && data.native_executable==null) || data.members.Any(p=>p.name=="~INDEX") || data.members.Select(p=>p.name).Distinct().Count()!=data.members.Length)throw new InvalidDataException("资源补丁元数据不匹配");
   foreach(var p in data.members) {
    if(p.source_size<0 || p.target_size<0 || p.source_size>64*1024*1024 || p.target_size>64*1024*1024 || !ValidHash(p.source_sha256) || !ValidHash(p.target_sha256) || p.runs==null)throw new InvalidDataException("资源补丁字段不匹配");
   }
   foreach(var p in data.literals)if(p.capacity<2 || p.capacity>1024 || Encoding.UTF8.GetByteCount(p.source)>=p.capacity || Encoding.UTF8.GetByteCount(p.target)>=p.capacity || p.source.Contains('\0') || p.target.Contains('\0'))throw new InvalidDataException("菜单字节槽不匹配");
   foreach(string name in new[]{legacy.Settings.archive_file,legacy.Settings.executable_file,legacy.Settings.backup_folder})if(!SimpleName(name))throw new InvalidDataException("非法补丁路径");
   if(legacy.Executable?.format=="native-menu-pe-v1" && data.native_executable==null)throw new InvalidDataException("缺少原生菜单程序差分");
   if(data.native_executable!=null) {
    var p=data.native_executable;var d=legacy.Executable;
    if(p.name!=legacy.Settings.executable_file || p.source_size<=0 || p.target_size<p.source_size || p.target_size>256*1024*1024 ||
      !ValidHash(p.source_sha256) || !ValidHash(p.target_sha256) || p.runs==null || d?.format!="native-menu-pe-v1" ||
      p.source_size!=d.original_size || p.target_size!=d.modified_size || p.source_sha256!=d.original_sha256 || p.target_sha256!=d.modified_sha256)
     throw new InvalidDataException("原生菜单程序补丁身份不匹配");
   }
  }
  static bool SimpleName(string s)=>!String.IsNullOrWhiteSpace(s) && s!="." && s!=".." && Path.GetFileName(s)==s && !s.Contains('/') && !s.Contains('\\') && !s.Contains(':');
  static bool ValidHash(string s)=>s!=null && s.Length==64 && s.All(c=>"0123456789abcdef".Contains(c));
  static string Digest(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
  static byte[] Decode(string s)=>Convert.FromHexString(s);
  static byte[] ApplyMember(byte[] original,MemberPatch patch) {
   if(original.Length!=patch.source_size || Digest(original)!=patch.source_sha256)throw new InvalidDataException("资源内容已变化，请反馈适配："+patch.name);
   byte[] output=new byte[patch.target_size];Buffer.BlockCopy(original,0,output,0,Math.Min(original.Length,output.Length));
   long end=0;
   foreach(var r in patch.runs) {
    byte[] old=Decode(r.old),next=Decode(r.@new);
    if(old.Length==0 || old.Length!=next.Length || r.offset<end || r.offset>Math.Min(original.Length,output.Length)-old.Length || !original.AsSpan((int)r.offset,old.Length).SequenceEqual(old))throw new InvalidDataException("资源差分位置不匹配："+patch.name);
    next.CopyTo(output,(int)r.offset);end=r.offset+old.Length;
   }
   byte[] tail=Convert.FromBase64String(patch.tail ?? "");int prefix=Math.Min(original.Length,output.Length);
   if(tail.Length!=output.Length-prefix)throw new InvalidDataException("资源差分尾部不匹配");tail.CopyTo(output,prefix);
   if(Digest(output)!=patch.target_sha256)throw new InvalidDataException("资源生成失败："+patch.name);return output;
  }
  // Returns original/installed counts. Resource hashes protect only members we edit.
  (int original,int installed) ArchiveState(string path) {
   using var archive=new ResourceArchive(path);int original=0,installed=0;
   foreach(var patch in data.members) {
    byte[] bytes=archive.Read(patch.name);string hash=Digest(bytes);
    if(hash==patch.source_sha256 && bytes.Length==patch.source_size)original++;
    else if(hash==patch.target_sha256 && bytes.Length==patch.target_size)installed++;
    else throw new InvalidDataException("待汉化资源已变化，请反馈适配："+patch.name);
   }
   archive.Index(new Dictionary<string,int>());return (original,installed);
  }
  sealed class FoundLiteral { public int offset; public byte[] target; public bool installed; }
  List<FoundLiteral> Literals(byte[] bytes) {
   if(bytes.Length<64 || Encoding.ASCII.GetString(bytes,0,2)!="MZ")throw new InvalidDataException("游戏程序不是有效PE文件");
   int pe=BitConverter.ToInt32(bytes,60);
   if(pe<64 || pe>bytes.Length-24 || Encoding.ASCII.GetString(bytes,pe,4)!="PE\0\0")throw new InvalidDataException("游戏程序PE头不匹配");
   int count=BitConverter.ToUInt16(bytes,pe+6),optional=BitConverter.ToUInt16(bytes,pe+20),table=checked(pe+24+optional);int lo=-1,hi=-1;
   if(table>bytes.Length-count*40)throw new InvalidDataException("游戏程序节表不匹配");
   for(int i=0;i<count;i++) {
    int row=table+40*i;string name=Encoding.ASCII.GetString(bytes,row,8).TrimEnd('\0');
    long size=BitConverter.ToUInt32(bytes,row+16),start=BitConverter.ToUInt32(bytes,row+20);uint flags=BitConverter.ToUInt32(bytes,row+36);
    if(start>bytes.Length-size)throw new InvalidDataException("游戏程序节区越界");
    if(name==".rdata") {if(lo>=0 || (flags&0xA0000000)!=0)throw new InvalidDataException("程序只读数据节不匹配");lo=(int)start;hi=(int)(start+size);}
   }
   if(lo<0)throw new InvalidDataException("游戏程序缺少.rdata");
   var result=new List<FoundLiteral>();
   foreach(var literal in data.literals) {
    byte[] old=new byte[literal.capacity],next=new byte[literal.capacity];Encoding.UTF8.GetBytes(literal.source).CopyTo(old,0);Encoding.UTF8.GetBytes(literal.target).CopyTo(next,0);
    var hits=new List<FoundLiteral>();
    for(int offset=lo;offset<=hi-old.Length;offset++) {
     if(offset>lo && bytes[offset-1]!=0)continue;
     if(bytes.AsSpan(offset,old.Length).SequenceEqual(old))hits.Add(new FoundLiteral {offset=offset,target=next});
     else if(bytes.AsSpan(offset,next.Length).SequenceEqual(next))hits.Add(new FoundLiteral {offset=offset,target=next,installed=true});
    }
    if(hits.Count!=1)throw new InvalidDataException("菜单原文定位不唯一或已变化，请反馈："+literal.source);result.Add(hits[0]);
   }
   int end=-1;foreach(var hit in result.OrderBy(h=>h.offset)){if(hit.offset<end)throw new InvalidDataException("菜单字节槽重叠");end=hit.offset+hit.target.Length;}return result;
  }
  (int original,int installed) ExeState(string path) {
   if(new FileInfo(path).Length>256*1024*1024)throw new InvalidDataException("游戏程序过大");
   if(data.native_executable!=null) {
    var p=data.native_executable;long size=new FileInfo(path).Length;string hash=Engine.Hash(path);
    if(size==p.source_size && hash==p.source_sha256)return(1,0);
    if(size==p.target_size && hash==p.target_sha256)return(0,1);
    throw new InvalidDataException("原生菜单仅匹配已核对的程序版本；程序哈希或尺寸不符");
   }
   var hits=Literals(File.ReadAllBytes(path));return(hits.Count(h=>!h.installed),hits.Count(h=>h.installed));
  }
  public void Transform(string source,string target,bool archive) {
   if(archive) {
    using var input=new ResourceArchive(source);var replacements=new SortedDictionary<string,byte[]>(StringComparer.Ordinal);
    foreach(var patch in data.members) {
     byte[] bytes=input.Read(patch.name);if(Digest(bytes)==patch.target_sha256 && bytes.Length==patch.target_size)continue;
     replacements.Add(patch.name,ApplyMember(bytes,patch));
    }
    byte[] index=input.Index(replacements.ToDictionary(p=>p.Key,p=>p.Value.Length));
    if(!index.SequenceEqual(input.Read("~INDEX")))replacements.Add("~INDEX",index);
    using(var output=new FileStream(target,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None)) {
     input.stream.Position=0;input.stream.CopyTo(output);
     foreach(var replacement in replacements) {
      output.Position=output.Length;while(output.Length%512!=0)output.WriteByte(0);
      long position=output.Position;output.Write(replacement.Value);
      output.Position=input.members[replacement.Key].toc;output.Write(BitConverter.GetBytes((ulong)position));output.Write(BitConverter.GetBytes((ulong)replacement.Value.Length));
     }
     output.Flush(true);
    }
    if(ArchiveState(target).original!=0)throw new InvalidDataException("汉化资源生成未完成");
   } else {
    byte[] bytes=File.ReadAllBytes(source);
    if(data.native_executable!=null) {
     var p=data.native_executable;
     if(bytes.Length!=p.target_size || Digest(bytes)!=p.target_sha256)bytes=ApplyMember(bytes,p);
    } else {var hits=Literals(bytes);foreach(var hit in hits)hit.target.CopyTo(bytes,hit.offset);}
    using(var output=new FileStream(target,FileMode.CreateNew,FileAccess.Write,FileShare.None)){output.Write(bytes);output.Flush(true);}
    if(ExeState(target).original!=0)throw new InvalidDataException("程序菜单生成未完成");
   }
  }
  ResourceState ReadState(string cache) {
   string path=Path.Combine(cache,Receipt);if(!File.Exists(path))return new ResourceState();
   if(new FileInfo(path).Length>65536)throw new InvalidDataException("安装记录损坏");
   var state=JsonSerializer.Deserialize<ResourceState>(File.ReadAllText(path),Json);
   if(state?.schema!=1 || state.files==null || state.files.Count>2 || state.files.Select(f=>f.name).Distinct().Count()!=state.files.Count)throw new InvalidDataException("安装记录损坏");
   foreach(var f in state.files)if(!SimpleName(f.name) || !SimpleName(f.backup) || !ValidHash(f.original) || !ValidHash(f.installed))throw new InvalidDataException("安装记录字段损坏");
   return state;
  }
  void VerifySourceBackup(string backup,string hash,bool archive) {
   if(!File.Exists(backup) || Engine.Hash(backup)!=hash)throw new InvalidDataException("安装前备份缺失或损坏");
   var scan=archive?ArchiveState(backup):ExeState(backup);
   if(scan.original<1 || scan.installed!=0)throw new InvalidDataException("备份不是本版补丁支持的原版资源或程序");
  }
  public ResourceInspection Inspect(string selected,bool includeExe=true) {
   string path=Path.GetFullPath(selected);if(!String.Equals(Path.GetFileName(path),legacy.Settings.archive_file,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("请选择 rom.zar");
   string dir=Path.GetDirectoryName(path),cache=Path.Combine(dir,legacy.Settings.backup_folder);var state=ReadState(cache);var result=new ResourceInspection {NativeExecutable=includeExe && data.native_executable!=null};
   foreach(string name in includeExe?new[]{legacy.Settings.archive_file,legacy.Settings.executable_file}:new[]{legacy.Settings.archive_file}) {
    string file=Path.Combine(dir,name);report("检查资源定位："+name,5);
    if(!File.Exists(file))throw new FileNotFoundException("缺少游戏文件："+name);
    string current=Engine.Hash(file);var saved=state.files.FirstOrDefault(f=>f.name==name);
    bool archive=name==legacy.Settings.archive_file; (int original,int installed) scan;
    try {
     scan=archive?ArchiveState(file):ExeState(file);
     if(scan.original>0 && scan.installed>0)throw new InvalidDataException("文件含部分汉化资源，请先恢复或反馈："+name);
    } catch(InvalidDataException) {
     // An older localization is accepted only through its exact receipt and a
     // verified original backup which passes this NEW payload's source checks.
     if(saved==null || saved.installed!=current)throw;
     string backup=Path.Combine(cache,saved.backup);VerifySourceBackup(backup,saved.original,archive);
     result.components.Add(new ResourceComponent {path=file,current=current,installed=true,upgrade=true,original=saved.original,backup=backup});
     continue;
    }
    var c=new ResourceComponent {path=file,current=current,installed=scan.original==0};
    if(c.installed) {
     if(saved!=null && saved.installed!=current)throw new InvalidDataException("安装记录与当前汉化文件不匹配："+name);
     if(saved!=null && saved.installed==current){c.original=saved.original;c.backup=Path.Combine(cache,saved.backup);VerifySourceBackup(c.backup,c.original,archive);}
     else { // Adopt a known legacy installation only with its exact recorded backup.
      Delta delta=archive?legacy.Archive:legacy.Executable;string backup=Path.Combine(cache,archive?"original.zar":"original.exe");
      if(current!=delta.modified_sha256 || !File.Exists(backup) || Engine.Hash(backup)!=delta.original_sha256)throw new InvalidDataException("汉化已存在，但缺少匹配的恢复记录或文件安装后已变化："+name);
      c.original=delta.original_sha256;c.backup=backup;
     }
    } else {
     c.original=current;
     c.backup=Path.Combine(cache,"original-"+current+(archive?".zar":".exe"));
    }
    if(File.Exists(c.backup) && Engine.Hash(c.backup)!=c.original)throw new InvalidDataException("备份损坏："+Path.GetFileName(c.backup));
    if(c.installed && !File.Exists(c.backup))throw new InvalidDataException("缺少恢复备份："+name);
    result.components.Add(c);
   }
   return result;
  }
  public string Operate(string selected,bool includeExe,bool restore) {
   var inspection=Inspect(selected,includeExe);
   if(restore?!inspection.CanRestore:!inspection.CanInstall)return restore?"ALREADY_RESTORED":"ALREADY_INSTALLED";
   string cache=Path.Combine(Path.GetDirectoryName(Path.GetFullPath(selected)),legacy.Settings.backup_folder);
   long required=64L*1024*1024;
   foreach(var c in inspection.components)required+=new FileInfo(c.path).Length*2;
   required+=data.members.Sum(m=>(long)m.target_size);
   if(new DriveInfo(Path.GetPathRoot(cache)).AvailableFreeSpace<required)throw new IOException("空间不足，需要约 "+required/1024/1024+" MiB");
   Directory.CreateDirectory(cache);
   using var gate=new FileStream(Path.Combine(cache,"operation.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None,1,FileOptions.DeleteOnClose);
   inspection=Inspect(selected,includeExe);
   string token=Guid.NewGuid().ToString("N");var stages=new Dictionary<ResourceComponent,string>();var expected=new Dictionary<ResourceComponent,string>();var prior=new Dictionary<ResourceComponent,string>();var written=new List<ResourceComponent>();
   string stateTemp=Path.Combine(cache,"receipt-"+token+".tmp"),statePath=Path.Combine(cache,Receipt),statePrior=Path.Combine(cache,"receipt-prior-"+token+".tmp");
   bool stateExisted=File.Exists(statePath),stateWritten=false;string stateHash=stateExisted?Engine.Hash(statePath):null;
   var temps=new List<string>{stateTemp,statePrior};
   try {
    foreach(var c in inspection.components) {
     if(restore?!c.installed:(c.installed && !c.upgrade))continue;
     if(!restore && !File.Exists(c.backup)) {
      string pending=Path.Combine(cache,"backup-"+token+"-"+Path.GetFileName(c.path));temps.Add(pending);File.Copy(c.path,pending);
      if(Engine.Hash(pending)!=c.current)throw new IOException("备份写入不完整");File.Move(pending,c.backup);
     }
     if(!File.Exists(c.backup) || Engine.Hash(c.backup)!=c.original)throw new IOException("备份发生变化");
     string stage=Path.Combine(cache,"stage-"+token+"-"+Path.GetFileName(c.path));stages.Add(c,stage);temps.Add(stage);
     report(restore?"恢复安装前文件："+Path.GetFileName(c.path):"按资源生成汉化："+Path.GetFileName(c.path),50);
     if(restore)File.Copy(c.backup,stage);else Transform(c.upgrade?c.backup:c.path,stage,Path.GetFileName(c.path)==legacy.Settings.archive_file);
     expected[c]=Engine.Hash(stage);
     if(restore && expected[c]!=c.original)throw new IOException("恢复临时文件不完整");
    }
    if(inspection.components.Any(c=>Engine.Hash(c.path)!=c.current))throw new IOException("源文件被其他程序修改，已中止");
    if(!restore) {
     var receipt=ReadState(cache);
     foreach(var c in inspection.components) {
      string name=Path.GetFileName(c.path);receipt.files.RemoveAll(f=>f.name==name);
      receipt.files.Add(new SavedComponent {name=name,backup=Path.GetFileName(c.backup),original=c.original,installed=expected.TryGetValue(c,out string installed)?installed:c.current});
     }
     using(var file=new FileStream(stateTemp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(receipt,Json)));file.Flush(true);}
    }
    int i=0;
    foreach(var c in inspection.components) {
     if(!stages.ContainsKey(c))continue;
     BeforeReplace?.Invoke(i++);string rollback=Path.Combine(cache,"transaction-"+token+"-"+Path.GetFileName(c.path));prior.Add(c,rollback);temps.Add(rollback);
     File.Replace(stages[c],c.path,rollback,true);
     if(Engine.Hash(rollback)!=c.current){File.Replace(rollback,c.path,null,true);throw new IOException("提交时源文件改变，已保留原状态");}
     written.Add(c);if(Engine.Hash(c.path)!=expected[c])throw new IOException("写入不完整，正在恢复");
    }
    if(!restore) {
     // Commit the receipt only after BOTH game components commit; retain its
     // exact previous bytes for any subsequent transaction rollback.
     if(File.Exists(statePath)!=stateExisted || (stateExisted && Engine.Hash(statePath)!=stateHash))throw new IOException("安装记录被其他程序改变，已中止");
     if(stateExisted)File.Replace(stateTemp,statePath,statePrior,true);else File.Move(stateTemp,statePath);
     stateWritten=true;
    }
    report(restore?"安装前文件恢复完成":"汉化安装完成（资源级匹配）",100);return restore?"RESTORED":"INSTALLED";
   } catch {
    if(stateWritten) {if(stateExisted)File.Replace(statePrior,statePath,null,true);else File.Delete(statePath);}
    foreach(var c in written.AsEnumerable().Reverse()) {
     File.Replace(prior[c],c.path,null,true);if(Engine.Hash(c.path)!=c.current)throw new IOException("事务恢复失败，请保留备份并反馈");
    }
    throw;
   } finally {foreach(var f in temps)if(File.Exists(f))try{File.Delete(f);}catch(IOException){}}
  }
 }
}
