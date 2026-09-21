# DOA5LR-Salons — sources

Everything we build for the pack is here, in the exact form used for the releases. Every plugin is a
single C file (32-bit Windows DLL renamed `.asi`, loaded by Ultimate ASI Loader from the game's `scripts\`
folder); the installer is a single C# file compiled with the C# compiler that ships in Windows.

| Folder | Builds | What it does |
|---|---|---|
| `InviteFix/` | `DOA5LR-InviteFix.asi` | Fixes the Invite button of the Lobby module (Steam relay stub) |
| `WiFi-Wired-Detector/` | `DOA5LR-WiFi-Wired-Detector.asi` | Wired / Wi-Fi tag next to names (0.8.7: ping display removed), netcode stats |
| `60fps-menus/` | `DOA5LR-60fps-menus.asi` | 60 fps menus, intros, win poses, story cutscenes |
| `Borderless/` | `DOA5LR-Borderless.asi` | Borderless window by default, F11 cycles modes |
| `UpdateCheck/` | `DOA5LR-UpdateCheck.asi` | Reads `version.txt`, opens the installer at game exit when a newer pack exists |
| `Installer/` | `DOA5LR-Salons-Installer.exe` | One-click install / update / restore (WinForms, .NET Framework 4.8) |
| `tools/` | — | `sign.ps1` (Authenticode signing) and our public signing certificate |

**Not here:** the Lobby module (`DOA5LR-Lobby.asi` 0.9.0) is a third-party community build — we ship the
binary as received and do not hold its source. Ultimate ASI Loader, AutoLink and Xidi are upstream projects
(see the credits in the main README).

## Build it yourself

### Plugins (`.asi`)

Requirements: Windows and **LLVM-MinGW** (the game is 32-bit, the scripts use `i686-w64-mingw32-gcc`).

```bat
winget install MartinStorsjo.LLVM-MinGW.UCRT
```

Then run `build.cmd` in a component folder, or `build-all.cmd` here. Each script finds the compiler through
the `LLVM_MINGW` variable, `PATH`, or the winget install location.

Every plugin produces two files:

- `DOA5LR-<name>.asi` — the **release** build, compiled with `-DNO_LOG`: the logging code is not compiled in,
  the plugin writes no file. This is what the pack ships.
- `DOA5LR-<name>-debug.asi` — same code with a local log file next to the `.asi`, for troubleshooting only.

The release builds are **reproducible**: the link timestamp is disabled (`-Wl,--no-insert-timestamp`), so the
same LLVM-MinGW version yields byte-for-byte the same `.asi`. To check a release: build, then compare your
hash with `SHA256SUMS-reproducible-build.txt` attached to the GitHub release (the files inside the pack carry an
Authenticode signature appended after the code, so their hash differs from an unsigned build — see below).

### Installer (`.exe`)

No SDK needed: `Installer\build.cmd` uses `%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe`, present on
every Windows 10/11. `make_icon.py` regenerates `installer.ico` (optional, Python + Pillow).

The built-in csc is the legacy C# 5 compiler and has no `/deterministic` option, so the `.exe` is not
byte-for-byte reproducible (module ID and timestamp change on each build). The code is 100 % in
`Installer.cs`, read it — that is the point.

## Code signing

Release binaries we build are signed with a **self-signed** certificate (`tools\DOA5LR-Salons-signing.cer`,
subject `CN=FGCsnow - DOA5LR-Salons`, SHA-256, RFC 3161 timestamp). This is not a CA-issued certificate: Windows
shows the chain as "not trusted", and SmartScreen ignores it. It only lets you check that a file was not
altered since we signed it, and it lowers some heuristic antivirus detections a bit. Check a file with:

```powershell
Get-AuthenticodeSignature .\DOA5LR-Salons-Installer.exe | Format-List Status, SignerCertificate
```

Expected: `Status : UnknownError` (untrusted root — normal for self-signed) and the signer thumbprint
`0EBE9F4F8879992F594F99E7B38C4B024A68F978`. **Do not install this certificate in your trusted roots**, it is not
needed. Anyone can sign their own builds with `tools\sign.cmd <file>` (it creates its own certificate;
set `SIGN_SUBJECT` to choose the name).

## Why antivirus tools flag ASI plugins

An `.asi` is a DLL loaded into `game.exe` that patches code in memory — that is exactly what a game mod
does, and also what some malware does, so heuristic engines flag the pattern. None of our plugins reads
anything outside the game, sends anything anywhere, or writes files (release builds). Read the code, build it,
compare the hashes. If a false positive bothers you, submit the file to your antivirus vendor
(Microsoft: https://www.microsoft.com/wdsi/filesubmission, Kaspersky: https://opentip.kaspersky.com).
