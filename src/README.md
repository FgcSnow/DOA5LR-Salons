# Build the DOA5LR-Salons candidate

This branch prepares the 0.3.9 candidate. The public update manifest stays on
0.3.8 until a release is deliberately published. These instructions build the
maintained components; they do not build the third-party Lobby, AutoLink or Xidi.

## Components

| Folder | Output | Purpose |
| --- | --- | --- |
| `Installer` | Installer 1.3 (.exe) | Setup, input chooser, backups and local diagnostic export |
| `InputLab/source` | Controls, Finder, inventory, companion, bridge | Optional keyboard remapping and local controller profiles |
| `UpdateCheck` | UpdateCheck 1.1 (.asi) | New-version banner and installer prompt after game exit |
| `InviteFix`, `WiFi-Wired-Detector`, `60fps-menus`, `Borderless` | Existing .asi plugins | Unchanged by this candidate |
| `tools` | Signing scripts and public certificate | Optional signing for maintained builds |

## Windows toolchain

Use Windows with .NET Framework 4.8, Python 3 and LLVM-MinGW UCRT x86 tools.
The game is 32-bit. The C# compiler is `%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe`.
Set `LLVM_MINGW` to your toolchain folder if it is not in the WinGet location.
The candidate was built using LLVM-MinGW 20260616 and the Windows C# compiler.

From the repository root, run:

```powershell
& .\src\Installer\build.cmd
& .\src\UpdateCheck\build.cmd
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

## Hashes and signing

Pack archives include SHA-256 inventories. The original Xidi is verified before
activation and kept for restoration. Generic keyboard defaults are packaged;
the tester's personal bindings are not included.

New InputLab and installer candidate binaries are unsigned. Existing maintained
ASI components may carry a self-signed project certificate; it is not a public-CA
trust guarantee. Do not add it to Trusted Root authorities. UpdateCheck's unsigned
build suppresses the PE link timestamp, but C# and InputLab outputs are not claimed
to be byte-for-byte reproducible. Compare source, toolchain and the published
artifact hashes rather than treating a hash alone as proof of safety.

Lobby 0.9.0 is an external binary whose source is not in this repository. It writes
a local log. Diagnostic export is manual, includes only named existing logs and a
small report, and uploads nothing. See the main README for the full network and
privacy scope.
