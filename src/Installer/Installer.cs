// DOA5LR-Salons Installer / Updater — single-file WinForms app, .NET Framework 4.8 (built with the csc.exe shipped in Windows).
// Community Mod Pack by FGCsnow & BonuStage. Original Auto Installer concept by BRG Hades.
//
// What it does:
//   - finds the DOA5LR game folder (Steam libraries), reads DOA5LR-Salons-VERSION.txt
//   - fetches version.txt (Cfg.VersionUrl), compares, shows notes, one-click INSTALL / UPDATE
//   - downloads the release zip, checks SHA256, waits for the game to be closed, backs up every file it
//     replaces or deletes, extracts (sub-folders included), applies the delete= list, keeps the user's .ini
//   - Restore backup, self-update (installer= line), --update mode (launched by DOA5LR-Telemetry at game exit)
//   - 1.2.0 : LAUNCH GAME button - starts DOA5LR through Steam (steam://rungameid), opens Steam first if it is not running
//             --play = explicit launcher mode: checks for updates, then opens input selection when InputLab is installed
//   - desktop shortcut opens the installer and configuration; the player chooses when to launch
//   - never writes steam_api / cream / DLC files; diagnostics only write the ZIP explicitly chosen by the user
//
// version.txt format (one key per line, unknown keys ignored — same file DOA5LR-Telemetry 0.3 reads):
//   version=0.3.3
//   url=https://github.com/<user>/DOA5LR-Salons/releases/download/v0.3.3/DOA5LR-Salons-0.3.3.zip
//   sha256=<sha256 of the zip>          size=<bytes>
//   notes=one-line summary (Telemetry shows this one)      note=detail line (0..n, installer shows these)
//   delete=relative\path                (0..n, files removed by this version — cumulative)
//   move=old\path|new\path              (0..n, migrations: e.g. root .ini -> scripts\ ; the user file is moved before extraction)
//   keep=*.ini                          (0..n, existing files never overwritten on update; default *.ini)
//   installer=https://.../DOA5LR-Salons-Installer.exe   installer_version=1.0.0   installer_sha256=<sha>
//   optional=id|label|glob;glob...     (0..n, 1.1.0: a component the player may leave out — its files are not extracted and are
//                                       removed if present; choice saved in DOA5LR-Salons-Components.txt and reused by --update)
//   optional_v2=id|label|glob;glob...  (1.3.1: same validation; older installers ignore this key and can self-update first)
//   file=name|url|fnv32|size            (for Telemetry AutoUpdate, ignored here)
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

// Version resource (VERSIONINFO) — an .exe with no company/description/version is a classic antivirus heuristic trigger.
[assembly: System.Reflection.AssemblyTitle("DOA5LR-Salons Installer")]
[assembly: System.Reflection.AssemblyDescription("Installer / updater for the DOA5LR-Salons community mod pack (Dead or Alive 5 Last Round lobbies)")]
[assembly: System.Reflection.AssemblyCompany("FGCsnow & BonuStage")]
[assembly: System.Reflection.AssemblyProduct("DOA5LR-Salons")]
[assembly: System.Reflection.AssemblyCopyright("Copyright (c) 2026 FGCsnow & BonuStage - github.com/FgcSnow/DOA5LR-Salons")]
[assembly: System.Reflection.AssemblyVersion("1.3.1.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.3.1.0")]
[assembly: System.Reflection.AssemblyInformationalVersion("1.3.1")]

static class Cfg
{
    public const string AppVersion = "1.3.1";
    public const string PackName = "DOA5LR-Salons";
    // Stable URL of version.txt (branch main of the GitHub repo). Set once, never changes.
    public const string OfficialVersionUrl = "https://raw.githubusercontent.com/FgcSnow/DOA5LR-Salons/main/version.txt";
    public static string VersionUrl = OfficialVersionUrl;   // --manifest <file|url> overrides (testing only)
    public static bool AllowLocalPack;   // only an explicit --manifest <local file> may name a local ZIP
    public const string ProjectUrl = "https://github.com/FgcSnow/DOA5LR-Salons";
    public const string VersionFile = "DOA5LR-Salons-VERSION.txt";
    public const string BackupDir = "DOA5LR-Salons-Backups";
    public const string ExeName = "DOA5LR-Salons-Installer.exe";
    public const string LogName = "DOA5LR-Salons-Installer.log";
    public const string GameExe = "game.exe";
    public const string GameFolderName = "Dead or Alive 5 Last Round";
    public const int SteamAppId = 311730;
    public const string TelemetryIni = "DOA5LR-Telemetry.ini";
    public const string UpdateCheckIni = "DOA5LR-UpdateCheck.ini";
    public const string BorderlessIni = "DOA5LR-Borderless.ini";
    public const string ComponentsFile = "DOA5LR-Salons-Components.txt";   // 1.1.0 : optional components chosen by the player
    // The original Xidi frontend shipped in the base pack. InputLab may replace the active frontend only
    // when both archive copies match this known release binary.
    public const string InputLabXidiSha256 = "7f2a1c7616515153d899b726c8ecf72d5fa81c27a9d14b5c394cdd2e09f325c5";
    public const string PatreonUrl = "https://www.patreon.com/cw/DoA5LRcommunitymod";   // empty = button hidden
    // 1.0.3 : files the pack cannot work without. Checked at every start and after every install: an antivirus can
    // quarantine one of them silently (a game plugin patches the game in memory, heuristics dislike that).
    public static readonly string[] InputLabRuntimeFiles = {
        "DOA5LR-InputBridge-Xidi.dll", "DOA5LR-InputBridge.ini", "DOA5LR-ControllerProfiles.ini", "DOA5LR-Companion.exe" };
    // Settings/detection stay available even when the experimental in-game runtime is OFF.
    public static readonly string[] InputLabAppFiles = {
        @"InputLab\payload\dinput8ex.bin", @"InputLab\DOA5LR-Commandes.exe", @"InputLab\DOA5LR-Companion.exe", @"InputLab\DOA5LR-Peripheriques.exe", @"InputLab\DOA5LR-Detecteur.exe",
        @"InputLab\DOA5LR-ControllerProfiles.ini", @"InputLab\Profil-clavier.ini" };
    public static readonly string[] InputLabFiles = InputLabRuntimeFiles.Concat(InputLabAppFiles).ToArray();
    public static readonly string[] RequiredFiles = {
        "dinput8.dll", "dinput8Hooked.dll", "DInput8.ini", "dinput8ex.bin", "Xidi.32.dll",
        @"scripts\DOA5LR-Lobby.asi", @"scripts\DOA5LR-InviteFix.asi", @"scripts\DOA5LR-Borderless.asi",
        @"scripts\DOA5LR-60fps-menus.asi", @"scripts\DOA5LR-WiFi-Wired-Detector.asi", @"scripts\DOA5LR-UpdateCheck.asi" };
    // Files the pack must never contain / the installer must never write (same rule as build_pack.py).
    public static readonly Regex Forbidden = new Regex(@"steam_api|cream|unlock|(^|[\\/])DLC", RegexOptions.IgnoreCase);
}

// ---------------------------------------------------------------- optional components (1.1.0)
// A component the player may leave out. Everything else in the pack is always installed — on purpose the wired/Wi-Fi tag
// (DOA5LR-WiFi-Wired-Detector) is NOT optional: the indicator is only worth something if no player can leave it out.
// The list comes from version.txt (optional= lines), but each ID and path glob must be in Known; Defaults is the
// legacy fallback for a manifest without them. A .ini of a component left out is kept; its other files are removed.
class Component
{
    public string Id, Label; public string[] Globs;
    public bool Owns(string rel) { return Globs.Any(g => Util.PathGlob(g, rel)); }
    public static readonly Component[] Defaults = {
        new Component { Id = "borderless", Label = "Borderless fullscreen window (F11 in game; display mode below)", Globs = new[] { @"scripts\DOA5LR-Borderless.asi", @"scripts\DOA5LR-Borderless.ini", @"scripts\BORDERLESS-EN.txt", @"scripts\Borderless-Source\*" } },
        new Component { Id = "60fps", Label = "60 fps menus, intros, win poses and Story cutscenes (offline only)", Globs = new[] { @"scripts\DOA5LR-60fps-menus.asi", @"scripts\DOA5LR-60fps-menus.ini", @"scripts\60FPS-EN.txt", @"scripts\60fps-Source\*" } } };
    public static readonly Component InputLab = new Component { Id = "inputlab", Label = "Experimental in-game keyboard remapping (settings app always available)", Globs = new[] { "DOA5LR-InputBridge-Xidi.dll", "DOA5LR-InputBridge.ini", "DOA5LR-ControllerProfiles.ini", "DOA5LR-Companion.exe" } };
    public static readonly Component[] Known = Defaults.Concat(new[] { InputLab }).ToArray();
    public static Component[] Current = Defaults;   // replaced by the manifest's optional= lines when it has some
    public static Component Parse(string v)
    {
        var p = v.Split('|'); if (p.Length != 3) return null;
        var c = new Component { Id = p[0].Trim().ToLowerInvariant(), Label = p[1].Trim(), Globs = p[2].Split(';').Select(g => g.Trim().Replace('/', '\\')).Where(g => g.Length > 0 && !g.Contains("..")).ToArray() };
        var known = Known.FirstOrDefault(item => item.Id == c.Id);
        if (known == null || !c.Globs.SequenceEqual(known.Globs, StringComparer.OrdinalIgnoreCase))
            throw new InvalidDataException("Refused: unsupported optional component: " + c.Id);
        return known;
    }
    // choice file in the game folder: one "id=0|1" per line. InputLab is opt-in.
    public static Dictionary<string, bool> Read(string game)
    {
        var d = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
        d["borderless"] = game != "" && (Util.InstalledVersion(game) != "" || File.Exists(Path.Combine(game, @"scripts\DOA5LR-Borderless.asi")) || File.Exists(Path.Combine(game, "DOA5LR-Borderless.asi")));
        d["inputlab"] = false;
        try { if (game != "") foreach (var ln in File.ReadAllLines(Path.Combine(game, Cfg.ComponentsFile))) { var i = ln.IndexOf('='); if (i > 0 && ln[0] != '#') d[ln.Substring(0, i).Trim()] = ln.Substring(i + 1).Trim() != "0"; } } catch { }
        return d;
    }
    public static bool Selected(Dictionary<string, bool> sel, string id) { bool b; return sel == null || !sel.TryGetValue(id, out b) || b; }
    public static void Write(string game, Dictionary<string, bool> sel)
    {
        File.WriteAllLines(Path.Combine(game, Cfg.ComponentsFile), new[] { "# " + Cfg.PackName + " optional components chosen in the installer (0 = left out). Everything else is always installed." }
            .Concat(Current.Select(c => c.Id + "=" + (Selected(sel, c.Id) ? "1" : "0"))));
    }
    public static List<Component> LeftOut(Dictionary<string, bool> sel) { return Current.Where(c => !Selected(sel, c.Id)).ToList(); }
    public static string Summary(Dictionary<string, bool> sel) { var o = LeftOut(sel); return o.Count == 0 ? "all components" : "left out: " + string.Join(", ", o.Select(c => c.Id)); }
}

// ---------------------------------------------------------------- manifest (version.txt)
class Manifest
{
    public string Version = "", Url = "", Sha256 = "", Notes = "", InstallerUrl = "", InstallerVersion = "", InstallerSha256 = "";
    public long Size;
    public List<string> NoteLines = new List<string>(), Delete = new List<string>(), Keep = new List<string>();
    public List<KeyValuePair<string, string>> Move = new List<KeyValuePair<string, string>>();
    public List<Component> Optional = new List<Component>();   // 1.1.0
    public static Manifest Parse(string text)
    {
        var m = new Manifest();
        foreach (var raw in text.Replace("\r", "").Split('\n'))
        {
            var ln = raw.Trim(); if (ln.Length == 0 || ln[0] == '#') continue;
            int i = ln.IndexOf('='); if (i <= 0) continue;
            string k = ln.Substring(0, i).Trim().ToLowerInvariant(), v = ln.Substring(i + 1).Trim();
            switch (k)
            {
                case "version": m.Version = v; break;
                case "url": m.Url = v; break;
                case "sha256": m.Sha256 = v.ToLowerInvariant(); break;
                case "size": long.TryParse(v, out m.Size); break;
                case "notes": m.Notes = v; break;
                case "note": m.NoteLines.Add(v); break;
                case "delete": if (v.Length > 0) m.Delete.Add(v.Replace('/', '\\')); break;
                case "keep": if (v.Length > 0) m.Keep.Add(v); break;
                case "move": { var mv = v.Split('|'); if (mv.Length == 2 && mv[0].Length > 0 && mv[1].Length > 0) m.Move.Add(new KeyValuePair<string, string>(mv[0].Trim().Replace('/', '\\'), mv[1].Trim().Replace('/', '\\'))); break; }
                case "installer": m.InstallerUrl = v; break;
                case "installer_version": m.InstallerVersion = v; break;
                case "installer_sha256": m.InstallerSha256 = v.ToLowerInvariant(); break;
                // Keep the old key for preview manifests. Public manifests use optional_v2
                // for InputLab so 1.1 can parse them before offering its own update.
                case "optional":
                case "optional_v2": { var c = Component.Parse(v); if (c != null && !m.Optional.Any(x => x.Id == c.Id)) m.Optional.Add(c); break; }
            }
        }
        if (m.Keep.Count == 0) m.Keep.Add("*.ini");
        Component.Current = m.Optional.Count > 0 ? m.Optional.ToArray() : Component.Defaults;
        return m;
    }
}

