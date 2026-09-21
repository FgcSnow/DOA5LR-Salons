// DOA5LR-Salons Installer / Updater — single-file WinForms app, .NET Framework 4.8 (built with the csc.exe shipped in Windows).
// Community Mod Pack by FGCsnow & BonuStage. Original Auto Installer concept by BRG Hades.
//
// What it does:
//   - finds the DOA5LR game folder (Steam libraries), reads DOA5LR-Salons-VERSION.txt
//   - fetches version.txt (Cfg.VersionUrl), compares, shows notes, one-click INSTALL / UPDATE
//   - downloads the release zip, checks SHA256, waits for the game to be closed, backs up every file it
//     replaces or deletes, extracts (sub-folders included), applies the delete= list, keeps the user's .ini
//   - Restore backup, self-update (installer= line), --update mode (launched by DOA5LR-Telemetry at game exit)
//   - never writes steam_api / cream / DLC files, never writes outside the game folder
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
[assembly: System.Reflection.AssemblyVersion("1.0.2.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.0.2.0")]
[assembly: System.Reflection.AssemblyInformationalVersion("1.0.2")]

static class Cfg
{
    public const string AppVersion = "1.0.2";
    public const string PackName = "DOA5LR-Salons";
    // Stable URL of version.txt (branch main of the GitHub repo). Set once, never changes.
    public const string OfficialVersionUrl = "https://raw.githubusercontent.com/FgcSnow/DOA5LR-Salons/main/version.txt";
    public static string VersionUrl = OfficialVersionUrl;   // --manifest <file|url> overrides (testing only)
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
    public const string PatreonUrl = "https://www.patreon.com/cw/DoA5LRcommunitymod";   // empty = button hidden
    // Files the pack must never contain / the installer must never write (same rule as build_pack.py).
    public static readonly Regex Forbidden = new Regex(@"steam_api|cream|unlock|(^|[\\/])DLC", RegexOptions.IgnoreCase);
}

