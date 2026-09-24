using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Windows.Forms;

static class Native {
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetKeyNameText(int param,StringBuilder name,int size);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] public static extern bool WritePrivateProfileString(string section,string key,string value,string path);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] public static extern uint GetPrivateProfileString(string section,string key,string fallback,StringBuilder value,uint size,string path);
}
sealed class InputLab : Form {
    const string OriginalXidiHash="7f2a1c7616515153d899b726c8ecf72d5fa81c27a9d14b5c394cdd2e09f325c5";
    readonly string root=AppDomain.CurrentDomain.BaseDirectory;
    readonly string game=FindGame();
    static string FindGame(){
        string baseDir=AppDomain.CurrentDomain.BaseDirectory;
        string parent=Path.GetFullPath(Path.Combine(baseDir,".."));
        if(File.Exists(Path.Combine(parent,"game.exe")))return parent;
        if(File.Exists(Path.Combine(baseDir,"game.exe")))return baseDir;
        try{
            string steam=Microsoft.Win32.Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam","SteamPath",null) as string;
            if(!string.IsNullOrEmpty(steam)){
                steam=steam.Replace('/','\\');
                var libraries=new List<string>{steam};
                string vdf=Path.Combine(steam,"steamapps","libraryfolders.vdf");
                if(File.Exists(vdf))foreach(string line in File.ReadAllLines(vdf)){
                    if(line.IndexOf("\"path\"",StringComparison.OrdinalIgnoreCase)<0)continue;
                    string[] parts=line.Split('"');
                    if(parts.Length>=4&&!string.IsNullOrEmpty(parts[3]))libraries.Add(parts[3].Replace("\\\\","\\"));
                }
                foreach(string library in libraries){
                    string candidate=Path.Combine(library,"steamapps","common","Dead or Alive 5 Last Round");
                    if(File.Exists(Path.Combine(candidate,"game.exe")))return candidate;
                }
            }
        }catch{}
        return parent;
    }
    readonly int[] original={17,31,30,32,36,37,38,50,22,23,24,49,57,28,25};
    readonly string[] names={"Up","Down","Left","Right","Guard / H","Punch / P","Kick / Cancel","Throw / Confirm","P + K","H + P + K","H + K","Taunt","Shortcut / Duel","Pause","Command list"};
    int[] keys;Button[] binds;int capture=-1;Label status;ComboBox mode;
    string Profile {get{return Path.Combine(root,"Profil-clavier.ini");}}
    string Backup {get{return Path.Combine(root,"Sauvegarde-avant-prototype");}}
    string Bridge {get{return Path.Combine(game,"dinput8ex.bin");}}
    string Payload {get{return Path.Combine(root,"payload","dinput8ex.bin");}}
    string Config {get{return Path.Combine(game,"DOA5LR-InputBridge.ini");}}
    static string Hash(string p){using(var s=File.OpenRead(p))using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
    static bool Running(){return Process.GetProcessesByName("game").Length>0;}
    static string KeyName(int scan){
        // Keep letters/punctuation from the physical keyboard layout, but display
        // common named keys in the application's language.
        switch(scan){case 1:return "Esc";case 14:return "Backspace";case 15:return "Tab";case 28:return "Enter";case 42:return "Left Shift";case 54:return "Right Shift";case 57:return "Space";case 58:return "Caps Lock";case 69:return "Num Lock";case 70:return "Scroll Lock";case 156:return "Num Enter";case 183:return "Print Screen";case 197:return "Pause";case 199:return "Home";case 200:return "Up arrow";case 201:return "Page Up";case 203:return "Left arrow";case 205:return "Right arrow";case 207:return "End";case 208:return "Down arrow";case 209:return "Page Down";case 210:return "Insert";case 211:return "Delete";case 221:return "Menu";}
        var b=new StringBuilder(128);int param=(scan&127)<<16;if((scan&128)!=0)param|=1<<24;Native.GetKeyNameText(param,b,128);return b.Length>0?b.ToString():"Key "+scan;
    }
    Button ButtonAt(string text,int x,int y,int w,Action action){var b=new Button{Text=text,Location=new Point(x,y),Size=new Size(w,34),FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(44,52,68),ForeColor=Color.White,TabStop=false};b.Click+=delegate{Safe(action);};Controls.Add(b);return b;}
    void LabelAt(string text,int x,int y,int w,int h,float size){Controls.Add(new Label{Text=text,Location=new Point(x,y),Size=new Size(w,h),Font=new Font("Segoe UI",size),ForeColor=Color.FromArgb(220,226,238)});}
    public InputLab(){
        Text="DOA5LR — Controls (experimental)";ClientSize=new Size(760,790);StartPosition=FormStartPosition.CenterScreen;FormBorderStyle=FormBorderStyle.FixedSingle;MaximizeBox=false;AutoScaleMode=AutoScaleMode.Dpi;
        BackColor=Color.FromArgb(20,25,35);ForeColor=Color.White;Font=new Font("Segoe UI",10);KeyPreview=true;
        keys=(int[])original.Clone();LoadProfile();
        LabelAt("DOA5LR  /  YOUR CONTROLS",24,18,710,34,19);
        ButtonAt("Controller finder",565,18,165,ShowDevices);
        LabelAt("Choose Keyboard or Controller, then launch the game with that mode.",24,60,710,25,10);
        LabelAt("Input mode for the next launch",24,99,310,28,10);
        mode=new ComboBox{Location=new Point(340,96),Size=new Size(390,30),DropDownStyle=ComboBoxStyle.DropDownList,BackColor=Color.White,ForeColor=Color.Black};
        mode.Items.AddRange(new object[]{"Keyboard + controller (experimental)","Keyboard","Controller (usual configuration)"});mode.SelectedIndex=SavedMode();Controls.Add(mode);
        LabelAt("Action (default game controls)",24,146,360,24,10);
        LabelAt("Your key — click to change",405,146,330,24,10);
        binds=new Button[original.Length];
        for(int i=0;i<original.Length;i++){int row=i;int y=180+i*30;LabelAt(names[i],30,y+4,360,25,10);binds[i]=ButtonAt(KeyName(keys[i]),405,y,325,delegate{capture=row;status.Text="Press the new key for: "+names[row]+". Esc cancels.";});binds[i].Height=27;}
        ButtonAt("Default keyboard layout",24,640,224,delegate{keys=(int[])original.Clone();RefreshKeys();status.Text="Native layout: ZQSD on AZERTY, WASD on QWERTY.";});
        ButtonAt("Move with arrow keys",267,640,224,delegate{keys=(int[])original.Clone();keys[0]=200;keys[1]=208;keys[2]=203;keys[3]=205;RefreshKeys();});
        ButtonAt("Save profile",510,640,220,SaveProfile);
        ButtonAt("Enable module",24,682,224,Install);
        ButtonAt("Play via Steam",267,682,224,Play);
        ButtonAt("Restore previous setup",510,682,220,delegate{if(File.Exists(Path.Combine(Backup,"complete")))Restore();else status.Text="To remove this pack component, reopen the installer and uncheck experimental in-game keyboard remapping.";});
        status=new Label{Location=new Point(24,733),Size=new Size(710,48),ForeColor=Color.FromArgb(143,206,234),Font=new Font("Segoe UI",9)};Controls.Add(status);
        mode.SelectedIndexChanged+=delegate{ShowModeHint();};
        ShowModeHint();
    }
    void ShowModeHint(){status.Text=mode.SelectedIndex==1?"Keyboard mode: disconnect controllers before launching. Play via Steam enables remapping when needed.":(mode.SelectedIndex==2?"Controller mode uses your usual game and Steam configuration. The optional module can stay disabled.":"Combined mode enables the experimental module. A controller connected at startup may block the keyboard.");}
    void Safe(Action action){try{action();}catch(Exception e){capture=-1;status.Text=e.Message;MessageBox.Show(this,e.Message,"DOA5LR — Controls",MessageBoxButtons.OK,MessageBoxIcon.Information);}}
    void RefreshKeys(){capture=-1;for(int i=0;i<keys.Length;i++)binds[i].Text=KeyName(keys[i]);}
    void LoadProfile(){
        bool knownModule=Installed()||(File.Exists(Bridge)&&Hash(Bridge)==OriginalXidiHash);
        // A portable identity template must not replace live bindings. An explicitly
        // saved draft remains preferred until the game configuration changes.
        string path=knownModule&&File.Exists(Config)&&!SavedProfileMatchesConfig()?Config:Profile;
        if(!File.Exists(path))return;
        var candidate=(int[])original.Clone();bool keyboard=false;
        foreach(var raw in File.ReadAllLines(path)){
            string line=raw.Trim();if(line.StartsWith("[")){keyboard=string.Equals(line,"[Keyboard]",StringComparison.OrdinalIgnoreCase);continue;}if(!keyboard)continue;
            var pair=line.Split('=');int a,b;if(pair.Length==2&&int.TryParse(pair[0],out a)&&int.TryParse(pair[1],out b)){int ix=Array.IndexOf(original,a);if(ix>=0&&b>0&&b<256)candidate[ix]=b;}
        }
        if(candidate.Distinct().Count()==candidate.Length)keys=candidate;
    }
    bool SavedProfileMatchesConfig(){
        if(!File.Exists(Profile))return false;
        bool metadata=false,saved=false;string basedOn=null;
        foreach(string raw in File.ReadAllLines(Profile)){
            string line=raw.Trim();if(line.StartsWith("[")){metadata=string.Equals(line,"[Profile]",StringComparison.OrdinalIgnoreCase);continue;}if(!metadata)continue;
            string[] pair=line.Split('=');if(pair.Length!=2)continue;
            if(string.Equals(pair[0].Trim(),"SavedByCommands",StringComparison.OrdinalIgnoreCase))saved=pair[1].Trim()=="1";
            if(string.Equals(pair[0].Trim(),"GameConfigSHA256",StringComparison.OrdinalIgnoreCase))basedOn=pair[1].Trim();
        }
        return saved&&string.Equals(basedOn,File.Exists(Config)?Hash(Config):"absent",StringComparison.OrdinalIgnoreCase);
    }
    int SavedMode(){
        if(!Installed())return IsPackManaged()?2:1;
        if(!File.Exists(Config))return 1;
        bool input=false;foreach(string raw in File.ReadAllLines(Config)){
            string line=raw.Trim();if(line.StartsWith("[")){input=string.Equals(line,"[Input]",StringComparison.OrdinalIgnoreCase);continue;}if(!input)continue;
            string[] pair=line.Split('=');if(pair.Length!=2||!string.Equals(pair[0].Trim(),"Mode",StringComparison.OrdinalIgnoreCase))continue;
            string value=pair[1].Trim();if(string.Equals(value,"Controller",StringComparison.OrdinalIgnoreCase))return 2;
            if(string.Equals(value,"Hybrid",StringComparison.OrdinalIgnoreCase))return 0;
            return 1;
        }return 1;
    }
    void SaveProfile(){
        if(keys.Distinct().Count()!=keys.Length)throw new Exception("Two actions use the same key.");
        var text=new StringBuilder("[Keyboard]\r\n");for(int i=0;i<keys.Length;i++)text.Append(original[i]+"="+keys[i]+"\r\n");
        text.Append("[Profile]\r\nSavedByCommands=1\r\nGameConfigSHA256="+(File.Exists(Config)?Hash(Config):"absent")+"\r\n");
        File.WriteAllText(Profile,text.ToString(),Encoding.ASCII);status.Text="Profile saved. Apply it by restarting with Play via Steam.";
    }
    void CheckClosed(){if(Running())throw new Exception("Close DOA5LR completely, then try again. No changes have been made.");}
    bool Installed(){return File.Exists(Bridge)&&File.Exists(Payload)&&Hash(Bridge)==Hash(Payload);}
    const string ComponentsName="DOA5LR-Salons-Components.txt";
    const string SettingsName=@"InputLab\previous-settings.txt";
    const string ManagedBackupMarker="pack-managed-v1";
    readonly string[] managed={"dinput8ex.bin","DInput8.ini","Xidi.ini","DOA5LR-InputBridge.ini","DOA5LR-InputBridge-Xidi.dll","DOA5LR-ControllerProfiles.ini","DOA5LR-Companion.exe"};
    string ComponentValue(){
        string path=Path.Combine(game,ComponentsName);
        if(!File.Exists(path))return null;
        foreach(string raw in File.ReadAllLines(path)){
            var pair=raw.Split(new[]{'='},2);
            if(pair.Length==2&&string.Equals(pair[0].Trim(),"inputlab",StringComparison.OrdinalIgnoreCase))return pair[1].Trim();
        }
        return null;
    }
    bool IsPackManaged(){return ComponentValue()!=null;}
    string[] BackupFiles(){return File.Exists(Path.Combine(Backup,ManagedBackupMarker))?managed.Concat(new[]{ComponentsName,SettingsName}).ToArray():managed;}
    string ArchiveBackup(string reason){
        string archived=Backup+"-"+reason+"-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,8);
        Directory.Move(Backup,archived);return archived;
    }
    void CreateBackup(bool packManaged){
        if(Directory.Exists(Backup)){
            // An installer may have disabled the runtime since this app made its
            // backup. Keep that older backup, but do not let it prevent reactivation.
            if(packManaged&&ComponentValue()=="0"&&Hash(Bridge)==OriginalXidiHash&&!File.Exists(Path.Combine(game,SettingsName)))ArchiveBackup("before-reactivation");
            else throw new IOException("A backup already exists. Restore it before installing again.");
        }
        Directory.CreateDirectory(Backup);
        string[] files=packManaged?managed.Concat(new[]{ComponentsName,SettingsName}).ToArray():managed;
        foreach(string n in files){
            string source=Path.Combine(game,n),target=Path.Combine(Backup,n);
            Directory.CreateDirectory(Path.GetDirectoryName(target));
            if(File.Exists(source))File.Copy(source,target);else File.WriteAllText(target+".absent","");
        }
        if(packManaged)File.WriteAllText(Path.Combine(Backup,ManagedBackupMarker),"Tracks component state and installer settings snapshot.");
        File.WriteAllText(Path.Combine(Backup,"complete"),"Backup complete");
    }
    static string ReadIni(string path,string section,string key){
        if(!File.Exists(path))return null;
        const string missing="__DOA5LR_INPUTLAB_MISSING__";
        var value=new StringBuilder(512);Native.GetPrivateProfileString(section,key,missing,value,(uint)value.Capacity,path);
        return value.ToString()==missing?null:value.ToString();
    }
    static void WriteIni(string path,string section,string key,string value){
        if(!Native.WritePrivateProfileString(section,key,value,path)||ReadIni(path,section,key)!=value)throw new IOException("Unable to update "+key+" in "+Path.GetFileName(path)+".");
    }
    static string EncodeSetting(string value){return value==null?"-":Convert.ToBase64String(Encoding.UTF8.GetBytes(value));}
    void SnapshotInstallerSettings(){
        string path=Path.Combine(game,SettingsName),dinput=Path.Combine(game,"DInput8.ini"),xidi=Path.Combine(game,"Xidi.ini");
        if(File.Exists(path))throw new IOException("The pack already manages this module. Repair it with the matching installer.");
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        // Same schema and native INI interpretation as the installer's InputLabSettings.
        File.WriteAllLines(path,new[]{"DOA5LR-InputLab-Settings-v1",
            "KeyboardOnly="+EncodeSetting(ReadIni(dinput,"PATCH","KeyboardOnly")),
            "XidiFileExisted="+(File.Exists(xidi)?"1":"0"),
            "ActiveVirtualControllerMask="+EncodeSetting(ReadIni(xidi,"Workarounds","ActiveVirtualControllerMask"))});
    }
    void SetComponentEnabled(){
        string path=Path.Combine(game,ComponentsName),text=File.ReadAllText(path);
        text=System.Text.RegularExpressions.Regex.Replace(text,@"(?im)^([ \t]*inputlab[ \t]*=)[^\r\n]*","${1}1");
        File.WriteAllText(path,text,new UTF8Encoding(false));
        if(ComponentValue()!="1")throw new IOException("Unable to save the component choice.");
    }
    void InstallFiles(){
        if(!File.Exists(Path.Combine(game,"game.exe")))throw new Exception("DOA5LR installation not found: "+game);
        if(!File.Exists(Bridge)||Hash(Bridge)!=OriginalXidiHash)throw new Exception("The input DLL differs from the verified pack. Installation stopped.");
        bool packManaged=IsPackManaged();
        if(packManaged&&ComponentValue()!="0")throw new IOException("The pack component state does not match its input DLL. Repair it with the matching installer.");
        if(File.Exists(Path.Combine(game,SettingsName)))throw new Exception("The pack already manages this module. Repair it with the matching installer.");
        foreach(string n in new[]{Payload,Path.Combine(root,"DOA5LR-ControllerProfiles.ini"),Path.Combine(root,"DOA5LR-Companion.exe"),Path.Combine(game,"DInput8.ini")})
            if(!File.Exists(n))throw new Exception("Application file missing: "+n+". Extract the entire application folder before enabling it.");
        if(Hash(Payload)==OriginalXidiHash)throw new Exception("The supplied module is the original Xidi. Installation stopped.");
        string preserved=Path.Combine(game,"DOA5LR-InputBridge-Xidi.dll");
        if(File.Exists(preserved)&&Hash(preserved)!=OriginalXidiHash)throw new Exception("The preserved Xidi differs from the verified pack. Installation stopped.");
        CreateBackup(packManaged);
        try{
            if(packManaged)SnapshotInstallerSettings();
            if(!File.Exists(preserved))File.Copy(Bridge,preserved);
            string controllers=Path.Combine(game,"DOA5LR-ControllerProfiles.ini");
            if(!File.Exists(controllers))File.Copy(Path.Combine(root,"DOA5LR-ControllerProfiles.ini"),controllers);
            string reader=Path.Combine(root,"DOA5LR-Companion.exe"),targetReader=Path.Combine(game,"DOA5LR-Companion.exe");
            if(!string.Equals(Path.GetFullPath(reader),Path.GetFullPath(targetReader),StringComparison.OrdinalIgnoreCase))File.Copy(reader,targetReader,true);
            File.Copy(Payload,Bridge,true);
            if(packManaged)SetComponentEnabled();
        }catch{
            RestoreFiles();ArchiveBackup("activation-rolled-back");throw;
        }
    }
    void Install(){PrepareAndRun(null);}
    string ProfileText(){var b=new StringBuilder("[Keyboard]\r\n");for(int i=0;i<keys.Length;i++)b.Append(original[i]+"="+keys[i]+"\r\n");return b.ToString();}
    void RestoreFiles(){
        if(!File.Exists(Path.Combine(Backup,"complete")))throw new Exception("Complete backup not found.");
        string[] files=BackupFiles();
        foreach(string n in files)if(File.Exists(Path.Combine(Backup,n))==File.Exists(Path.Combine(Backup,n+".absent")))throw new Exception("Inconsistent backup for "+n+". Restore stopped.");
        foreach(string n in files){
            string src=Path.Combine(Backup,n),dst=Path.Combine(game,n);
            if(File.Exists(src)){Directory.CreateDirectory(Path.GetDirectoryName(dst));File.Copy(src,dst,true);}
            else if(File.Exists(dst))File.Delete(dst);
        }
    }
    void Restore(){
        CheckClosed();
        if(!Installed()){
            if(IsPackManaged()&&ComponentValue()=="0"&&File.Exists(Bridge)&&Hash(Bridge)==OriginalXidiHash){mode.SelectedIndex=2;status.Text="The optional module is already disabled. Your profiles and the controls app are still available.";return;}
            throw new Exception("The module is not installed or has been replaced. Automatic restore stopped.");
        }
        RestoreFiles();ArchiveBackup("restored");mode.SelectedIndex=SavedMode();
        status.Text="Previous setup restored. Your personal profile has been kept.";
    }
    static void StartSteam(){
        string steam=Microsoft.Win32.Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam","SteamExe",null) as string;
        if(string.IsNullOrEmpty(steam)||!File.Exists(steam))throw new IOException("Steam.exe not found. Open Steam, then try again.");
        Process.Start(new ProcessStartInfo(steam,"-applaunch 311730"){UseShellExecute=true});
    }
    void ApplySelectedMode(){
        bool keyboard=mode.SelectedIndex!=2,hybrid=mode.SelectedIndex==0;
        File.WriteAllText(Config,"[Input]\r\nMode="+(hybrid?"Hybrid":(keyboard?"Keyboard":"Controller"))+"\r\n"+ProfileText(),Encoding.ASCII);
        WriteIni(Path.Combine(game,"Xidi.ini"),"Workarounds","ActiveVirtualControllerMask",keyboard?"0":"15");
        WriteIni(Path.Combine(game,"DInput8.ini"),"PATCH","KeyboardOnly",hybrid?"1":"0");
    }
    void PrepareAndRun(Action launch){
        CheckClosed();capture=-1;
        if(!File.Exists(Path.Combine(game,"game.exe")))throw new IOException("DOA5LR installation not found: "+game);
        bool wasInstalled=Installed();
        if(!wasInstalled&&mode.SelectedIndex==2){
            if(launch!=null)launch();
            status.Text=launch==null?"Controller mode uses the usual configuration. Select Keyboard or combined mode to enable the optional module.":"Launching with the usual controller configuration. The optional module stays disabled.";
            return;
        }
        if(mode.SelectedIndex==1)CheckKeyboardStartup();
        // Preserve launch-time edits too: a failed Steam launch must not silently
        // enable the component or replace the player's previously applied mode.
        var previous=new Dictionary<string,byte[]>();
        foreach(string path in new[]{Config,Path.Combine(game,"DInput8.ini"),Path.Combine(game,"Xidi.ini"),Profile})previous[path]=File.Exists(path)?File.ReadAllBytes(path):null;
        bool activated=false;
        try{
            if(!wasInstalled){InstallFiles();activated=true;}
            ApplySelectedMode();SaveProfile();
            if(launch!=null)launch();
        }catch{
            if(activated){RestoreFiles();ArchiveBackup("activation-rolled-back");}
            foreach(var item in previous){if(item.Value!=null)File.WriteAllBytes(item.Key,item.Value);else if(File.Exists(item.Key))File.Delete(item.Key);}
            throw;
        }
        status.Text=launch==null?"Module enabled and profile applied. Click Play via Steam when ready.":(mode.SelectedIndex==0?"Experimental combined mode: a controller connected at startup may block keyboard input.":(mode.SelectedIndex==1?"Launching with your keyboard profile. Try it in training first.":"Launching in controller mode. Keyboard remapping is disabled."));
    }
    void Play(){PrepareAndRun(StartSteam);}
    void ShowDevices(){
        string detector=Path.Combine(root,"DOA5LR-Detecteur.exe");
        if(File.Exists(detector)){
            Process.Start(new ProcessStartInfo(detector){UseShellExecute=true,WorkingDirectory=root});
            status.Text="Controller finder opened: search by name or VID/PID.";
            return;
        }
        var start=new ProcessStartInfo(Path.Combine(root,"DOA5LR-Peripheriques.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,StandardOutputEncoding=Encoding.UTF8};
        string devices;using(var p=Process.Start(start)){devices=p.StandardOutput.ReadToEnd();p.WaitForExit();if(p.ExitCode!=0)throw new IOException("Unable to detect devices.");}
        if(string.IsNullOrWhiteSpace(devices))devices="No DirectInput controller detected. Connect your device, then reopen this list.";
        File.WriteAllText(Path.Combine(root,"Peripheriques-detectes.txt"),devices,Encoding.UTF8);
        using(var dialog=new Form{Text="Devices — model identifiers",Size=new Size(780,310),StartPosition=FormStartPosition.CenterParent}){
            var text=new TextBox{Multiline=true,ReadOnly=true,Dock=DockStyle.Fill,ScrollBars=ScrollBars.Both,Font=new Font("Segoe UI",10),Text=devices.Replace("\t","    ")+"\r\n\r\nVID = vendor · PID = model\r\nThe same model may be sold under several names. Two units can share these IDs.\r\n\r\nInitial profile: DualSense Edge 054C:0DF2.\r\nOther sticks / hitbox controllers: device detection is available; button profiles need configuration.\r\nXInput devices use their standard layout."};dialog.Controls.Add(text);dialog.ShowDialog(this);
        }
    }
    void CheckKeyboardStartup(){
        string inventory=Path.Combine(root,"DOA5LR-Peripheriques.exe");
        if(!File.Exists(inventory))throw new IOException("Controller check is missing. Extract the entire app folder before launching Keyboard mode.");
        var output=new StringBuilder();
        var start=new ProcessStartInfo(inventory){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,StandardOutputEncoding=Encoding.UTF8};
        using(var process=Process.Start(start)){
            process.OutputDataReceived+=delegate(object sender,DataReceivedEventArgs e){if(e.Data!=null)lock(output){output.AppendLine(e.Data);}};
            process.BeginOutputReadLine();
            if(!process.WaitForExit(8000)){process.Kill();process.WaitForExit();throw new IOException("Controller check timed out. Reconnect or disconnect your controller, then try again.");}
            process.WaitForExit();
            if(process.ExitCode!=0)throw new IOException("Unable to check connected controllers. Close the finder and try again.");
        }
        string detected;lock(output){detected=output.ToString();}
        if(!string.IsNullOrWhiteSpace(detected))throw new IOException("A controller is still connected. This prototype can lose keyboard input when the game starts with a controller connected.\r\n\r\nDisconnect your controller, then click Play via Steam again, or choose Controller mode. The game has not been launched.");
    }
    protected override bool ProcessCmdKey(ref Message msg,Keys keyData){
        if(capture<0)return base.ProcessCmdKey(ref msg,keyData);
        if((keyData&Keys.KeyCode)==Keys.Escape){capture=-1;status.Text="Selection cancelled.";return true;}
        int raw=msg.LParam.ToInt32();int scan=(raw>>16)&255;if((raw&(1<<24))!=0)scan|=128;
        if((raw&(1<<30))!=0)return true;
        if(scan==0||scan==1||scan==29||scan==157||scan==56||scan==184||scan==219||scan==220)return true;
        if(capture>=0&&((scan>=59&&scan<=68)||scan==87||scan==88)){status.Text="F1–F12 are reserved for pack shortcuts in this prototype. Choose another key.";return true;}
        if(capture>=0){int other=Array.IndexOf(keys,scan);if(other>=0&&other!=capture)keys[other]=keys[capture];keys[capture]=scan;RefreshKeys();status.Text="Key changed. Duplicate assignments are swapped to keep the profile consistent.";}
        return true;
    }
    [STAThread]static void Main(string[] args){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);using(var app=new InputLab()){
        if(args.Length==1&&args[0]=="--install"){try{app.Install();Console.WriteLine(app.status.Text);}catch(Exception e){Console.Error.WriteLine(e.Message);Environment.ExitCode=1;}return;}
        if(args.Length==1&&args[0]=="--restore"){try{app.Restore();Console.WriteLine(app.status.Text);}catch(Exception e){Console.Error.WriteLine(e.Message);Environment.ExitCode=1;}return;}
        if(args.Length==1&&args[0]=="--play-keyboard"){try{app.mode.SelectedIndex=1;app.Play();}catch(Exception e){Console.Error.WriteLine(e.Message);Environment.ExitCode=1;}return;}
        if(args.Length==1&&args[0]=="--configure-keyboard"){app.mode.SelectedIndex=1;app.ShowModeHint();}
        if(args.Length==2&&args[0]=="--preview"){app.Show();Application.DoEvents();using(var bmp=new Bitmap(app.Width,app.Height)){app.DrawToBitmap(bmp,new Rectangle(0,0,bmp.Width,bmp.Height));bmp.Save(args[1]);}return;}
        Application.Run(app);
    }}
}