static class Util
{
    public static string LogPath = Path.Combine(Path.GetTempPath(), Cfg.LogName);
    public static void Log(string s)
    {
        try { File.AppendAllText(LogPath, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + s + "\r\n"); } catch { }
    }
    public static int CmpVer(string a, string b)
    {
        Func<string, int[]> p = s => Regex.Matches(s ?? "", @"\d+").Cast<Match>().Select(x => int.Parse(x.Value)).Concat(new[] { 0, 0, 0, 0 }).Take(4).ToArray();
        int[] va = p(a), vb = p(b);
        for (int i = 0; i < 4; i++) if (va[i] != vb[i]) return va[i].CompareTo(vb[i]);
        return 0;
    }
    public static string Sha256(string path)
    {
        using (var h = SHA256.Create()) using (var f = File.OpenRead(path)) return BitConverter.ToString(h.ComputeHash(f)).Replace("-", "").ToLowerInvariant();
    }
    public static bool Glob(string pattern, string name)
    {
        return Regex.IsMatch(name, "^" + Regex.Escape(pattern).Replace("\\*", ".*").Replace("\\?", ".") + "$", RegexOptions.IgnoreCase);
    }
    // 1.1.0 : glob on a whole relative path (dir\name.ext or dir\*), case-insensitive
    public static bool PathGlob(string pattern, string rel)
    {
        return Regex.IsMatch(rel.Replace('/', '\\'), "^" + Regex.Escape(pattern.Replace('/', '\\')).Replace("\\*", ".*").Replace("\\?", ".") + "$", RegexOptions.IgnoreCase);
    }
    public static string Human(long b) { return b < 1 << 20 ? (b / 1024.0).ToString("0.#") + " KB" : (b / 1048576.0).ToString("0.0") + " MB"; }

