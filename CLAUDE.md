# DOA5LR-Salons â€” shared notes for contributors and their AI assistants

This file is read automatically by Claude Code when it runs in this repository.
It is the shared context of the team: keep it short, factual and **public-safe**
(this repository is public â€” no personal data, e-mails, tokens, webhooks, private keys,
local paths of one machine, or anything about unofficial ports/cracks/DLC unlockers).

## What the project is

Community mod pack for **Dead or Alive 5 Last Round (PC, Steam, 32-bit game.exe)**,
maintained by FGCsnow & BonuStage. It restores the Lobby menu, fixes Steam invites and
room joins, tags wired/Wi-Fi players, and ships optional display/60 fps/replay modules,
all installed and updated by `DOA5LR-Salons-Installer.exe` from the public `version.txt`.

## Repository layout

| Path | Content |
| --- | --- |
| `src/<Component>/` | Source of each maintained plugin (`.asi` loaded by Ultimate ASI Loader) or tool, with its `build.cmd` / `.ini` / user guide |
| `src/Installer/` | C# (.NET Framework 4.8) installer/updater + its Python tests in `test/` |
| `src/InputLab/` | Controls app, controller finder, keyboard bridge (C#/C++) + tests |
| `src/tools/` | Signing scripts and the **public** certificate only |
| `tools/` | Release builders (`build_release_0XYZ.py`), release tests, `pack_docs.py` |
| `docs/` | Public release notes, GitHub release texts, input guide, bug template |
| `version.txt` | **Live update manifest** read by every installed copy (installer + UpdateCheck) |

Not in this repo: Lobby 0.9.0 (external binary, no source), AutoLink, Xidi, ASI Loader.

## Toolchain

Windows, Python 3, .NET Framework 4.8 `csc.exe`
(`%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe`), LLVM-MinGW UCRT **x86**
(set `LLVM_MINGW` if not in the WinGet location). Everything targets 32-bit.
Details and test commands: `src/README.md`.

## Rules everyone follows

1. **`version.txt` on `main` is production.** Every player's installer reads it. Change it only
   in a release PR, after the ZIP and installer are uploaded to the matching GitHub release and
   their SHA-256/size are verified. A wrong hash or URL breaks updates for everyone.
2. **Work on a branch, merge through a PR.** Name branches after the change
   (`claude/0.3.12-xyz`, `bonustage/rollback-fix`, â€¦). Never force-push `main`.
3. **Releases are built by a script in `tools/`, never by hand.** A builder takes the previous
   published pack, changes only what it announces, keeps every other file byte-identical,
   and must call `pack_docs.pack_guides()` + `check_pack_guides()` (a stale README once
   shipped with the wrong version number).
4. **Test without the real game first.** Installer tests use fake game folders and never start
   Steam. Only after that, test in a real game with the game closed during installation.
5. **No logging or telemetry in public builds** unless it is local, documented and opt-out.
   Nothing is ever uploaded silently.
6. **WiFi-Wired-Detector stays a plain wired/Wi-Fi tag.** No ping display, no "force wired",
   no delay tweaking, no experiments in that plugin. (Other online work â€” room diagnostics,
   join/invite fixes â€” is fine.)
7. **60 fps module stays offline-only.** Running it in online rooms caused desyncs/freezes.
8. **Manifest compatibility:** older installers reject unknown component ids in `optional` /
   `optional_v2` but ignore unknown keys â€” new components go in a new key (`optional_v3`, â€¦).
9. **Signing:** only the maintainer holds the private key; unsigned development builds are
   fine for testing. Sign before computing final hashes. Never commit a `.pfx`/private key.
10. **Binaries are not committed** (`.asi`, `.exe`, zips â€” see `.gitignore`). Release builders
    pin the SHA-256 of any binary they take from outside the repo.

## Game-side facts worth knowing

- Plugins live in `<game>\scripts\` (Replay Takeover lives next to `game.exe`, where it reads its `.ini`).
- User settings are the `.ini` files; the installer keeps them on update (`keep=*.ini`).
- The game's `.text` section is encrypted on disk (Steam stub): reverse-engineer from memory,
  not from the file.
- Crashes at game exit (inside `exit()`, exit code 0) are pre-existing and unrelated to lobbies.

## Where to put shared knowledge

- Decisions, findings, reverse-engineering notes that the whole team needs â†’ `docs/notes/`
  (one Markdown file per topic, dated), then add a one-line pointer here if it changes a rule.
- Personal notes and machine-specific paths â†’ `CLAUDE.local.md` (git-ignored) or your own
  Claude memory, not this file.

## Release preparation, 2026-09-30

- RandomStages and Crimson-VFX sources are private in the team repository, `source/pack-maps/`. Do not reintroduce them into public Git history. The frozen 0.3.14 builder requires `--maps-source` and archived installer 1.3.5 source via `--installer-source`; the PS4 builder uses the validated base pack and current installer 1.3.6.
- Keep the released JoinFix 0.3 in the pack. Experimental JoinFix builds, including 0.4/0.5, are excluded by explicit maintainer instruction.
- Prepared PS4 archives are validated but not yet published. Production manifest updates still follow the release rule above.
