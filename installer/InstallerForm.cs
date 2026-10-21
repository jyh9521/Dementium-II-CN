using System;
using System.Diagnostics;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace LocalizationInstaller {
    sealed class Card : Panel {
        public Card() { DoubleBuffered=true; BackColor=Color.White; }
        protected override void OnPaint(PaintEventArgs e) {
            e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
            using(var path=Shape.Round(new Rectangle(0,0,Width-1,Height-1),18))
            using(var brush=new SolidBrush(BackColor)) e.Graphics.FillPath(brush,path);
        }
        protected override void OnPaintBackground(PaintEventArgs e) { e.Graphics.Clear(Parent==null?BackColor:Parent.BackColor); }
    }
    static class Shape {
        public static GraphicsPath Round(Rectangle box,int radius) {
            var p=new GraphicsPath();int d=Math.Min(radius*2,Math.Min(box.Width,box.Height));
            p.AddArc(box.X,box.Y,d,d,180,90);p.AddArc(box.Right-d,box.Y,d,d,270,90);
            p.AddArc(box.Right-d,box.Bottom-d,d,d,0,90);p.AddArc(box.X,box.Bottom-d,d,d,90,90);p.CloseFigure();return p;
        }
    }
    sealed class Pill : Button {
        public bool Primary;
        bool over;
        public Pill() { FlatStyle=FlatStyle.Flat;FlatAppearance.BorderSize=0;Cursor=Cursors.Hand;TabStop=true;DoubleBuffered=true; }
        protected override void OnMouseEnter(EventArgs e) { over=true;Invalidate();base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { over=false;Invalidate();base.OnMouseLeave(e); }
        protected override void OnPaint(PaintEventArgs e) {
            e.Graphics.Clear(Parent.BackColor);e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
            Color color=!Enabled?Color.FromArgb(231,229,235):Primary?(over?Color.FromArgb(87,64,147):Color.FromArgb(105,78,173)):(over?Color.FromArgb(225,216,242):Color.FromArgb(237,230,248));
            using(var p=Shape.Round(new Rectangle(0,0,Width-1,Height-1),Height/2))
            using(var b=new SolidBrush(color))e.Graphics.FillPath(b,p);
            TextRenderer.DrawText(e.Graphics,Text,Font,ClientRectangle,!Enabled?Color.FromArgb(151,147,158):Primary?Color.White:Color.FromArgb(90,65,145),TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter);
            if(Focused)ControlPaint.DrawFocusRectangle(e.Graphics,new Rectangle(9,7,Width-19,Height-15));
        }
    }
    public sealed class InstallerForm : Form {
        readonly Payload data;
        readonly TextBox file=new TextBox(),log=new TextBox();
        readonly Pill browse=new Pill(),verify=new Pill(),install=new Pill(),restore=new Pill(),admin=new Pill();
        readonly CheckBox executable=new CheckBox();
        readonly ProgressBar bar=new ProgressBar();
        readonly Label state=new Label();
        bool busy;
        public InstallerForm(Payload payload,string selected=null) {
            data=payload;
            AutoScaleMode=AutoScaleMode.None;
            Text=payload.Settings.title;ClientSize=new Size(820,760);MinimumSize=new Size(760,650);
            Font=new Font("Microsoft YaHei UI",10F);BackColor=Color.FromArgb(248,246,252);ShowIcon=false;
            StartPosition=FormStartPosition.CenterScreen;
            var title=LabelAt(payload.Settings.subtitle,34,28,750,28,11,Color.FromArgb(125,101,154));
            var heading=LabelAt("病房Ⅱ  简体中文汉化补丁",32,65,750,48,24,Color.FromArgb(38,30,48));
            heading.Font=new Font("Microsoft YaHei UI",24F,FontStyle.Bold);
            LabelAt(payload.Settings.notice,35,132,750,48,10,Color.FromArgb(83,76,94));
            var target=new Card {Location=new Point(32,193),Size=new Size(756,146),Anchor=AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right};Controls.Add(target);
            var label=new Label {Text="游戏资源文件",Location=new Point(22,17),AutoSize=true,ForeColor=Color.FromArgb(57,46,72)};target.Controls.Add(label);
            file.AutoSize=false;file.SetBounds(23,53,547,30);file.BorderStyle=BorderStyle.FixedSingle;file.Anchor=AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right;target.Controls.Add(file);
            browse.Text="浏览…";browse.SetBounds(587,44,145,45);browse.Anchor=AnchorStyles.Top|AnchorStyles.Right;target.Controls.Add(browse);
            executable.Text="同时处理同目录 EXE 中的5个菜单词";executable.SetBounds(23,104,650,25);executable.Checked=true;target.Controls.Add(executable);
            verify.Text="验证文件";verify.SetBounds(32,359,190,48);Controls.Add(verify);
            install.Text="安装汉化";install.Primary=true;install.SetBounds(241,359,220,48);install.Enabled=false;Controls.Add(install);
            restore.Text="恢复原版";restore.SetBounds(598,359,190,48);restore.Anchor=AnchorStyles.Top|AnchorStyles.Right;restore.Enabled=false;Controls.Add(restore);
            state.SetBounds(35,422,750,44);state.Text="先选择自己的 rom.zar，再验证文件";state.ForeColor=Color.FromArgb(95,79,118);state.Anchor=AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right;Controls.Add(state);
            bar.SetBounds(35,473,750,7);bar.Anchor=AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right;Controls.Add(bar);
            var logs=new Card {Location=new Point(32,496),Size=new Size(756,154),Anchor=AnchorStyles.Top|AnchorStyles.Bottom|AnchorStyles.Left|AnchorStyles.Right};Controls.Add(logs);
            var caption=new Label {Text="操作日志",Location=new Point(22,15),AutoSize=true};logs.Controls.Add(caption);
            log.Multiline=true;log.ReadOnly=true;log.BorderStyle=BorderStyle.None;log.BackColor=Color.White;log.ScrollBars=ScrollBars.Vertical;
            log.SetBounds(23,45,710,90);log.Anchor=AnchorStyles.Top|AnchorStyles.Bottom|AnchorStyles.Left|AnchorStyles.Right;log.Font=new Font("Microsoft YaHei UI",9F);logs.Controls.Add(log);
            var footer=LabelAt(payload.Settings.footer,35,668,750,54,9,Color.FromArgb(119,111,128));footer.Anchor=AnchorStyles.Bottom|AnchorStyles.Left|AnchorStyles.Right;
            admin.Text="以管理员身份重新打开";admin.SetBounds(546,720,242,30);admin.Anchor=AnchorStyles.Bottom|AnchorStyles.Right;admin.Visible=false;Controls.Add(admin);
            var foot=LabelAt("本地差分安装  /  自动备份  /  可恢复原版",35,725,485,24,9,Color.FromArgb(143,131,158));foot.Anchor=AnchorStyles.Bottom|AnchorStyles.Left;
            browse.Click+=delegate { using(var dialog=new OpenFileDialog {Title="选择你自己的 rom.zar",Filter="游戏资源文件 (rom.zar)|rom.zar|所有文件|*.*",CheckFileExists=true,RestoreDirectory=true})
                if(dialog.ShowDialog(this)==DialogResult.OK)SelectArchive(dialog.FileName); };
            file.TextChanged+=delegate {if(!busy)ResetValidation();};executable.CheckedChanged+=delegate {if(!busy)ResetValidation();};
            verify.Click+=async delegate {await Work(null);};install.Click+=async delegate {await Work(false);};restore.Click+=async delegate {await Work(true);};
            admin.Click+=delegate {
                try {Process.Start(new ProcessStartInfo(Application.ExecutablePath,"--select \""+file.Text+"\"") {UseShellExecute=true,Verb="runas"});Close();}
                catch(Exception ex){Append("未重新打开："+ex.Message,0);}
            };
            FormClosing+=delegate(object sender,FormClosingEventArgs e) {if(busy){e.Cancel=true;state.Text="正在处理文件，请等待完成后再关闭";}};
            if(selected!=null)SelectArchive(selected);
            // Framework WinForms can report DeviceDpi=96 while its point fonts
            // render at the system's 192 DPI. Scale geometry exactly once using
            // the actual desktop graphics DPI, leaving point-font sizes alone.
            using(var g=Graphics.FromHwnd(IntPtr.Zero))ScaleGeometry(g.DpiX/96F);
        }
        void ScaleGeometry(float scale) {
            if(Math.Abs(scale-1)<.01)return;
            var bounds=new Dictionary<Control,Rectangle>();var anchors=new Dictionary<Control,AnchorStyles>();
            Action<Control> collect=null;
            collect=delegate(Control parent) {parent.SuspendLayout();foreach(Control c in parent.Controls){bounds[c]=c.Bounds;anchors[c]=c.Anchor;c.Anchor=AnchorStyles.Top|AnchorStyles.Left;collect(c);}};
            collect(this);Size client=ClientSize,min=MinimumSize;
            ClientSize=new Size((int)Math.Round(client.Width*scale),(int)Math.Round(client.Height*scale));
            MinimumSize=new Size((int)Math.Round(min.Width*scale),(int)Math.Round(min.Height*scale));
            foreach(var pair in bounds){var b=pair.Value;pair.Key.Bounds=new Rectangle((int)Math.Round(b.X*scale),(int)Math.Round(b.Y*scale),(int)Math.Round(b.Width*scale),(int)Math.Round(b.Height*scale));}
            foreach(var pair in anchors)pair.Key.Anchor=pair.Value;
            foreach(var c in bounds.Keys)c.ResumeLayout(false);ResumeLayout(false);
        }
        Label LabelAt(string text,int x,int y,int width,int height,float size,Color color) {
            var l=new Label {Text=text,Location=new Point(x,y),Size=new Size(width,height),Font=new Font("Microsoft YaHei UI",size),ForeColor=color,BackColor=Color.Transparent};Controls.Add(l);return l;
        }
        void SelectArchive(string path) {
            file.Text=path;executable.Checked=File.Exists(Path.Combine(Path.GetDirectoryName(path),data.Settings.executable_file));
            Append(executable.Checked?"完整模式：资源文件＋同目录游戏程序":"仅资源模式：不处理 EXE，5个程序菜单词保持原文",0);
        }
        void ResetValidation() {install.Enabled=false;restore.Enabled=false;state.Text="路径或模式已变化，请重新验证";bar.Value=0;}
        void Append(string message,int value) {
            if(InvokeRequired) {BeginInvoke(new Action<string,int>(Append),message,value);return;}
            log.AppendText(DateTime.Now.ToString("HH:mm:ss")+"  "+message+Environment.NewLine);
            bar.Value=Math.Max(0,Math.Min(100,value));
        }
        async Task Work(bool? restoreOriginal) {
            if(busy)return;
            string selected=file.Text.Trim();bool include=executable.Checked;
            if(String.IsNullOrEmpty(selected)){state.Text="请先选择 rom.zar";return;}
            if(restoreOriginal.HasValue && MessageBox.Show(this,
                restoreOriginal.Value?"将恢复所选文件的原版。设置、存档不变，原版备份保留。":"将自动备份原文件，并安装本版汉化。不会启动游戏。",
                restoreOriginal.Value?"确认恢复原版":"确认安装",MessageBoxButtons.OKCancel,MessageBoxIcon.Question)!=DialogResult.OK)return;
            busy=true;file.Enabled=false;browse.Enabled=false;verify.Enabled=false;install.Enabled=false;restore.Enabled=false;executable.Enabled=false;admin.Visible=false;
            state.Text=restoreOriginal.HasValue?(restoreOriginal.Value?"正在恢复原版…":"正在安装汉化…"):"正在验证文件…";
            try {
                var engine=new Engine(data,Append);
                if(restoreOriginal.HasValue) {
                    string result=await Task.Run(()=>engine.Operate(selected,include,restoreOriginal.Value));Append(result,100);
                }
                Inspection status=await Task.Run(()=>engine.Inspect(selected,include));
                state.Text=status.Summary;install.Enabled=status.CanInstall;restore.Enabled=status.CanRestore;bar.Value=100;
                Append("验证完成；游戏未启动",100);
            } catch(UnauthorizedAccessException ex) {
                state.Text="目标目录需要写入权限，可点击右下角以管理员身份重新打开";admin.Visible=true;Append(ex.Message,0);
            } catch(Exception ex) {state.Text="操作未完成："+ex.Message;Append(ex.Message,0);}
            finally {busy=false;file.Enabled=true;browse.Enabled=true;verify.Enabled=true;executable.Enabled=true;}
        }
    }
    static class Program {
        static int CheckLayout(Control parent) {
            int count=0;
            foreach(Control c in parent.Controls) {
                var label=c as Label;
                if(label!=null && !label.AutoSize && !String.IsNullOrEmpty(label.Text)) {
                    Size measured=TextRenderer.MeasureText(label.Text,label.Font,new Size(label.ClientSize.Width,Int32.MaxValue),TextFormatFlags.WordBreak|TextFormatFlags.TextBoxControl);
                    if(measured.Height>label.ClientSize.Height)throw new InvalidDataException("Clipped label: "+label.Text+" measured="+measured.Height+" available="+label.ClientSize.Height);
                    count++;
                }
                count+=CheckLayout(c);
            }
            return count;
        }
        [STAThread] static void Main(string[] args) {
            Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
            try {
                string selected=args.Length==2 && args[0]=="--select"?args[1]:null;
                var form=new InstallerForm(Payload.Load(),selected);
                if(args.Length==2 && args[0]=="--render-preview") {
                    form.ShowInTaskbar=false;form.StartPosition=FormStartPosition.Manual;form.Location=new Point(-30000,-30000);
                    form.Show();Application.DoEvents();
                    int labels=CheckLayout(form);
                    using(var g=form.CreateGraphics())File.WriteAllText(args[1]+".layout.txt","GraphicsDpi="+g.DpiX+" checked_labels="+labels+" clipped_labels=0 Client="+form.ClientSize);
                    using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(args[1]);}form.Close();return;
                }
                Application.Run(form);
            }catch(Exception ex) {
                if(args.Length==2 && args[0]=="--render-preview") {File.WriteAllText(args[1]+".error.txt",ex.ToString());Environment.Exit(1);}
                MessageBox.Show("安装器初始化失败："+ex.Message,"汉化安装器",MessageBoxButtons.OK,MessageBoxIcon.Error);
            }
        }
    }
}
