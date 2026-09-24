$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Path '..\test' -Force | Out-Null
$tool = if ($env:LLVM_MINGW) { Get-Item -LiteralPath (Join-Path $env:LLVM_MINGW 'bin\i686-w64-mingw32-g++.exe') } else { Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW*\llvm-mingw-*\bin\i686-w64-mingw32-g++.exe" | Select-Object -First 1 }
if (!$tool) { throw 'LLVM-MinGW x86 missing' }
$compiler=$tool.FullName
$header=Join-Path $tool.Directory.Parent.FullName 'include\dinput.h'
python generate_wrappers.py $header
if ($LASTEXITCODE) { throw 'Wrapper generation failed' }
& $compiler -std=c++17 -O2 -Wall -Wextra -static -shared bridge.cpp bridge.def -o ..\test\dinput8ex.bin -ldinput8 -ldxguid '-Wl,--kill-at'
if ($LASTEXITCODE) { throw 'Bridge compilation failed' }
& $compiler -std=c++17 -O2 -Wall -Wextra -static test_remap.cpp -o ..\test\test_remap.exe -ldxguid
if ($LASTEXITCODE) { throw 'Test compilation failed' }
& ..\test\test_remap.exe
if ($LASTEXITCODE) { throw 'Remapping tests failed' }
python generate_mock.py $header
if ($LASTEXITCODE) { throw 'Mock generation failed' }
& $compiler -std=c++17 -O2 -static test_com.cpp -o ..\test\test_com.exe -ldinput8 -ldxguid
if ($LASTEXITCODE) { throw 'COM tests compilation failed' }
& ..\test\test_com.exe
if ($LASTEXITCODE) { throw 'COM tests failed' }
& $compiler -std=c++17 -O2 -Wall -Wextra -static test_switch.cpp -o ..\test\test_switch.exe
if ($LASTEXITCODE) { throw 'Switch compilation failed' }
& ..\test\test_switch.exe
if ($LASTEXITCODE) { throw 'Switch tests failed' }
& $compiler -O2 -Wall -Wextra -static list_devices.cpp -o ..\DOA5LR-Peripheriques.exe -ldxguid
if ($LASTEXITCODE) { throw 'Device inventory compilation failed' }
& $compiler -std=c++17 -O2 -Wall -Wextra -static -municode companion_reader.cpp -o ..\DOA5LR-Companion.exe -ldinput8 -ldxguid -lwinmm
if ($LASTEXITCODE) { throw 'Companion reader compilation failed' }
& "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe" /nologo /target:winexe /platform:x86 /out:..\DOA5LR-Commandes.exe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll InputLab.cs
if ($LASTEXITCODE) { throw 'UI compilation failed' }
& "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe" /nologo /target:winexe /platform:x86 /out:..\DOA5LR-Detecteur.exe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll Detector.cs
if ($LASTEXITCODE) { throw 'Detector UI compilation failed' }
New-Item -ItemType Directory -Path '..\payload' -Force | Out-Null
Copy-Item -LiteralPath '..\test\dinput8ex.bin' -Destination '..\payload\dinput8ex.bin' -Force
