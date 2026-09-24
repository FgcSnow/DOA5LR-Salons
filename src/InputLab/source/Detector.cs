using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;

// This is a local inventory and profile viewer. Detection alone does not create
// button mappings for an unknown controller model.
sealed class Detector : Form {
    sealed class Profile {
        public string Id;
        public string Name;
        public bool Enabled;
    }
    sealed class Device {
        public string Name;
        public string Id;
        public string Capabilities;
        public Profile Profile;
        public bool Connected;
    }

    readonly string root=AppDomain.CurrentDomain.BaseDirectory;
    string ProfilesPath {
        get {
            string parent=Path.GetFullPath(Path.Combine(root,".."));
            string installed=Path.Combine(parent,"DOA5LR-ControllerProfiles.ini");
            return File.Exists(Path.Combine(parent,"game.exe"))&&File.Exists(installed)
                ?installed:Path.Combine(root,"DOA5LR-ControllerProfiles.ini");
        }
    }
    readonly List<Device> devices=new List<Device>();
    readonly TextBox query=new TextBox();
    readonly ListView results=new ListView();
    readonly Label summary=new Label();
    readonly Label detail=new Label();
    readonly Button copyId=new Button();

    static readonly Color background=Color.FromArgb(20,25,35);
    static readonly Color muted=Color.FromArgb(187,199,219);
    static readonly Color accent=Color.FromArgb(143,206,234);

    static Button MakeButton(string title,int x,int y,int width){
        return new Button{Text=title,Location=new Point(x,y),Size=new Size(width,34),
            FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(44,52,68),ForeColor=Color.White};
    }

    public Detector(){
        Text="DOA5LR — Controller Finder";
        ClientSize=new Size(930,610);
        StartPosition=FormStartPosition.CenterScreen;
        FormBorderStyle=FormBorderStyle.FixedSingle;
        MaximizeBox=false;
        AutoScaleMode=AutoScaleMode.Dpi;
        BackColor=background;
        ForeColor=Color.White;
        Font=new Font("Segoe UI",10);

        Controls.Add(new Label{Text="CONTROLLERS, STICKS AND HITBOXES",Location=new Point(22,18),
            Size=new Size(600,34),Font=new Font("Segoe UI",18),ForeColor=Color.White});
        Controls.Add(new Label{Text="Search connected devices and controller profiles included in this pack.",
            Location=new Point(24,57),Size=new Size(880,26),ForeColor=muted});
        Controls.Add(new Label{Text="Name or VID/PID",Location=new Point(24,101),Size=new Size(145,26),ForeColor=muted});
        query.Location=new Point(170,97);query.Size=new Size(535,30);
        query.TextChanged+=delegate{ApplyFilter();};Controls.Add(query);
        var refresh=MakeButton("Detect / refresh",718,95,186);
        refresh.Click+=delegate{RefreshInventory();};Controls.Add(refresh);

        results.Location=new Point(24,145);results.Size=new Size(880,302);
        results.View=View.Details;results.FullRowSelect=true;results.MultiSelect=false;
        results.HideSelection=false;results.BackColor=Color.FromArgb(31,37,49);
        results.ForeColor=Color.White;results.BorderStyle=BorderStyle.FixedSingle;
        results.Columns.Add("Device",305);
        results.Columns.Add("VID / PID",175);
        results.Columns.Add("Capabilities",205);
        results.Columns.Add("Profile",190);
        results.SelectedIndexChanged+=delegate{ShowSelected();};Controls.Add(results);

        summary.Location=new Point(24,457);summary.Size=new Size(880,24);
        summary.ForeColor=accent;Controls.Add(summary);
        detail.Location=new Point(24,488);detail.Size=new Size(880,47);
        detail.ForeColor=muted;Controls.Add(detail);

        copyId=MakeButton("Copy selected ID",24,552,216);
        copyId.Enabled=false;copyId.Click+=delegate{CopySelectedId();};Controls.Add(copyId);
        var profiles=MakeButton("Open profiles",254,552,189);
        profiles.Click+=delegate{OpenProfiles();};Controls.Add(profiles);
        var commands=MakeButton("Keyboard / controller",457,552,225);
        commands.Click+=delegate{OpenCommands();};Controls.Add(commands);
        Controls.Add(new Label{Text="Offline search",Location=new Point(735,559),
            Size=new Size(170,24),ForeColor=muted,TextAlign=ContentAlignment.MiddleRight});

        Shown+=delegate{RefreshInventory();};
    }

