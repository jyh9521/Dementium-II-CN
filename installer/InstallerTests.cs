using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using LocalizationInstaller;

static class InstallerTests {
    static int count;
    static string root;
    static string Digest(byte[] bytes) {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
    static void Assert(bool value,string message) {if(!value)throw new Exception(message);}
    static Delta Patch(byte[] a,byte[] b,string format) {
        int start=3;return new Delta {format=format,original_size=a.Length,modified_size=b.Length,
            original_sha256=Digest(a),modified_sha256=Digest(b),append=Convert.ToBase64String(b.Skip(a.Length).ToArray()),
            runs=new [] {new PatchRun {offset=start,old=a[start].ToString("x2"),@new=b[start].ToString("x2")}}};
    }
    static byte[] rom=Encoding.UTF8.GetBytes("ZAR1 ORIGINAL ARCHIVE FIXTURE");
    static byte[] exe=Encoding.UTF8.GetBytes("MZ__ ORIGINAL PROGRAM FIXTURE");
    static Payload Data() {
        var modified=rom.Concat(Encoding.UTF8.GetBytes(" + APPENDED LOCALIZATION")).ToArray();modified[3]=70;
        var program=(byte[])exe.Clone();program[3]=99;
        return new Payload {Archive=Patch(rom,modified,"zar-sparse-delta-v1"),Executable=Patch(exe,program,"fixed-slot-utf8-v1"),
            Settings=new Settings {archive_file="rom.zar",executable_file="Game.exe",backup_folder="cn-backup"}};
    }
    static string Fixture() {
        string dir=Path.Combine(root,Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);
        File.WriteAllBytes(Path.Combine(dir,"rom.zar"),rom);File.WriteAllBytes(Path.Combine(dir,"Game.exe"),exe);return dir;
    }
    static void Original(string dir) {Assert(File.ReadAllBytes(Path.Combine(dir,"rom.zar")).SequenceEqual(rom),"ROM not restored");Assert(File.ReadAllBytes(Path.Combine(dir,"Game.exe")).SequenceEqual(exe),"EXE not restored");}
    static void Reject(Action action) {bool rejected=false;try {action();}catch(Exception){rejected=true;}Assert(rejected,"Expected rejection");}
    static void Case(string name,Action test) {test();count++;Console.WriteLine("PASS "+name);}
    static void Unit() {
        Case("embedded resources load",delegate {var p=Payload.Load();Assert(p.Archive.original_size>500000000,"Missing real payload");new Engine(p);});
        Case("baseline verify leaves bytes unchanged",delegate {var d=Fixture();var s=new Engine(Data()).Inspect(Path.Combine(d,"rom.zar"),true);Assert(s.CanInstall && !s.CanRestore,"Bad state");Original(d);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Verification wrote files");});
        Case("install both components",delegate {var d=Fixture();var p=Data();var e=new Engine(p);Assert(e.Operate(Path.Combine(d,"rom.zar"),true,false)=="INSTALLED","Install result");Assert(Engine.Hash(Path.Combine(d,"rom.zar"))==p.Archive.modified_sha256,"ROM result");Assert(Engine.Hash(Path.Combine(d,"Game.exe"))==p.Executable.modified_sha256,"EXE result");});
        Case("restore byte identical",delegate {var d=Fixture();var e=new Engine(Data());e.Operate(Path.Combine(d,"rom.zar"),true,false);e.Operate(Path.Combine(d,"rom.zar"),true,true);Original(d);Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Backup folder remains");});
        Case("native menu PE delta appended section installs and reverses",delegate {var d=Fixture();var p=Data();var program=exe.Concat(Encoding.ASCII.GetBytes("NEW SECTION FIXTURE")).ToArray();program[3]=99;p.Executable=Patch(exe,program,"native-menu-pe-v1");var e=new Engine(p);var path=Path.Combine(d,"rom.zar");e.Operate(path,true,false);Assert(File.ReadAllBytes(Path.Combine(d,"Game.exe")).SequenceEqual(program),"Native PE payload mismatch");Assert(e.Operate(path,true,false)=="ALREADY_INSTALLED","Native idempotence");e.Operate(path,true,true);Original(d);});
        Case("native menu unknown program rejects before archive writes",delegate {var d=Fixture();var p=Data();p.Executable.format="native-menu-pe-v1";File.AppendAllText(Path.Combine(d,"Game.exe"),"UNKNOWN");var id=HashFile(Path.Combine(d,"rom.zar"));Reject(()=>new Engine(p).Operate(Path.Combine(d,"rom.zar"),true,false));Assert(HashFile(Path.Combine(d,"rom.zar"))==id && !Directory.Exists(Path.Combine(d,"cn-backup")),"Unknown native EXE changed archive");});
        Case("repeated install no write",delegate {var d=Fixture();var e=new Engine(Data());var path=Path.Combine(d,"rom.zar");e.Operate(path,true,false);var t=File.GetLastWriteTimeUtc(path);Assert(e.Operate(path,true,false)=="ALREADY_INSTALLED","Idempotent install");Assert(File.GetLastWriteTimeUtc(path)==t,"Unnecessary write");});
        Case("repeated restore no write",delegate {var d=Fixture();var e=new Engine(Data());var path=Path.Combine(d,"rom.zar");var t=File.GetLastWriteTimeUtc(path);Assert(e.Operate(path,true,true)=="ALREADY_RESTORED","Idempotent restore");Assert(File.GetLastWriteTimeUtc(path)==t,"Unnecessary write");});
        Case("rom-only file supported",delegate {var d=Fixture();File.Delete(Path.Combine(d,"Game.exe"));var e=new Engine(Data());var path=Path.Combine(d,"rom.zar");e.Operate(path,false,false);e.Operate(path,false,true);Assert(File.ReadAllBytes(path).SequenceEqual(rom),"ROM-only restore");});
        Case("missing required exe rejected",delegate {var d=Fixture();File.Delete(Path.Combine(d,"Game.exe"));Reject(()=>new Engine(Data()).Operate(Path.Combine(d,"rom.zar"),true,false));Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Wrote backup before validation");});
        Case("unknown rom rejected without writes",delegate {var d=Fixture();File.AppendAllText(Path.Combine(d,"rom.zar"),"unknown");Reject(()=>new Engine(Data()).Operate(Path.Combine(d,"rom.zar"),true,false));Assert(!Directory.Exists(Path.Combine(d,"cn-backup")),"Unknown version wrote files");});
        Case("unknown exe rejected before rom write",delegate {var d=Fixture();File.AppendAllText(Path.Combine(d,"Game.exe"),"unknown");Reject(()=>new Engine(Data()).Operate(Path.Combine(d,"rom.zar"),true,false));Assert(File.ReadAllBytes(Path.Combine(d,"rom.zar")).SequenceEqual(rom),"Unknown EXE changed ROM");});
        Case("corrupt backup rejected",delegate {var d=Fixture();var e=new Engine(Data());var path=Path.Combine(d,"rom.zar");e.Operate(path,true,false);var before=Engine.Hash(path);File.AppendAllText(Path.Combine(d,"cn-backup/rom.zar"),"bad");Reject(()=>e.Operate(path,true,true));Assert(Engine.Hash(path)==before,"Corrupt backup changed game");});
        Case("installed without backup rejected",delegate {var d=Fixture();var e=new Engine(Data());var path=Path.Combine(d,"rom.zar");e.Operate(path,true,false);File.Delete(Path.Combine(d,"cn-backup/rom.zar"));Reject(()=>e.Inspect(path,true));});
        Case("mixed state install resumes",delegate {var d=Fixture();var e=new Engine(Data());var path=Path.Combine(d,"rom.zar");e.Operate(path,false,false);e.Operate(path,true,false);Assert(!e.Inspect(path,true).CanInstall,"Mixed state not completed");e.Operate(path,true,true);Original(d);});
        Case("mixed state can restore",delegate {var d=Fixture();var e=new Engine(Data());var path=Path.Combine(d,"rom.zar");e.Operate(path,false,false);e.Operate(path,true,true);Original(d);});
        Case("second replacement failure rolls back first",delegate {var d=Fixture();var e=new Engine(Data());e.BeforeReplace=delegate(int i){if(i==1)throw new IOException("injected failure");};Reject(()=>e.Operate(Path.Combine(d,"rom.zar"),true,false));Original(d);Assert(Engine.Hash(Path.Combine(d,"cn-backup/rom.zar"))==Digest(rom),"Backup changed");});
        Case("first replacement failure leaves originals",delegate {var d=Fixture();var e=new Engine(Data());e.BeforeReplace=delegate(int i){throw new IOException("injected failure");};Reject(()=>e.Operate(Path.Combine(d,"rom.zar"),true,false));Original(d);});
        Case("settings saves and unrelated data preserved",delegate {var d=Fixture();var path=Path.Combine(d,"rom.zar");File.WriteAllText(Path.Combine(d,"save.dat"),"USER_SAVE");File.WriteAllText(Path.Combine(d,"settings.ini"),"USER_CONFIG");var e=new Engine(Data());e.Operate(path,true,false);e.Operate(path,true,true);Assert(File.ReadAllText(Path.Combine(d,"save.dat"))=="USER_SAVE","Save changed");Assert(File.ReadAllText(Path.Combine(d,"settings.ini"))=="USER_CONFIG","Settings changed");});
        Case("wrong filename rejected",delegate {var d=Fixture();var p=Path.Combine(d,"another.zar");File.WriteAllBytes(p,rom);Reject(()=>new Engine(Data()).Inspect(p,false));});
        Case("out-of-bounds delta rejected",delegate {var p=Data();p.Archive.runs[0].offset=p.Archive.original_size;Reject(()=>new Engine(p));});
        Case("overlapping delta rejected",delegate {var p=Data();p.Archive.runs=new [] {p.Archive.runs[0],p.Archive.runs[0]};Reject(()=>new Engine(p));});
        Case("wrong expected bytes rejected",delegate {var d=Fixture();var p=Data();p.Archive.runs[0].old="00";Reject(()=>new Engine(p).Operate(Path.Combine(d,"rom.zar"),true,false));Original(d);});
        Case("backup path traversal rejected",delegate {var p=Data();p.Settings.backup_folder="../outside";Reject(()=>new Engine(p));});
        Case("operation lock respected",delegate {var d=Fixture();var cache=Path.Combine(d,"cn-backup");Directory.CreateDirectory(cache);using(var f=new FileStream(Path.Combine(cache,"operation.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))Reject(()=>new Engine(Data()).Operate(Path.Combine(d,"rom.zar"),true,false));Original(d);});
        Case("VDF comments escapes BOM and nested objects",delegate {var n=SteamLocator.Parse("\uFEFF// comment\n\"root\" { \"path\" \"D:\\\\Steam Library\" \"nested\" { \"x\" \"quoted\\\"text\" }}").Children[0];Assert(n.Get("path")==@"D:\Steam Library","Escape parse");Assert(n.Children[1].Get("x")=="quoted\"text","Quote parse");});
        Case("malformed VDF rejected",delegate {Reject(()=>SteamLocator.Parse("root { value \"oops"));});
        Case("modern Steam library on another drive folder",delegate {SteamFixture(false,false,false,false);});
        Case("legacy Steam library entries",delegate {SteamFixture(true,false,false,false);});
        Case("wrong app manifest rejected",delegate {SteamFixture(false,true,false,false);});
        Case("manifest traversal rejected",delegate {SteamFixture(false,false,true,false);});
        Case("missing required game executable not detected",delegate {SteamFixture(false,false,false,true);});
        Case("stale library ignored",delegate {Assert(SteamLocator.Discover(new[]{Path.Combine(root,Guid.NewGuid().ToString())}).Count==0,"Stale found");});
        ResourceTests.Run(Case,root);
        Console.WriteLine("INSTALLER_UNIT tests="+count+" result=PASS");
    }
    static string HashFile(string path)=>Engine.Hash(path);
    static void SteamFixture(bool legacy,bool wrong,bool traversal,bool missing) {
        string install=Path.Combine(root,Guid.NewGuid().ToString()),library=Path.Combine(root,"中文 Steam Library "+Guid.NewGuid().ToString());
        Directory.CreateDirectory(Path.Combine(install,"steamapps"));Directory.CreateDirectory(Path.Combine(library,"steamapps","common","Custom Game Folder"));
        string encoded=library.Replace("\\","\\\\");
        File.WriteAllText(Path.Combine(install,"steamapps/libraryfolders.vdf"),"\"libraryfolders\" { \"1\" "+(legacy?"\""+encoded+"\"":"{ \"path\" \""+encoded+"\" }")+" }");
        File.WriteAllText(Path.Combine(library,"steamapps/appmanifest_5342930.acf"),"\"AppState\" { \"appid\" \""+(wrong?"123":"5342930")+"\" \"installdir\" \""+(traversal?"../outside":"Custom Game Folder")+"\" }");
        string game=Path.Combine(library,"steamapps/common/Custom Game Folder");File.WriteAllText(Path.Combine(game,"rom.zar"),"test");if(!missing)File.WriteAllText(Path.Combine(game,"Dementium II.exe"),"test");
        var found=SteamLocator.Discover(new[]{install,install});Assert(found.Count==(wrong||traversal||missing?0:1),"Library detection count");
        if(found.Count>0)Assert(Path.GetFullPath(found[0])==Path.GetFullPath(Path.Combine(game,"rom.zar")),"Wrong install directory");
    }
    static void Real(string source,string target) {
        var p=Payload.Load();var e=new Engine(p,delegate(string m,int n){Console.WriteLine(n+"% "+m);});
        Assert(!Directory.Exists(target),"Real test output must not exist");Directory.CreateDirectory(target);
        string archive=Path.Combine(target,p.Settings.archive_file),program=Path.Combine(target,p.Settings.executable_file);
        File.Copy(Path.Combine(source,p.Settings.archive_file),archive);File.Copy(Path.Combine(source,p.Settings.executable_file),program);
        Assert(Engine.Hash(archive)==p.Archive.original_sha256,"Original fixture hash");
        e.Inspect(archive,true);Console.WriteLine("BASELINE files=2 original_hashes=PASS");
        Assert(e.Operate(archive,true,false)=="INSTALLED","Real install");
        Assert(Engine.Hash(archive)==p.Archive.modified_sha256 && Engine.Hash(program)==p.Executable.modified_sha256,"Installed hashes");
        Assert(e.Operate(archive,true,false)=="ALREADY_INSTALLED","Real idempotence");Console.WriteLine("MODIFIED files=2 installed_hashes=PASS idempotence=PASS");
        Assert(e.Operate(archive,true,true)=="RESTORED","Real restore");Assert(e.Operate(archive,true,true)=="ALREADY_RESTORED","Real restore idempotence");
        Assert(Engine.Hash(archive)==p.Archive.original_sha256 && Engine.Hash(program)==p.Executable.original_sha256,"Restored hashes");
        Console.WriteLine("ROLLBACK files=2 restored=BYTE_IDENTICAL backup=REMOVED game_launch=NEVER result=PASS");
    }
    public static int Main(string[] args) {
        if(args.Length==2 && (args[0]=="--resource-install" || args[0]=="--resource-restore")) {
            try {
                string result=new ResourceEngine(Payload.Load(),ResourcePayload.Load()).Operate(args[1],true,args[0]=="--resource-restore");
                Console.WriteLine("RESOURCE_OPERATION result="+result+" game_launch=NEVER");return 0;
            } catch(Exception ex) {Console.Error.WriteLine(ex);return 1;}
        }
        try {if(args.Length==1 && args[0]=="--detect"){foreach(var p in SteamLocator.Installed())Console.WriteLine("STEAM_DETECTED="+p);return 0;}
            if(args.Length==3 && args[0]=="--real"){Real(args[1],args[2]);return 0;}
            if(args.Length==3 && args[0]=="--resource-real"){ResourceTests.Real(args[1],args[2]);return 0;}
            if(args.Length==2 && args[0]=="--inspect"){var result=new ResourceEngine(Payload.Load(),ResourcePayload.Load()).Inspect(args[1],true);Console.WriteLine("INSPECT files="+result.components.Count+" can_install="+result.CanInstall+" can_restore="+result.CanRestore+" writes=NONE executable_match="+(result.NativeExecutable?"NATIVE_EXACT":"RELOCATED_LITERALS")+" result=PASS");return 0;}
            root=Path.GetFullPath(args.Length==1?args[0]:"build/installer-unit-tests");Directory.CreateDirectory(root);Unit();return 0;
        }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}
    }
}
