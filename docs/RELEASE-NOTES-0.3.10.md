# DOA5LR-Salons 0.3.10 — Rooms that nobody could join are fixed

**Everyone who creates rooms should update: the fix works on the room host's side.**

## The bug

Sometimes a player accepts your invite (or joins from the room list), enters the room, and **leaves on their own after about 30 seconds**. Everyone else trying the same room gets the same result until the room is closed and created again.

Cause, found on 25/09/2026: when a room is created, DOA5LR writes a random network encryption key into the Steam room data **as text**. When one of its random bytes is 0, Steam cuts the key at that byte. Joining players read a broken key, their join request cannot be read by the host, and the game gives up after its 30-second timeout. It happens in about **1 room in 11**, at random — private or public makes no difference.

## The fix: DOA5LR-JoinFix 0.3 (new, always installed)

| Part | What it does | Default |
| --- | --- | --- |
| **KeyFix** | Just before *your* room is published, zero bytes in the key are replaced both in the game's key and in the published copy. The game reads its key again for every packet, so everything stays consistent. Rooms whose key has no zero byte are not touched. | On |
| **AcceptMembers** | Always accepts the network link of players who are in your room. | On |
| **InviteRetry** | After you accept an invite, asks Steam again for the room data if it has not arrived (every 3 s, 5 times max). | On |
| **F7 = copy room link** | In a room, press F7: its `steam://joinlobby/...` link is copied to the clipboard (high beep). Paste it on Discord; a click joins your room while the game is running. Private rooms have no "Join game" button in Steam. | F7 |
| **FastFail** | While joining, stops at once with the game's own error message when Steam reports the host cannot be reached, instead of waiting up to 90 s. Not yet seen in real use. | Off |

Settings: `scripts\DOA5LR-JoinFix.ini`. No log file, nothing is sent anywhere. Source in `scripts\JoinFix-Source`.

Validated in real play on 25/09/2026: a room whose key contained a zero byte was repaired and a friend joined in 0.25 s; the same situation without the fix had made them leave after 30 s.

Every other file is **byte-identical to 0.3.9**, including installer 1.3.1 and the Lobby, InviteFix and network-tag plugins.

## Update

Close DOA5LR and run the installer (or accept the in-game update notice after closing the game). Your settings and component choices are kept.

| Download | Use it for |
| --- | --- |
| [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.10/DOA5LR-Salons-Installer.exe) | Recommended for installing, updating or repairing the pack. |
| [DOA5LR-Salons-0.3.10.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.10/DOA5LR-Salons-0.3.10.zip) | Full pack archive for a new setup (includes the installer). |

The controls app (portable) is unchanged: use the 0.3.9 download if you need it.

## Signing

JoinFix is signed with the project's existing self-signed certificate (not a public certification authority; no Windows trust or antivirus guarantee). Microsoft Defender reported no threat on the release files (signatures 1.459.398.0, 25/09/2026).

[Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)
