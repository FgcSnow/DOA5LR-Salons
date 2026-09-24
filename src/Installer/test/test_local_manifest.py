"""A movable local bundle is opt-in and verifies its ZIP before installation."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
code = r'''
using System;
using System.IO;
static class LocalPackTests {
    static void Reject(Action action) {
        try { action(); } catch (InvalidDataException) { return; }
        throw new Exception("Expected local pack rejection");
    }
    static void Main(string[] args) {
        string folder=args[0]; Directory.CreateDirectory(folder);
        string zip=Path.Combine(folder,"candidate.zip");
        File.WriteAllText(zip,"Verified test bytes; this test never installs or executes them.");
        Cfg.VersionUrl=Path.Combine(folder,"version.txt");
        File.WriteAllText(Cfg.VersionUrl,"fixture");
        var manifest=new Manifest { Url="candidate.zip", Version="test-local-"+Guid.NewGuid().ToString("N"), Sha256=Util.Sha256(zip), Size=new FileInfo(zip).Length };
        var engine=new Engine { Status=s=>{}, Progress=p=>{} };
        Cfg.AllowLocalPack=false;
        Reject(()=>engine.DownloadPack(manifest));
        Cfg.AllowLocalPack=true;
        string downloaded=engine.DownloadPack(manifest);
        if(Util.Sha256(downloaded)!=manifest.Sha256)throw new Exception("Sibling ZIP changed");
        File.Delete(downloaded);
        manifest.Url=zip;
        downloaded=engine.DownloadPack(manifest); File.Delete(downloaded);
        manifest.Url=@"..\candidate.zip";
        Reject(()=>engine.DownloadPack(manifest));
        manifest.Url="candidate.zip"; manifest.Sha256="";
        Reject(()=>engine.DownloadPack(manifest));
        Console.WriteLine("PASS: sibling ZIP, absolute ZIP, remote opt-out, traversal and missing hash guards");
    }
}
'''
with tempfile.TemporaryDirectory(prefix="doa5lr-local-manifest-") as directory:
    path=Path(directory)
    source=path/"Harness.cs"
    source.write_text(code,encoding="utf-8")
    exe=path/"Harness.exe"
    compiler=Path(os.environ["WINDIR"])/"Microsoft.NET/Framework/v4.0.30319/csc.exe"
    subprocess.run([str(compiler),"/nologo","/target:exe","/main:LocalPackTests","/out:"+str(exe),"/r:System.IO.Compression.dll","/r:System.IO.Compression.FileSystem.dll",str(root/"Installer.cs"),str(source)],check=True)
    subprocess.run([str(exe),str(path/"A moved folder with spaces")],check=True)
