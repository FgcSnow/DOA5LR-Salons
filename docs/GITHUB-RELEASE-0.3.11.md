# DOA5LR-Salons 0.3.11 — Replay Takeover in the pack

**Replay Takeover 2.5, by BonuStage & FGCsnow, now comes with the pack and the installer.**

## Replay Takeover 2.5

While a Dead or Alive 5 Last Round replay plays, you take control of one of the two players and replay the situation against what the opponent really did. A checkpoint is saved the moment you take control, and you can jump back to it instantly as many times as you want. Broken walls, tables and benches come back as they were at the checkpoint.

| Button (PlayStation pad) | Keyboard | Action |
| --- | --- | --- |
| **L2** | F5 | During the replay: take control (if both players are human, pick P1 or P2) |
| **Select** | | Jump back to the checkpoint and keep control |
| **Start** | | Jump back and give control back to the replay |
| **L3** | F7 | Jump back with the stage rebuilt |

Buttons can be changed in `DOA5LR-ReplayTakeover.ini`. Full guide (English): `scripts\REPLAY-TAKEOVER-EN.txt`. Source: `scripts\ReplayTakeover-Source`. It only acts while a replay plays.

## Installer 1.3.2: a check box, on by default

- New **"Replay Takeover"** check box in the Components list, **checked by default**. Untick it to leave the mod out: its files are removed, your `.ini` is kept. The choice is remembered for every future update.
- The mod installs next to `game.exe` (`DOA5LR-ReplayTakeover.asi` + `DOA5LR-ReplayTakeover.ini`), exactly where its own installer puts it. If you already installed it by hand, it is simply updated to 2.5 and your settings are kept — never loaded twice.
- Installer 1.1–1.3.1 offer the 1.3.2 update first; accept it to get the check box. (An older installer that is not updated installs Replay Takeover without the check box.)

## Privacy

Replay Takeover writes a local `DOA5LR-ReplayTakeover.log` next to the game (reset at each launch, useful for crash reports). It sends nothing anywhere.

## Everything else

Every other pack file is **byte-identical to 0.3.10** (JoinFix, Lobby, InviteFix, network tag, controls app…).

## Update

Close DOA5LR and run the installer (or accept the in-game update notice after closing the game). Your settings and component choices are kept.

| Download | Use it for |
| --- | --- |
| [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.11/DOA5LR-Salons-Installer.exe) | Recommended for installing, updating or repairing the pack. |
| [DOA5LR-Salons-0.3.11.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.11/DOA5LR-Salons-0.3.11.zip) | Full pack archive for a new setup (includes the installer). |

## Signing

Replay Takeover and the installer are signed with the project's existing self-signed certificate (not a public certification authority; no Windows trust or antivirus guarantee).

[Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)
