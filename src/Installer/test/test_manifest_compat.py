"""Check public manifests with exact shipped legacy sources and the current UI.

Requires DOA5LR_BASE_ZIP (published 0.3.8) and DOA5LR_PREVIEW_ZIP (preview.1).
Set DOA5LR_RELEASE_MANIFEST to test an actual release version.txt instead of the fixture.
Only temporary fixtures/harnesses are written; no network, Steam or game launch.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CSC = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
ARCHIVES = (
    ("1.1.0", "DOA5LR_BASE_ZIP", "6bffba7fdef2713d433879f01dfe2e0d9ca908bd8f8ec9be17c5e86f0cc14061"),
    ("1.3.0", "DOA5LR_PREVIEW_ZIP", "3fc4f9fc3348a3954080d24a3999d3e0532c8558ed90da858438449e72afd3f2"),
)
INPUTLAB = r"inputlab|Experimental in-game keyboard remapping (settings app always available)|DOA5LR-InputBridge-Xidi.dll;DOA5LR-InputBridge.ini;DOA5LR-ControllerProfiles.ini;DOA5LR-Companion.exe"
OPTIONALS = (
    r"optional=borderless|Borderless|scripts\DOA5LR-Borderless.asi;scripts\DOA5LR-Borderless.ini;scripts\BORDERLESS-EN.txt;scripts\Borderless-Source\*",
    r"optional=60fps|60 fps|scripts\DOA5LR-60fps-menus.asi;scripts\DOA5LR-60fps-menus.ini;scripts\60FPS-EN.txt;scripts\60fps-Source\*",
)
MANIFEST = "\n".join([
    "version=0.3.9", "url=https://example.invalid/pack.zip", "sha256=" + "a" * 64,
    "size=123", "installer=https://example.invalid/installer.exe", "installer_version=1.3.1",
    "installer_sha256=" + "b" * 64, "keep=*.ini", *OPTIONALS, "optional_v2=" + INPUTLAB, "",
])
LEGACY = r'''
using System;
using System.IO;
using System.Linq;
static class ManifestCompatHarness {
    static void Main(string[] args) {
        string text=File.ReadAllText(args[0]);
        var manifest=Manifest.Parse(text);
        if(Cfg.AppVersion!=args[1] || manifest.Version!="0.3.9" || manifest.InstallerVersion!="1.3.1" ||
           manifest.InstallerUrl!=args[2] || manifest.InstallerSha256!=args[3] ||
           manifest.Url!=args[4] || manifest.Sha256!=args[5] || manifest.Size!=long.Parse(args[6]) ||
           Util.CmpVer(manifest.InstallerVersion,Cfg.AppVersion)<=0 || Component.Current.Any(c=>c.Id=="inputlab") || Component.Current.Length!=2)
            throw new Exception("Legacy manifest parsing/self-update route failed");
        bool rejected=false;
        try { Manifest.Parse(text.Replace("optional_v2=inputlab|","optional=inputlab|")); }
        catch(InvalidDataException) { rejected=true; }
        if(args[1]=="1.1.0" && !rejected)throw new Exception("Original 1.1 regression was not reproduced");
        Console.WriteLine("PASS exact shipped "+Cfg.AppVersion+": public manifest parses and installer self-update is reachable");
    }
}
'''
CURRENT = r'''
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
static class ManifestCompatHarness {
    static int checks;
    static void Check(bool value,string name) { if(!value)throw new Exception(name); checks++; Console.WriteLine("PASS "+name); }
    static object Field(object owner,string name) { return owner.GetType().GetField(name,BindingFlags.Instance|BindingFlags.NonPublic).GetValue(owner); }
    static void Focus(Form form) { typeof(Form).GetMethod("OnActivated",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(form,new object[]{EventArgs.Empty}); }
    [STAThread] static void Main(string[] args) {
        string text=File.ReadAllText(args[0]);
        var manifest=Manifest.Parse(text);
        Check(Cfg.AppVersion=="1.3.1" && Assembly.GetExecutingAssembly().GetName().Version.ToString()=="1.3.1.0","installer/assembly version is 1.3.1");
        Check(manifest.Version=="0.3.9" && manifest.InstallerVersion=="1.3.1" &&
              manifest.InstallerUrl==args[2] && manifest.InstallerSha256==args[3] &&
              manifest.Url==args[4] && manifest.Sha256==args[5] && manifest.Size==long.Parse(args[6]),
              "current parser preserves release URLs, versions, hashes and archive size");
        Check(manifest.Optional.Count==3 && Component.Current.Count(c=>c.Id=="inputlab")==1,"optional_v2 adds exactly one validated InputLab component");
        string old=string.Join("\n",text.Split('\n').Where(l=>!l.StartsWith("optional_v2="))).Replace("version=0.3.9\n","version=0.3.8\n");
        Manifest.Parse(old);
        string game=args[1];Directory.CreateDirectory(Path.Combine(game,"InputLab"));
        File.WriteAllText(Path.Combine(game,"game.exe"),"Fake game; never executable.",Encoding.UTF8);
        Check(!Component.Current.Any(c=>c.Id=="inputlab") && !InputLauncher.Enabled(game),"0.3.8 without optional_v2 keeps normal launch and no InputLab component");
        Manifest.Parse(text.Replace("optional_v2=inputlab|","optional=inputlab|"));
        Check(Component.Current.Count(c=>c.Id=="inputlab")==1,"preview optional=inputlab manifests remain supported");
        Manifest.Parse(text+text.Substring(text.IndexOf("optional_v2=")));
        Check(Component.Current.Count(c=>c.Id=="inputlab")==1,"duplicate component does not create duplicate controls");
        bool invalid=false;
        try { Manifest.Parse(text.Replace("DOA5LR-InputBridge-Xidi.dll;","evil.dll;")); } catch(InvalidDataException){invalid=true;}
        Check(invalid,"optional_v2 retains strict path ownership validation");
        Manifest.Parse(text);
        string components=Path.Combine(game,Cfg.ComponentsFile),profile=Path.Combine(game,"DOA5LR-InputBridge.ini");
        File.WriteAllText(Path.Combine(game,@"InputLab\DOA5LR-Commandes.exe"),"Fake controls; never executable.",Encoding.UTF8);
        File.WriteAllText(profile,"[Input]\r\nMode=Keyboard\r\n[Keyboard]\r\n37=33\r\n",Encoding.UTF8);
        byte[] before=File.ReadAllBytes(profile);
        using(var form=new MainForm(false)) {
            ((TextBox)Field(form,"txtGame")).Text=game;
            var choices=(List<CheckBox>)Field(form,"chkComp");
            var input=choices.Single(c=>(string)c.Tag=="inputlab");
            Check(!input.Checked && ((Button)Field(form,"btnFinder")).Enabled,"new UI shows InputLab unchecked while installed controls remain available");
            File.WriteAllText(components,"inputlab=1\r\nborderless=0\r\n60fps=1\r\n",Encoding.UTF8);
            Focus(form);
            Check(input.Checked,"new UI restores a saved ON choice with optional_v2");
            input.Checked=false;Focus(form);
            Check(!input.Checked,"new UI preserves an unsaved OFF choice on focus");
        }
        Check(File.ReadAllBytes(profile).SequenceEqual(before),"manifest/UI selection leaves keyboard profile untouched");
        Console.WriteLine("All "+checks+" current manifest/UI compatibility checks passed; no UI shown or processes launched.");
    }
}
'''


def compile_and_run(folder, source, harness_code, args):
    folder.mkdir()
    harness = folder / "Harness.cs"
    harness.write_text(harness_code, encoding="utf-8")
    exe = folder / "Harness.exe"
    subprocess.run([str(CSC), "/nologo", "/target:exe", "/platform:x86", "/main:ManifestCompatHarness",
                    "/out:" + str(exe), "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll",
                    str(source), str(harness)], check=True)
    subprocess.run([str(exe), *map(str, args)], check=True)


with tempfile.TemporaryDirectory(prefix="doa5lr-manifest-compat-") as directory:
    temp = Path(directory)
    manifest = temp / "version.txt"
    release_manifest = os.environ.get("DOA5LR_RELEASE_MANIFEST")
    if release_manifest:
        original_manifest = Path(release_manifest).resolve()
        manifest.write_bytes(original_manifest.read_bytes())
        print("Testing actual release manifest:", original_manifest, flush=True)
    else:
        manifest.write_text(MANIFEST, encoding="utf-8")
        print("Testing synthetic compatibility manifest", flush=True)
    print("Manifest SHA256:", hashlib.sha256(manifest.read_bytes()).hexdigest(), flush=True)
    fields = dict(line.split("=", 1) for line in manifest.read_text(encoding="utf-8-sig").splitlines()
                  if "=" in line and not line.startswith("#"))
    expected_fields = [fields[key].strip() for key in ("installer", "installer_sha256", "url", "sha256", "size")]
    assert fields["version"].strip() == "0.3.9" and fields["installer_version"].strip() == "1.3.1"
    for version, variable, expected in ARCHIVES:
        archive = Path(os.environ[variable])
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected, "Unexpected " + variable
        source = temp / ("Installer-" + version + ".cs")
        with zipfile.ZipFile(archive) as z:
            source.write_bytes(z.read("scripts/Installer-Source/Installer.cs"))
        compile_and_run(temp / version, source, LEGACY, [manifest, version, *expected_fields])
    compile_and_run(temp / "current", ROOT / "Installer.cs", CURRENT, [manifest, temp / "fake game", *expected_fields])
