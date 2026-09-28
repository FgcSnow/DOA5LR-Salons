# DOA5LR-Salons 0.3.12 — Lobby crash fix (Replay Takeover 2.6)

**If you updated to 0.3.11 and the game crashed in lobbies, update to 0.3.12.**

## What was wrong

After 0.3.11, some players crashed while browsing the lobby list or creating a room (Windows reported an access violation inside `game.exe`, in the game's own memory-release code). Going back to 0.3.10 made the crashes stop, and the only change in 0.3.11 was Replay Takeover 2.5.

Replay Takeover only does something during replays, but to save and restore checkpoints it hooks parts of the game that run **all the time**: every memory allocation of the game (on every thread), the stage physics, the frame loop and the simulation step counter. In 2.5 those hooks stayed active everywhere, including in lobbies and online matches, where the game is busy with the network. We could not prove which hook triggered the crash, so the fix removes all of them from online play.

## The fix: Replay Takeover 2.6 sleeps while you are online

- As soon as you are online (lobby list, room, online match, spectating), every hook lets the game run **untouched**: no allocation tracking, no physics or stage notes, no frame or input handling. The game's online state is read the same way as the 60 fps mod does since 0.3.6 (tested in lobbies).
- **F5 / F6 / F7 are ignored online**, so they are left to the other mods (F7 = copy the room link, JoinFix).
- Back offline, Replay Takeover wakes up and works **exactly as in 2.5**. Replays cannot be played online, so nothing is lost.
- The local `DOA5LR-ReplayTakeover.log` now shows `En ligne : module en veille` when you go online and `Hors ligne : module actif (…, 0 actions de replay vues en ligne)` when you come back — handy for crash reports.

Tested before release by the player who had the crashes: a lobby session with a room created and joined, no crash, log confirming that the mod slept the whole time.

## Everything else

Every other pack file is **byte-identical to 0.3.11** (installer 1.3.2 unchanged: your Replay Takeover check box choice is kept).

## Update

Close DOA5LR and run the installer (or accept the in-game update notice after closing the game). Your settings and component choices are kept.

| Download | Use it for |
| --- | --- |
| [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.12/DOA5LR-Salons-Installer.exe) | Recommended for installing, updating or repairing the pack. |
| [DOA5LR-Salons-0.3.12.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.12/DOA5LR-Salons-0.3.12.zip) | Full pack archive for a new setup (includes the installer). |

## Signing

Replay Takeover and the installer are signed with the project's existing self-signed certificate (not a public certification authority; no Windows trust or antivirus guarantee).

[Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)
