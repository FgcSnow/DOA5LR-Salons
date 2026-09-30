# Release 0.3.15 with Installer 1.3.9

Combines the 0.3.15 map support check and hairstyle corrections with broader x86 costume loader detection. Version 1.3.9 no longer requires the literal configuration filename inside an otherwise recognized loader. Existing DLLs are preserved.

New installer and r2 archives are uploaded to v0.3.15. GitHub digests and sizes match local builds. Archive integrity, unchanged game modules and costume assets, and exact core + maps reconstruction were checked. PS4 installation and rollback tests, component tests and split download tests pass.

Merging this PR activates the production manifest for 0.3.15 and Installer 1.3.9. It supersedes the contents of PRs #11 and #12; no separate merge is needed. Compatibility with every real loader and every hairstyle combination is not established. The separate DebugArchive antivirus report remains unresolved.
