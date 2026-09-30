# DOA5LR-Salons 0.3.15 — emergency online Random fix

RandomStages 2.1 in 0.3.14 used an incorrect address to detect online play. Extra PS4 stages could therefore be selected with players who did not have them, risking an endless loading screen.

- RandomStages 2.2 corrects online detection and, with `Online=0` (default), excludes extra stages unless every lobby member reports map support. Ranked play/no lobby uses native Random. `Online=1` remains an explicit bypass; existing INI settings are preserved, so keep `Online=0` for the check.
- PS4 costume hairstyle choices/order corrected for 13 of the 15 costumes, including fixed hair for Ayane 054 and specific hair for Kasumi 054. These settings are now in the automatic skins download.
- Installer 1.3.8 accepts missing `appid` and `orgapi` in an otherwise compatible existing local loader configuration. It validates the default original DLL and preserves user settings. No Steam/proxy DLLs are distributed.

Validation: installer regression tests passed; archive checksums, integrity inventories and isolated installation of the real archives checked. Snow confirmed mixed-lobby exclusion in game and four targeted hairstyle menu tests. Positive extra-stage selection between two updated players remains to be confirmed; not all hairstyle combinations have been combat-tested.

Update using DOA5LR-Salons-Installer.exe. Keep PS4 skins selected if you use the native costume pack. Existing settings are kept and replaced files are backed up.
