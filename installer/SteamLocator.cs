using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Microsoft.Win32;

namespace LocalizationInstaller {
    // Valve KeyValues text: quoted/bare tokens, nested objects, comments, escapes.
    public sealed class VdfNode {
        public string Key, Value;
        public List<VdfNode> Children=new List<VdfNode>();
        public string Get(string key) { return Children.FirstOrDefault(n=>String.Equals(n.Key,key,StringComparison.OrdinalIgnoreCase))?.Value; }
    }
    public static class SteamLocator {
        public const string AppId="5342930";
        public static VdfNode Parse(string text) {
            int i=0;
            Func<string> token=delegate {
                while(i<text.Length) {
                    if(Char.IsWhiteSpace(text[i]) || text[i]=='\uFEFF'){i++;continue;}
                    if(i+1<text.Length && text[i]=='/' && text[i+1]=='/') {while(i<text.Length && text[i]!='\n')i++;continue;}
                    break;
                }
                if(i==text.Length)return null;
                char c=text[i++];if(c=='{' || c=='}')return c.ToString();
                var b=new StringBuilder();
                if(c=='"') {
                    while(i<text.Length) {
                        c=text[i++];if(c=='"')return b.ToString();
                        if(c=='\\' && i<text.Length && (text[i]=='\\' || text[i]=='"')) c=text[i++];
                        b.Append(c);
                    }
                    throw new InvalidDataException("Unterminated VDF string");
                }
                b.Append(c);while(i<text.Length && !Char.IsWhiteSpace(text[i]) && text[i]!='{' && text[i]!='}')b.Append(text[i++]);return b.ToString();
            };
            Action<VdfNode,int,bool> read=null;
            read=delegate(VdfNode parent,int depth,bool nested) {
                if(depth>32)throw new InvalidDataException("VDF nesting too deep");
                string key;
                while((key=token())!=null) {
                    if(key=="}"){if(!nested)throw new InvalidDataException("Unexpected VDF end");return;}
                    string value=token();if(value==null || value=="}")throw new InvalidDataException("Missing VDF value");
                    var node=new VdfNode {Key=key};parent.Children.Add(node);
                    if(value=="{")read(node,depth+1,true);else node.Value=value;
                }
                if(nested)throw new InvalidDataException("Unclosed VDF object");
            };
            var root=new VdfNode();read(root,0,false);return root;
        }
        static VdfNode Read(string path) {
            if(new FileInfo(path).Length>8*1024*1024)throw new InvalidDataException("VDF too large");
            return Parse(File.ReadAllText(path,Encoding.UTF8));
        }
        public static List<string> Discover(IEnumerable<string> steamRoots) {
            var libraries=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach(string root in steamRoots.Where(p=>!String.IsNullOrWhiteSpace(p)).Distinct(StringComparer.OrdinalIgnoreCase)) {
                try {
                    libraries.Add(Path.GetFullPath(root));
                    string file=Path.Combine(root,"steamapps","libraryfolders.vdf");
                    if(!File.Exists(file))continue;
                    var tree=Read(file).Children.FirstOrDefault(n=>String.Equals(n.Key,"libraryfolders",StringComparison.OrdinalIgnoreCase));
                    if(tree==null)continue;
                    foreach(var child in tree.Children) {
                        int index;if(!Int32.TryParse(child.Key,out index))continue;
                        string library=child.Get("path") ?? child.Value;
                        if(!String.IsNullOrWhiteSpace(library) && Path.IsPathRooted(library))libraries.Add(Path.GetFullPath(library));
                    }
                } catch(Exception ex) when(ex is IOException || ex is UnauthorizedAccessException || ex is ArgumentException) { }
            }
            var found=new List<string>();
            foreach(string library in libraries.OrderBy(s=>s,StringComparer.OrdinalIgnoreCase)) {
                try {
                    string manifest=Path.Combine(library,"steamapps","appmanifest_"+AppId+".acf");
                    if(!File.Exists(manifest))continue;
                    var app=Read(manifest).Children.FirstOrDefault(n=>String.Equals(n.Key,"AppState",StringComparison.OrdinalIgnoreCase));
                    if(app==null || app.Get("appid")!=AppId)continue;
                    string dir=app.Get("installdir");
                    if(String.IsNullOrWhiteSpace(dir) || dir=="." || dir==".." || dir.IndexOfAny(new[]{'\\','/',':'})>=0)continue;
                    string game=Path.Combine(library,"steamapps","common",dir),rom=Path.Combine(game,"rom.zar");
                    if(File.Exists(rom) && File.Exists(Path.Combine(game,"Dementium II.exe")))found.Add(rom);
                } catch(Exception ex) when(ex is IOException || ex is UnauthorizedAccessException || ex is ArgumentException) { }
            }
            return found.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        }
        public static List<string> Installed() {
            var roots=new List<string>();
            foreach(var hive in new[]{RegistryHive.CurrentUser,RegistryHive.LocalMachine})
            foreach(var view in new[]{RegistryView.Registry32,RegistryView.Registry64}) {
                try {using(var key=RegistryKey.OpenBaseKey(hive,view).OpenSubKey(@"Software\Valve\Steam")) {
                    if(key!=null)foreach(string name in new[]{"SteamPath","InstallPath"}) {string path=key.GetValue(name) as string;if(path!=null)roots.Add(path);}
                }}catch(System.Security.SecurityException){}catch(UnauthorizedAccessException){}
            }
            foreach(string folder in new[]{Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles)})
                if(!String.IsNullOrEmpty(folder))roots.Add(Path.Combine(folder,"Steam"));
            return Discover(roots);
        }
    }
}