    // ---- game folder detection : Steam libraries -> appmanifest_311730.acf -> common\Dead or Alive 5 Last Round
    public static string FindGameFolder()
    {
        var roots = new List<string>();
        try { var v = Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamPath", null) as string; if (!string.IsNullOrEmpty(v)) roots.Add(v.Replace('/', '\\')); } catch { }
        try { var v = Registry.GetValue(@"HKEY_LOCAL_MACHINE\SOFTWARE\Valve\Steam", "InstallPath", null) as string; if (!string.IsNullOrEmpty(v)) roots.Add(v); } catch { }
        try { var v = Registry.GetValue(@"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath", null) as string; if (!string.IsNullOrEmpty(v)) roots.Add(v); } catch { }
        var libs = new List<string>(roots);
        foreach (var r in roots.ToArray())
        {
            var vdf = Path.Combine(r, "steamapps", "libraryfolders.vdf");
            if (!File.Exists(vdf)) continue;
            try
            {
                foreach (Match m in Regex.Matches(File.ReadAllText(vdf), "\"path\"\\s+\"([^\"]+)\""))
                    libs.Add(m.Groups[1].Value.Replace("\\\\", "\\"));
            }
            catch { }
        }
        foreach (var lib in libs.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            var g = Path.Combine(lib, "steamapps", "common", Cfg.GameFolderName);
            if (File.Exists(Path.Combine(g, Cfg.GameExe))) return g;
        }
        // running from inside the game folder (installer shipped in the pack)
        var here = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
        if (File.Exists(Path.Combine(here, Cfg.GameExe))) return here;
        foreach (var d in new[] { @"C:\Program Files (x86)\Steam", @"D:\SteamLibrary", @"D:\Steam", @"E:\SteamLibrary" })
        {
            var g = Path.Combine(d, "steamapps", "common", Cfg.GameFolderName);
            if (File.Exists(Path.Combine(g, Cfg.GameExe))) return g;
        }
        return "";
    }
    // 1.0.3 : required files absent from an installed pack (empty list = all there)
    public static List<string> MissingRequired(string game)
    {
        var miss = new List<string>();
        var selection = Component.Read(game);
        var left = Component.LeftOut(selection);   // 1.1.0 : a component the player left out is not required
        try { foreach (var rel in Cfg.RequiredFiles) if (!left.Any(c => c.Owns(rel)) && !File.Exists(Path.Combine(game, rel))) miss.Add(rel); } catch { }
        if (Component.Current.Any(c => c.Id == "inputlab"))
            try {
                var required = Cfg.InputLabAppFiles.AsEnumerable();
                if (Component.Selected(selection, "inputlab")) required = required.Concat(Cfg.InputLabRuntimeFiles);
                foreach (var rel in required) if (!File.Exists(Path.Combine(game, rel))) miss.Add(rel);
            } catch { }
        return miss;
    }
    public static string MissingMessage(List<string> miss)
    {
        return "These required files are MISSING from the game folder:\r\n\r\n    " + string.Join("\r\n    ", miss) +
               "\r\n\r\nThe pack needs every one of them. With files missing, the LOBBY entry, Steam invites, the controller fix, " +
               "borderless or the 60 fps menus may be absent or misbehave, and online matches can fail. Do not play with a partial pack." +
               "\r\n\r\nThe usual cause is your antivirus quarantining a file (a game plugin patches the game in memory, which looks suspicious to heuristics; " +
               "these are false positives, the sources are public). Open your antivirus' protection history / quarantine, restore the file(s), add the game folder " +
               "to its exclusions, then click REINSTALL (repair) here. If your antivirus keeps deleting them, please report it as a false positive to its vendor.";
    }
    public static string InstalledVersion(string game)
    {
        try { var p = Path.Combine(game, Cfg.VersionFile); if (File.Exists(p)) return File.ReadAllText(p).Trim(); } catch { }
        // pre-0.3.2 packs had no VERSION.txt: detect an old install by its loader
        if (File.Exists(Path.Combine(game, "DOA5LR-Lobby.asi"))) return "old";
        return "";
    }
    public static Process[] GameProcesses(string game)
    {
        var list = new List<Process>();
        foreach (var p in Process.GetProcessesByName(Path.GetFileNameWithoutExtension(Cfg.GameExe)))
        {
            string path = null;
            try { path = p.MainModule.FileName; } catch { }
            if (path == null || string.Equals(Path.GetDirectoryName(path).TrimEnd('\\'), game.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase)) list.Add(p);
        }
        return list.ToArray();
    }
    // ---- 1.2.0 : launch through Steam
    public static string SteamExe()
    {
        try { var v = Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamExe", null) as string; if (!string.IsNullOrEmpty(v) && File.Exists(v.Replace('/', '\\'))) return v.Replace('/', '\\'); } catch { }
        try { var v = Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamPath", null) as string; if (!string.IsNullOrEmpty(v)) { var e = Path.Combine(v.Replace('/', '\\'), "steam.exe"); if (File.Exists(e)) return e; } } catch { }
        return "";
    }
    public static bool SteamRunning() { try { return Process.GetProcessesByName("steam").Length > 0; } catch { return false; } }
    // Steam writes the logged-in account id here once it is ready (0 while starting / logged out)
    public static bool SteamLoggedIn()
    {
        try { var v = Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam\ActiveProcess", "ActiveUser", 0); return v is int && (int)v != 0; } catch { return false; }
    }
    // ---- 1.2.0 : .lnk through the shell's own IShellLink (no WScript.Shell / script host, nothing for an antivirus to frown at)
    [System.Runtime.InteropServices.ComImport, System.Runtime.InteropServices.Guid("00021401-0000-0000-C000-000000000046")] class ShellLinkCo { }
    [System.Runtime.InteropServices.ComImport, System.Runtime.InteropServices.InterfaceType(System.Runtime.InteropServices.ComInterfaceType.InterfaceIsIUnknown), System.Runtime.InteropServices.Guid("000214F9-0000-0000-C000-000000000046")]
    interface IShellLinkW
    {
        void GetPath(IntPtr a, int b, IntPtr c, int d); void GetIDList(out IntPtr a); void SetIDList(IntPtr a);
        void GetDescription(IntPtr a, int b); void SetDescription([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string a);
        void GetWorkingDirectory(IntPtr a, int b); void SetWorkingDirectory([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string a);
        void GetArguments(IntPtr a, int b); void SetArguments([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string a);
        void GetHotkey(out short a); void SetHotkey(short a); void GetShowCmd(out int a); void SetShowCmd(int a);
        void GetIconLocation(IntPtr a, int b, out int c); void SetIconLocation([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string a, int b);
        void SetRelativePath([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string a, int b);
        void Resolve(IntPtr a, int b); void SetPath([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string a);
    }
    public static void CreateShortcut(string lnk, string target, string args, string workDir, string icon, string desc)
    {
        var sl = (IShellLinkW)new ShellLinkCo();
        sl.SetPath(target); sl.SetArguments(args); sl.SetWorkingDirectory(workDir); sl.SetIconLocation(icon, 0); sl.SetDescription(desc);
        ((System.Runtime.InteropServices.ComTypes.IPersistFile)sl).Save(lnk, true);
        System.Runtime.InteropServices.Marshal.ReleaseComObject(sl);
    }
    public static void SteamRunGame() { Process.Start(new ProcessStartInfo("steam://rungameid/" + Cfg.SteamAppId) { UseShellExecute = true }); }
    // ---- display mode (Borderless 1.1) : 2 = borderless, 1 = window, 0 = fullscreen (game setting)
    public static string BorderlessIniPath(string game)
    {
        foreach (var sub in new[] { "scripts", "plugins", "" }) { var p = Path.Combine(game, sub, Cfg.BorderlessIni); if (File.Exists(p)) return p; }
        return null;
    }
    public static int ReadDisplayMode(string game)
    {
        var p = BorderlessIniPath(game); if (p == null) return -1;
        try { var m = Regex.Match(File.ReadAllText(p), @"^Mode=(\d)", RegexOptions.Multiline); return m.Success ? int.Parse(m.Groups[1].Value) : 2; } catch { return -1; }
    }
    public static string GameIniPath()
    {
        try { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KoeiTecmo", "DOA5LR", "DOA5LR.ini"); } catch { return null; }
    }
    public static void WriteDisplayMode(string game, int mode)
    {
        var p = BorderlessIniPath(game); if (p == null) return;
        var txt = File.ReadAllText(p);
        txt = Regex.IsMatch(txt, @"^Mode=\d", RegexOptions.Multiline) ? Regex.Replace(txt, @"^Mode=\d", "Mode=" + mode, RegexOptions.Multiline) : txt.TrimEnd() + "\r\nMode=" + mode + "\r\n";
        File.WriteAllText(p, txt, new UTF8Encoding(false));
        var gi = GameIniPath();
        if (gi != null && File.Exists(gi))
        {
            var raw = File.ReadAllBytes(gi); bool wide = raw.Length >= 2 && raw[0] == 0xFF && raw[1] == 0xFE;
            var enc = wide ? (Encoding)new UnicodeEncoding(false, true) : Encoding.Default;
            var g = wide ? Encoding.Unicode.GetString(raw, 2, raw.Length - 2) : Encoding.Default.GetString(raw);
            var want = mode == 0 ? "FULLSCREEN" : "WINDOW";
            if (Regex.IsMatch(g, @"^SCREEN_TYPE=", RegexOptions.Multiline)) { g = Regex.Replace(g, @"^SCREEN_TYPE=[^\r\n]*", "SCREEN_TYPE=" + want, RegexOptions.Multiline); File.WriteAllText(gi, g, enc); }
        }
        Log("display mode set to " + mode + " (" + (mode == 2 ? "borderless" : mode == 1 ? "window" : "fullscreen") + ")");
    }
    public static bool CanWrite(string dir)
    {
        try { var t = Path.Combine(dir, ".doa5lr-write-test-" + Guid.NewGuid().ToString("N")); File.WriteAllBytes(t, new byte[1]); File.Delete(t); return true; } catch { return false; }
    }
    public static void SetupTls()
    {
        try { ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12 | (SecurityProtocolType)12288; }
        catch { try { ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12; } catch { } }
    }
    static bool IsLocal(string u) { return !u.StartsWith("http", StringComparison.OrdinalIgnoreCase); }
    public static string HttpGetText(string url)
    {
        if (IsLocal(url)) return File.ReadAllText(url, Encoding.UTF8);
        using (var wc = new WebClient()) { wc.Headers[HttpRequestHeader.UserAgent] = Cfg.PackName + "-Installer/" + Cfg.AppVersion; wc.Headers[HttpRequestHeader.CacheControl] = "no-cache"; wc.Encoding = Encoding.UTF8; return wc.DownloadString(url + (url.Contains("?") ? "&" : "?") + "t=" + DateTime.UtcNow.Ticks); }
    }
    public static void Download(string url, string dest, Action<long, long> progress)
    {
        if (IsLocal(url)) { File.Copy(url, dest, true); progress(new FileInfo(dest).Length, new FileInfo(dest).Length); return; }
        var req = (HttpWebRequest)WebRequest.Create(url);
        req.UserAgent = Cfg.PackName + "-Installer/" + Cfg.AppVersion; req.AllowAutoRedirect = true; req.Timeout = 60000;
        using (var resp = (HttpWebResponse)req.GetResponse()) using (var s = resp.GetResponseStream()) using (var f = File.Create(dest))
        {
            long total = resp.ContentLength, done = 0; var buf = new byte[1 << 16]; int n; var last = DateTime.MinValue;
            while ((n = s.Read(buf, 0, buf.Length)) > 0)
            {
                f.Write(buf, 0, n); done += n;
                if ((DateTime.Now - last).TotalMilliseconds > 100) { last = DateTime.Now; progress(done, total); }
            }
            progress(done, total);
        }
    }
}

// Preserve only the two settings InputLab owns. Other user edits in these INIs survive enable/disable.
static class InputLabSettings
{
    public const string SnapshotRel = @"InputLab\previous-settings.txt";
    const string Missing = "-";
    const string Header = "DOA5LR-InputLab-Settings-v1";
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern uint GetPrivateProfileString(string section, string key, string fallback, StringBuilder value, uint size, string path);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool WritePrivateProfileString(string section, string key, string value, string path);

    static string ReadKey(string path, string section, string key)
    {
        if (!File.Exists(path)) return null;
        var sentinel = "__DOA5LR_INPUTLAB_MISSING__";
        var value = new StringBuilder(512);
        GetPrivateProfileString(section, key, sentinel, value, (uint)value.Capacity, path);
        return value.ToString() == sentinel ? null : value.ToString();
    }
    static void WriteKey(string path, string section, string key, string value)
    {
        if (value == null && !File.Exists(path)) return;
        if (!WritePrivateProfileString(section, key, value, path))
            throw new IOException("Could not update " + Path.GetFileName(path) + " (" + new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error()).Message + ").");
        if (ReadKey(path, section, key) != value) throw new IOException("Could not verify " + key + " in " + Path.GetFileName(path) + ".");
    }
    static string Encode(string value) { return value == null ? Missing : Convert.ToBase64String(Encoding.UTF8.GetBytes(value)); }
    static string Decode(string value) { return value == Missing ? null : Encoding.UTF8.GetString(Convert.FromBase64String(value)); }
    static Dictionary<string, string> ReadSnapshot(string path)
    {
        var lines = File.ReadAllLines(path);
        if (lines.Length < 4 || lines[0] != Header) throw new InvalidDataException("InputLab settings backup is invalid: " + path);
        var d = lines.Skip(1).Select(s => s.Split(new[] { '=' }, 2)).Where(p => p.Length == 2).ToDictionary(p => p[0], p => p[1], StringComparer.Ordinal);
        foreach (var key in new[] { "KeyboardOnly", "XidiFileExisted", "ActiveVirtualControllerMask" })
            if (!d.ContainsKey(key)) throw new InvalidDataException("InputLab settings backup lacks " + key + ".");
        if (d["XidiFileExisted"] != "0" && d["XidiFileExisted"] != "1") throw new InvalidDataException("InputLab settings backup has an invalid Xidi state.");
        Decode(d["KeyboardOnly"]); Decode(d["ActiveVirtualControllerMask"]);
        return d;
    }
    public static void VerifyExisting(string game)
    {
        var path = Path.Combine(game, SnapshotRel);
        if (!File.Exists(path)) throw new InvalidDataException("InputLab's previous input settings are missing. Restore a backup before disabling InputLab.");
        ReadSnapshot(path);
    }
    public static void Activate(string game)
    {
        var dinput = Path.Combine(game, "DInput8.ini");
        var xidi = Path.Combine(game, "Xidi.ini");
        var snapshot = Path.Combine(game, SnapshotRel);
        if (!File.Exists(dinput)) throw new FileNotFoundException("InputLab requires DInput8.ini", dinput);
        if (File.Exists(snapshot)) ReadSnapshot(snapshot); // retain the original values across later updates
        else
        {
            Directory.CreateDirectory(Path.GetDirectoryName(snapshot));
            File.WriteAllLines(snapshot, new[] { Header,
                "KeyboardOnly=" + Encode(ReadKey(dinput, "PATCH", "KeyboardOnly")),
                "XidiFileExisted=" + (File.Exists(xidi) ? "1" : "0"),
                "ActiveVirtualControllerMask=" + Encode(ReadKey(xidi, "Workarounds", "ActiveVirtualControllerMask")) });
        }
        // Repair/update must honor the mode the controls app already applied.
        // The INI is preserved by keep=*.ini; forcing Hybrid here breaks native
        // controller input while leaving Mode=Controller displayed in the app.
        string mode = ReadKey(Path.Combine(game, "DOA5LR-InputBridge.ini"), "Input", "Mode");
        bool keyboard = string.Equals(mode, "Keyboard", StringComparison.OrdinalIgnoreCase);
        bool controller = string.Equals(mode, "Controller", StringComparison.OrdinalIgnoreCase);
        WriteKey(dinput, "PATCH", "KeyboardOnly", keyboard || controller ? "0" : "1");
        WriteKey(xidi, "Workarounds", "ActiveVirtualControllerMask", controller ? "15" : "0");
    }
    public static bool Deactivate(string game)
    {
        var snapshot = Path.Combine(game, SnapshotRel);
        if (!File.Exists(snapshot)) return false;
        var d = ReadSnapshot(snapshot);
        var dinput = Path.Combine(game, "DInput8.ini");
        var xidi = Path.Combine(game, "Xidi.ini");
        WriteKey(dinput, "PATCH", "KeyboardOnly", Decode(d["KeyboardOnly"]));
        WriteKey(xidi, "Workarounds", "ActiveVirtualControllerMask", Decode(d["ActiveVirtualControllerMask"]));
        if (d["XidiFileExisted"] == "0" && File.Exists(xidi))
        {
            var meaningful = File.ReadAllLines(xidi).Any(ln => { var s = ln.Trim(); return s != "" && !s.StartsWith(";") && !s.StartsWith("#") && !s.StartsWith("["); });
            if (!meaningful) File.Delete(xidi);
        }
        File.Delete(snapshot); // runtime ownership ends here; the core InputLab folder remains installed
        return true;
    }
}

// ---------------------------------------------------------------- install / restore engine
class Engine
{
    public string Game;
    public Action<string> Status = s => { };
    public Action<int> Progress = p => { };
    public Func<string, string, bool> Confirm = (t, m) => true; // (title, message) -> yes/no ; called on the UI thread by the form
    public bool FreshInstall;
    public string BackupFolder;
    public bool SelfReplaced;
    readonly StringBuilder report = new StringBuilder();
    public string Report { get { return report.ToString(); } }

    static ZipArchiveEntry ExactlyOneEntry(List<ZipArchiveEntry> entries, string rel)
    {
        var matches = entries.Where(e => e.FullName.Replace('/', '\\').Equals(rel, StringComparison.OrdinalIgnoreCase)).ToList();
        if (matches.Count != 1) throw new InvalidDataException("InputLab requires exactly one " + rel + " in the archive.");
        return matches[0];
    }
    static string ArchiveSha256(ZipArchiveEntry entry)
    {
        using (var h = SHA256.Create()) using (var s = entry.Open()) return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
    }
    static string ValidateInputLabArchive(List<ZipArchiveEntry> entries)
    {
        foreach (var rel in Cfg.InputLabFiles) ExactlyOneEntry(entries, rel);
        var original = ExactlyOneEntry(entries, "dinput8ex.bin");
        var preserved = ExactlyOneEntry(entries, "DOA5LR-InputBridge-Xidi.dll");
        var bridge = ExactlyOneEntry(entries, @"InputLab\payload\dinput8ex.bin");
        var originalHash = ArchiveSha256(original);
        if (originalHash != Cfg.InputLabXidiSha256 || ArchiveSha256(preserved) != originalHash)
            throw new InvalidDataException("InputLab requires the original Xidi frontend in both dinput8ex.bin and DOA5LR-InputBridge-Xidi.dll; archive differs from the expected release.");
        var bridgeHash = ArchiveSha256(bridge);
        if (bridge.Length == 0 || bridgeHash == originalHash)
            throw new InvalidDataException("InputLab bridge payload is empty or duplicates Xidi.");
        return bridgeHash;
    }
    static bool ContainsUnicodeMarker(string path, string marker)
    {
        var bytes = File.ReadAllBytes(path);
        var pattern = Encoding.Unicode.GetBytes(marker);
        for (int i = 0; i <= bytes.Length - pattern.Length; i++)
        {
            int j = 0;
            while (j < pattern.Length && bytes[i + j] == pattern[j]) j++;
            if (j == pattern.Length) return true;
        }
        return false;
    }
    static bool LegacyStandaloneInputLab(string game)
    {
        var active = Path.Combine(game, "dinput8ex.bin");
        var preserved = Path.Combine(game, "DOA5LR-InputBridge-Xidi.dll");
        var config = Path.Combine(game, "DOA5LR-InputBridge.ini");
        if (File.Exists(Path.Combine(game, InputLabSettings.SnapshotRel)) || !File.Exists(active) || !File.Exists(preserved) || !File.Exists(config)) return false;
        return Util.Sha256(preserved) == Cfg.InputLabXidiSha256 &&
               Util.Sha256(active) != Cfg.InputLabXidiSha256 &&
               ContainsUnicodeMarker(active, "DOA5LR-InputBridge-Xidi.dll");
    }

    string Abs(string rel) { return Path.GetFullPath(Path.Combine(Game, rel)); }
    bool Inside(string abs) { return abs.StartsWith(Path.GetFullPath(Game).TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase); }
    void Line(string s) { report.AppendLine(s); Util.Log(s); }

    public int GraceSeconds;   // --update : the game is exiting, give it time before nagging
    public void WaitGameClosed()
    {
        for (int i = 0; i < GraceSeconds * 2 && Util.GameProcesses(Game).Length > 0; i++) { Status("Waiting for the game to close..."); Thread.Sleep(500); }
        while (Util.GameProcesses(Game).Length > 0)
        {
            Status("DOA5LR is running — close the game to continue.");
            if (!Confirm("Close the game", "Dead or Alive 5 Last Round is still running.\r\n\r\nClose the game, then click OK to continue (Cancel to abort).")) throw new OperationCanceledException("Cancelled: game still running.");
        }
    }

    public string DownloadPack(Manifest m)
    {
        bool local = !m.Url.StartsWith("http", StringComparison.OrdinalIgnoreCase);
        string source = m.Url;
        // An explicitly selected local manifest may use a sibling ZIP filename,
        // so a test bundle can be moved without baking in one player's PC path.
        if (local && Cfg.AllowLocalPack && !Path.IsPathRooted(source) &&
            source == Path.GetFileName(source) && !source.Contains(":"))
            source = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(Cfg.VersionUrl)), source);
        if (local && (!Cfg.AllowLocalPack || !Path.IsPathRooted(source) || !File.Exists(source) || m.Sha256.Length != 64 || m.Size <= 0))
            throw new InvalidDataException("Local packs require --manifest <local file>, an absolute ZIP path or sibling ZIP filename, SHA256 and size.");
        var dir = Path.Combine(Path.GetTempPath(), Cfg.PackName); Directory.CreateDirectory(dir);
        var zip = Path.Combine(dir, Cfg.PackName + "-" + m.Version + ".zip");
        if (File.Exists(zip) && m.Sha256.Length == 64 && Util.Sha256(zip) == m.Sha256) { Line("using cached download " + zip); return zip; }
        Status("Downloading " + Cfg.PackName + " " + m.Version + "...");
        Util.Download(source, zip + ".part", (d, t) => { if (t > 0) Progress((int)(d * 100 / t)); Status("Downloading " + Cfg.PackName + " " + m.Version + "  " + Util.Human(d) + (t > 0 ? " / " + Util.Human(t) : "")); });
        if (File.Exists(zip)) File.Delete(zip);
        File.Move(zip + ".part", zip);
        if (m.Size > 0 && new FileInfo(zip).Length != m.Size) throw new Exception("Download size mismatch (" + new FileInfo(zip).Length + " vs " + m.Size + " bytes). Try again.");
        if (m.Sha256.Length == 64) { Status("Checking file integrity..."); var h = Util.Sha256(zip); if (h != m.Sha256) { File.Delete(zip); throw new Exception("SHA256 mismatch: the download is corrupted or tampered. Aborted, nothing was changed."); } Line("sha256 OK " + h); }
        else Line("WARNING: no sha256 in version.txt, integrity not verified");
        return zip;
    }

    // Install (fresh or update) from a local zip; returns the backup folder.
    public void InstallZip(string zip, Manifest m) { InstallZip(zip, m, null); }
    public void InstallZip(string zip, Manifest m, Dictionary<string, bool> sel)
    {
        Game = Path.GetFullPath(Game);
        if (!File.Exists(Path.Combine(Game, Cfg.GameExe))) throw new Exception("game.exe not found in " + Game);
        var prev = Util.InstalledVersion(Game);
        FreshInstall = prev == "";
        Line((FreshInstall ? "INSTALL " : "UPDATE " + prev + " -> ") + (m != null ? m.Version : "?") + " from " + zip + " into " + Game);
        WaitGameClosed();
        // A standalone prototype predating this installer changed DInput8/Xidi settings without recording
        // their original values. Neither opting in nor out can reconstruct those values safely.
        if (LegacyStandaloneInputLab(Game))
            throw new InvalidDataException("An older InputLab prototype was detected without a backup of its original settings. Restore the backup created before the standalone prototype, then run this installer again. No game files have been changed.");
        var self = Path.GetFullPath(Application.ExecutablePath);
        var keep = m != null ? m.Keep : new List<string> { "*.ini" };
        var stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
        BackupFolder = Path.Combine(Game, Cfg.BackupDir, stamp);
        for (int k = 2; Directory.Exists(BackupFolder); k++) BackupFolder = Path.Combine(Game, Cfg.BackupDir, stamp + "-" + k);
        var bman = new List<string> { "# " + Cfg.PackName + " backup " + stamp + " — previous version: " + (prev == "" ? "(none)" : prev) + (m != null ? " — installed: " + m.Version : "") };
        int replaced = 0, added = 0, kept = 0, deleted = 0, skipped = 0, moved = 0, leftOut = 0;
        var selection = Component.Read(Game);
        bool wasInputLabOn = Component.Current.Any(c => c.Id == "inputlab") && Component.Selected(selection, "inputlab");
        if (sel != null) foreach (var choice in sel) selection[choice.Key] = choice.Value;
        sel = selection;
        var left = Component.LeftOut(sel); var leftFiles = new List<string>(); var leftDirs = new List<string>();
        bool inputLabOn = Component.Current.Any(c => c.Id == "inputlab") && Component.Selected(sel, "inputlab");
        if (wasInputLabOn) InputLabSettings.VerifyExisting(Game); // fail before changing files if the old values cannot be restored
        else if (inputLabOn && File.Exists(Path.Combine(Game, InputLabSettings.SnapshotRel))) InputLabSettings.VerifyExisting(Game);
        string inputLabBridgeHash = null;
        Line("components: " + Component.Summary(sel));

        using (var z = ZipFile.OpenRead(zip))
        {
            var entries = z.Entries.Where(e => !string.IsNullOrEmpty(e.Name)).ToList();
            // 1. safety pass: nothing outside the game folder, nothing forbidden
            foreach (var e in entries)
            {
                var rel = e.FullName.Replace('/', '\\');
                if (rel.Contains("..") || Path.IsPathRooted(rel) || !Inside(Abs(rel))) throw new Exception("Refused: unsafe path in archive: " + e.FullName);
                if (Cfg.Forbidden.IsMatch(rel)) throw new Exception("Refused: the archive contains a forbidden file (" + e.FullName + "). This is not an official pack.");
            }
            if (Component.Current.Any(c => c.Id == "inputlab")) inputLabBridgeHash = ValidateInputLabArchive(entries); // app/payload must be complete even with runtime OFF
            if (!entries.Any(e => e.FullName.Equals(Cfg.VersionFile, StringComparison.OrdinalIgnoreCase))) throw new Exception("Refused: archive has no " + Cfg.VersionFile + " at its root (wrong zip?).");
            Status("Backing up files that will be replaced...");
            if (m != null) foreach (var rel in m.Delete)
                if (Path.IsPathRooted(rel) || rel.Contains("..") || !Inside(Abs(rel)))
                    throw new InvalidDataException("Refused: unsafe delete in version.txt: " + rel);
            Progress(0);
            // 2. backup everything we will touch
            var moves = m != null ? m.Move : new List<KeyValuePair<string, string>>();
            foreach (var mv in moves)
            {
                var a = Abs(mv.Key); var b2 = Abs(mv.Value);
                if (!Inside(a) || !Inside(b2) || mv.Key.Contains("..") || mv.Value.Contains("..") || Cfg.Forbidden.IsMatch(mv.Key) || Cfg.Forbidden.IsMatch(mv.Value))
                    throw new Exception("Refused: unsafe move in version.txt: " + mv.Key + " -> " + mv.Value);
            }
            // 1.1.0 : files on disk that belong to a component left out (a dir\* glob covers the whole folder, whatever is in it)
            foreach (var c in left) foreach (var g in c.Globs)
            {
                if (g.EndsWith("\\*")) { var d = Abs(g.Substring(0, g.Length - 2)); if (Inside(d + "\\") && Directory.Exists(d)) { leftDirs.Add(d); leftFiles.AddRange(Directory.GetFiles(d, "*", SearchOption.AllDirectories).Select(f => f.Substring(Path.GetFullPath(Game).TrimEnd('\\').Length + 1))); } }
                else if (g.IndexOf('*') < 0 && Inside(Abs(g)) && File.Exists(Abs(g))) leftFiles.Add(g);
            }
            var keptDefaults = entries.Select(e => e.FullName.Replace('/', '\\')).Where(rel => File.Exists(Abs(rel)) && keep.Any(k => Util.Glob(k, Path.GetFileName(rel)))).Select(rel => rel + ".new");
            var touched = entries.Select(e => e.FullName.Replace('/', '\\')).Concat(keptDefaults).Concat(m != null ? m.Delete : new List<string>()).Concat(moves.Select(mv => mv.Key)).Concat(moves.Select(mv => mv.Value)).Concat(new[] { Cfg.ComponentsFile })
                .Concat(Component.Current.Any(c => c.Id == "inputlab") ? new[] { "Xidi.ini", InputLabSettings.SnapshotRel } : new string[0])
                .Concat(leftFiles).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
            Directory.CreateDirectory(BackupFolder);
            foreach (var rel in touched)
            {
                var abs = Abs(rel);
                if (File.Exists(abs))
                {
                    var b = Path.Combine(BackupFolder, rel); Directory.CreateDirectory(Path.GetDirectoryName(b));
                    File.Copy(abs, b, true); bman.Add("had|" + rel);
                }
                else bman.Add("new|" + rel);
            }
            File.WriteAllLines(Path.Combine(BackupFolder, "backup-manifest.txt"), bman);
            // 2b. migrations (move=): the user's file follows the new layout, then keep=*.ini protects it
            foreach (var mv in moves)
            {
                var a = Abs(mv.Key); var b2 = Abs(mv.Value);
                if (!File.Exists(a)) continue;
                Directory.CreateDirectory(Path.GetDirectoryName(b2));
                if (File.Exists(b2)) File.Delete(b2);
                File.Move(a, b2); moved++; Line("moved " + mv.Key + " -> " + mv.Value);
            }
            // 3. extract
            int i = 0;
            foreach (var e in entries)
            {
                var rel = e.FullName.Replace('/', '\\'); var abs = Abs(rel);
                Status("Installing " + rel); Progress(++i * 100 / entries.Count);
                if (left.Any(c => c.Owns(rel))) { leftOut++; continue; }   // 1.1.0 : component left out — not extracted (old copies removed below)
                Directory.CreateDirectory(Path.GetDirectoryName(abs));
                bool exists = File.Exists(abs);
                if (exists && keep.Any(k => Util.Glob(k, Path.GetFileName(rel))))
                {
                    // user settings: keep theirs, drop the new default next to it only if different
                    var tmp = abs + ".new"; e.ExtractToFile(tmp, true);
                    if (Util.Sha256(tmp) == Util.Sha256(abs)) File.Delete(tmp); else Line("kept your " + rel + " (new default saved as " + Path.GetFileName(tmp) + ")");
                    kept++; continue;
                }
                if (string.Equals(abs, self, StringComparison.OrdinalIgnoreCase))
                {
                    e.ExtractToFile(abs + ".new", true); SelfReplaced = true; Line("installer itself updated (applied on exit)"); continue;
                }
                try { e.ExtractToFile(abs, true); }
                catch (IOException ex) { throw new Exception("Cannot write " + rel + " (" + ex.Message + "). Is the game or a launcher still open?"); }
                if (exists) replaced++; else added++;
            }
            // 4. delete list
            if (m != null) foreach (var rel in m.Delete)
            {
                var abs = Abs(rel);
                if (!Inside(abs) || Cfg.Forbidden.IsMatch(rel) && !rel.Equals("DLC Unlocker.txt", StringComparison.OrdinalIgnoreCase)) { skipped++; continue; }
                if (File.Exists(abs)) { try { File.Delete(abs); deleted++; Line("removed obsolete " + rel); } catch (Exception ex) { Line("could not remove " + rel + ": " + ex.Message); } }
            }
        }
        // InputLab is opt-in: the mandatory archive frontend remains the original Xidi when unchecked.
        // Both frontend copies were verified in the archive before backup/extraction; check disk again
        // before placing the bridge so an unexpected delete or partial extraction cannot be hidden.
        if (inputLabOn)
        {
            var active = Abs("dinput8ex.bin");
            var preserved = Abs("DOA5LR-InputBridge-Xidi.dll");
            var bridge = Abs(@"InputLab\payload\dinput8ex.bin");
            if (!File.Exists(active) || !File.Exists(preserved) || !File.Exists(bridge) ||
                Util.Sha256(active) != Cfg.InputLabXidiSha256 || Util.Sha256(preserved) != Cfg.InputLabXidiSha256 ||
                Util.Sha256(bridge) != inputLabBridgeHash)
                throw new InvalidDataException("InputLab frontend verification failed; use Restore backup to undo this install.");
            File.Copy(bridge, active, true);
            if (Util.Sha256(active) != inputLabBridgeHash)
                throw new IOException("InputLab bridge could not be verified after installation; use Restore backup.");
            InputLabSettings.Activate(Game);
            Line("InputLab activated: bridge is dinput8ex.bin; original Xidi is DOA5LR-InputBridge-Xidi.dll");
        }
        else if (Component.Current.Any(c => c.Id == "inputlab") && InputLabSettings.Deactivate(Game))
            Line("InputLab deactivated: original DInput8/Xidi settings restored");
        // 5. make sure the telemetry plugin knows where version.txt lives (older installs had VersionUrl empty)
        foreach (var sub in new[] { "", "scripts", "plugins" }) foreach (var pair in new[] { new[] { Cfg.TelemetryIni, "Telemetry" }, new[] { Cfg.UpdateCheckIni, "UpdateCheck" } })
        try
        {
            var ini = Path.Combine(Game, sub, pair[0]);
            if (File.Exists(ini))
            {
                var txt = File.ReadAllText(ini, Encoding.UTF8);
                if (Regex.IsMatch(txt, @"^VersionUrl=\s*$", RegexOptions.Multiline)) { txt = Regex.Replace(txt, @"^VersionUrl=\s*$", "VersionUrl=" + Cfg.OfficialVersionUrl, RegexOptions.Multiline); File.WriteAllText(ini, txt, new UTF8Encoding(false)); Line("set VersionUrl in " + pair[0]); }
                else if (!Regex.IsMatch(txt, @"^VersionUrl=", RegexOptions.Multiline)) { txt = Regex.Replace(txt, @"^\[" + pair[1] + @"\]\s*$", "[" + pair[1] + "]\r\nVersionUrl=" + Cfg.OfficialVersionUrl, RegexOptions.Multiline); File.WriteAllText(ini, txt, new UTF8Encoding(false)); Line("added VersionUrl to " + pair[0]); }
            }
        }
        catch (Exception ex) { Line(pair[0] + " not patched: " + ex.Message); }
        // 1.1.0 : components left out — old copies removed (backed up above), a .ini is kept (settings), then the choice is
        // remembered (read back by --update, the file check and the next run of this installer)
        foreach (var rel in leftFiles.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            var abs = Abs(rel); if (!Inside(abs) || Cfg.Forbidden.IsMatch(rel) || !File.Exists(abs)) continue;
            if (rel.EndsWith(".ini", StringComparison.OrdinalIgnoreCase)) { Line("kept your " + rel + " (settings of a component left out)"); continue; }
            File.Delete(abs); Line("removed " + rel + " (component left out)");
        }
        foreach (var d in leftDirs.OrderByDescending(d => d.Length)) try { if (Directory.Exists(d) && !Directory.EnumerateFileSystemEntries(d).Any()) Directory.Delete(d); } catch { }
        Component.Write(Game, sel);
        // folders emptied by the delete list
        if (m != null) foreach (var d in m.Delete.Select(r => Path.GetDirectoryName(Abs(r))).Where(d => d != null).Distinct(StringComparer.OrdinalIgnoreCase).OrderByDescending(d => d.Length))
            try { if (Inside(d + "\\") && Directory.Exists(d) && !Directory.EnumerateFileSystemEntries(d).Any()) Directory.Delete(d); } catch { }
        File.WriteAllLines(Path.Combine(BackupFolder, "backup-manifest.txt"), bman);
        Line(string.Format("done: {0} replaced, {1} added, {2} settings kept, {3} moved, {4} removed, {5} skipped, {7} left out — backup in {6}", replaced, added, kept, moved, deleted, skipped, BackupFolder, leftOut));
        Progress(100);
    }

    public List<string> Backups()
    {
        var d = Path.Combine(Game, Cfg.BackupDir);
        if (!Directory.Exists(d)) return new List<string>();
        return Directory.GetDirectories(d).Where(x => File.Exists(Path.Combine(x, "backup-manifest.txt"))).OrderByDescending(x => x).ToList();
    }

    public void Restore(string backup)
    {
        Game = Path.GetFullPath(Game);
        Line("RESTORE from " + backup);
        WaitGameClosed();
        var lines = File.ReadAllLines(Path.Combine(backup, "backup-manifest.txt"));
        int restored = 0, removed = 0, n = 0;
        foreach (var ln in lines)
        {
            Progress(++n * 100 / Math.Max(1, lines.Length));
            var p = ln.Split(new[] { '|' }, 2); if (p.Length != 2) continue;
            var rel = p[1]; var abs = Abs(rel);
            if (!Inside(abs) || Cfg.Forbidden.IsMatch(rel)) continue;
            if (p[0] == "had")
            {
                var src = Path.Combine(backup, rel); if (!File.Exists(src)) continue;
                Status("Restoring " + rel); Directory.CreateDirectory(Path.GetDirectoryName(abs));
                if (string.Equals(abs, Path.GetFullPath(Application.ExecutablePath), StringComparison.OrdinalIgnoreCase)) { File.Copy(src, abs + ".new", true); SelfReplaced = true; }
                else File.Copy(src, abs, true);
                restored++;
            }
            else if (p[0] == "new" && File.Exists(abs))
            {
                Status("Removing " + rel);
                try { File.Delete(abs); removed++; } catch (Exception ex) { Line("could not remove " + rel + ": " + ex.Message); }
            }
        }
        // remove empty folders we created
        foreach (var d in Directory.GetDirectories(Game, "*", SearchOption.AllDirectories).OrderByDescending(x => x.Length))
            try { if (!Directory.EnumerateFileSystemEntries(d).Any()) Directory.Delete(d); } catch { }
        Line(string.Format("restore done: {0} files restored, {1} removed", restored, removed));
        Progress(100);
    }

    // Replace the running exe with <exe>.new and relaunch (used after self-update / restore).
    // Windows lets a running .exe be renamed (not overwritten): move ourselves to .old, move .new in place, start it.
    // No hidden command shell involved (a hidden "move & start" shell is a classic antivirus heuristic trigger).
    // The .old file is removed at the next start (see Main).
    public static void ApplySelfReplaceAndRestart(string args)
    {
        var exe = Application.ExecutablePath; var old = exe + ".old"; var nw = exe + ".new";
        try
        {
            if (File.Exists(old)) File.Delete(old);
            File.Move(exe, old); File.Move(nw, exe);
            Process.Start(new ProcessStartInfo(exe, args) { UseShellExecute = true, WorkingDirectory = Path.GetDirectoryName(exe) });
        }
        catch (Exception ex)
        {
            Util.Log("self-replace failed: " + ex.Message);
            try { if (!File.Exists(exe) && File.Exists(old)) File.Move(old, exe); } catch { }
            MessageBox.Show("The installer could not replace itself (" + ex.Message + ").\r\nRename " + Path.GetFileName(nw) + " to " + Path.GetFileName(exe) + " by hand.", "Installer update", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        Application.Exit();
    }
}

// The settings app is always installed in InputLab-capable packs; only its runtime is opt-in.
// Opening this UI must never start Steam or change the player's selected input mode.
static class InputLauncher
{
    public static bool Available(string game) { return !string.IsNullOrEmpty(game) && File.Exists(Path.Combine(game, @"InputLab\DOA5LR-Commandes.exe")); }
    public static bool Enabled(string game)
    {
        if (string.IsNullOrEmpty(game)) return false;
        if (Available(game) || Component.Current.Any(c => c.Id == "inputlab")) return true;
        // A missing/quarantined chooser must not turn an installed pack back into a direct Steam launcher.
        try { return File.ReadLines(Path.Combine(game, Cfg.ComponentsFile)).Any(line => Regex.IsMatch(line, @"^\s*inputlab\s*=", RegexOptions.IgnoreCase)); }
        catch { return false; }
    }

    public static bool TryOpen(string game, Action<ProcessStartInfo> open = null)
    {
        if (!Enabled(game)) return false;
        var exe = Path.GetFullPath(Path.Combine(game, @"InputLab\DOA5LR-Commandes.exe"));
        if (!File.Exists(exe)) throw new FileNotFoundException("The Keyboard / controller app is missing. Repair the mod pack, or restore the InputLab folder from the pack ZIP before playing. The experimental runtime may remain unchecked.", exe);
        var start = new ProcessStartInfo(exe) { WorkingDirectory = Path.GetDirectoryName(exe), UseShellExecute = true };
        if (open == null) StartOrActivate(start); else open(start);
        return true;
    }

    static void StartOrActivate(ProcessStartInfo start)
    {
        foreach (var process in Process.GetProcessesByName(Path.GetFileNameWithoutExtension(start.FileName)))
        {
            using (process)
            {
                try
                {
                    if (!string.Equals(process.MainModule.FileName, start.FileName, StringComparison.OrdinalIgnoreCase)) continue;
                    var window = process.MainWindowHandle;
                    if (window != IntPtr.Zero) { ShowWindow(window, 9); SetForegroundWindow(window); }
                    return; // Also avoid a duplicate while the matching app is still creating its window.
                }
                catch { } // An unrelated/inaccessible process must not prevent opening this installed app.
            }
        }
        Process.Start(start);
    }

    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr window, int command);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
}

// Local, opt-in support archive. Fixed allowlists only: no recursive discovery,
// full INI dumps, Steam configuration, saves, telemetry logs, or upload.
static class DiagnosticBundle
{
    public const int MaxLogBytes = 2 * 1024 * 1024;
    const long MaxHashBytes = 32L * 1024 * 1024;
    static readonly string[] LogNames = { "DOA5LR-Lobby.log", Cfg.LogName, "DOA5LR-InputBridge.log", "DOA5LR-InviteFix.log" };
    static readonly string[] PluginNames = { "DOA5LR-Lobby.asi", "DOA5LR-InviteFix.asi", "DOA5LR-WiFi-Wired-Detector.asi", "DOA5LR-UpdateCheck.asi", "DOA5LR-Borderless.asi", "DOA5LR-60fps-menus.asi" };
    static readonly string[] BinaryNames = { "dinput8.dll", "dinput8Hooked.dll", "dinput8ex.bin", "Xidi.32.dll", "DOA5LR-InputBridge-Xidi.dll", "DOA5LR-Companion.exe", Cfg.ExeName,
        @"InputLab\DOA5LR-Commandes.exe", @"InputLab\DOA5LR-Detecteur.exe", @"InputLab\DOA5LR-Peripheriques.exe", @"InputLab\DOA5LR-Companion.exe" };
    static string Root(string path) { return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar); }
    static bool Under(string path, string directory) { return string.Equals(path, directory, StringComparison.OrdinalIgnoreCase) || path.StartsWith(directory + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase); }
    static bool HasLinkedAncestor(string path)
    {
        for (string p = Path.GetFullPath(path); !string.IsNullOrEmpty(p); p = Path.GetDirectoryName(p))
            if ((File.Exists(p) || Directory.Exists(p)) && (File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0) return true;
        return false;
    }
    static string CheckedFile(string game, string rel, out string status)
    {
        string path = Path.GetFullPath(Path.Combine(game, rel));
        status = "missing";
        try
        {
            if (!Under(path, game)) { status = "outside game folder: skipped"; return null; }
            if (HasLinkedAncestor(path)) { status = "linked path: skipped"; return null; }
            if (!File.Exists(path)) return null;
            status = "available"; return path;
        }
        catch { status = "unavailable"; return null; }
    }
    static FileStream OpenShared(string path) { return new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete); }
    static byte[] ReadBounded(string path, int limit, bool tail, out bool truncated)
    {
        using (var input = OpenShared(path))
        {
            long length = input.Length; truncated = length > limit;
            if (tail && truncated) input.Seek(length - limit, SeekOrigin.Begin);
            byte[] bytes = new byte[(int)Math.Min(length, limit)]; int used = 0, n;
            while (used < bytes.Length && (n = input.Read(bytes, used, bytes.Length - used)) > 0) used += n;
            if (used != bytes.Length) Array.Resize(ref bytes, used);
            return bytes;
        }
    }
    static string SmallText(string game, string rel)
    {
        string status, path = CheckedFile(game, rel, out status); if (path == null) return "";
        try { bool cut; var bytes = ReadBounded(path, 65536, false, out cut); return cut ? "" : Encoding.UTF8.GetString(bytes).TrimStart('\uFEFF'); }
        catch { return ""; }
    }
    static string IniValue(string text, string section, string key)
    {
        bool inside = section == null;
        foreach (string raw in text.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
        {
            string line = raw.Trim(); if (line.StartsWith(";") || line.StartsWith("#")) continue;
            if (line.StartsWith("[") && line.EndsWith("]")) { inside = section != null && string.Equals(line.Substring(1, line.Length - 2).Trim(), section, StringComparison.OrdinalIgnoreCase); continue; }
            int equal = line.IndexOf('='); if (inside && equal > 0 && string.Equals(line.Substring(0, equal).Trim(), key, StringComparison.OrdinalIgnoreCase)) return line.Substring(equal + 1).Trim();
        }
        return "";
    }
    static void AddText(ZipArchive zip, string name, string value)
    { using (var writer = new StreamWriter(zip.CreateEntry(name, CompressionLevel.Optimal).Open(), new UTF8Encoding(false))) writer.Write(value); }
    static string HashFile(string path)
    {
        using (var input = OpenShared(path))
        using (var hash = SHA256.Create())
        {
            long length = input.Length; if (length > MaxHashBytes) return "larger than 32 MiB: hash skipped";
            byte[] buffer = new byte[65536]; long remaining = length;
            while (remaining > 0) { int n = input.Read(buffer, 0, (int)Math.Min(buffer.Length, remaining)); if (n == 0) return "changed during export: hash skipped"; hash.TransformBlock(buffer, 0, n, buffer, 0); remaining -= n; }
            if (input.Length != length) return "changed during export: hash skipped";
            hash.TransformFinalBlock(new byte[0], 0, 0);
            return BitConverter.ToString(hash.Hash).Replace("-", "").ToLowerInvariant();
        }
    }
    public static string FindLog(string game, string name)
    {
        if (string.IsNullOrWhiteSpace(game) || !LogNames.Contains(name, StringComparer.OrdinalIgnoreCase)) return null;
        foreach (string rel in new[] { name, Path.Combine("scripts", name) }) { string status, path = CheckedFile(Root(game), rel, out status); if (path != null) return path; }
        return null;
    }
    public static void Export(string game, string destination)
    {
        if (string.IsNullOrWhiteSpace(game) || !Directory.Exists(game)) throw new IOException("Select the game folder before exporting diagnostics.");
        game = Root(game); destination = Path.GetFullPath(destination);
        if (Under(destination, game)) throw new IOException("Save the diagnostics ZIP outside the game folder.");
        if (HasLinkedAncestor(game) || HasLinkedAncestor(destination)) throw new IOException("Linked folders or files cannot be used for diagnostics. Choose a regular folder.");
        if (!string.Equals(Path.GetExtension(destination), ".zip", StringComparison.OrdinalIgnoreCase)) throw new IOException("Choose a .zip filename.");
        // CreateNew prevents overwriting another file, including any source file.
        using (var output = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (var zip = new ZipArchive(output, ZipArchiveMode.Create))
        {
            AddText(zip, "README.txt", "DOA5LR-Salons diagnostics - review before sharing\r\n\r\n" +
                "This archive was created locally by your request. Nothing was uploaded.\r\n" +
                "It contains a small settings/version report, hashes of known mod files, and only the existing Lobby, Installer, InputBridge and InviteFix logs from the game root/scripts folders.\r\n" +
                "Each log is limited to its last 2 MiB; a tail may begin in the middle of a line or encoded character. Logs are copied as-is, NOT anonymized.\r\n" +
                "Logs may contain player names, Steam IDs, IP addresses, local paths or other session details. Inspect the files and remove sensitive information before you send them.\r\n" +
                "No Steam configuration, credentials, game saves, crash dumps, telemetry logs or mod binaries are intentionally collected. Files are selected from a fixed allowlist, not a folder scan.\r\n" +
                "Missing logs are listed in report.txt. This feature does not enable debug logging or change the game. A hash confirms file identity, not safety.\r\n\r\n" +
                "When reporting a problem, add reproduction steps, selected input mode, device model/keyboard layout, Steam Input status, and a screenshot if useful.\r\n");
            var report = new StringBuilder("DOA5LR-Salons diagnostics\r\nGenerated UTC: " + DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture) + "\r\nInstaller: " + Cfg.AppVersion + "\r\n");
            string version = SmallText(game, Cfg.VersionFile).Trim();
            report.AppendLine("Pack version: " + (Regex.IsMatch(version, @"\A[0-9A-Za-z.+_-]{1,64}\z") ? version : "missing or invalid"));
            string components = SmallText(game, Cfg.ComponentsFile);
            foreach (string component in new[] { "borderless", "60fps", "inputlab" }) { string value = IniValue(components, null, component); report.AppendLine("Component " + component + ": " + (value == "0" || value == "1" ? value : "not recorded")); }
            string mode = IniValue(SmallText(game, "DOA5LR-InputBridge.ini"), "Input", "Mode");
            report.AppendLine("Saved input mode: " + (new[] { "Keyboard", "Controller", "Hybrid" }.Contains(mode, StringComparer.OrdinalIgnoreCase) ? mode : "not recorded") + " (only relevant when inputlab is enabled)");
            report.AppendLine("\r\nExisting logs (up to the last 2 MiB each):");
            foreach (string rel in LogNames.Concat(LogNames.Select(n => Path.Combine("scripts", n))))
            {
                string status, path = CheckedFile(game, rel, out status), name = rel.Replace('\\', '/');
                if (path != null) try
                {
                    bool cut; byte[] bytes = ReadBounded(path, MaxLogBytes, true, out cut);
                    using (var entry = zip.CreateEntry("logs/" + name, CompressionLevel.Optimal).Open()) entry.Write(bytes, 0, bytes.Length);
                    status = "included " + bytes.Length + " bytes" + (cut ? " (tail only)" : "");
                }
                catch { status = "unreadable: skipped"; }
                report.AppendLine(name + ": " + status);
            }
            report.AppendLine("\r\nSHA-256 of known mod files (file contents are not included):");
            foreach (string rel in BinaryNames.Concat(PluginNames).Concat(PluginNames.Select(n => Path.Combine("scripts", n))))
            {
                string status, path = CheckedFile(game, rel, out status);
                if (path != null) try { status = HashFile(path); } catch { status = "unreadable: hash skipped"; }
                report.AppendLine(rel.Replace('\\', '/') + ": " + status);
            }
            AddText(zip, "report.txt", report.ToString());
        }
    }
}

// ---------------------------------------------------------------- UI
class MainForm : Form
{
    static readonly Color BG = Color.FromArgb(0x1A, 0x21, 0x30), PANEL = Color.FromArgb(0x22, 0x2B, 0x3C), FIELD = Color.FromArgb(0x11, 0x16, 0x20),
        RED = Color.FromArgb(0xE2, 0x37, 0x44), YEL = Color.FromArgb(0xF5, 0xC5, 0x42), TXT = Color.FromArgb(0xE8, 0xEC, 0xF2), DIM = Color.FromArgb(0xA6, 0xB0, 0xC0), BTN = Color.FromArgb(0x3A, 0x46, 0x5C), OK = Color.FromArgb(0x3C, 0xC1, 0x7A);

    Label lblInstalled, lblLatest, lblState, lblStatus, lblSub;
    RichTextBox txtNotes; TextBox txtGame;
    Button btnMain, btnLaunch, btnShortcut, btnFinder, btnRestore, btnBackups, btnCheck, btnCredits, btnBrowse, btnLog;
    ComboBox cbDisplay; Label lblDisplay;
    Label lblComp, lblCompSub; readonly List<CheckBox> chkComp = new List<CheckBox>();   // 1.1.0
    Dictionary<string, bool> sel = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase), saved = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
    ProgressBar bar;
    public static string GameOverride;
    Manifest manifest; string game = ""; string installed = ""; bool busy; readonly bool updateMode, playMode;
    List<string> missing = new List<string>(); bool missingWarned;   // 1.0.3

    public MainForm(bool updateMode, bool playMode = false)
    {
        this.updateMode = updateMode; this.playMode = playMode && !updateMode;
        Text = Cfg.PackName + " Installer " + Cfg.AppVersion; BackColor = BG; ForeColor = TXT;
        Font = new Font("Segoe UI", 10f); ClientSize = new Size(760, 844); StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedSingle; MaximizeBox = false;
        AutoScaleMode = AutoScaleMode.Dpi; AutoScaleDimensions = new SizeF(96f, 96f);
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
        Build();
        Shown += async (s, e) => { DetectGame(); await CheckAsync(); if (this.playMode && !IsDisposed && !Disposing) await LaunchAction(); };   // 1.2.0 : --play
        Activated += (s, e) => {
            if (busy || game == "") return;
            // Controls may activate the runtime. Do not overwrite component choices the player is still editing.
            if (!SelectionChanged()) LoadSelection();
            RefreshInstalled();
        };
    }

    Label L(string t, int x, int y, int w, float size = 10f, bool bold = false, Color? c = null)
    {
        var l = new Label { Text = t, Left = x, Top = y, Width = w, AutoSize = false, Height = (int)(size * 2.4), ForeColor = c ?? TXT, Font = new Font("Segoe UI", size, bold ? FontStyle.Bold : FontStyle.Regular), BackColor = Color.Transparent, UseMnemonic = false };
        Controls.Add(l); return l;
    }
    Button B(string t, int x, int y, int w, int h, Color bg, EventHandler click, bool bold = false)
    {
        var b = new Button { Text = t.Replace("&", "&&"), Left = x, Top = y, Width = w, Height = h, BackColor = bg, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", bold ? 11f : 10f, bold ? FontStyle.Bold : FontStyle.Regular), Cursor = Cursors.Hand };
        b.FlatAppearance.BorderSize = 0; b.FlatAppearance.MouseOverBackColor = ControlPaint.Light(bg, 0.15f); b.Click += click; Controls.Add(b); return b;
    }
    void Build()
    {
        int x = 32, w = ClientSize.Width - 64;
        L("DEAD OR ALIVE 5 LAST ROUND", x, 22, w, 10f, true, RED);
        L(Cfg.PackName + " — Lobby Mods", x, 44, w - 240, 17f, true);
        L("Community Mod Pack by FGCsnow & BonuStage  ·  Original Auto Installer concept by BRG Hades", x, 88, w, 9f, false, DIM);

        var p = new Panel { Left = x, Top = 120, Width = w, Height = 168, BackColor = PANEL }; Controls.Add(p);
        Func<string, int, int, int, float, bool, Color, Label> PL = (t, px, py, pw, sz, bold, c) => { var l = new Label { Text = t, Left = px, Top = py, Width = pw, Height = (int)(sz * 2.4), ForeColor = c, Font = new Font("Segoe UI", sz, bold ? FontStyle.Bold : FontStyle.Regular), BackColor = Color.Transparent, UseMnemonic = false }; p.Controls.Add(l); return l; };
        PL("Installed", 16, 12, 200, 9f, false, DIM); lblInstalled = PL("…", 16, 32, 200, 16f, true, TXT);
        PL("Latest", 236, 12, 200, 9f, false, DIM); lblLatest = PL("…", 236, 32, 200, 16f, true, TXT);
        lblState = PL("Checking for updates…", 456, 32, 230, 11f, true, YEL);
        txtNotes = new RichTextBox { Left = 16, Top = 76, Width = w - 32, Height = 80, ReadOnly = true, ScrollBars = RichTextBoxScrollBars.Vertical, BackColor = FIELD, ForeColor = TXT, BorderStyle = BorderStyle.None, Font = new Font("Segoe UI", 9.5f), TabStop = false };
        p.Controls.Add(txtNotes);

        L("Game folder", x, 300, 130, 12f, true);
        lblSub = L("Found automatically from Steam. Change it only if needed.", x + 140, 306, w - 140, 9f, false, DIM);
        txtGame = new TextBox { Left = x, Top = 332, Width = w - 132, Height = 32, BackColor = FIELD, ForeColor = TXT, BorderStyle = BorderStyle.FixedSingle, Font = new Font("Segoe UI", 10.5f) };
        txtGame.TextChanged += (s, e) => { game = txtGame.Text.Trim(); LoadSelection(); RefreshInstalled(); };
        Controls.Add(txtGame);
        btnBrowse = B("Browse", x + w - 120, 330, 120, 34, BTN, (s, e) => Browse());

        // 1.1.0 : optional components. Lobby, InviteFix, WiFi-Wired-Detector, controller fix and UpdateCheck are always installed.
        lblComp = L("Components", x, 378, 130, 12f, true);
        lblCompSub = L("Always installed: Lobby, invites, network tag, Xidi, updater.", x + 140, 384, w - 140, 9f, false, DIM);
        BuildComponents();

        btnMain = B("CHECKING…", x, 500, w, 56, RED, async (s, e) => await MainAction(), true);
        bar = new ProgressBar { Left = x, Top = 566, Width = w, Height = 8, Style = ProgressBarStyle.Continuous, Visible = false }; Controls.Add(bar);
        lblStatus = L("", x, 580, w, 9.5f, false, DIM);

        lblDisplay = L("Display mode", x, 602, 120, 10f, true); lblDisplay.Top = 605;
        cbDisplay = new ComboBox { Left = x + 120, Top = 602, Width = 360, DropDownStyle = ComboBoxStyle.DropDownList, BackColor = FIELD, ForeColor = TXT, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", 10f) };
        cbDisplay.Items.AddRange(new object[] { "Fullscreen (game setting)", "Window (with borders)", "Borderless fullscreen (recommended)" });
        cbDisplay.SelectedIndexChanged += (s, e) => { if (!busy && cbDisplay.Enabled && cbDisplay.Tag == null) { try { Util.WriteDisplayMode(game, cbDisplay.SelectedIndex); Status("Display mode: " + cbDisplay.Text + " — applied at the next game launch (F11 in game switches too)."); } catch (Exception ex) { Status("Display mode not saved: " + ex.Message); } } };
        Controls.Add(cbDisplay);
        btnLaunch = B("▶   LAUNCH GAME", x, 644, w - 396, 44, OK, async (s, e) => await LaunchAction(), true);   // 1.2.0
        btnShortcut = B("Desktop shortcut", x + 308, 644, 180, 44, BTN, (s, e) => MakeShortcut());   // 1.2.0
        btnFinder = B("Keyboard / controller", x + 496, 644, 200, 44, BTN, (s, e) => OpenInputSettings());
        btnRestore = B("Restore backup", x, 700, 150, 40, BTN, async (s, e) => await RestoreAction());
        btnBackups = B("Backups folder", x + 154, 700, 150, 40, BTN, (s, e) => OpenBackups());
        btnCheck = B("Check again", x + 308, 700, 130, 40, BTN, async (s, e) => await CheckAsync());
        btnLog = B("Logs", x + 442, 700, 80, 40, BTN, (s, e) => ShowLogs());
        btnCredits = B("Credits & Thanks", x + 526, 700, w - 526, 40, BTN, (s, e) => Credits());
        if (Cfg.PatreonUrl != "")
        {
            var bp = B("♥  Support us on Patreon", x + w - 230, 44, 230, 36, Color.FromArgb(0xF9, 0x66, 0x54), (s, e) => { try { Process.Start(Cfg.PatreonUrl); } catch { } });
            bp.Font = new Font("Segoe UI", 10f, FontStyle.Bold); bp.BringToFront();
        }
        L("Installer " + Cfg.AppVersion + "  ·  " + Cfg.ProjectUrl.Replace("https://", ""), x, 760, w, 9f, false, DIM);
        L("The pack contains no Steam / DLC files. Your .ini settings are kept on every update.", x, 782, w, 9f, false, DIM);
        L("Made with ♥ for the DOA5LR community — original Auto Installer by BRG Hades.", x, 808, w, 9f, false, DIM);
    }
    // 1.1.0 : one check box per optional component (list = Component.Current, may change once the manifest is read)
    void BuildComponents()
    {
        foreach (var c in chkComp) Controls.Remove(c); chkComp.Clear();
        int x = 32, top = 408;
        foreach (var comp in Component.Current)
        {
            var cb = new CheckBox { Text = comp.Label, Tag = comp.Id, Left = x + 8, Top = top, AutoSize = true, ForeColor = TXT, BackColor = Color.Transparent, Font = new Font("Segoe UI", 10f), Checked = Component.Selected(sel, comp.Id), Cursor = Cursors.Hand };
            cb.CheckedChanged += (s, e) => { if (busy) return; sel[(string)cb.Tag] = cb.Checked; if (cbDisplay != null && (string)cb.Tag == "borderless") { cbDisplay.Enabled = cb.Checked && cbDisplay.Tag == null; lblDisplay.ForeColor = cbDisplay.Enabled ? TXT : DIM; } UpdateState(); };
            Controls.Add(cb); chkComp.Add(cb); top += 26;
        }
        if (lblComp != null) lblComp.Visible = lblCompSub.Visible = chkComp.Count > 0;
    }
    void LoadSelection()
    {
        saved = Component.Read(game); sel = new Dictionary<string, bool>(saved, StringComparer.OrdinalIgnoreCase);
        foreach (var cb in chkComp) cb.Checked = Component.Selected(sel, (string)cb.Tag);
    }
    bool SelectionChanged() { return Component.Current.Any(c => Component.Selected(sel, c.Id) != Component.Selected(saved, c.Id)); }

    void SetBusy(bool b) { busy = b; foreach (var c in new Control[] { btnMain, btnLaunch, btnFinder, btnRestore, btnBackups, btnCheck, btnBrowse, btnLog, txtGame }.Concat(chkComp)) c.Enabled = !b; bar.Visible = b; if (!b) bar.Value = 0; }
    void Status(string s) { if (InvokeRequired) { BeginInvoke(new Action<string>(Status), s); return; } lblStatus.Text = s; }
    void Progress(int p) { if (InvokeRequired) { BeginInvoke(new Action<int>(Progress), p); return; } bar.Value = Math.Max(0, Math.Min(100, p)); }
    bool Confirm(string t, string m) { if (InvokeRequired) return (bool)Invoke(new Func<string, string, bool>(Confirm), t, m); return MessageBox.Show(this, m, t, MessageBoxButtons.OKCancel, MessageBoxIcon.Warning) == DialogResult.OK; }

    void ShowLogs()
    {
        var menu = new ContextMenuStrip();
        menu.Items.Add("Open installer log", null, (s, e) => OpenKnownLog(Cfg.LogName));
        menu.Items.Add("Open lobby log", null, (s, e) => OpenKnownLog("DOA5LR-Lobby.log"));
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Export diagnostics ZIP...", null, async (s, e) => await ExportDiagnostics());
        menu.Closed += (s, e) => menu.Dispose();
        menu.Show(btnLog, new Point(0, btnLog.Height));
    }
    void OpenKnownLog(string name)
    {
        try
        {
            string path = DiagnosticBundle.FindLog(game, name);
            if (path == null) { MessageBox.Show(this, "No " + name + " was found in the game folder or scripts. Reproduce the problem first; this button does not enable debug logging.", "Logs", MessageBoxButtons.OK, MessageBoxIcon.Information); return; }
            Process.Start(new ProcessStartInfo("notepad.exe", QuoteShortcutArgument(path)) { UseShellExecute = true });
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "Could not open log", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
    }
    async Task ExportDiagnostics()
    {
        if (busy) return;
        if (string.IsNullOrWhiteSpace(game) || !Directory.Exists(game)) { MessageBox.Show(this, "Select the game folder before exporting diagnostics.", "Diagnostics", MessageBoxButtons.OK, MessageBoxIcon.Information); return; }
        string destination;
        using (var dialog = new SaveFileDialog { Title = "Save diagnostics ZIP - review logs before sharing", Filter = "ZIP archive (*.zip)|*.zip", DefaultExt = "zip", AddExtension = true,
            FileName = "DOA5LR-Diagnostics-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".zip", InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), OverwritePrompt = false })
        {
            dialog.FileOk += (s, e) => { if (File.Exists(dialog.FileName)) { e.Cancel = true; MessageBox.Show(this, "That file already exists. Choose a new filename so the existing file is kept.", "Diagnostics filename", MessageBoxButtons.OK, MessageBoxIcon.Information); } };
            if (dialog.ShowDialog(this) != DialogResult.OK) return;
            destination = dialog.FileName;
        }
        SetBusy(true); Status("Collecting existing local logs. Nothing will be uploaded...");
        try
        {
            string selectedGame = game;
            await Task.Run(() => DiagnosticBundle.Export(selectedGame, destination));
            Status("Diagnostics ZIP saved. Review its contents before sharing.");
            MessageBox.Show(this, "Saved to:\r\n" + destination + "\r\n\r\nNo upload was made. Logs are copied as-is and may contain player names, Steam IDs, IP addresses or local paths. Review README.txt and the logs before sharing. Only the last 2 MiB of each allowed existing log is included.\r\n\r\nNo debug logging was enabled and no game settings were changed.", "Diagnostics saved", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex) { Status("Diagnostics export failed: " + ex.Message); MessageBox.Show(this, ex.Message + "\r\n\r\nChoose a new ZIP filename outside the game folder. No game settings were changed.", "Diagnostics export failed", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
        finally { SetBusy(false); UpdateState(); }
    }

    void DetectGame()
    {
        game = GameOverride ?? Util.FindGameFolder(); txtGame.Text = game;
        if (game != "") Util.LogPath = Path.Combine(game, Cfg.LogName);
        Util.Log("--- " + Cfg.PackName + " Installer " + Cfg.AppVersion + (updateMode ? " (--update)" : "") + " game=" + (game == "" ? "(not found)" : game));
        if (game == "") { lblSub.Text = "Not found — click Browse and pick the folder that contains game.exe."; lblSub.ForeColor = YEL; }
        LoadSelection(); RefreshInstalled();
    }
    void RefreshInstalled()
    {
        bool ok = game != "" && File.Exists(Path.Combine(game, Cfg.GameExe));
        installed = ok ? Util.InstalledVersion(game) : "";
        missing = ok && installed != "" ? Util.MissingRequired(game) : new List<string>();
        if (missing.Count > 0) Util.Log("required files missing: " + string.Join(", ", missing));
        lblInstalled.Text = !ok ? "—" : installed == "" ? "not installed" : installed == "old" ? "old pack (< 0.3.2)" : installed + (missing.Count > 0 ? "  ⚠ " + missing.Count + " file(s) missing" : "");
        if (cbDisplay != null)
        {
            int m = ok ? Util.ReadDisplayMode(game) : -1;
            bool bl = Component.Selected(sel, "borderless");   // 1.1.0 : no display mode without Borderless
            cbDisplay.Tag = "sync"; cbDisplay.Enabled = m >= 0 && bl; cbDisplay.SelectedIndex = m >= 0 ? m : 2; cbDisplay.Tag = m >= 0 ? null : "off";
            lblDisplay.ForeColor = m >= 0 && bl ? TXT : DIM;
        }
        txtGame.ForeColor = ok || game == "" ? TXT : RED;
        UpdateState();
    }
    void UpdateState()
    {
        bool ok = game != "" && File.Exists(Path.Combine(game, Cfg.GameExe));
        if (btnLaunch != null) { btnLaunch.Enabled = ok && !busy; btnLaunch.Text = InputLauncher.Enabled(game) ? "▶   CHOOSE INPUT / PLAY" : "▶   LAUNCH GAME"; }   // works offline too (no manifest needed)
        if (btnFinder != null) btnFinder.Enabled = ok && !busy && InputLauncher.Available(game);
        if (manifest == null) { btnMain.Text = "CHECKING…"; btnMain.Enabled = false; return; }
        btnMain.Enabled = ok && !busy && manifest.Url != "";
        if (!ok) { lblState.Text = "Select the game folder"; lblState.ForeColor = YEL; btnMain.Text = "SELECT THE GAME FOLDER FIRST"; btnMain.BackColor = BTN; return; }
        if (installed == "") { lblState.Text = "Ready to install"; lblState.ForeColor = YEL; btnMain.Text = "INSTALL MOD PACK " + manifest.Version; btnMain.BackColor = RED; }
        else if (installed == "old" || Util.CmpVer(installed, manifest.Version) < 0) { lblState.Text = "Update available"; lblState.ForeColor = YEL; btnMain.Text = "UPDATE TO " + manifest.Version; btnMain.BackColor = RED; }
        else if (missing.Count > 0) { lblState.Text = "⚠ " + missing.Count + " required file(s) missing — antivirus? Restore them, then REINSTALL"; lblState.ForeColor = RED; btnMain.Text = "REINSTALL " + manifest.Version + " (repair)"; btnMain.BackColor = RED; }
        else if (SelectionChanged()) { lblState.Text = "Components changed — click APPLY"; lblState.ForeColor = YEL; btnMain.Text = "APPLY CHANGES (reinstall " + manifest.Version + ")"; btnMain.BackColor = RED; }
        else { lblState.Text = "Up to date ✔"; lblState.ForeColor = OK; btnMain.Text = "REINSTALL " + manifest.Version + " (repair)"; btnMain.BackColor = BTN; }
        btnMain.FlatAppearance.MouseOverBackColor = ControlPaint.Light(btnMain.BackColor, 0.15f);
    }
    // 1.0.3 : one warning dialog per run when the installed pack has required files missing
    void WarnMissing()
    {
        if (missing.Count == 0 || missingWarned) return;
        missingWarned = true; Activate(); TopMost = true; TopMost = false;
        MessageBox.Show(this, Util.MissingMessage(missing), "Required files missing — the pack will not work", MessageBoxButtons.OK, MessageBoxIcon.Warning);
    }

    async Task CheckAsync()
    {
        if (busy) return;
        manifest = null; UpdateState(); lblLatest.Text = "…"; lblState.Text = "Checking for updates…"; lblState.ForeColor = YEL; txtNotes.Text = "";
        try
        {
            var txt = await Task.Run(() => Util.HttpGetText(Cfg.VersionUrl));
            manifest = Manifest.Parse(txt);
            if (manifest.Version == "") throw new Exception("version.txt has no version= line");
            lblLatest.Text = manifest.Version;
            BuildComponents();   // 1.1.0 : optional= lines of version.txt
            RefreshInstalled();  // reevaluate required files now that this manifest's components are known
            var notes = new List<string>(); if (manifest.Notes != "") notes.Add(manifest.Notes); notes.AddRange(manifest.NoteLines.Select(n => "• " + n));
            txtNotes.Text = string.Join("\r\n", notes);
            Util.Log("version.txt: latest " + manifest.Version + " installed " + (installed == "" ? "(none)" : installed) + " url " + manifest.Url);
            UpdateState();
            await SelfUpdateCheck();
            if (updateMode)
            {
                bool outdated = installed != "" && (installed == "old" || Util.CmpVer(installed, manifest.Version) < 0);
                if (!outdated && missing.Count > 0)
                {   // 1.0.3 : up to date but files missing (antivirus) -> warn at game exit, offer the repair
                    Activate(); TopMost = true; TopMost = false; missingWarned = true;
                    if (MessageBox.Show(this, Util.MissingMessage(missing) + "\r\n\r\nReinstall the pack now (repair)?", "Required files missing — the pack will not work", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.Yes) { await MainAction(); return; }
                    Close(); return;
                }
                if (!outdated) { Util.Log("--update: already up to date, exiting"); Close(); return; }
                if (Snoozed(manifest.Version)) { Util.Log("--update: " + manifest.Version + " snoozed by the player, exiting"); Close(); return; }
                Activate(); TopMost = true; TopMost = false;
                if (MessageBox.Show(this, Cfg.PackName + " " + manifest.Version + " is available (you have " + installed + ").\r\n\r\n" + txtNotes.Text + "\r\n\r\nUpdate now?  (No = ask again tomorrow)", "Update available", MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes) await MainAction();
                else { Snooze(manifest.Version); Close(); }
            }
            else if (!playMode) WarnMissing();   // 1.2.0 : --play asks in LaunchAction instead
        }
        catch (Exception ex)
        {
            lblLatest.Text = "?"; lblState.Text = "Cannot reach the update server"; lblState.ForeColor = RED;
            txtNotes.Text = "Could not read version.txt: " + ex.Message + "\r\nCheck your connection, then click Check again.";
            Util.Log("check failed: " + ex.Message);
            btnMain.Text = "OFFLINE — CHECK AGAIN"; btnMain.Enabled = false;
            if (updateMode) Close();
        }
    }

    async Task SelfUpdateCheck()
    {
        if (manifest == null || manifest.InstallerUrl == "" || Util.CmpVer(manifest.InstallerVersion, Cfg.AppVersion) <= 0) return;
        if (MessageBox.Show(this, "A new version of this installer is available (" + manifest.InstallerVersion + ", you have " + Cfg.AppVersion + ").\r\nUpdate the installer now? It will restart.", "Installer update", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        SetBusy(true);
        try
        {
            var dest = Application.ExecutablePath + ".new";
            await Task.Run(() => Util.Download(manifest.InstallerUrl, dest, (d, t) => { if (t > 0) Progress((int)(d * 100 / t)); Status("Downloading installer " + Util.Human(d)); }));
            if (manifest.InstallerSha256.Length == 64 && Util.Sha256(dest) != manifest.InstallerSha256) { File.Delete(dest); throw new Exception("installer SHA256 mismatch, update aborted"); }
            Util.Log("installer self-update to " + manifest.InstallerVersion);
            Engine.ApplySelfReplaceAndRestart(updateMode ? "--update" : playMode ? "--play" : "");
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "Installer update failed", MessageBoxButtons.OK, MessageBoxIcon.Error); Util.Log("self-update failed: " + ex.Message); }
        finally { SetBusy(false); }
    }

    async Task MainAction()
    {
        if (busy || manifest == null || manifest.Url == "") return;
        if (!File.Exists(Path.Combine(game, Cfg.GameExe))) { MessageBox.Show(this, "game.exe not found in:\r\n" + game, "Game folder", MessageBoxButtons.OK, MessageBoxIcon.Warning); return; }
        if (!Util.CanWrite(game)) { Relaunch("Writing to the game folder needs administrator rights (Steam is under Program Files). Restart the installer as administrator?"); return; }
        var eng = new Engine { Game = game, Status = Status, Progress = Progress, Confirm = Confirm, GraceSeconds = updateMode ? 30 : 0 };
        SetBusy(true);
        try
        {
            var zip = await Task.Run(() => eng.DownloadPack(manifest));
            var choice = new Dictionary<string, bool>(sel, StringComparer.OrdinalIgnoreCase);
            await Task.Run(() => eng.InstallZip(zip, manifest, choice));
            await Task.Delay(1500);   // 1.0.3 : give a real-time antivirus the time to react before we check the files
            LoadSelection(); RefreshInstalled();
            if (missing.Count > 0)
            {
                Util.Log("install finished but required files already missing: " + string.Join(", ", missing));
                Status("Installed, but " + missing.Count + " required file(s) were removed right away (antivirus?)");
                MessageBox.Show(this, "The pack was extracted, but these files were removed again within seconds — your antivirus almost certainly quarantined them:\r\n\r\n    " + string.Join("\r\n    ", missing) +
                    "\r\n\r\nDo not play like this. Restore them from the antivirus quarantine, add the game folder to its exclusions, then click REINSTALL (repair).", "Files removed by the antivirus", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                if (eng.SelfReplaced) Engine.ApplySelfReplaceAndRestart("");
                return;
            }
            Status("Done. " + (eng.FreshInstall ? "Installed " : "Updated to ") + manifest.Version + " — backup: " + Path.GetFileName(eng.BackupFolder));
            var msg = (eng.FreshInstall ? "Installed " : "Updated to ") + Cfg.PackName + " " + manifest.Version + " (" + Component.Summary(choice) + ").\r\n\r\n" + eng.Report.Split('\n').Where(l => l.Contains("kept your") || l.Contains("removed obsolete") || l.Contains("moved ") || l.Contains("left out")).Select(l => l.Substring(l.IndexOf("  ") + 2).Trim()).DefaultIfEmpty("").Aggregate((a, b) => a + "\r\n" + b).Trim();
            msg += (eng.FreshInstall ? "\r\n\r\nRead READ-ME-FIRST-EN.txt in the game folder once (controller setup, lobby key)." : "") + "\r\n\r\nYou can start the game.";
            bool play = false;
            if (updateMode || eng.SelfReplaced) MessageBox.Show(this, msg.Trim(), "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
            else play = MessageBox.Show(this, msg.Trim() + (InputLauncher.Enabled(game) ? "\r\n\r\nOpen Keyboard / controller to choose your input before playing?" : "\r\n\r\nLaunch the game now (through Steam)?"), "Success", MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes;
            if (eng.FreshInstall && !updateMode && !File.Exists(ShortcutPath) &&   // first install -> offer the configuration shortcut
                MessageBox.Show(this, "Add a \"" + Path.GetFileNameWithoutExtension(ShortcutPath) + "\" shortcut to your desktop?\r\n\r\nDouble-click it to open the installer and review your settings. Choose Keyboard / controller or launch through Steam when you are ready.", "Desktop shortcut", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                MakeShortcut(false);
            if (play) { SetBusy(false); await LaunchAction(true); return; }
            if (eng.SelfReplaced) Engine.ApplySelfReplaceAndRestart("");
            else if (updateMode) Close();
        }
        catch (OperationCanceledException ex) { Status(ex.Message); Util.Log(ex.Message); }
        catch (Exception ex) { Status("Failed: " + ex.Message); Util.Log("FAILED: " + ex); MessageBox.Show(this, ex.Message + (eng.BackupFolder != null ? "\r\n\r\nA backup was made before the change: " + eng.BackupFolder + "\r\nUse Restore backup if something looks wrong." : ""), "Installation failed", MessageBoxButtons.OK, MessageBoxIcon.Error); }
        finally { if (!IsDisposed) { SetBusy(false); UpdateState(); } }
    }

    // InputLab opens its choice UI first; only its Play button launches Steam. Without InputLab, LAUNCH GAME goes
    // through Steam (keeps the player's Steam launch options, overlay, invites). If Steam is not running,
    // offer to open it first and start the game once the account is logged in. The installer closes when game.exe is up.
    async Task LaunchAction(bool justInstalled = false)
    {
        if (busy) return;
        if (!File.Exists(Path.Combine(game, Cfg.GameExe))) { MessageBox.Show(this, "game.exe not found in:\r\n" + game, "Game folder", MessageBoxButtons.OK, MessageBoxIcon.Warning); return; }
        if (Util.GameProcesses(game).Length > 0) { Status("DOA5LR is already running."); return; }
        if (!justInstalled && manifest != null && manifest.Url != "")
        {
            bool outdated = installed == "old" || (installed != "" && Util.CmpVer(installed, manifest.Version) < 0);
            string why = outdated ? Cfg.PackName + " " + manifest.Version + " is available (you have " + installed + ").\r\nOnline lobbies need the latest version."
                       : missing.Count > 0 ? missing.Count + " required file(s) of the pack are missing (antivirus?)." : null;
            if (why != null)
            {
                var r = MessageBox.Show(this, why + "\r\n\r\nYes = " + (outdated ? "update" : "repair") + " first, then launch\r\nNo = launch anyway", "Before you play", MessageBoxButtons.YesNoCancel, MessageBoxIcon.Question);
                if (r == DialogResult.Cancel) return;
                if (r == DialogResult.Yes) { await MainAction(); return; }   // MainAction offers to launch when it succeeds
            }
        }
        if (InputLauncher.Enabled(game))
        {
            if (OpenInputSettings() && playMode) Close();
            return; // A missing/broken app must not silently bypass the input choice and start the game.
        }
        SetBusy(true); bar.Visible = false;
        try
        {
            if (!Util.SteamRunning())
            {
                var exe = Util.SteamExe();
                if (MessageBox.Show(this, "Steam is not running.\r\n\r\nOpen Steam now? The game starts as soon as Steam is ready (log in if Steam asks you to).", "Launch game", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK) { Status(""); return; }
                Util.Log("launch: starting Steam " + (exe == "" ? "(steam:// protocol)" : exe));
                if (exe != "") Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true, WorkingDirectory = Path.GetDirectoryName(exe) });
                else Process.Start(new ProcessStartInfo("steam://open/main") { UseShellExecute = true });
                var t0 = DateTime.UtcNow;
                while (!(Util.SteamRunning() && Util.SteamLoggedIn()))
                {
                    int sec = (int)(DateTime.UtcNow - t0).TotalSeconds;
                    if (sec >= 180) { Util.Log("launch: Steam not ready after 180 s, sending the launch request anyway"); break; }
                    Status("Waiting for Steam to start… (" + sec + " s)");
                    await Task.Delay(1000);
                }
                await Task.Delay(3000);   // Steam reports the user before it accepts launch requests
            }
            Util.Log("launch: steam://rungameid/" + Cfg.SteamAppId + " (pack " + (installed == "" ? "not installed" : installed) + ")");
            Util.SteamRunGame();
            var t1 = DateTime.UtcNow;
            while ((DateTime.UtcNow - t1).TotalSeconds < 90)
            {
                if (Util.GameProcesses(game).Length > 0) { Util.Log("launch: game.exe started, closing the installer"); Status("DOA5LR started — have fun!"); await Task.Delay(1500); Close(); return; }
                Status("Launching DOA5LR through Steam… (" + (int)(DateTime.UtcNow - t1).TotalSeconds + " s)");
                await Task.Delay(1000);
            }
            Util.Log("launch: game.exe not seen after 90 s");
            Status("The game did not start yet — check Steam (updates, launch prompt), then try again.");
        }
        catch (Exception ex) { Status("Launch failed: " + ex.Message); Util.Log("launch FAILED: " + ex.Message); MessageBox.Show(this, "Could not launch the game through Steam:\r\n" + ex.Message + "\r\n\r\nStart it from your Steam library instead.", "Launch game", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
        finally { if (!IsDisposed) { SetBusy(false); UpdateState(); } }
    }

    // "DOA5LR (Lobby Mods)" -> installer and configuration; launching requires an explicit click.
    static string ShortcutPath { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "DOA5LR (Lobby Mods).lnk"); } }
    static string QuoteShortcutArgument(string value)
    {
        // Windows command-line quoting, including embedded quotes and trailing backslashes.
        var quoted = new StringBuilder("\""); int slashes = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slashes++; continue; }
            quoted.Append('\\', c == '"' ? slashes * 2 + 1 : slashes);
            quoted.Append(c); slashes = 0;
        }
        quoted.Append('\\', slashes * 2); quoted.Append('"');
        return quoted.ToString();
    }
    static string ShortcutArguments(string gamePath)
    {
        var args = new List<string>();
        if (!string.IsNullOrEmpty(gamePath)) { args.Add("--game"); args.Add(QuoteShortcutArgument(gamePath)); }
        if (!string.Equals(Cfg.VersionUrl, Cfg.OfficialVersionUrl, StringComparison.Ordinal))
        { args.Add("--manifest"); args.Add(QuoteShortcutArgument(Cfg.VersionUrl)); }
        return string.Join(" ", args);
    }
    void MakeShortcut(bool explain = true)
    {
        try
        {
            var lnk = ShortcutPath;
            var icon = game != "" && File.Exists(Path.Combine(game, Cfg.GameExe)) ? Path.Combine(game, Cfg.GameExe) : Application.ExecutablePath;
            var args = ShortcutArguments(game);
            Util.CreateShortcut(lnk, Application.ExecutablePath, args, Path.GetDirectoryName(Application.ExecutablePath), icon,
                "Opens " + Cfg.PackName + " installer and configuration; choose your settings before launching");
            Util.Log("shortcut created: " + lnk + " -> " + Application.ExecutablePath + " " + args);
            Status("Desktop shortcut created: " + Path.GetFileName(lnk));
            if (explain) MessageBox.Show(this, "Shortcut \"" + Path.GetFileNameWithoutExtension(lnk) + "\" added to your desktop.\r\n\r\nDouble-click it to open the installer and review your settings. Choose Keyboard / controller or launch through Steam when you are ready.\r\n\r\nKeep this installer where it is now:\r\n" + Application.ExecutablePath + "\r\n(if you move it, click Desktop shortcut again).", "Desktop shortcut", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex) { Status("Shortcut failed: " + ex.Message); Util.Log("shortcut FAILED: " + ex.Message); }
    }

    async Task RestoreAction()
    {
        if (busy) return;
        var eng = new Engine { Game = game, Status = Status, Progress = Progress, Confirm = Confirm };
        var list = eng.Backups();
        if (game == "" || list.Count == 0) { MessageBox.Show(this, "No backup found in " + Path.Combine(game, Cfg.BackupDir), "Restore backup", MessageBoxButtons.OK, MessageBoxIcon.Information); return; }
        string pick = null;
        using (var d = new Form { Text = "Restore which backup?", ClientSize = new Size(520, 300), StartPosition = FormStartPosition.CenterParent, BackColor = BG, ForeColor = TXT, FormBorderStyle = FormBorderStyle.FixedDialog, MinimizeBox = false, MaximizeBox = false, Font = Font })
        {
            var lb = new ListBox { Left = 16, Top = 16, Width = 488, Height = 220, BackColor = FIELD, ForeColor = TXT, BorderStyle = BorderStyle.None };
            foreach (var b in list) { var first = File.ReadLines(Path.Combine(b, "backup-manifest.txt")).FirstOrDefault() ?? ""; lb.Items.Add(Path.GetFileName(b) + "   " + first.Replace("# " + Cfg.PackName + " backup " + Path.GetFileName(b) + " — ", "")); }
            lb.SelectedIndex = 0; d.Controls.Add(lb);
            var ok = new Button { Text = "Restore", Left = 384, Top = 250, Width = 120, Height = 36, BackColor = RED, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, DialogResult = DialogResult.OK }; ok.FlatAppearance.BorderSize = 0; d.Controls.Add(ok);
            var ca = new Button { Text = "Cancel", Left = 254, Top = 250, Width = 120, Height = 36, BackColor = BTN, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, DialogResult = DialogResult.Cancel }; ca.FlatAppearance.BorderSize = 0; d.Controls.Add(ca);
            d.AcceptButton = ok; d.CancelButton = ca;
            if (d.ShowDialog(this) != DialogResult.OK) return; pick = list[lb.SelectedIndex];
        }
        if (MessageBox.Show(this, "Restore the game folder to the state saved in " + Path.GetFileName(pick) + "?\r\nFiles added by that update will be removed and replaced files put back.", "Restore backup", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        if (!Util.CanWrite(game)) { Relaunch("Writing to the game folder needs administrator rights. Restart the installer as administrator?"); return; }
        SetBusy(true);
        try { await Task.Run(() => eng.Restore(pick)); LoadSelection(); RefreshInstalled(); Status("Backup " + Path.GetFileName(pick) + " restored."); MessageBox.Show(this, "Backup restored.", "Restore backup", MessageBoxButtons.OK, MessageBoxIcon.Information); if (eng.SelfReplaced) Engine.ApplySelfReplaceAndRestart(""); }
        catch (OperationCanceledException ex) { Status(ex.Message); }
        catch (Exception ex) { Status("Restore failed: " + ex.Message); Util.Log("RESTORE FAILED: " + ex); MessageBox.Show(this, ex.Message, "Restore failed", MessageBoxButtons.OK, MessageBoxIcon.Error); }
        finally { SetBusy(false); UpdateState(); }
    }

    string SnoozePath { get { return Path.Combine(game, Cfg.ExeName.Replace(".exe", ".snooze")); } }
    bool Snoozed(string ver)
    {
        try { var p = File.ReadAllText(SnoozePath).Split('|'); return p.Length == 2 && p[0] == ver && (DateTime.UtcNow - new DateTime(long.Parse(p[1]), DateTimeKind.Utc)).TotalHours < 24; } catch { return false; }
    }
    void Snooze(string ver) { try { File.WriteAllText(SnoozePath, ver + "|" + DateTime.UtcNow.Ticks); } catch { } }

    void Relaunch(string why)
    {
        if (MessageBox.Show(this, why, "Administrator rights", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        try { Process.Start(new ProcessStartInfo(Application.ExecutablePath, updateMode ? "--update" : "") { UseShellExecute = true, Verb = "runas" }); Application.Exit(); } catch (Exception ex) { Util.Log("elevation refused: " + ex.Message); }
    }
    void Browse()
    {
        using (var d = new FolderBrowserDialog { Description = "Select the Dead or Alive 5 Last Round folder (the one that contains game.exe)", SelectedPath = game != "" ? game : @"C:\", ShowNewFolderButton = false })
            if (d.ShowDialog(this) == DialogResult.OK) { txtGame.Text = d.SelectedPath; if (File.Exists(Path.Combine(d.SelectedPath, Cfg.GameExe))) { Util.LogPath = Path.Combine(d.SelectedPath, Cfg.LogName); lblSub.Text = "Game folder set."; lblSub.ForeColor = DIM; LoadSelection(); RefreshInstalled(); } else MessageBox.Show(this, "game.exe is not in this folder.", "Game folder", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
    }
    void OpenBackups()
    {
        var d = game == "" ? "" : Path.Combine(game, Cfg.BackupDir);
        if (d == "" || !Directory.Exists(d)) { MessageBox.Show(this, "No backup yet. One is created automatically at every install / update.", "Backups", MessageBoxButtons.OK, MessageBoxIcon.Information); return; }
        Process.Start("explorer.exe", "\"" + d + "\"");
    }
    bool OpenInputSettings()
    {
        try
        {
            if (!InputLauncher.TryOpen(game)) { Status("Install or repair the mod pack to add Keyboard / controller settings."); return false; }
            Status("Choose Keyboard or Controller, then click Play via Steam when you are ready.");
            Util.Log("launch: opened Keyboard / controller; waiting for the player's choice");
            return true;
        }
        catch (Exception ex)
        {
            Status("Could not open Keyboard / controller: " + ex.Message); Util.Log("input settings FAILED: " + ex);
            MessageBox.Show(this, ex.Message, "Keyboard / controller", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return false;
        }
    }
    void Credits()
    {
        MessageBox.Show(this,
            "DOA5LR-Salons — Community Lobby Mods\r\n\r\n" +
            "Community Mod Pack: FGCsnow (@FgcSnow) & BonuStage\r\n" +
            "Original Auto Installer (the idea and the layout this tool follows): BRG Hades — thank you!\r\n\r\n" +
            "Included mods & tools:\r\n" +
            "• Lobby (online rooms) 0.9.0 — community build\r\n" +
            "• InviteFix, WiFi/Wired Detector, 60 fps menus, Borderless, UpdateCheck — FGCsnow\r\n" +
            "• Ultimate ASI Loader — ThirteenAG (MIT)\r\n" +
            "• Xidi controller layer — Samuel Grossman (BSD)\r\n" +
            "• d3d9 resolution mod — original author credited in Optional-Resolution-Mod\\README-EN.txt\r\n\r\n" +
            "Installer " + Cfg.AppVersion + " (optional components since 1.1.0, LAUNCH GAME + desktop shortcut since 1.2.0 — idea by Inyo) — source in the pack repository: " + Cfg.ProjectUrl + "\r\n" +
            "Testers and everyone in the DOA5LR lobbies: thank you.\r\n\r\n" +
            "Privacy: diagnostics are exported locally; nothing is uploaded automatically. UpdateCheck reads the public version manifest; the installer downloads updates. Lobby/network modules communicate with other players. Lobby writes a local log.\r\n" +
            (Cfg.PatreonUrl != "" ? "Support the project: " + Cfg.PatreonUrl : ""),
            "Credits & Thanks", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
}

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        bool updateMode = args.Any(a => a.Equals("--update", StringComparison.OrdinalIgnoreCase));
        bool playMode = args.Any(a => a.Equals("--play", StringComparison.OrdinalIgnoreCase));   // explicit launcher mode
        string gameArg = null; bool auto = args.Any(a => a.Equals("--auto", StringComparison.OrdinalIgnoreCase));
        Dictionary<string, bool> compArg = null;   // 1.1.0 : --components borderless=0,60fps=1 (headless tests)
        for (int i = 0; i + 1 < args.Length; i++)
        {
            if (args[i].Equals("--manifest", StringComparison.OrdinalIgnoreCase)) { Cfg.VersionUrl = args[i + 1]; Cfg.AllowLocalPack = Path.IsPathRooted(Cfg.VersionUrl) && File.Exists(Cfg.VersionUrl); }
            if (args[i].Equals("--game", StringComparison.OrdinalIgnoreCase)) gameArg = args[i + 1];
            if (args[i].Equals("--components", StringComparison.OrdinalIgnoreCase)) { compArg = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase); foreach (var kv in args[i + 1].Split(',')) { var q = kv.Split('='); if (q.Length == 2) compArg[q[0].Trim()] = q[1].Trim() != "0"; } }
        }
        if (auto)
        {
            // headless: --auto --game <dir> [--manifest <file|url>] ; result in <game>\DOA5LR-Salons-Installer.log, exit code 0/1
            var g = gameArg ?? Util.FindGameFolder();
            Util.LogPath = Path.Combine(g != "" && Directory.Exists(g) ? g : Path.GetTempPath(), Cfg.LogName);
            Util.SetupTls();
            try
            {
                var m = Manifest.Parse(Util.HttpGetText(Cfg.VersionUrl));
                var eng = new Engine { Game = g, Status = s => Util.Log("  " + s), Confirm = (t, s) => false };
                var zip = eng.DownloadPack(m); eng.InstallZip(zip, m, compArg);
                Util.Log("auto: OK " + m.Version); Environment.Exit(0);
            }
            catch (Exception ex) { Util.Log("auto: FAILED " + ex.Message); Environment.Exit(1); }
        }
        MainForm.GameOverride = gameArg;
        // leftover from a previous self-update
        try { var n = Application.ExecutablePath + ".new"; if (File.Exists(n) && new FileInfo(n).LastWriteTimeUtc < DateTime.UtcNow.AddMinutes(-10)) File.Delete(n); } catch { }
        try { var o = Application.ExecutablePath + ".old"; if (File.Exists(o)) File.Delete(o); } catch { }   // previous version of ourselves, replaced by ApplySelfReplaceAndRestart
        Util.SetupTls();
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainForm(updateMode, playMode));
    }
}