    static string NormalizeId(string id){return (id??"").Trim().ToUpperInvariant();}
    static Dictionary<string,Profile> ReadProfiles(string path){
        var profiles=new Dictionary<string,Profile>(StringComparer.OrdinalIgnoreCase);
        if(!File.Exists(path))return profiles;
        Profile current=null;
        foreach(string raw in File.ReadAllLines(path,Encoding.UTF8)){
            string line=raw.Trim();
            if(line.Length==0||line.StartsWith(";")||line.StartsWith("#"))continue;
            if(line.StartsWith("[")&&line.EndsWith("]")){
                string id=NormalizeId(line.Substring(1,line.Length-2));
                current=id.StartsWith("VID_")&&id.Contains("&PID_")?new Profile{Id=id,Name=id}:null;
                if(current!=null)profiles[id]=current;
                continue;
            }
            if(current==null)continue;
            int equal=line.IndexOf('=');if(equal<1)continue;
            string key=line.Substring(0,equal).Trim();
            string value=line.Substring(equal+1).Trim();
            if(key.Equals("Name",StringComparison.OrdinalIgnoreCase)&&value.Length>0)current.Name=value;
            if(key.Equals("Enabled",StringComparison.OrdinalIgnoreCase))current.Enabled=value=="1";
        }
        return profiles;
    }

    static string Enumerate(string executable){
        if(!File.Exists(executable))throw new IOException("DOA5LR-Peripheriques.exe is missing from the application folder.");
        var output=new StringBuilder();
        var start=new ProcessStartInfo(executable){UseShellExecute=false,CreateNoWindow=true,
            RedirectStandardOutput=true,StandardOutputEncoding=Encoding.UTF8};
        using(var process=Process.Start(start)){
            process.OutputDataReceived+=delegate(object sender,DataReceivedEventArgs args){
                if(args.Data!=null)lock(output){output.AppendLine(args.Data);}
            };
            process.BeginOutputReadLine();
            if(!process.WaitForExit(8000)){
                process.Kill();process.WaitForExit();
                throw new IOException("Detection timed out after 8 seconds. Reconnect the controller and try again.");
            }
            process.WaitForExit();
            if(process.ExitCode!=0)throw new IOException("Windows could not list the controllers (code "+process.ExitCode+").");
        }
        lock(output){return output.ToString();}
    }

