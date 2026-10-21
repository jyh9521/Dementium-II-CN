using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Threading;
using MaterialDesignThemes.Wpf;
using Microsoft.Win32;

namespace LocalizationInstaller {
 public partial class MaterialWindow : Window {
  readonly Payload payload;
  bool busy;
  public MaterialWindow(Payload data,string selected=null,bool preview=false) {
   payload=data;InitializeComponent();
   ArchivePath.TextChanged+=delegate {if(!busy){Install.IsEnabled=Restore.IsEnabled=false;Status.Text="路径已变化，请验证文件";}};
   Closing+=delegate(object s,System.ComponentModel.CancelEventArgs e){if(busy){e.Cancel=true;Status.Text="正在处理文件，请等待完成后再关闭";}};
   Loaded+=async delegate {
    var easing=new CubicEase {EasingMode=EasingMode.EaseOut};
    ContentRoot.BeginAnimation(OpacityProperty,new DoubleAnimation(0,1,TimeSpan.FromMilliseconds(240)));
    ContentRoot.RenderTransform.BeginAnimation(TranslateTransform.YProperty,new DoubleAnimation(12,0,TimeSpan.FromMilliseconds(280)){EasingFunction=easing});
    if(selected!=null){ArchivePath.Text=selected;Status.Text="请验证文件";}
    else if(!preview)await DetectAsync();else Status.Text="先检测或选择 rom.zar，再验证文件";
   };
  }
  void Append(string message,int percentage=0) {
   if(!Dispatcher.CheckAccess()){Dispatcher.InvokeAsync(()=>Append(message,percentage));return;}
   Log.AppendText(DateTime.Now.ToString("HH:mm:ss")+"  "+message+Environment.NewLine);Log.ScrollToEnd();
   if(busy)Status.Text=message;
  }
  async Task DetectAsync() {
   if(busy)return;busy=true;Detect.IsEnabled=Browse.IsEnabled=Verify.IsEnabled=ArchivePath.IsEnabled=false;Install.IsEnabled=Restore.IsEnabled=false;Status.Text="正在读取 Steam 安装清单…";
   try {
    var found=await Task.Run(()=>SteamLocator.Installed());
    if(found.Count>0){ArchivePath.Text=found[0];Status.Text="已找到游戏，请验证文件";foreach(var path in found)Append("Steam 安装清单："+path);}
    else {Status.Text="未找到完整的 Steam 安装，请点击浏览选择 rom.zar";Append("已检查 Steam 注册位置、库配置和游戏清单；未修改任何文件");}
   }catch(Exception ex){Status.Text="自动检测未完成，请手动浏览选择";Append(ex.Message);}
   finally{busy=false;Detect.IsEnabled=Browse.IsEnabled=Verify.IsEnabled=ArchivePath.IsEnabled=true;}
  }
  async void Detect_Click(object s,RoutedEventArgs e){await DetectAsync();}
  void Browse_Click(object s,RoutedEventArgs e){var dialog=new OpenFileDialog {Title="请选择游戏根目录的 rom.zar",Filter="游戏资源文件 (rom.zar)|rom.zar",CheckFileExists=true};if(dialog.ShowDialog(this)==true)ArchivePath.Text=dialog.FileName;}
  async void Verify_Click(object s,RoutedEventArgs e){await Work(null);}
  async void Install_Click(object s,RoutedEventArgs e){await Work(false);}
  async void Restore_Click(object s,RoutedEventArgs e){await Work(true);}
  void Link_Click(object s,RequestNavigateEventArgs e){Process.Start(new ProcessStartInfo(e.Uri.AbsoluteUri){UseShellExecute=true});e.Handled=true;}
  async Task<bool> Confirm(string title,string text) {
   var panel=new StackPanel {Margin=new Thickness(26),MaxWidth=420};
   panel.Children.Add(new TextBlock {Text=title,FontSize=22,Margin=new Thickness(0,0,0,18)});
   panel.Children.Add(new TextBlock {Text=text,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,0,0,24)});
   var buttons=new StackPanel {Orientation=Orientation.Horizontal,HorizontalAlignment=HorizontalAlignment.Right};
   var cancel=new Button {Content="取消",Style=(Style)FindResource("MaterialDesignTextButton"),Command=DialogHost.CloseDialogCommand,CommandParameter=false,Margin=new Thickness(0,0,12,0)};
   var ok=new Button {Content="确认",Style=(Style)FindResource("MaterialDesignFilledButton"),Command=DialogHost.CloseDialogCommand,CommandParameter=true};
   buttons.Children.Add(cancel);buttons.Children.Add(ok);panel.Children.Add(buttons);
   return (await Dialogs.ShowDialog(panel)) is bool result && result;
  }
  async Task Work(bool? restore) {
   if(busy)return;string path=ArchivePath.Text.Trim();
   if(String.IsNullOrWhiteSpace(path)){Status.Text="请先选择 rom.zar";return;}
   // Lock UI before opening a dialog: no concurrent operations or path changes.
   busy=true;ArchivePath.IsEnabled=Browse.IsEnabled=Detect.IsEnabled=Verify.IsEnabled=Install.IsEnabled=Restore.IsEnabled=false;
   try {
    if(restore.HasValue && !await Confirm(restore.Value?"恢复原版":"安装汉化",restore.Value?"将恢复 rom.zar 和同目录游戏程序。存档与设置不变，原版备份保留。":"将备份 rom.zar 和同目录游戏程序，并安装汉化。存档与设置不变，不会启动游戏。")) {Status.Text="操作已取消，请重新验证";return;}
    var engine=new Engine(payload,Append);
    Status.Text=restore.HasValue?(restore.Value?"正在恢复…":"正在安装…"):"正在验证…";
    if(restore.HasValue)Append(await Task.Run(()=>engine.Operate(path,true,restore.Value)));
    var state=await Task.Run(()=>engine.Inspect(path,true));
    Install.IsEnabled=state.CanInstall;Restore.IsEnabled=state.CanRestore;Append("验证完成；游戏未启动");Status.Text=state.Summary;
   }catch(UnauthorizedAccessException ex){
    Append(ex.Message);Status.Text="目标目录需要写入权限";
    if(await Confirm("写入权限","是否以管理员身份重新打开安装器？不会启动游戏。")) {
     try{Process.Start(new ProcessStartInfo(Environment.ProcessPath,"--select \""+path+"\""){UseShellExecute=true,Verb="runas"});busy=false;Close();}
     catch(Exception elevation){Append("未重新打开："+elevation.Message);}
    }
   }catch(Exception ex){Status.Text="操作未完成，请查看日志";Append(ex.Message);}
   finally{busy=false;ArchivePath.IsEnabled=Browse.IsEnabled=Detect.IsEnabled=Verify.IsEnabled=true;}
  }
 }
 static class MaterialProgram {
  static int CountVisual<T>(DependencyObject node) {
   int count=node is T && (node is not UIElement element || element.IsVisible)?1:0;
   for(int i=0;i<VisualTreeHelper.GetChildrenCount(node);i++)count+=CountVisual<T>(VisualTreeHelper.GetChild(node,i));return count;
  }
  static void Snapshot(FrameworkElement visual,string path,double scale) {
   var bmp=new RenderTargetBitmap((int)Math.Ceiling(visual.ActualWidth*scale),(int)Math.Ceiling(visual.ActualHeight*scale),96*scale,96*scale,PixelFormats.Pbgra32);
   var surface=new DrawingVisual();using(var drawing=surface.RenderOpen()) {
    var rectangle=new Rect(0,0,visual.ActualWidth,visual.ActualHeight);
    drawing.DrawRectangle(new SolidColorBrush(Color.FromRgb(255,251,254)),null,rectangle);
    drawing.DrawRectangle(new VisualBrush(visual),null,rectangle);
   }
   bmp.Render(surface);
   var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bmp));using(var file=File.Create(path))encoder.Save(file);
  }
  [STAThread] public static int Main(string[] args) {
   bool preview=args.Length>=2 && args[0]=="--render-preview";
   try {
    var app=new Application();
    string selected=args.Length==2 && args[0]=="--select"?args[1]:null;
    var window=new MaterialWindow(Payload.Load(),selected,preview);
    if(preview) {
     window.ShowInTaskbar=false;window.WindowStartupLocation=WindowStartupLocation.Manual;window.Left=-30000;window.Top=-30000;
     double scale=args.Length>2?Double.Parse(args[2],System.Globalization.CultureInfo.InvariantCulture):1;
     if(args.Length>4){window.Width=Double.Parse(args[3]);window.Height=Double.Parse(args[4]);}
     window.Loaded+=async delegate {
      try {
       bool animated=window.ContentRoot.HasAnimatedProperties;double first=window.ContentRoot.Opacity;
       await Task.Delay(35);Snapshot(window.Dialogs,args[1]+".motion-start.png",scale);
       await Task.Delay(450);window.UpdateLayout();
       int ripples=CountVisual<Ripple>(window);if(ripples<5 || !animated || window.ContentRoot.Opacity<.99 || first>=.99)throw new InvalidDataException("Material motion/template check failed: ripples="+ripples+" animated="+animated+" initial="+first+" final="+window.ContentRoot.Opacity);
       if(CountVisual<CheckBox>(window)!=0 || CountVisual<ProgressBar>(window)!=0)throw new InvalidDataException("Removed controls still present");
       Snapshot(window.Dialogs,args[1],scale);
       File.WriteAllText(args[1]+".layout.txt","WPF MaterialDesign3 preview width="+window.ActualWidth+" height="+window.ActualHeight+" raster_scale="+scale+" material_ripples="+ripples+" entry_animation=PASS checkbox=NONE progressbar=NONE runtime="+Environment.Version+" game_launch=NEVER");
       window.Close();
      }catch(Exception ex){File.WriteAllText(args[1]+".error.txt",ex.ToString());Environment.ExitCode=1;window.Close();}
     };
    }
    app.Run(window);return Environment.ExitCode;
   }catch(Exception ex){if(preview)File.WriteAllText(args[1]+".error.txt",ex.ToString());else MessageBox.Show(ex.ToString(),"安装器初始化失败");return 1;}
  }
 }
}
