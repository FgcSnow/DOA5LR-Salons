# DOA5LR-Salons 0.3.13 — Danger Zone + The Crimson 1 & 2

**New stages on PC: Danger Zone, The Crimson 1 and The Crimson 2 (PS4 versions), offline and online, Random included.**

## What's new

- **Three PS4 stages:** pick them by hand in the stage select (proper thumbnails; Crimson 1 and 2 share one slot, switch the variant in Solo), or tick them in the game's **Random** filter (three new check boxes). The original stages are all still there.
- **Installer 1.3.3 adds a "Maps" check box, on by default.** Untick it to leave the stages out (their files are removed, your .ini settings are kept); tick it again to get them back.
- **⚠️ Online, everyone in the room (players and spectators) needs the maps.** Update before joining rooms that use them. A player without the maps loads another stage (the Dojo) instead: no crash expected, but the match will very likely desync (not tested).
- **AutoLink works with the maps**, but only put character folders in the `AutoLink` folder (plus `_Movie`, `_Texture`, `_Sound`, `_Stages`). During the tests, a player crashed after the first fight because of modding tools stored in `AutoLink\_Modding`; once they were moved out of the game folder, the crashes stopped.

## New: DOA5LR-Diagnostic

Open `DOA5LR-Diagnostic\DOA5LR Diagnostic.cmd` in your game folder:

- **Check**: stage files, lobby modules (rooms, invites, JoinFix, wired/Wi-Fi, updater), other mods, AutoLink folders.
- **Play (with the probe)**: starts a small read-only observer (no hook, no injection) that records the stage, fight and how the game exits, then starts the game through Steam.
- **Send my logs**: builds a ZIP on your Desktop, shows what's inside, and sends it to FGCsnow on Discord **only after you confirm**. Never: IP, SteamID, chat, controller inputs or saves. An optional `.dmp` shows where the game crashed (it holds a piece of the game's memory and may include your Steam name; untick it if you prefer).
- **Detailed crash reports** (optional, admin rights once): Windows keeps a small `.dmp` when the game crashes.

The stage modules write local logs next to the game (effects, stage events) for crash reports. Nothing is sent unless you click **Send my logs**.

## Repair after an antivirus

The installer now also checks `scripts\DOA5LR-JoinFix.asi` and the main stage modules. If an antivirus removed one, it offers to repair the pack when you close the game.

## Everything else

Every other pack file is **byte-identical to 0.3.12** (Lobby, JoinFix, InviteFix, WiFi-Wired-Detector, UpdateCheck, Borderless, 60 fps, Replay Takeover 2.6, controls app). The download is bigger (about 270 MB) because it now contains the stages.

**Pre-release testers (dz-crimson-test-r4/r5):** don't use the pre-release window's "Remove the maps" any more; untick **Maps** in the installer instead.

## Update

Close DOA5LR and run the installer (or accept the update notice after closing the game). Accept the installer update to 1.3.3 first. Your settings and component choices are kept.

| Download | Use it for |
| --- | --- |
| [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.13/DOA5LR-Salons-Installer.exe) | Recommended for installing, updating or repairing the pack. |
| [DOA5LR-Salons-0.3.13.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.13/DOA5LR-Salons-0.3.13.zip) | Full pack archive for a new setup (includes the installer). |

## Signing

The installer and the Diagnostic probe are signed with the project's existing self-signed certificate (not a public certification authority; no Windows trust or antivirus guarantee).

[Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)
