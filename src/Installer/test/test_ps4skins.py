"""Installer 1.3.6 PS4 costumes regression tests, entirely offline.

Compiles the current source into a temporary directory and installs tiny synthetic
packs into fake game folders. TEMP/TMP are isolated, no actual game or shipped
installer is touched, and fake PE fixtures are inspected but never executed.
Run: python src/Installer/test/test_ps4skins.py
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / "Installer.cs"
CSC = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
SKIN_PATHS = (
    "DLC/990015/990015.bcm", "DLC/990015/data/990015.bin",
    "DLC/990015/data/990015.blp", "DLC/990015/data/990015.lnk",
)
GUIDE = "scripts/PS4-SKINS-EN.txt"
SKINS = {path: ("synthetic costume data " + path).encode() * 7 for path in SKIN_PATHS}
OPTIONAL = "optional_v6=ps4skins|PS4 costumes|" + ";".join(
    path.replace("/", "\\") for path in (*SKIN_PATHS, GUIDE))
CONFIG = (b"; personal caf\xe9 settings -- keep every byte\r\n[steam]\r\n"
          b"appid=311730\r\norgapi=steam_api_original.dll\r\n"
          b"; personal options\r\n[dlc]\r\n12345=My existing DLC\r\n"
          b"\r\n[extra]\r\nunknown = keep this spacing\r\n")
CORE = {
    "DOA5LR-Salons-VERSION.txt": b"0.3.15\r\n", "dinput8.dll": b"loader",
    "dinput8Hooked.dll": b"autolink", "DInput8.ini": b"[PATCH]\r\n",
    "dinput8ex.bin": b"xidi", "Xidi.32.dll": b"xidi",
    "scripts/DOA5LR-Lobby.asi": b"lobby", "scripts/DOA5LR-InviteFix.asi": b"invites",
    "scripts/DOA5LR-WiFi-Wired-Detector.asi": b"network",
    "scripts/DOA5LR-UpdateCheck.asi": b"updates", "scripts/DOA5LR-JoinFix.asi": b"join",
    "scripts/DOA5LR-Borderless.asi": b"borderless", "scripts/DOA5LR-60fps-menus.asi": b"fps",
    GUIDE: b"PS4 costumes guide\r\n",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(files):
    return json.dumps([{"path": path, "sha256": sha(data), "size": len(data)}
                       for path, data in files.items()], indent=2).encode()


CORE["DOA5LR-Diagnostic/ps4skins-files.json"] = inventory(SKINS)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def archive(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        for name, data in files.items():
            target.writestr(name, data)
    return path.read_bytes()


def pe(proxy=False):
    data = bytearray(128)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 64)
    data[64:68] = b"PE\0\0"
    struct.pack_into("<H", data, 68, 0x14C)
    return bytes(data) + b"SteamAPI_Init\0" + (b"cream_api.ini\0" if proxy else b"")


PROBE = r'''
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
static class Ps4SkinsProbe {
    static void Check(bool ok,string message) { if(!ok)throw new Exception(message);Console.WriteLine("PASS "+message); }
    static object Field(object owner,string name) { return owner.GetType().GetField(name,BindingFlags.Instance|BindingFlags.NonPublic).GetValue(owner); }
    [STAThread] static void Main(string[] args) {
        if(args[0]=="restore") { new Engine { Game=args[1] }.Restore(args[2]);return; }
        if(args[0]=="maps") {
            var maps=Component.Known.First(c=>c.Id=="maps");
            Console.WriteLine("optional_v5=maps|Maps|"+string.Join(";",maps.Globs));return;
        }
        string game=args[1];Manifest.Parse(File.ReadAllText(args[0]));
        Check(Cfg.AppVersion=="1.3.6" && Assembly.GetExecutingAssembly().GetName().Version.ToString()=="1.3.6.0","installer and assembly versions 1.3.6");
        Check(Component.Current.Count(c=>c.Id=="ps4skins")==1,"optional_v6 owns exactly one PS4 component");
        Check(Cfg.Ps4LoaderCompatible(game),"synthetic x86 loader/config accepted without executing it");
        var skins=Component.Current.Single(c=>c.Id=="ps4skins");
        foreach(string path in skins.Globs.Where(p=>p.StartsWith("DLC",StringComparison.OrdinalIgnoreCase)))
            Check(!Cfg.IsForbidden(path) && !Cfg.IsForbidden(path.ToUpperInvariant().Replace('\\','/')),"exact costume asset allowed: "+path);
        foreach(string path in new[]{@"DLC\12345\file.bin",@"DLC\990015\other.bin",@"DLC\990015\990015.bcm.extra",@"DLC\990015\data\other.bin",@"DLC\990015\data\990015.bin\extra",@"other\DLC\990015\990015.bcm",@"steam_api.dll",@"steam_api_original.dll",@"cream_api.ini",@"scripts\unlock.asi"})
            Check(Cfg.IsForbidden(path),"unrelated/protected file refused: "+path);
        string config=Path.Combine(game,"cream_api.ini");byte[] original=File.ReadAllBytes(config);
        string text=File.ReadAllText(config);
        foreach(string invalid in new[]{text.Replace("appid=311730","appid=1"),text.Replace("appid=311730", ""),text.Replace("orgapi=steam_api_original.dll",@"orgapi=..\steam_api_original.dll"),text.Replace("orgapi=steam_api_original.dll","orgapi=steam_api.dll"),text+"\r\n[steam]\r\nappid=311730\r\n",text+"\r\n[dlc]\r\n",text.Replace("[dlc]","[dlc]\r\n990015=A\r\n990015=B"),text.Replace("[steam]","[steam]\r\nunlockall=true"),text.Replace("[steam]","[steam]\r\nunlockall=1")}) {
            File.WriteAllText(config,invalid);Check(!Cfg.Ps4LoaderCompatible(game),"unsupported/ambiguous loader configuration refused");
        }
        File.WriteAllText(config,text.Replace("[dlc]", "[other]"));
        byte[] missingSectionBefore=File.ReadAllBytes(config);
        var repair=Ps4Skins.Preflight(game);
        Check(repair.Before.SequenceEqual(missingSectionBefore),"preflight preserves source bytes and does not write config");
        string repaired=System.Text.Encoding.GetEncoding(28591).GetString(repair.After);
        Check(repaired.EndsWith("[dlc]\r\n990015=PS4 costumes\r\n") && repaired.Contains("12345=My existing DLC"),"missing dlc section appended without changing unrelated sections");
        File.WriteAllBytes(config,repair.After);
        Check(Ps4Skins.Preflight(game).After.SequenceEqual(repair.After),"repaired registration is idempotent");
        File.WriteAllText(config,text.Replace("[steam]","[steam]\r\nunlockall=true").Replace("[dlc]","[dlc]\r\n990015=Existing custom registration"));
        Check(Cfg.Ps4LoaderCompatible(game),"existing PS4 registration is accepted without expanding unlockall configuration");
        File.WriteAllBytes(config,original);
        string proxy=Path.Combine(game,"steam_api.dll");byte[] proxyBytes=File.ReadAllBytes(proxy);
        File.WriteAllText(proxy,"SteamAPI_Init cream_api.ini");Check(!Cfg.Ps4LoaderCompatible(game),"non-PE proxy refused");
        File.WriteAllBytes(proxy,proxyBytes);
        string originalDll=Path.Combine(game,"steam_api_original.dll");byte[] originalDllBytes=File.ReadAllBytes(originalDll);
        byte[] wrongMachine=(byte[])originalDllBytes.Clone();wrongMachine[68]=0x64;wrongMachine[69]=0x86;
        File.WriteAllBytes(originalDll,wrongMachine);Check(!Cfg.Ps4LoaderCompatible(game),"64-bit original DLL refused for x86 game");
        File.WriteAllBytes(originalDll,originalDllBytes.Take(128).ToArray());Check(!Cfg.Ps4LoaderCompatible(game),"original DLL without expected Steam API marker refused");
        File.Delete(originalDll);Check(!Cfg.Ps4LoaderCompatible(game),"missing original DLL refused");
        File.WriteAllBytes(originalDll,originalDllBytes);
        Component.Current=Component.Defaults.Concat(new[]{Component.InputLab,Component.ReplayTakeover,Component.Maps,skins}).ToArray();
        using(var form=new MainForm(false)) {
            ((TextBox)Field(form,"txtGame")).Text=game;
            form.PerformLayout();
            var boxes=(List<CheckBox>)Field(form,"chkComp");var button=(Button)Field(form,"btnMain");
            Check(boxes.Count==6,"UI contains all six components");
            foreach(var box in boxes) Console.WriteLine("UI "+box.Tag+" "+box.Bounds);
            Check(boxes.All(c=>c.Bottom<=button.Top && c.Right<=form.ClientSize.Width),"six component labels fit before the install button and inside the window");
            Check(boxes.OrderBy(c=>c.Top).Zip(boxes.OrderBy(c=>c.Top).Skip(1),(a,b)=>a.Bottom<=b.Top).All(v=>v),"component checkboxes do not overlap");
            Check(boxes.Single(c=>(string)c.Tag=="ps4skins").Checked,"compatible loader enables PS4 default in UI");
        }
        Check(File.ReadAllBytes(config).SequenceEqual(original),"UI and compatibility checks preserve existing configuration");
    }
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix="doa5lr-ps4skins-test-") as directory:
        root = Path(directory)
        scratch = root / "temp"
        scratch.mkdir()
        env = dict(os.environ, TEMP=str(scratch), TMP=str(scratch))
        exe = root / "Installer.exe"
        probe = root / "Probe.exe"
        harness = root / "Probe.cs"
        harness.write_text(PROBE, encoding="utf-8")
        flags = [str(CSC), "/nologo", "/target:exe", "/platform:x86",
                 "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll"]
        subprocess.run([*flags, "/main:Program", "/out:" + str(exe), str(SOURCE)], check=True)
        subprocess.run([*flags, "/main:Ps4SkinsProbe", "/out:" + str(probe), str(SOURCE), str(harness)], check=True)

        def check(condition, message):
            if not condition:
                raise AssertionError(message)
            print("PASS " + message, flush=True)

        def game(name, compatible=True, config=CONFIG):
            target = root / name
            write(target / "game.exe", b"Fake fixture -- never executed.")
            if compatible:
                write(target / "cream_api.ini", config)
                write(target / "steam_api.dll", pe(True))
                write(target / "steam_api_original.dll", pe())
            return target

        pack = root / "pack"
        pack.mkdir()
        core_zip = pack / "core.zip"
        full_zip = pack / "full.zip"
        data_zip = pack / "skins.zip"
        core_bytes = archive(core_zip, CORE)
        full_bytes = archive(full_zip, CORE)
        data_bytes = archive(data_zip, SKINS)
        base = ["version=0.3.15", "url=" + str(full_zip), "sha256=" + sha(full_bytes),
                "size=" + str(len(full_bytes)), "notes=offline synthetic PS4 fixture", "keep=*.ini", OPTIONAL]
        # A core+skins manifest must never require the legacy full archive.
        full_zip.unlink()

        def manifest(name, skin_bytes=data_bytes, core_content=core_bytes, extra=()):
            target = root / (name + ".txt")
            lines = [*base, "core=%s|%s|%d" % (core_zip, sha(core_content), len(core_content)),
                     "skins_data=%s|%s|%d" % (data_zip, sha(skin_bytes), len(skin_bytes)), *extra]
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return target

        version = manifest("version")
        good = game("compatible")

        def clear_cache():
            cache = scratch / "DOA5LR-Salons"
            if cache.exists():
                shutil.rmtree(cache)

        def run(target, components=None, use=version, success=True):
            args = [str(exe), "--auto", "--game", str(target), "--manifest", str(use)]
            if components is not None:
                args += ["--components", components]
            log_path = target / "DOA5LR-Salons-Installer.log"
            if log_path.exists():
                log_path.unlink()
            result = subprocess.run(args, env=env, capture_output=True, timeout=60)
            log = log_path.read_text(encoding="utf-8-sig", errors="replace") if log_path.exists() else ""
            if (result.returncode == 0) != success:
                raise AssertionError("Unexpected installer result %s:\n%s\n%s" %
                                     (result.returncode, result.stdout.decode(errors="replace"), log))
            return log

        def installed(target):
            return all((target / path).is_file() and (target / path).read_bytes() == content
                       for path, content in SKINS.items())

        def snapshot(target):
            return {str(path.relative_to(target)): path.read_bytes() for path in target.rglob("*")
                    if path.is_file() and path.name != "DOA5LR-Salons-Installer.log"}

        def backups(target):
            folder = target / "DOA5LR-Salons-Backups"
            return set(folder.iterdir()) if folder.exists() else set()

        def failed_unchanged(target, use=version, components="ps4skins=1"):
            before = snapshot(target)
            output = run(target, components, use, success=False)
            check(snapshot(target) == before, "failure leaves all fake game files and backups unchanged")
            return output

        print("\nFresh default, registration and backup", flush=True)
        proxy_before = (good / "steam_api.dll").read_bytes()
        original_before = (good / "steam_api_original.dll").read_bytes()
        before = backups(good)
        run(good)
        check(installed(good) and (good / GUIDE).exists(), "compatible default installs core and all four skins assets without legacy full ZIP")
        cfg = (good / "cream_api.ini").read_bytes()
        check(re.sub(br"990015=PS4 costumes\r?\n", b"", cfg, count=1) == CONFIG and cfg.count(b"990015=") == 1,
              "registration adds one PS4 row preserving every existing byte, ANSI comment and CRLF")
        new_backup, = backups(good) - before
        check((new_backup / "cream_api.ini").read_bytes() == CONFIG, "original loader configuration backed up exactly")
        check((good / "steam_api.dll").read_bytes() == proxy_before and
              (good / "steam_api_original.dll").read_bytes() == original_before, "existing loader DLLs never replaced")

        print("\nIntact assets skip data download; altered assets repair", flush=True)
        data_zip.rename(data_zip.with_suffix(".away"))
        clear_cache()
        before = backups(good)
        run(good)
        check(installed(good), "intact assets allow an update with no skins ZIP available")
        new_backup, = backups(good) - before
        check(not (new_backup / "DLC").exists(), "core-only update does not touch or back up intact skins assets")
        data_zip.with_suffix(".away").rename(data_zip)
        altered = SKIN_PATHS[1]
        write(good / altered, b"altered costume asset")
        before = backups(good)
        run(good)
        new_backup, = backups(good) - before
        check(installed(good) and (new_backup / altered).read_bytes() == b"altered costume asset", "altered asset repaired with exact old bytes backed up")
        check((good / "cream_api.ini").read_bytes() == cfg, "reinstallation does not duplicate or rewrite registration")

        print("\nOFF, saved choice and re-enable", flush=True)
        sentinels = {"DLC/990015/user-file.txt": b"keep alongside skins", "DLC/12345/keep.bin": b"other DLC"}
        for path, content in sentinels.items():
            write(good / path, content)
        data_zip.rename(data_zip.with_suffix(".away"))
        clear_cache()
        run(good, "ps4skins=0")
        check(not any((good / path).exists() for path in (*SKIN_PATHS, GUIDE)), "OFF removes only the four managed assets and guide without a data download")
        check((good / "cream_api.ini").read_bytes() == cfg and all((good / p).read_bytes() == b for p, b in sentinels.items()), "OFF preserves loader config and all unrelated DLC files")
        run(good)
        check(not (good / SKIN_PATHS[0]).exists(), "OFF choice remembered on following update")
        data_zip.with_suffix(".away").rename(data_zip)
        run(good, "ps4skins=1")
        check(installed(good), "explicit re-enable downloads and restores skins")

        print("\nUnsupported loader and custom registration", flush=True)
        unsupported = game("unsupported", compatible=False)
        failed_unchanged(unsupported)
        data_zip.rename(data_zip.with_suffix(".away"))
        clear_cache()
        run(unsupported)
        check(not any((unsupported / path).exists() for path in (*SKIN_PATHS, "cream_api.ini", "steam_api.dll")), "unsupported default installs core with skins OFF and creates no loader/config")
        data_zip.with_suffix(".away").rename(data_zip)
        custom_cfg = CONFIG.replace(b"[dlc]\r\n", b"[dlc]\r\n990015=My personal label\r\n")
        custom = game("custom-registration", config=custom_cfg)
        run(custom)
        check(installed(custom) and (custom / "cream_api.ini").read_bytes() == custom_cfg, "existing 990015 registration keeps its label and every config byte")

        restore_game = game("restore")
        run(restore_game)
        restore_backup, = backups(restore_game)
        check("ps4skins-config|cream_api.ini" in (restore_backup / "backup-manifest.txt").read_text(encoding="utf-8-sig"), "configuration change has its explicit restore marker")
        subprocess.run([str(probe), "restore", str(restore_game), str(restore_backup)], check=True, env=env)
        check((restore_game / "cream_api.ini").read_bytes() == CONFIG and
              not any((restore_game / path).exists() for path in SKIN_PATHS), "restore recovers exact original config and removes newly installed skins")
        check((restore_game / "steam_api.dll").read_bytes() == pe(True) and
              (restore_game / "steam_api_original.dll").read_bytes() == pe(), "restore leaves both existing loader DLLs intact")

        print("\nCorrupt and unexpected data archives", flush=True)
        missing = game("corrupt")
        corrupted = bytearray(data_bytes)
        corrupted[len(corrupted) // 2] ^= 0xFF
        data_zip.write_bytes(corrupted)
        clear_cache()
        log = failed_unchanged(missing)
        check("SHA256 mismatch" in log, "corrupt optional archive rejected by outer hash before game writes")
        bad_bytes = archive(data_zip, {**SKINS, "DLC/990015/unexpected.bin": b"unexpected"})
        bad_manifest = manifest("extra-entry", skin_bytes=bad_bytes)
        clear_cache()
        failed_unchanged(missing, bad_manifest)
        bad_assets = dict(SKINS)
        bad_assets[SKIN_PATHS[0]] = b"same archive accepted hash; individual file differs"
        bad_bytes = archive(data_zip, bad_assets)
        bad_manifest = manifest("wrong-inner-hash", skin_bytes=bad_bytes)
        clear_cache()
        failed_unchanged(missing, bad_manifest)
        data_zip.write_bytes(data_bytes)

        print("\nForbidden DLC archive and widened component", flush=True)
        hostile_bytes = archive(full_zip, {**CORE, **SKINS, "DLC/12345/forbidden.bin": b"never install"})
        hostile_manifest = root / "forbidden-full.txt"
        hostile_manifest.write_text("\n".join(["version=0.3.15", "url=" + str(full_zip),
                                              "sha256=" + sha(hostile_bytes), "size=" + str(len(hostile_bytes)), OPTIONAL]) + "\n")
        clear_cache()
        failed_unchanged(missing, hostile_manifest)
        widened = root / "widened.txt"
        widened.write_text(version.read_text().replace("DLC\\990015\\990015.bcm;", "DLC\\*;"))
        failed_unchanged(missing, widened)
        full_zip.unlink()

        print("\nMaps and costumes together", flush=True)
        maps_option = subprocess.check_output([str(probe), "maps"], env=env, text=True).strip()
        maps = {"CodexCrimson/CRIMSON1.TMC": b"synthetic stage data"}
        maps_zip = pack / "maps.zip"
        maps_bytes = archive(maps_zip, maps)
        combined_core = dict(CORE)
        combined_core["DOA5LR-Diagnostic/maps-files.json"] = inventory(maps)
        for name in ("Crimson", "DangerZone", "ExtraStages", "RandomStages"):
            combined_core["scripts/DOA5LR-" + name + ".asi"] = name.encode()
        combined_bytes = archive(core_zip, combined_core)
        combined_manifest = manifest("maps-and-skins", core_content=combined_bytes,
                                     extra=[maps_option, "data=maps|%s|%s|%d" % (maps_zip, sha(maps_bytes), len(maps_bytes))])
        combined = game("combined")
        clear_cache()
        run(combined, use=combined_manifest)
        check(installed(combined) and all((combined / path).read_bytes() == content for path, content in maps.items()), "maps and skins data merge and install together")
        maps_zip.rename(maps_zip.with_suffix(".away"))
        data_zip.rename(data_zip.with_suffix(".away"))
        clear_cache()
        run(combined, use=combined_manifest)
        check(installed(combined), "both intact optional datasets update with only core available")
        check(not list((scratch / "DOA5LR-Salons").glob("*-merged.zip")), "successful installs leave no temporary merged ZIP")
        probe_game = game("ui-probe")
        subprocess.run([str(probe), str(version), str(probe_game)], check=True, env=env)
        print("ALL PS4 SKINS TESTS PASSED", flush=True)


if __name__ == "__main__":
    main()
