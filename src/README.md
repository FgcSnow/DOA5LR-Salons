# Build DOA5LR-Salons 0.3.9

These instructions build the maintained components of DOA5LR-Salons 0.3.9.
They do not build the third-party Lobby, AutoLink or Xidi. Build and test work
is separate from publishing a release or changing the public update manifest.

## Components

| Folder | Output | Purpose |
| --- | --- | --- |
| `Installer` | Installer 1.3.1 (.exe) | Setup, input chooser, backups, local diagnostic export and manifest compatibility |
| `InputLab/source` | Controls, Finder, inventory, companion, bridge | Optional keyboard remapping and local controller profiles |
| `UpdateCheck` | UpdateCheck 1.1 (.asi) | New-version banner and installer prompt after game exit |
| `JoinFix` | JoinFix 0.2 (.asi), pack 0.3.10 | Room join fix: repairs the room encryption key published by the host (see `JOINFIX-EN.txt`) |
| `InviteFix`, `WiFi-Wired-Detector`, `60fps-menus`, `Borderless` | Existing .asi plugins | Unchanged since 0.3.8 |
| `tools` | Signing scripts and public certificate | Optional signing for maintained builds |

## Windows toolchain

Use Windows with .NET Framework 4.8, Python 3 and LLVM-MinGW UCRT x86 tools.
The game is 32-bit. The C# compiler is `%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe`.
Set `LLVM_MINGW` to your toolchain folder if it is not in the WinGet location.
The 0.3.9 build toolchain uses LLVM-MinGW 20260616 and the Windows C# compiler.

From the repository root, run:

```powershell
& .\src\Installer\build.cmd
& .\src\UpdateCheck\build.cmd
& .\src\JoinFix\build.cmd
& .\src\InputLab\source\build.ps1
```

The InputLab build runs its remapping, DirectInput wrapper and source-switching
unit tests. Generated binaries and test fixtures are ignored by Git. The InputLab
build writes its tools in `src/InputLab` and its bridge in `src/InputLab/payload`.
It never writes into a real game installation.

## Isolated checks

Installer tests create fake game folders and never launch Steam. Tests that verify
the original Xidi require the unmodified published 0.3.8 ZIP. Download it from the
project release and set `DOA5LR_BASE_ZIP` to its path. Its expected SHA-256 is
`6bffba7fdef2713d433879f01dfe2e0d9ca908bd8f8ec9be17c5e86f0cc14061`.

```powershell
$env:DOA5LR_BASE_ZIP = 'C:\Downloads\DOA5LR-Salons-0.3.8.zip'
python .\src\Installer\test\test_inputlab.py
python .\src\Installer\test\test_launch_input.py
python .\src\Installer\test\test_local_manifest.py
python .\src\Installer\test\test_diagnostic_bundle.py
python .\src\InputLab\test\test_keyboard_startup.py
python .\src\InputLab\test\optional-runtime\test_optional_runtime.py
python .\src\UpdateCheck\test\test_banner.py
```

The last test loads the actual UpdateCheck DLL into fake game processes, reads
the public version manifest over HTTPS and may show a two-second test banner.
It checks the outdated, current and banner-disabled cases. A harmless installer
stub records `--update`; neither Steam nor the real game is started.

## Package a local preview

Keep the base ZIP unmodified. After building, use the repository's packaging tool:

```powershell
python .\tools\build_inputlab_preview.py --base-zip $env:DOA5LR_BASE_ZIP --finder .\src\InputLab\DOA5LR-Detecteur.exe
```

Outputs go into `preview-output`. The local manifest names its neighboring ZIP,
so the files can be moved together. Start the candidate explicitly:

```powershell
& .\preview-output\DOA5LR-Salons-Installer-InputLab-draft.exe --manifest "$PWD\preview-output\version-0.3.9-inputlab-draft.txt"
```

Running the installer without `--manifest` uses the official published manifest.
The preview builder performs no upload, release creation or real-game writes.

## Package version 0.3.9

After the preview inputs and public documentation are ready, create the stable
delivery from the repository root:

```powershell
python .\tools\build_release_039.py --preview-dir 'C:\Build\DOA5LR-Salons-0.3.9-Preview' --out 'C:\Build\DOA5LR-Salons-0.3.9-Release'
```

Use your actual preview and output directories. The stable build uses the current
installer source, including the 1.3.1 compatibility fix. The same release installer
is supplied as a separate download and retained inside the full pack ZIP so
UpdateCheck can find it after a new installation. The stable manifest uses the
compatible `optional_v2` entry for InputLab so an older installer can offer its own
update without rejecting an unknown component.

Build output alone does not publish GitHub assets or change the public update
channel. Verify the exact signed outputs, archive contents, manifests and hashes
before publication. Scan those final artifacts and record the result separately;
a previous preview scan does not cover newly signed or rebuilt files.

## Hashes and signing

Pack archives include SHA-256 inventories. The original Xidi is verified before
activation and kept for restoration. Generic keyboard defaults are packaged;
the tester's personal bindings are not included.

The component build commands above produce unsigned development outputs. The
0.3.9 installer and InputLab release builds use the project's existing self-signed
code-signing certificate. Signing changes binary hashes and must happen before
packaging, final checksums and the recorded artifact scan. The helper scripts are
in `src/tools`; signing requires the matching private key in the maintainer's
certificate store. Never distribute that private key.

A self-signed certificate is not a public-CA trust guarantee and does not guarantee
SmartScreen or antivirus acceptance. Do not add it to Trusted Root authorities.
Third-party binaries retain their upstream signing status. UpdateCheck's unsigned
build suppresses the PE link timestamp, but C# and InputLab outputs are not claimed
to be byte-for-byte reproducible. Compare source, toolchain and published artifact
hashes rather than treating a hash alone as proof of safety.

Lobby 0.9.0 is an external binary whose source is not in this repository. It writes
a local log. Diagnostic export is manual, includes only named existing logs and a
small report, and uploads nothing. See the main README for the full network and
privacy scope.