// ---------------------------------------------------------------- manifest (version.txt)
class Manifest
{
    public string Version = "", Url = "", Sha256 = "", Notes = "", InstallerUrl = "", InstallerVersion = "", InstallerSha256 = "";
    public long Size;
    public List<string> NoteLines = new List<string>(), Delete = new List<string>(), Keep = new List<string>();
    public List<KeyValuePair<string, string>> Move = new List<KeyValuePair<string, string>>();
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
            }
        }
        if (m.Keep.Count == 0) m.Keep.Add("*.ini");
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
        var dir = Path.Combine(Path.GetTempPath(), Cfg.PackName); Directory.CreateDirectory(dir);
        var zip = Path.Combine(dir, Cfg.PackName + "-" + m.Version + ".zip");
        if (File.Exists(zip) && m.Sha256.Length == 64 && Util.Sha256(zip) == m.Sha256) { Line("using cached download " + zip); return zip; }
        Status("Downloading " + Cfg.PackName + " " + m.Version + "...");
        Util.Download(m.Url, zip + ".part", (d, t) => { if (t > 0) Progress((int)(d * 100 / t)); Status("Downloading " + Cfg.PackName + " " + m.Version + "  " + Util.Human(d) + (t > 0 ? " / " + Util.Human(t) : "")); });
        if (File.Exists(zip)) File.Delete(zip);
        File.Move(zip + ".part", zip);
        if (m.Size > 0 && new FileInfo(zip).Length != m.Size) throw new Exception("Download size mismatch (" + new FileInfo(zip).Length + " vs " + m.Size + " bytes). Try again.");
        if (m.Sha256.Length == 64) { Status("Checking file integrity..."); var h = Util.Sha256(zip); if (h != m.Sha256) { File.Delete(zip); throw new Exception("SHA256 mismatch: the download is corrupted or tampered. Aborted, nothing was changed."); } Line("sha256 OK " + h); }
        else Line("WARNING: no sha256 in version.txt, integrity not verified");
        return zip;
    }

    // Install (fresh or update) from a local zip; returns the backup folder.
    public void InstallZip(string zip, Manifest m)
    {
        Game = Path.GetFullPath(Game);
        if (!File.Exists(Path.Combine(Game, Cfg.GameExe))) throw new Exception("game.exe not found in " + Game);
        var prev = Util.InstalledVersion(Game);
        FreshInstall = prev == "";
        Line((FreshInstall ? "INSTALL " : "UPDATE " + prev + " -> ") + (m != null ? m.Version : "?") + " from " + zip + " into " + Game);
        WaitGameClosed();
        var self = Path.GetFullPath(Application.ExecutablePath);
        var keep = m != null ? m.Keep : new List<string> { "*.ini" };
        var stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
        BackupFolder = Path.Combine(Game, Cfg.BackupDir, stamp);
        for (int k = 2; Directory.Exists(BackupFolder); k++) BackupFolder = Path.Combine(Game, Cfg.BackupDir, stamp + "-" + k);
        var bman = new List<string> { "# " + Cfg.PackName + " backup " + stamp + " — previous version: " + (prev == "" ? "(none)" : prev) + (m != null ? " — installed: " + m.Version : "") };
        int replaced = 0, added = 0, kept = 0, deleted = 0, skipped = 0, moved = 0;

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
            if (!entries.Any(e => e.FullName.Equals(Cfg.VersionFile, StringComparison.OrdinalIgnoreCase))) throw new Exception("Refused: archive has no " + Cfg.VersionFile + " at its root (wrong zip?).");
            Status("Backing up files that will be replaced...");
            Progress(0);
            // 2. backup everything we will touch
            var moves = m != null ? m.Move : new List<KeyValuePair<string, string>>();
            foreach (var mv in moves)
            {
                var a = Abs(mv.Key); var b2 = Abs(mv.Value);
                if (!Inside(a) || !Inside(b2) || mv.Key.Contains("..") || mv.Value.Contains("..") || Cfg.Forbidden.IsMatch(mv.Key) || Cfg.Forbidden.IsMatch(mv.Value))
                    throw new Exception("Refused: unsafe move in version.txt: " + mv.Key + " -> " + mv.Value);
            }
            var touched = entries.Select(e => e.FullName.Replace('/', '\\')).Concat(m != null ? m.Delete : new List<string>()).Concat(moves.Select(mv => mv.Key)).Concat(moves.Select(mv => mv.Value)).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
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
                Directory.CreateDirectory(Path.GetDirectoryName(abs));
                bool exists = File.Exists(abs);
                if (exists && !FreshInstall && keep.Any(k => Util.Glob(k, Path.GetFileName(rel))))
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
        // folders emptied by the delete list
        if (m != null) foreach (var d in m.Delete.Select(r => Path.GetDirectoryName(Abs(r))).Where(d => d != null).Distinct(StringComparer.OrdinalIgnoreCase).OrderByDescending(d => d.Length))
            try { if (Inside(d + "\\") && Directory.Exists(d) && !Directory.EnumerateFileSystemEntries(d).Any()) Directory.Delete(d); } catch { }
        File.WriteAllLines(Path.Combine(BackupFolder, "backup-manifest.txt"), bman);
        Line(string.Format("done: {0} replaced, {1} added, {2} settings kept, {3} moved, {4} removed, {5} skipped — backup in {6}", replaced, added, kept, moved, deleted, skipped, BackupFolder));
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
    public static void ApplySelfReplaceAndRestart(string args)
    {
        var exe = Application.ExecutablePath;
        var cmd = "/c timeout /t 2 /nobreak >nul & move /y \"" + exe + ".new\" \"" + exe + "\" & start \"\" \"" + exe + "\" " + args;
        Process.Start(new ProcessStartInfo("cmd.exe", cmd) { WindowStyle = ProcessWindowStyle.Hidden, CreateNoWindow = true, UseShellExecute = false });
        Application.Exit();
    }
}

// ---------------------------------------------------------------- UI
class MainForm : Form
{
    static readonly Color BG = Color.FromArgb(0x1A, 0x21, 0x30), PANEL = Color.FromArgb(0x22, 0x2B, 0x3C), FIELD = Color.FromArgb(0x11, 0x16, 0x20),
        RED = Color.FromArgb(0xE2, 0x37, 0x44), YEL = Color.FromArgb(0xF5, 0xC5, 0x42), TXT = Color.FromArgb(0xE8, 0xEC, 0xF2), DIM = Color.FromArgb(0xA6, 0xB0, 0xC0), BTN = Color.FromArgb(0x3A, 0x46, 0x5C), OK = Color.FromArgb(0x3C, 0xC1, 0x7A);

