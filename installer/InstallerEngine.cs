using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace LocalizationInstaller {
    public sealed class PatchRun { public long offset; public string old; public string @new; }
    public sealed class Delta {
        public string format, original_sha256, modified_sha256, append;
        public long original_size, modified_size;
        public PatchRun[] runs;
    }
    public sealed class Settings {
        public string title, subtitle, archive_file, executable_file, backup_folder;
        public string notice, footer;
    }
    public sealed class Payload {
        public Delta Archive, Executable;
        public Settings Settings;
        public static Payload Load() {
            return new Payload { Archive=Read<Delta>("patch.rom.gz",true),
                Executable=Read<Delta>("patch.exe.gz",true), Settings=Read<Settings>("installer.json",false) };
        }
        static T Read<T>(string name,bool compressed) {
            using(var raw=Assembly.GetExecutingAssembly().GetManifestResourceStream(name)) {
                if(raw==null) throw new InvalidDataException("Missing embedded resource: "+name);
                using(var memory=new MemoryStream()) {
                    if(compressed) { using(var gz=new GZipStream(raw,CompressionMode.Decompress)) CopyBounded(gz,memory); }
                    else CopyBounded(raw,memory);
                    return JsonSerializer.Deserialize<T>(Encoding.UTF8.GetString(memory.ToArray()).TrimStart('\uFEFF'),new JsonSerializerOptions { IncludeFields=true });
                }
            }
        }
        static void CopyBounded(Stream src,Stream dst) {
            byte[] buffer=new byte[65536]; int n;
            while((n=src.Read(buffer,0,buffer.Length))>0) {
                if(dst.Length+n>64*1024*1024) throw new InvalidDataException("Embedded resource too large");
                dst.Write(buffer,0,n);
            }
        }
    }
    public sealed class Component {
        public string Path, Backup, Current;
        public Delta Delta;
        public bool IsInstalled { get { return Current==Delta.modified_sha256; } }
    }
    public sealed class Inspection {
        public readonly List<Component> Components=new List<Component>();
        public bool CanInstall { get { return Components.Any(c=>!c.IsInstalled); } }
        public bool CanRestore { get { return Components.Any(c=>c.IsInstalled); } }
        public string Summary { get { return CanInstall && CanRestore ? "检测到中断安装状态，可继续安装或恢复" : CanRestore ? "已安装本版汉化，原版备份已验证" : "原版文件验证通过，可以安装"; } }
    }
    public sealed class Engine {
        readonly Payload payload;
        readonly Action<string,int> progress;
        // Test-only dependency injection; the GUI always leaves this null.
        internal Action<int> BeforeReplace=null;
        public Engine(Payload data,Action<string,int> report=null) {
            payload=data; progress=report ?? delegate(string s,int n) {};
            ValidateDelta(data.Archive,"zar-sparse-delta-v1");
            ValidateDelta(data.Executable,"fixed-slot-utf8-v1");
            foreach(string name in new [] {data.Settings.archive_file,data.Settings.executable_file,data.Settings.backup_folder})
                if(String.IsNullOrWhiteSpace(name) || System.IO.Path.GetFileName(name)!=name || name=="." || name=="..")
                    throw new InvalidDataException("Invalid payload file name");
        }
        public static string Hash(string path) {
            using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read,1024*1024,FileOptions.SequentialScan))
            using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(f)).Replace("-","").ToLowerInvariant();
        }
        static byte[] Hex(string s) {
            if(s==null || s.Length%2!=0) throw new InvalidDataException("Malformed patch bytes");
            var a=new byte[s.Length/2];for(int i=0;i<a.Length;i++) a[i]=Convert.ToByte(s.Substring(i*2,2),16);return a;
        }
        static void ValidateDelta(Delta d,string format) {
            if(d==null || d.format!=format || d.runs==null || d.original_size<=0 || d.modified_size<d.original_size)
                throw new InvalidDataException("Invalid patch metadata");
            foreach(string hash in new [] {d.original_sha256,d.modified_sha256})
                if(hash==null || hash.Length!=64 || hash.Any(c=>!"0123456789abcdef".Contains(c))) throw new InvalidDataException("Invalid patch identity");
            long end=0;
            foreach(var r in d.runs) {
                byte[] a=Hex(r.old),b=Hex(r.@new);
                if(a.Length==0 || a.Length!=b.Length || r.offset<end || r.offset>d.original_size-a.Length)
                    throw new InvalidDataException("Invalid patch range");
                end=r.offset+a.Length;
            }
            byte[] append=Convert.FromBase64String(d.append ?? "");
            if(d.modified_size-d.original_size!=append.Length) throw new InvalidDataException("Invalid append size");
        }
        public Inspection Inspect(string selected,bool includeExecutable) {
            string path=System.IO.Path.GetFullPath(selected);
            if(!String.Equals(System.IO.Path.GetFileName(path),payload.Settings.archive_file,StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("请选择名为 "+payload.Settings.archive_file+" 的游戏资源文件");
            string dir=System.IO.Path.GetDirectoryName(path),backup=System.IO.Path.Combine(dir,payload.Settings.backup_folder);
            var result=new Inspection();
            result.Components.Add(new Component { Path=path,Backup=System.IO.Path.Combine(backup,"original.zar"),Delta=payload.Archive });
            if(includeExecutable) result.Components.Add(new Component {Path=System.IO.Path.Combine(dir,payload.Settings.executable_file),Backup=System.IO.Path.Combine(backup,"original.exe"),Delta=payload.Executable});
            int step=0;
            foreach(var c in result.Components) {
                if(!File.Exists(c.Path)) throw new FileNotFoundException("未找到文件："+System.IO.Path.GetFileName(c.Path));
                progress("正在验证 "+System.IO.Path.GetFileName(c.Path)+"…",5+step++*12);
                c.Current=Hash(c.Path);long size=new FileInfo(c.Path).Length;
                if(!((c.Current==c.Delta.original_sha256 && size==c.Delta.original_size) ||
                    (c.Current==c.Delta.modified_sha256 && size==c.Delta.modified_size)))
                    throw new InvalidDataException("文件版本不匹配，未作修改："+System.IO.Path.GetFileName(c.Path)+"。本补丁仅支持 Steam 2026 build 26091059 的指定原版，或本补丁已安装版本");
                if(File.Exists(c.Backup) && Hash(c.Backup)!=c.Delta.original_sha256)
                    throw new InvalidDataException("原版备份校验失败，未作修改："+c.Backup);
                if(c.IsInstalled && !File.Exists(c.Backup))
                    throw new InvalidDataException("检测到汉化文件，但缺少原版备份："+c.Backup);
                progress(System.IO.Path.GetFileName(c.Path)+"："+(c.IsInstalled?"汉化版":"原版")+" SHA-256 通过",30);
            }
            return result;
        }
        public string Operate(string selected,bool includeExecutable,bool restore) {
            Inspection inspection=Inspect(selected,includeExecutable);
            if(restore ? !inspection.CanRestore : !inspection.CanInstall) return restore?"ALREADY_RESTORED":"ALREADY_INSTALLED";
            string dir=System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(selected));
            string cache=System.IO.Path.Combine(dir,payload.Settings.backup_folder);
            long required=64L*1024*1024;
            foreach(var c in inspection.Components) {
                string desired=restore?c.Delta.original_sha256:c.Delta.modified_sha256;
                if(c.Current!=desired) required+=restore?c.Delta.original_size:c.Delta.modified_size;
                if(!restore && !File.Exists(c.Backup)) required+=c.Delta.original_size;
            }
            if(new DriveInfo(System.IO.Path.GetPathRoot(dir)).AvailableFreeSpace<required)
                throw new IOException("可用空间不足，需要约 "+(required/1024/1024)+" MiB 用于备份和临时文件");
            Directory.CreateDirectory(cache);
            using(var gate=new FileStream(System.IO.Path.Combine(cache,"operation.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None,1,FileOptions.DeleteOnClose)) {
                inspection=Inspect(selected,includeExecutable);
                string token=Guid.NewGuid().ToString("N");
                var stages=new Dictionary<Component,string>();var prior=new Dictionary<Component,string>();var written=new List<Component>();
                try {
                    foreach(var c in inspection.Components) {
                        if(!restore && !File.Exists(c.Backup)) {
                            string pending=System.IO.Path.Combine(cache,"backup-"+token+"-"+System.IO.Path.GetFileName(c.Path));
                            stages[c]=pending;
                            progress("备份原版 "+System.IO.Path.GetFileName(c.Path)+"…",35);
                            File.Copy(c.Path,pending,false);
                            if(Hash(pending)!=c.Delta.original_sha256) throw new IOException("备份写入校验失败");
                            File.Move(pending,c.Backup);stages.Remove(c);
                        }
                        if(File.Exists(c.Backup) && Hash(c.Backup)!=c.Delta.original_sha256) throw new IOException("原版备份发生变化");
                        string desired=restore?c.Delta.original_sha256:c.Delta.modified_sha256;
                        if(c.Current==desired) continue;
                        string stage=System.IO.Path.Combine(cache,"stage-"+token+"-"+System.IO.Path.GetFileName(c.Path));stages[c]=stage;
                        progress((restore?"正在恢复 ":"正在应用差分 ")+System.IO.Path.GetFileName(c.Path)+"…",50);
                        Apply(c.Path,stage,c.Delta,restore);
                    }
                    if(inspection.Components.Any(c=>Hash(c.Path)!=c.Current)) throw new IOException("操作过程中源文件被其他程序改变，已中止");
                    int index=0;
                    foreach(var c in inspection.Components) {
                        if(!stages.ContainsKey(c)) continue;
                        if(BeforeReplace!=null) BeforeReplace(index);
                        string rollback=System.IO.Path.Combine(cache,"transaction-"+token+"-"+System.IO.Path.GetFileName(c.Path));
                        prior[c]=rollback;
                        File.Replace(stages[c],c.Path,rollback,true);
                        if(Hash(rollback)!=c.Current) {
                            File.Replace(rollback,c.Path,null,true);prior.Remove(c);
                            throw new IOException("文件在提交前发生变化，已保留该版本并中止安装");
                        }
                        written.Add(c);index++;
                        progress("写入后校验 "+System.IO.Path.GetFileName(c.Path)+"…",85);
                        if(Hash(c.Path)!=(restore?c.Delta.original_sha256:c.Delta.modified_sha256)) throw new IOException("写入后哈希不符");
                    }
                    progress(restore?"原版恢复完成":"汉化安装完成",100);
                    return restore?"RESTORED":"INSTALLED";
                } catch {
                    foreach(var c in written.AsEnumerable().Reverse()) {
                        if(File.Exists(prior[c])) File.Replace(prior[c],c.Path,null,true);
                        if(Hash(c.Path)!=c.Current) throw new IOException("事务恢复失败，请使用已验证的原版备份恢复："+c.Backup);
                    }
                    throw;
                } finally {
                    foreach(string temp in stages.Values.Concat(prior.Values))
                        if(File.Exists(temp)) { try {File.Delete(temp);} catch(IOException) {} }
                }
            }
        }
        public static void Apply(string source,string target,Delta delta,bool reverse) {
            if(delta==null || (delta.format!="zar-sparse-delta-v1" && delta.format!="fixed-slot-utf8-v1"))
                throw new InvalidDataException("Unsupported patch format");
            ValidateDelta(delta,delta.format);
            string expected=reverse?delta.modified_sha256:delta.original_sha256;
            string desired=reverse?delta.original_sha256:delta.modified_sha256;
            if(Hash(source)!=expected) throw new InvalidDataException("应用差分前文件校验失败");
            using(var input=new FileStream(source,FileMode.Open,FileAccess.Read,FileShare.Read,1024*1024,FileOptions.SequentialScan))
            using(var output=new FileStream(target,FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None,1024*1024)) {
                input.CopyTo(output,1024*1024);
                foreach(var run in delta.runs) {
                    byte[] old=Hex(reverse?run.@new:run.old),replacement=Hex(reverse?run.old:run.@new);
                    byte[] actual=new byte[old.Length];output.Position=run.offset;
                    if(output.Read(actual,0,actual.Length)!=actual.Length || !actual.SequenceEqual(old)) throw new InvalidDataException("差分原字节守卫失败");
                    output.Position=run.offset;output.Write(replacement,0,replacement.Length);
                }
                if(reverse) output.SetLength(delta.original_size);
                else { output.Position=delta.original_size;byte[] append=Convert.FromBase64String(delta.append ?? "");output.Write(append,0,append.Length); }
                output.Flush(true);
            }
            if(Hash(target)!=desired) throw new InvalidDataException("差分结果 SHA-256 不符");
        }
    }
}