    void RefreshInventory(){
        devices.Clear();
        string error=null;
        Dictionary<string,Profile> profiles;
        try{profiles=ReadProfiles(ProfilesPath);}
        catch(Exception e){profiles=new Dictionary<string,Profile>(StringComparer.OrdinalIgnoreCase);
            error="Could not read the profiles: "+e.Message;}
        string inventory="";
        try{inventory=Enumerate(Path.Combine(root,"DOA5LR-Peripheriques.exe"));}
        catch(Exception e){error=(error==null?"":error+" ")+e.Message;}
        var connectedIds=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach(string raw in inventory.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries)){
            string[] fields=raw.Split('\t');if(fields.Length<2)continue;
            string id=NormalizeId(fields[1]);Profile profile;
            profiles.TryGetValue(id,out profile);
            devices.Add(new Device{Name=fields[0].Trim(),Id=id,
                Capabilities=fields.Length>2?fields[2].Trim():"—",Profile=profile,Connected=true});
            connectedIds.Add(id);
        }
        foreach(Profile profile in profiles.Values){
            if(!connectedIds.Contains(profile.Id))devices.Add(new Device{Name=profile.Name,Id=profile.Id,
                Capabilities="Not connected",Profile=profile,Connected=false});
        }
        ApplyFilter();
        detail.Text=error!=null?error:
            "Detection means Windows recognizes the device. A controller needs a button profile before this module can use it.";
    }

    static bool Contains(string value,string part){return (value??"").IndexOf(part,StringComparison.OrdinalIgnoreCase)>=0;}
    static string ProfileStatus(Device device){
        if(device.Profile==null)return "Profile needed";
        return device.Profile.Enabled?"Profile enabled" : "Profile disabled";
    }
    void ApplyFilter(){
        string search=query.Text.Trim();
        results.BeginUpdate();results.Items.Clear();
        int shown=0;int connected=0;
        foreach(Device device in devices){
            if(search.Length>0&&!Contains(device.Name,search)&&!Contains(device.Id,search)
               &&!Contains(device.Profile==null?"":device.Profile.Name,search))continue;
            var item=new ListViewItem(device.Name);
            item.SubItems.Add(device.Id=="VID_0000&PID_0000"?"ID unavailable":device.Id);
            item.SubItems.Add(device.Capabilities);
            item.SubItems.Add(ProfileStatus(device));
            if(!device.Connected)item.ForeColor=muted;
            item.Tag=device;results.Items.Add(item);shown++;
            if(device.Connected)connected++;
        }
        results.EndUpdate();
        copyId.Enabled=false;
        summary.Text=shown==0?
            "No local results. Connect your controller and refresh, or add a profile to the catalogue.":
            shown+" result(s) · "+connected+" connected · "+(shown-connected)+" offline profile(s)";
    }
    void ShowSelected(){
        Device selected=Selected();
        copyId.Enabled=selected!=null&&selected.Id!="VID_0000&PID_0000";
        if(selected==null)return;
        detail.Text=selected.Profile==null?
            "Windows sees this device, but the module does not have a button mapping for it. Set up a profile before playing.":
            (selected.Connected?"Connected · ":"Profile available, device not connected · ")+selected.Profile.Name+
            (selected.Profile.Enabled?" · enabled in the catalogue.":" · disabled in the catalogue.");
    }
    Device Selected(){return results.SelectedItems.Count==0?null:results.SelectedItems[0].Tag as Device;}
    void CopySelectedId(){Device device=Selected();if(device!=null){Clipboard.SetText(device.Id);detail.Text="ID copied: "+device.Id;}}
    void OpenProfiles(){
        string path=ProfilesPath;
        if(File.Exists(path))Process.Start(new ProcessStartInfo("notepad.exe","\""+path+"\"") {UseShellExecute=true});
        else MessageBox.Show(this,"The profiles file is missing from this folder.","Profiles",MessageBoxButtons.OK,MessageBoxIcon.Information);
    }
    void OpenCommands(){
        string path=Path.Combine(root,"DOA5LR-Commandes.exe");
        if(File.Exists(path))Process.Start(new ProcessStartInfo(path){UseShellExecute=true,WorkingDirectory=root});
        else MessageBox.Show(this,"The Keyboard / controller app is missing from this folder. Enable the Keyboard / controller option in the pack installer.","Keyboard / controller",MessageBoxButtons.OK,MessageBoxIcon.Information);
    }

    [STAThread]static void Main(string[] args){
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        using(var app=new Detector()){
            if(args.Length==2&&args[0]=="--preview"){
                app.Show();Application.DoEvents();
                using(var image=new Bitmap(app.Width,app.Height)){
                    app.DrawToBitmap(image,new Rectangle(0,0,image.Width,image.Height));image.Save(args[1]);
                }
                return;
            }
            Application.Run(app);
        }
    }
}