    Label lblInstalled, lblLatest, lblState, lblStatus, lblSub;
    RichTextBox txtNotes; TextBox txtGame;
    Button btnMain, btnRestore, btnBackups, btnCheck, btnCredits, btnBrowse, btnLog;
    ComboBox cbDisplay; Label lblDisplay;
    ProgressBar bar;
    public static string GameOverride;
    Manifest manifest; string game = ""; string installed = ""; bool busy; readonly bool updateMode;

    public MainForm(bool updateMode)
    {
        this.updateMode = updateMode;
        Text = Cfg.PackName + " Installer " + Cfg.AppVersion; BackColor = BG; ForeColor = TXT;
        Font = new Font("Segoe UI", 10f); ClientSize = new Size(760, 676); StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedSingle; MaximizeBox = false;
        AutoScaleMode = AutoScaleMode.Dpi; AutoScaleDimensions = new SizeF(96f, 96f);
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
        Build();
        Shown += async (s, e) => { DetectGame(); await CheckAsync(); };
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
        txtGame.TextChanged += (s, e) => { game = txtGame.Text.Trim(); RefreshInstalled(); };
        Controls.Add(txtGame);
        btnBrowse = B("Browse", x + w - 120, 330, 120, 34, BTN, (s, e) => Browse());

        btnMain = B("CHECKING…", x, 384, w, 56, RED, async (s, e) => await MainAction(), true);
        bar = new ProgressBar { Left = x, Top = 450, Width = w, Height = 8, Style = ProgressBarStyle.Continuous, Visible = false }; Controls.Add(bar);
        lblStatus = L("", x, 464, w, 9.5f, false, DIM);

        lblDisplay = L("Display mode", x, 486, 120, 10f, true); lblDisplay.Top = 489;
        cbDisplay = new ComboBox { Left = x + 120, Top = 486, Width = 360, DropDownStyle = ComboBoxStyle.DropDownList, BackColor = FIELD, ForeColor = TXT, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", 10f) };
        cbDisplay.Items.AddRange(new object[] { "Fullscreen (game setting)", "Window (with borders)", "Borderless fullscreen (recommended)" });
        cbDisplay.SelectedIndexChanged += (s, e) => { if (!busy && cbDisplay.Enabled && cbDisplay.Tag == null) { try { Util.WriteDisplayMode(game, cbDisplay.SelectedIndex); Status("Display mode: " + cbDisplay.Text + " — applied at the next game launch (F11 in game switches too)."); } catch (Exception ex) { Status("Display mode not saved: " + ex.Message); } } };
        Controls.Add(cbDisplay);
        btnRestore = B("Restore backup", x, 532, 150, 40, BTN, async (s, e) => await RestoreAction());
        btnBackups = B("Backups folder", x + 154, 532, 150, 40, BTN, (s, e) => OpenBackups());
        btnCheck = B("Check again", x + 308, 532, 130, 40, BTN, async (s, e) => await CheckAsync());
        btnLog = B("Log", x + 442, 532, 80, 40, BTN, (s, e) => { try { Process.Start("notepad.exe", Util.LogPath); } catch { } });
        btnCredits = B("Credits & Thanks", x + 526, 532, w - 526, 40, BTN, (s, e) => Credits());
        if (Cfg.PatreonUrl != "")
        {
            var bp = B("♥  Support us on Patreon", x + w - 230, 44, 230, 36, Color.FromArgb(0xF9, 0x66, 0x54), (s, e) => { try { Process.Start(Cfg.PatreonUrl); } catch { } });
            bp.Font = new Font("Segoe UI", 10f, FontStyle.Bold); bp.BringToFront();
        }
        L("Installer " + Cfg.AppVersion + "  ·  " + Cfg.ProjectUrl.Replace("https://", ""), x, 592, w, 9f, false, DIM);
        L("The pack contains no Steam / DLC files. Your .ini settings are kept on every update.", x, 614, w, 9f, false, DIM);
        L("Made with ♥ for the DOA5LR community — original Auto Installer by BRG Hades.", x, 640, w, 9f, false, DIM);
    }

    void SetBusy(bool b) { busy = b; foreach (var c in new Control[] { btnMain, btnRestore, btnBackups, btnCheck, btnBrowse, txtGame }) c.Enabled = !b; bar.Visible = b; if (!b) bar.Value = 0; }
    void Status(string s) { if (InvokeRequired) { BeginInvoke(new Action<string>(Status), s); return; } lblStatus.Text = s; }
    void Progress(int p) { if (InvokeRequired) { BeginInvoke(new Action<int>(Progress), p); return; } bar.Value = Math.Max(0, Math.Min(100, p)); }
    bool Confirm(string t, string m) { if (InvokeRequired) return (bool)Invoke(new Func<string, string, bool>(Confirm), t, m); return MessageBox.Show(this, m, t, MessageBoxButtons.OKCancel, MessageBoxIcon.Warning) == DialogResult.OK; }

    void DetectGame()
    {
        game = GameOverride ?? Util.FindGameFolder(); txtGame.Text = game;
        if (game != "") Util.LogPath = Path.Combine(game, Cfg.LogName);
        Util.Log("--- " + Cfg.PackName + " Installer " + Cfg.AppVersion + (updateMode ? " (--update)" : "") + " game=" + (game == "" ? "(not found)" : game));
        if (game == "") { lblSub.Text = "Not found — click Browse and pick the folder that contains game.exe."; lblSub.ForeColor = YEL; }
        RefreshInstalled();
    }
    void RefreshInstalled()
    {
        bool ok = game != "" && File.Exists(Path.Combine(game, Cfg.GameExe));
        installed = ok ? Util.InstalledVersion(game) : "";
        lblInstalled.Text = !ok ? "—" : installed == "" ? "not installed" : installed == "old" ? "old pack (< 0.3.2)" : installed;
        if (cbDisplay != null)
        {
            int m = ok ? Util.ReadDisplayMode(game) : -1;
            cbDisplay.Tag = "sync"; cbDisplay.Enabled = m >= 0; cbDisplay.SelectedIndex = m >= 0 ? m : 2; cbDisplay.Tag = null;
            lblDisplay.ForeColor = m >= 0 ? TXT : DIM;
        }
        txtGame.ForeColor = ok || game == "" ? TXT : RED;
        UpdateState();
    }
    void UpdateState()
    {
        bool ok = game != "" && File.Exists(Path.Combine(game, Cfg.GameExe));
        if (manifest == null) { btnMain.Text = "CHECKING…"; btnMain.Enabled = false; return; }
        btnMain.Enabled = ok && !busy && manifest.Url != "";
        if (!ok) { lblState.Text = "Select the game folder"; lblState.ForeColor = YEL; btnMain.Text = "SELECT THE GAME FOLDER FIRST"; btnMain.BackColor = BTN; return; }
        if (installed == "") { lblState.Text = "Ready to install"; lblState.ForeColor = YEL; btnMain.Text = "INSTALL MOD PACK " + manifest.Version; btnMain.BackColor = RED; }
        else if (installed == "old" || Util.CmpVer(installed, manifest.Version) < 0) { lblState.Text = "Update available"; lblState.ForeColor = YEL; btnMain.Text = "UPDATE TO " + manifest.Version; btnMain.BackColor = RED; }
        else { lblState.Text = "Up to date ✔"; lblState.ForeColor = OK; btnMain.Text = "REINSTALL " + manifest.Version + " (repair)"; btnMain.BackColor = BTN; }
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
            var notes = new List<string>(); if (manifest.Notes != "") notes.Add(manifest.Notes); notes.AddRange(manifest.NoteLines.Select(n => "• " + n));
            txtNotes.Text = string.Join("\r\n", notes);
            Util.Log("version.txt: latest " + manifest.Version + " installed " + (installed == "" ? "(none)" : installed) + " url " + manifest.Url);
            UpdateState();
            await SelfUpdateCheck();
            if (updateMode)
            {
                bool outdated = installed != "" && (installed == "old" || Util.CmpVer(installed, manifest.Version) < 0);
                if (!outdated) { Util.Log("--update: already up to date, exiting"); Close(); return; }
                if (Snoozed(manifest.Version)) { Util.Log("--update: " + manifest.Version + " snoozed by the player, exiting"); Close(); return; }
                Activate(); TopMost = true; TopMost = false;
                if (MessageBox.Show(this, Cfg.PackName + " " + manifest.Version + " is available (you have " + installed + ").\r\n\r\n" + txtNotes.Text + "\r\n\r\nUpdate now?  (No = ask again tomorrow)", "Update available", MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes) await MainAction();
                else { Snooze(manifest.Version); Close(); }
            }
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
            Engine.ApplySelfReplaceAndRestart(updateMode ? "--update" : "");
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
            await Task.Run(() => eng.InstallZip(zip, manifest));
            RefreshInstalled();
            Status("Done. " + (eng.FreshInstall ? "Installed " : "Updated to ") + manifest.Version + " — backup: " + Path.GetFileName(eng.BackupFolder));
            var msg = (eng.FreshInstall ? "Installed " : "Updated to ") + Cfg.PackName + " " + manifest.Version + ".\r\n\r\n" + eng.Report.Split('\n').Where(l => l.Contains("kept your") || l.Contains("removed obsolete") || l.Contains("moved ")).Select(l => l.Substring(l.IndexOf("  ") + 2).Trim()).DefaultIfEmpty("").Aggregate((a, b) => a + "\r\n" + b).Trim();
            msg += (eng.FreshInstall ? "\r\n\r\nRead READ-ME-FIRST-EN.txt in the game folder once (controller setup, lobby key)." : "") + "\r\n\r\nYou can start the game.";
            MessageBox.Show(this, msg.Trim(), "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
            if (eng.SelfReplaced) Engine.ApplySelfReplaceAndRestart("");
            else if (updateMode) Close();
        }
        catch (OperationCanceledException ex) { Status(ex.Message); Util.Log(ex.Message); }
        catch (Exception ex) { Status("Failed: " + ex.Message); Util.Log("FAILED: " + ex); MessageBox.Show(this, ex.Message + (eng.BackupFolder != null ? "\r\n\r\nA backup was made before the change: " + eng.BackupFolder + "\r\nUse Restore backup if something looks wrong." : ""), "Installation failed", MessageBoxButtons.OK, MessageBoxIcon.Error); }
        finally { SetBusy(false); UpdateState(); }
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
        try { await Task.Run(() => eng.Restore(pick)); RefreshInstalled(); Status("Backup " + Path.GetFileName(pick) + " restored."); MessageBox.Show(this, "Backup restored.", "Restore backup", MessageBoxButtons.OK, MessageBoxIcon.Information); if (eng.SelfReplaced) Engine.ApplySelfReplaceAndRestart(""); }
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
            if (d.ShowDialog(this) == DialogResult.OK) { txtGame.Text = d.SelectedPath; if (File.Exists(Path.Combine(d.SelectedPath, Cfg.GameExe))) { Util.LogPath = Path.Combine(d.SelectedPath, Cfg.LogName); lblSub.Text = "Game folder set."; lblSub.ForeColor = DIM; } else MessageBox.Show(this, "game.exe is not in this folder.", "Game folder", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
    }
    void OpenBackups()
    {
        var d = game == "" ? "" : Path.Combine(game, Cfg.BackupDir);
        if (d == "" || !Directory.Exists(d)) { MessageBox.Show(this, "No backup yet. One is created automatically at every install / update.", "Backups", MessageBoxButtons.OK, MessageBoxIcon.Information); return; }
        Process.Start("explorer.exe", "\"" + d + "\"");
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
            "Installer " + Cfg.AppVersion + " — source in the pack repository: " + Cfg.ProjectUrl + "\r\n" +
            "Testers and everyone in the DOA5LR lobbies: thank you.\r\n\r\n" +
            "Privacy: the public pack sends nothing anywhere. UpdateCheck only downloads version.txt from GitHub.\r\n" +
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
        string gameArg = null; bool auto = args.Any(a => a.Equals("--auto", StringComparison.OrdinalIgnoreCase));
        for (int i = 0; i + 1 < args.Length; i++)
        {
            if (args[i].Equals("--manifest", StringComparison.OrdinalIgnoreCase)) Cfg.VersionUrl = args[i + 1];
            if (args[i].Equals("--game", StringComparison.OrdinalIgnoreCase)) gameArg = args[i + 1];
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
                var zip = eng.DownloadPack(m); eng.InstallZip(zip, m);
                Util.Log("auto: OK " + m.Version); Environment.Exit(0);
            }
            catch (Exception ex) { Util.Log("auto: FAILED " + ex.Message); Environment.Exit(1); }
        }
        MainForm.GameOverride = gameArg;
        // leftover from a previous self-update
        try { var n = Application.ExecutablePath + ".new"; if (File.Exists(n) && new FileInfo(n).LastWriteTimeUtc < DateTime.UtcNow.AddMinutes(-10)) File.Delete(n); } catch { }
        Util.SetupTls();
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainForm(updateMode));
    }
}
