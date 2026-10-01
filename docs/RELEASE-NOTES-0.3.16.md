# DOA5LR-Salons 0.3.16 — correct stage thumbnails, tidier game folder

- **Wrong stage thumbnails fixed.** Since 0.3.13 some tiles showed the picture of another stage while still loading the right one: Lorelei Halloween (DLC), and the lower levels of Scramble, Plant and Circus that you reach with the up arrow on their tile. The stage-select texture had replaced picture slots that belong to those stages. It now changes only one blank placeholder slot the game never shows (The Crimson 1, which also gets its own PS4 picture instead of The Crimson 2's); Danger Zone and The Crimson 2 use the pictures already present in the PC files. Every other picture is the original one, checked against the game's own stage-to-picture table, the tiles' variants and the PS4 table. ExtraStages 2.0.9 and the new texture ship together (each refuses the other's old version and then keeps the native thumbnails).
- **Tidier game folder.** The eleven stage modules are now in `scripts\DOA5LR-Stages\` and their logs in `DOA5LR-Logs\` (old logs are moved there on first start; a log over 4 MB is deleted). Their seven `.ini` files move into `scripts\DOA5LR-Stages\` too, with your settings unchanged (a module still finds an `.ini` left next to `game.exe`). The update removes the old copies in `scripts\` (the same module in two folders would be loaded twice).
- **Installer 1.3.11:** knows the new folder, removes a stage module found in both places, checks the modules where they now are. Older installers offered the update first propose the new installer.
- **DOA5LR-Diagnostic** reads the logs in `DOA5LR-Logs\` too.
- All pack modules are self-signed, the stage modules included.

- **PS4 skins removed from the pack.** The installer no longer offers, downloads, checks or removes them; players who installed them keep their files and their costume loader configuration.

Small update: when your stage data is intact, only about 10 MB are downloaded.

Validation: stage module self-tests, installer test suite (0.3.15 → 0.3.16 upgrade, no duplicate module, settings kept), isolated installation of the real archives, Windows Defender scan of every file. In game on the maintainer's PC: every stage module loaded from the new folder, logs only in `DOA5LR-Logs\`, correct Lorelei Halloween and Attack on Titan thumbnails.

Update with DOA5LR-Salons-Installer.exe (close the game first).
