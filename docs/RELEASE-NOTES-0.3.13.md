# DOA5LR-Salons 0.3.13 — Danger Zone + The Crimson 1 & 2

## New stages
- **Danger Zone**, **The Crimson 1** and **The Crimson 2** (PS4 versions) on PC: manual pick with proper thumbnails, three new check boxes in the game's Random filter, offline and online. The original stages are unchanged.
- Installer 1.3.3 adds a **Maps** check box, **on by default**. Untick it to leave the maps out: their files are removed and your .ini settings are kept.
- **Online, everyone in the room (players and spectators) needs the maps.**

## AutoLink
AutoLink costumes work with the maps. Only put character folders in `AutoLink` (and `_Movie`, `_Texture`, `_Sound`, `_Stages`). During the tests, a player crashed after the first fight because of modding tools stored in `AutoLink\_Modding`; after moving them out of the game folder, the crashes stopped. The Diagnostic tool warns about unknown folders there.

## DOA5LR-Diagnostic
New folder `DOA5LR-Diagnostic` (open `DOA5LR Diagnostic.cmd`):
- **Check**: maps files, lobby modules (Lobby, JoinFix, InviteFix, WiFi-Wired, UpdateCheck), other mods, AutoLink folders.
- **Play (with the probe)**: starts an external read-only observer (no hook, no injection) that records the stage, fight and network state and how the game exits, then starts the game through Steam.
- **Send my logs**: builds a ZIP (Desktop), shows its content, and sends it to FGCsnow's Discord only after you confirm. Contents: stage/fight timeline, maps modules logs, mod list (names and hashes), AutoLink summary, Windows crash events of the game, and an optional .dmp. Never: IP, SteamID, chat, controller inputs or saves. The .dmp holds a piece of the game's memory and may include your Steam name; untick it if you prefer.
- **Detailed crash reports** (optional, admin rights once): Windows keeps a small .dmp when the game crashes.

## Repair
The installer now also checks `scripts\DOA5LR-JoinFix.asi` and the main maps modules. If an antivirus removed one, the installer offers to repair the pack when you close the game.

## Unchanged
Every other file is byte-identical to 0.3.12 (Lobby, JoinFix, InviteFix, WiFi-Wired-Detector, UpdateCheck, Borderless, 60fps, Replay Takeover 2.6, controls app).

## Download size
The pack ZIP now contains the stages (about 270 MB). A later version will download the stages separately.
