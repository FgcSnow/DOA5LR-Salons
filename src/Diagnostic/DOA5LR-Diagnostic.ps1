# DOA5LR-Salons - Diagnostic : verification (maps DZ/Crimson, modules de salon, AutoLink), sonde, envoi des logs.
# Installe par le pack dans <jeu>\DOA5LR-Diagnostic. Windows PowerShell 5.1.
# Rien n'est envoye sans clic sur "Envoyer mes logs" + confirmation du joueur.
param([ValidateSet('Gui','Collect','Send','Check')][string]$Mode = 'Gui', [string]$Jeu = '', [string]$Out = '', [string]$Message = '', [switch]$Dump)
$ErrorActionPreference = 'Stop'
$Here    = [IO.Path]::GetFullPath($PSScriptRoot)
$Root    = [IO.Path]::GetFullPath((Join-Path $Here '..'))
$Sonde   = Join-Path $Here 'Sonde'
$Title   = 'DOA5LR-Salons - Diagnostic'
$MaxZip  = 9500000   # limite des fichiers joints Discord (10 Mo)
$WerKey  = 'HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\game.exe'

function Get-Webhook {
    $f = Join-Path $Here 'envoi-logs.txt'
    if (!(Test-Path -LiteralPath $f)) { return '' }
    foreach ($l in Get-Content -LiteralPath $f) { $l = $l.Trim(); if ($l -match '^https://(discord\.com|discordapp\.com)/api/webhooks/\d+/[\w-]+$') { return $l } }
    return ''
}

function Find-Game {
    if (Test-Path -LiteralPath (Join-Path $Root 'game.exe')) { return $Root }   # installe dans le dossier du jeu
    $bases = @()
    foreach ($key in @('HKCU:\Software\Valve\Steam','HKLM:\SOFTWARE\WOW6432Node\Valve\Steam')) {
        $v = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
        if ($v.SteamPath) { $bases += $v.SteamPath }; if ($v.InstallPath) { $bases += $v.InstallPath }
    }
    $bases += @("${env:ProgramFiles(x86)}\Steam","${env:ProgramFiles}\Steam")
    foreach ($base in @($bases | Select-Object -Unique)) {
        $vdf = Join-Path $base 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) { foreach ($m in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw),'"path"\s+"([^"]+)"')) { $bases += $m.Groups[1].Value.Replace('\\','\') } }
    }
    $found = @($bases | Select-Object -Unique | ForEach-Object { Join-Path ($_ -replace '/','\') 'steamapps\common\Dead or Alive 5 Last Round' } | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'game.exe') } | ForEach-Object { [IO.Path]::GetFullPath($_) } | Select-Object -Unique)
    if ($found.Count -ge 1) { return $found[0] }
    return ''
}

function Get-Sha([string]$p) {
    # .NET direct : Get-FileHash manque sur certains Windows PowerShell 5.1
    $h = [Security.Cryptography.SHA256]::Create(); $fs = [IO.File]::Open($p, 'Open', 'Read', 'ReadWrite')
    try { return (-join ($h.ComputeHash($fs) | ForEach-Object { $_.ToString('x2') })) } finally { $fs.Dispose(); $h.Dispose() }
}

function Get-PackVersion([string]$game) {
    $vf = Join-Path $game 'DOA5LR-Salons-VERSION.txt'
    if (Test-Path -LiteralPath $vf) { return ((Get-Content -LiteralPath $vf -TotalCount 1) -as [string]).Trim() }
    return 'inconnue'
}
function Get-MapsChoice([string]$game) {
    # choix de la case "Maps" de l'installateur (DOA5LR-Salons-Components.txt) ; absente = cochee
    $f = Join-Path $game 'DOA5LR-Salons-Components.txt'
    if (Test-Path -LiteralPath $f) { foreach ($l in Get-Content -LiteralPath $f) { if ($l -match '^\s*maps\s*=\s*0') { return $false } } }
    return $true
}
function Invoke-Check([string]$game) {
    $out = New-Object Collections.Generic.List[string]
    $out.Add('Pack DOA5LR-Salons : ' + (Get-PackVersion $game))
    # 1. maps DZ / Crimson
    $list = @((Get-Content -LiteralPath (Join-Path $Here 'maps-files.json') -Raw | ConvertFrom-Json) | ForEach-Object { $_ })
    if (!(Get-MapsChoice $game)) { $out.Add('Maps DZ / Crimson : case decochee dans l installateur (maps non installees).') }
    else {
        $bad = @()
        foreach ($e in $list) {
            $p = Join-Path $game ($e.path -replace '/', '\')
            if (!(Test-Path -LiteralPath $p -PathType Leaf)) { $bad += "$($e.path) (absent)" }
            elseif ((Get-Item -LiteralPath $p).Length -ne [long]$e.size -or (Get-Sha $p) -ine $e.sha256) { $bad += "$($e.path) (modifie)" }
        }
        if ($bad.Count) { $out.Add("ATTENTION : maps DZ / Crimson incompletes ou modifiees ($($bad.Count)) : " + (($bad | Select-Object -First 8) -join ', ') + '. Relance l installateur DOA5LR-Salons (Reinstall). / Maps incomplete: run the installer (Reinstall).') }
        else { $out.Add("Maps DZ / Crimson : OK ($($list.Count) fichiers identiques au pack).") }
    }
    # 2. modules de salon
    $salons = [ordered]@{}
    foreach ($e in @((Get-Content -LiteralPath (Join-Path $Here 'salons-modules.json') -Raw | ConvertFrom-Json) | ForEach-Object { $_ })) { $salons[$e.path] = $e.sha256 }
    $bad = @()
    foreach ($k in $salons.Keys) {
        $p = Join-Path $game ($k -replace '/', '\')
        if (!(Test-Path -LiteralPath $p -PathType Leaf)) { $bad += "$k (absent)" } elseif ((Get-Sha $p) -ine $salons[$k]) { $bad += "$k (autre version)" }
    }
    if ($bad.Count) { $out.Add('ATTENTION : modules de salon incomplets ou modifies : ' + ($bad -join ', ') + '. Relance l installateur DOA5LR-Salons (Reinstall). / Lobby modules incomplete: run the installer (Reinstall).') }
    else { $out.Add('Modules de salon : OK (salons, invitations, JoinFix, cable/Wi-Fi, mise a jour).') }
    # 3. autres modules ASI (info)
    $known = @($list | Where-Object { $_.path -like '*.asi' } | ForEach-Object { [IO.Path]::GetFileName($_.path) }) + @($salons.Keys | ForEach-Object { [IO.Path]::GetFileName($_) }) + @('DOA5LR-ReplayTakeover.asi','DOA5LR-60fps-menus.asi','DOA5LR-Borderless.asi')
    $asi = @(Get-ChildItem -LiteralPath $game -Filter '*.asi' -File -ErrorAction SilentlyContinue)
    foreach ($sub in 'scripts','plugins') { $d = Join-Path $game $sub; if (Test-Path -LiteralPath $d) { $asi += @(Get-ChildItem -LiteralPath $d -Filter '*.asi' -File -Recurse -ErrorAction SilentlyContinue) } }
    $others = @($asi | Where-Object { $_.Name -notin $known } | ForEach-Object { $_.FullName.Substring($game.Length + 1) })
    if ($others.Count) { $out.Add('Info : autres modules ASI (hors pack) : ' + ($others -join ', ')) }
    # 4. AutoLink
    $st = @(Get-AutoLinkStrays $game)
    if ($st.Count) { $out.Add('ATTENTION : AutoLink contient des dossiers qui ne sont pas des persos (' + ($st -join ', ') + ') : sors-les du dossier du jeu (des outils de modding dans AutoLink ont fait planter le jeu apres les combats).') }
    return $out
}

function Copy-Tail([string]$src, [string]$dst, [long]$max) {
    $fs = [IO.File]::Open($src, 'Open', 'Read', 'ReadWrite,Delete')
    try {
        $len = $fs.Length; $start = [Math]::Max(0, $len - $max); $fs.Position = $start
        $out = [IO.File]::Create($dst)
        try {
            if ($start -gt 0) { $h = [Text.Encoding]::ASCII.GetBytes("[... debut coupe : $start octets / start trimmed ...]`r`n"); $out.Write($h, 0, $h.Length) }
            $fs.CopyTo($out)
        } finally { $out.Dispose() }
    } finally { $fs.Dispose() }
}

function Get-AutoLinkInfo([string]$game) {
    $r = New-Object Collections.Generic.List[string]
    $ini = Join-Path $game 'DInput8.ini'
    $r.Add('dinput8Hooked.dll (AutoLink) : ' + (Test-Path -LiteralPath (Join-Path $game 'dinput8Hooked.dll')))
    $r.Add('d3d9.dll : ' + (Test-Path -LiteralPath (Join-Path $game 'd3d9.dll')))
    if (Test-Path -LiteralPath $ini) {
        $inPatch = $false
        foreach ($l in Get-Content -LiteralPath $ini) {
            if ($l -match '^\s*\[(.+)\]') { $inPatch = ($Matches[1] -eq 'PATCH'); continue }
            if ($inPatch -and $l -match '^\s*[A-Za-z_0-9]+\s*=') { $r.Add('  [PATCH] ' + $l.Trim()) }
            if ($l -match '^\s*Swap[A-Za-z]*\s*=|^\s*ForceStageIndex\s*=') { $r.Add('  ' + $l.Trim()) }
        }
    } else { $r.Add('DInput8.ini : absent') }
    $al = Join-Path $game 'AutoLink'
    if (Test-Path -LiteralPath $al) {
        $all = @(Get-ChildItem -LiteralPath $al -Recurse -File -Force -ErrorAction SilentlyContinue)
        $r.Add(('AutoLink : {0} fichiers, {1:N0} Mo' -f $all.Count, (($all | Measure-Object Length -Sum).Sum / 1MB)))
        foreach ($d in @(Get-ChildItem -LiteralPath $al -Directory -Force -ErrorAction SilentlyContinue)) {
            $f = @(Get-ChildItem -LiteralPath $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue)
            $slots = @(Get-ChildItem -LiteralPath $d.FullName -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object Name) -join ','
            $r.Add(('  {0,-14} {1,5} fichiers {2,8:N1} Mo  dossiers: {3}' -f $d.Name, $f.Count, (($f | Measure-Object Length -Sum).Sum / 1MB), $slots))
        }
    } else { $r.Add('AutoLink : dossier absent') }
    return $r
}

function Get-CrashEvents([string]$game) {
    $list = @()
    try {
        . (Join-Path $Sonde 'CrashEventParser.ps1')
        $raw = @(Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000,1001,1002; StartTime=(Get-Date).AddDays(-2)} -ErrorAction SilentlyContinue)
        foreach ($e in $raw) { $s = ConvertFrom-DoaCrashEventXml -EventXml $e.ToXml() -ExpectedGamePath (Join-Path $game 'game.exe'); if ($s) { $list += $s } }
    } catch { $list += [pscustomobject]@{ error = 'lecture du journal Windows impossible' } }
    return $list
}

function Write-HangDump([string]$dest) {
    # Instantane d'un jeu fige (lecture seule, MiniDumpNormal). PowerShell 32 bits pour un dump x86 lisible.
    $p = Get-Process game -ErrorAction SilentlyContinue | Select-Object -First 1
    if (!$p) { return $false }
    $ps32 = Join-Path $env:WINDIR 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
    if (!(Test-Path $ps32)) { $ps32 = 'powershell.exe' }
    $code = @"
Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public static class D{[DllImport("dbghelp.dll",SetLastError=true)]public static extern bool MiniDumpWriteDump(IntPtr h,int id,Microsoft.Win32.SafeHandles.SafeFileHandle f,int t,IntPtr a,IntPtr b,IntPtr c);[DllImport("kernel32.dll",SetLastError=true)]public static extern IntPtr OpenProcess(int a,bool b,int c);}'
`$h=[D]::OpenProcess(0x0410,`$false,$($p.Id)); `$fs=[IO.File]::Create('$($dest.Replace("'","''"))')
try { if(![D]::MiniDumpWriteDump(`$h,$($p.Id),`$fs.SafeFileHandle,0,[IntPtr]::Zero,[IntPtr]::Zero,[IntPtr]::Zero)){exit 1} } finally { `$fs.Dispose() }
"@
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($code))
    $pr = Start-Process -FilePath $ps32 -ArgumentList @('-NoProfile','-EncodedCommand',$enc) -WindowStyle Hidden -Wait -PassThru
    return ($pr.ExitCode -eq 0 -and (Test-Path -LiteralPath $dest) -and (Get-Item -LiteralPath $dest).Length -gt 0)
}

function New-LogZip([string]$game, [string]$note, [bool]$withDump, [string]$zipPath) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $work = Join-Path ([IO.Path]::GetTempPath()) ("DOA5LR-Logs-" + $stamp + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6))
    New-Item -ItemType Directory -Path $work | Out-Null
    $info = New-Object Collections.Generic.List[string]
    $info.Add('Outil : DOA5LR-Diagnostic'); $info.Add('Date (UTC) : ' + [DateTime]::UtcNow.ToString('o'))
    $info.Add('Windows : ' + [Environment]::OSVersion.VersionString)
    $info.Add('Note du joueur : ' + $note)
    $info.Add('Pack salons : ' + (Get-PackVersion $game))
    $info.Add('Jeu en cours : ' + [bool](Get-Process game -ErrorAction SilentlyContinue))
    $info.Add(''); $info.Add('=== Verification ===')
    try { foreach ($l in (Invoke-Check $game)) { $info.Add($l) } } catch { $info.Add('verification impossible : ' + $_.Exception.Message) }
    $info.Add(''); $info.Add('=== AutoLink ===')
    $info.Add('Dossiers non-persos dans AutoLink : ' + ((@(Get-AutoLinkStrays $game)) -join ', '))
    foreach ($l in (Get-AutoLinkInfo $game)) { $info.Add($l) }
    $info.Add(''); $info.Add('=== Modules (racine, scripts, plugins) ===')
    $mods = @(Get-ChildItem -LiteralPath $game -File -Force | Where-Object { $_.Extension -in '.asi','.dll','.bin' })
    foreach ($sub in 'scripts','plugins') { $d = Join-Path $game $sub; if (Test-Path -LiteralPath $d) { $mods += @(Get-ChildItem -LiteralPath $d -File -Force | Where-Object { $_.Extension -in '.asi','.dll' }) } }
    foreach ($f in $mods) { $info.Add(('{0}  {1,9}  {2}' -f (Get-Sha $f.FullName), $f.Length, $f.FullName.Substring($game.Length + 1))) }
    [IO.File]::WriteAllLines((Join-Path $work 'environnement.txt'), $info, (New-Object Text.UTF8Encoding($false)))
    ConvertTo-Json -InputObject @(Get-CrashEvents $game) -Depth 5 | Set-Content -LiteralPath (Join-Path $work 'plantages-windows-48h.json') -Encoding UTF8
    # Journaux des modules des maps (la fin seulement). Pas le journal du salon (noms de joueurs).
    $logs = New-Item -ItemType Directory -Path (Join-Path $work 'journaux-modules')
    foreach ($f in @(Get-ChildItem -LiteralPath $game -File -Filter 'DOA5LR-*.log' -Force)) {
        if ($f.Name -match '^DOA5LR-(Crimson|DangerZone|DNZ|ExtraStages|RandomStages|DebugArchive|ReplayTakeover)') { Copy-Tail $f.FullName (Join-Path $logs.FullName $f.Name) 1MB }
    }
    # Captures de la sonde : les 3 dernieres sessions.
    $sess = Join-Path $Sonde 'Sessions'
    if (Test-Path -LiteralPath $sess) {
        $dst = New-Item -ItemType Directory -Path (Join-Path $work 'sonde')
        foreach ($s in @(Get-ChildItem -LiteralPath $sess -Directory | Sort-Object Name -Descending | Select-Object -First 3)) {
            try { & (Join-Path $Sonde 'Exporter-plantage-Windows.ps1') -SessionDirectory $s.FullName -ExpectedGamePath (Join-Path $game 'game.exe') | Out-Null } catch {}
            $t = New-Item -ItemType Directory -Path (Join-Path $dst.FullName $s.Name)
            foreach ($f in @(Get-ChildItem -LiteralPath $s.FullName -Recurse -File)) {
                $rel = $f.FullName.Substring($s.FullName.Length + 1); $target = Join-Path $t.FullName $rel
                New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
                Copy-Tail $f.FullName $target 3MB
            }
        }
    }
    if ($withDump) {
        $dumps = New-Item -ItemType Directory -Path (Join-Path $work 'dump')
        if (Get-Process game -ErrorAction SilentlyContinue) { [void](Write-HangDump (Join-Path $dumps.FullName 'game-fige.dmp')) }
        $dirs = @(Join-Path $env:LOCALAPPDATA 'CrashDumps')
        foreach ($k in @($WerKey, 'HKLM:\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps')) {
            $v = (Get-ItemProperty -LiteralPath $k -ErrorAction SilentlyContinue).DumpFolder
            if ($v) { $dirs += [Environment]::ExpandEnvironmentVariables($v) }
        }
        $last = @($dirs | Select-Object -Unique | ForEach-Object { Get-ChildItem -LiteralPath $_ -Filter 'game.exe*.dmp' -File -ErrorAction SilentlyContinue }) | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-2) } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($last) { Copy-Item -LiteralPath $last.FullName -Destination (Join-Path $dumps.FullName ('plantage-' + $last.Name)) }
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    [IO.Compression.ZipFile]::CreateFromDirectory($work, $zipPath, [IO.Compression.CompressionLevel]::Optimal, $false)
    if ((Get-Item -LiteralPath $zipPath).Length -gt $MaxZip -and (Test-Path -LiteralPath (Join-Path $work 'dump'))) {
        # Trop gros pour Discord : on garde seulement le plus petit dump.
        $keep = Get-ChildItem -LiteralPath (Join-Path $work 'dump') -File | Sort-Object Length | Select-Object -First 1
        Get-ChildItem -LiteralPath (Join-Path $work 'dump') -File | Where-Object { $_.FullName -ne $keep.FullName } | Remove-Item -Force
        Remove-Item -LiteralPath $zipPath -Force
        [IO.Compression.ZipFile]::CreateFromDirectory($work, $zipPath, [IO.Compression.CompressionLevel]::Optimal, $false)
        if ((Get-Item -LiteralPath $zipPath).Length -gt $MaxZip) {
            Remove-Item -LiteralPath (Join-Path $work 'dump') -Recurse -Force; Remove-Item -LiteralPath $zipPath -Force
            [IO.Compression.ZipFile]::CreateFromDirectory($work, $zipPath, [IO.Compression.CompressionLevel]::Optimal, $false)
        }
    }
    $files = @(Get-ChildItem -LiteralPath $work -Recurse -File | ForEach-Object { $_.FullName.Substring($work.Length + 1) })
    Remove-Item -LiteralPath $work -Recurse -Force
    return $files
}

function Send-LogZip([string]$zip, [string]$text) {
    $hook = Get-Webhook
    if (!$hook) { throw "Envoi automatique non configure : envoie le ZIP a la main (il est sur ton Bureau)." }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Add-Type -AssemblyName System.Net.Http
    $client = New-Object Net.Http.HttpClient; $client.Timeout = [TimeSpan]::FromSeconds(120)
    $form = New-Object Net.Http.MultipartFormDataContent
    if ($text.Length -gt 1900) { $text = $text.Substring(0, 1900) }
    $payload = @{ content = $text; allowed_mentions = @{ parse = @() } } | ConvertTo-Json -Depth 4 -Compress
    $form.Add((New-Object Net.Http.StringContent($payload, [Text.Encoding]::UTF8, 'application/json')), 'payload_json')
    $bytes = New-Object Net.Http.ByteArrayContent(,[IO.File]::ReadAllBytes($zip))
    $bytes.Headers.ContentType = [Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/zip')
    $form.Add($bytes, 'files[0]', [IO.Path]::GetFileName($zip))
    try {
        $resp = $client.PostAsync($hook, $form).GetAwaiter().GetResult()
        if (!$resp.IsSuccessStatusCode) { throw ('Discord a refuse l envoi (HTTP ' + [int]$resp.StatusCode + ').') }
    } finally { $client.Dispose() }
}

function Get-AutoLinkStrays([string]$game) {
    $al = Join-Path $game 'AutoLink'
    if (!(Test-Path -LiteralPath $al -PathType Container)) { return }
    $known = @('_Movie','_Texture','_Sound','_Stages')
    $names = Join-Path $al 'NAME.txt'
    if (Test-Path -LiteralPath $names) { $known += @(Get-Content -LiteralPath $names | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
    foreach ($d in @(Get-ChildItem -LiteralPath $al -Directory -Force -ErrorAction SilentlyContinue)) { if ($d.Name -notin $known) { $d.Name } }
}
function Warn-AutoLinkStrays([bool]$popup) {
    if (!$game) { return }
    $st = @(Get-AutoLinkStrays $game)
    if (!$st.Count) { return }
    $t = "AutoLink contient des dossiers qui ne sont pas des persos : " + ($st -join ', ') + "`r`nSors-les du dossier du jeu (ex. sur le Bureau) : des outils de modding dans AutoLink ont fait planter le jeu apres les combats.`r`nAutoLink contains non-character folders: move them out of the game folder (modding tools there caused crashes after fights)."
    Say ('ATTENTION : ' + $t)
    if ($popup) { [void][Windows.Forms.MessageBox]::Show($t, $Title, 'OK', 'Warning') }
}
function Clear-BigLogs([string]$game) {
    # Le journal des effets de Crimson grossit a chaque partie : on repart de zero s'il depasse 20 Mo.
    foreach ($f in @(Get-ChildItem -LiteralPath $game -File -Filter 'DOA5LR-Crimson*.log' -ErrorAction SilentlyContinue)) {
        if ($f.Length -gt 20MB) { try { $old = $f.FullName + '.old'; Copy-Tail $f.FullName $old 2MB; Remove-Item -LiteralPath $f.FullName -Force } catch {} }
    }
}

# ---------- mode ligne de commande (tests) ----------
if ($Mode -ne 'Gui') {
    if (!$Jeu) { $Jeu = Find-Game }
    if (!$Out) { $Out = Join-Path ([Environment]::GetFolderPath('Desktop')) ('DOA5LR-Logs-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.zip') }
    if ($Mode -eq 'Check') { Invoke-Check $Jeu; exit 0 }
    $list = New-LogZip $Jeu $Message ([bool]$Dump) $Out
    $list | ForEach-Object { "  $_" }; "ZIP : $Out  ($((Get-Item $Out).Length) octets)"
    if ($Mode -eq 'Check') { Invoke-Check $Jeu; exit 0 }
    if ($Mode -eq 'Send') { Send-LogZip $Out ("Test : " + $Message); 'Envoye.' }
    exit 0
}

# ---------- fenetre ----------
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$game = Find-Game

$form = New-Object Windows.Forms.Form
$form.Text = $Title; $form.Size = New-Object Drawing.Size(780, 700); $form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'; $form.MaximizeBox = $false; $form.AutoScaleMode = 'Dpi'
$form.Font = New-Object Drawing.Font('Segoe UI', 9)
try { $form.Icon = [Drawing.Icon]::ExtractAssociatedIcon((Join-Path $game 'game.exe')) } catch {}

$info = New-Object Windows.Forms.Label
$info.Location = '14,10'; $info.Size = '740,200'; $info.UseMnemonic = $false
$info.Text = @"
DOA5LR-SALONS - DIAGNOSTIC
Si le jeu plante ou gele : clique "Envoyer mes logs" (si le jeu est fige, AVANT de le fermer).
If the game crashes or freezes: click "Send my logs" (if it is frozen, BEFORE closing it).

- Maps Danger Zone / The Crimson 1-2 : en ligne, TOUT LE MONDE dans le salon (joueurs ET spectateurs) doit
  les avoir. / Online, EVERYONE in the room (players AND spectators) needs the maps.
- AutoLink : ne mets QUE les dossiers des persos dedans (pas d'outils de modding) : ca faisait planter
  apres les combats. / AutoLink: only character folders inside (no modding tools): it caused crashes.
- Les maps se cochent / decochent dans l'installateur DOA5LR-Salons (case "Maps").
  Maps are turned on / off with the "Maps" check box of the DOA5LR-Salons installer.
"@
$form.Controls.Add($info)

$gameLabel = New-Object Windows.Forms.Label
$gameLabel.Location = '14,208'; $gameLabel.Size = '640,32'; $gameLabel.UseMnemonic = $false
$form.Controls.Add($gameLabel)
$browse = New-Object Windows.Forms.Button
$browse.Location = '664,210'; $browse.Size = '90,26'; $browse.Text = 'Changer...'
$form.Controls.Add($browse)

$log = New-Object Windows.Forms.TextBox
$log.Location = '14,376'; $log.Size = '740,264'; $log.Multiline = $true; $log.ScrollBars = 'Vertical'; $log.ReadOnly = $true
$log.Font = New-Object Drawing.Font('Consolas', 9)
$form.Controls.Add($log)

function Say([string]$t) { $log.AppendText($t + "`r`n"); [Windows.Forms.Application]::DoEvents() }
function Refresh-Game {
    if ($game) {
        $m = if (Get-MapsChoice $game) { 'cochees / on' } else { 'decochees / off' }
        $gameLabel.Text = "Jeu / Game : $game`r`nPack DOA5LR-Salons $(Get-PackVersion $game)  -  Maps DZ / Crimson : $m"
    } else { $gameLabel.Text = 'Jeu introuvable : clique "Changer..." / Game not found: click "Changer..."' }
}
function Game-Running { [bool](Get-Process game -ErrorAction SilentlyContinue) }
function New-Btn([string]$text, [string]$loc, [string]$size = '365,40') {
    $b = New-Object Windows.Forms.Button; $b.Text = $text; $b.Location = $loc; $b.Size = $size; $form.Controls.Add($b); return $b
}
$bPlay  = New-Btn "Jouer (avec la sonde)`r`nPlay (with the probe)" '14,244'
$bSend  = New-Btn "Envoyer mes logs`r`nSend my logs" '389,244'
$bCheck = New-Btn "Verifier`r`nCheck" '14,290'
$bWer   = New-Btn "Rapports de plantage detailles`r`nDetailed crash reports" '389,290'
$bPlay.BackColor = [Drawing.Color]::FromArgb(210, 240, 210)
$bSend.BackColor = [Drawing.Color]::FromArgb(215, 228, 250)
$foot = New-Object Windows.Forms.Label
$foot.Location = '14,336'; $foot.Size = '740,34'; $foot.UseMnemonic = $false
$foot.Text = "Les logs ne partent que si tu cliques `"Envoyer`" puis confirmes. Aucune IP, SteamID, chat ou entree de manette.`r`nLogs are only sent when you click Send and confirm. No IP, SteamID, chat or controller inputs."
$form.Controls.Add($foot)

function Set-Wer([bool]$enable) {
    $k = 'HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\game.exe'
    $cmd = if (!$enable) { "reg delete `"$k`" /f" } else { "reg add `"$k`" /v DumpType /t REG_DWORD /d 1 /f & reg add `"$k`" /v DumpCount /t REG_DWORD /d 3 /f & reg add `"$k`" /v DumpFolder /t REG_EXPAND_SZ /d `"%LOCALAPPDATA%\CrashDumps`" /f" }
    try { Start-Process -FilePath 'cmd.exe' -ArgumentList "/c $cmd" -Verb RunAs -WindowStyle Hidden -Wait } catch { Say 'Annule. / Cancelled.'; return }
    Say $(if (Test-Path $WerKey) { 'Rapports de plantage detailles : ACTIVES / ON' } else { 'Rapports de plantage detailles : desactives / OFF' })
}

$browse.Add_Click({
    $d = New-Object Windows.Forms.FolderBrowserDialog; $d.Description = 'Dossier du jeu (contient game.exe)'
    if ($d.ShowDialog() -eq 'OK') { if (Test-Path -LiteralPath (Join-Path $d.SelectedPath 'game.exe')) { $script:game = $d.SelectedPath; Refresh-Game } else { Say 'game.exe absent de ce dossier.' } }
})
$bCheck.Add_Click({
    if (!$game) { Say 'Jeu introuvable.'; return }
    $form.Cursor = 'WaitCursor'; Say '--- Verification / Check ---'
    try { foreach ($l in (Invoke-Check $game)) { Say $l } } catch { Say ('Erreur : ' + $_.Exception.Message) }
    $form.Cursor = 'Default'
})
$bPlay.Add_Click({
    if (!$game) { Say 'Jeu introuvable.'; return }
    $asked = Join-Path $Here 'rapports-proposes.flag'
    if (!(Test-Path $WerKey) -and !(Test-Path -LiteralPath $asked)) {
        try { [IO.File]::WriteAllText($asked, 'ok') } catch {}
        if ([Windows.Forms.MessageBox]::Show("Activer les rapports de plantage detailles (recommande) ?`n`nSi le jeu plante, Windows gardera un petit fichier .dmp qui montre OU il a plante. Il ne part que si tu l'envoies avec `"Envoyer mes logs`". Demande les droits administrateur une seule fois.`n`nTurn on detailed crash reports (recommended)? Admin rights asked once.", $Title, 'YesNo', 'Question') -eq 'Yes') { Set-Wer $true }
    }
    Warn-AutoLinkStrays $true
    Clear-BigLogs $game
    $probe = Join-Path $Sonde 'DOA5LR-TestEnLigne.exe'
    if (!(Get-Process DOA5LR-TestEnLigne -ErrorAction SilentlyContinue)) { Start-Process -FilePath $probe -WorkingDirectory $Sonde -WindowStyle Hidden; Say 'Sonde demarree (elle s arrete seule quand le jeu se ferme). / Probe started.' }
    else { Say 'Sonde deja en marche. / Probe already running.' }
    if (!(Game-Running)) { Start-Process 'steam://rungameid/311730'; Say 'Lancement du jeu via Steam... / Starting the game through Steam...' }
})
$bWer.Add_Click({
    $on = Test-Path $WerKey
    $q = if ($on) { "Les rapports de plantage detailles sont ACTIVES. Les desactiver ?`n`nDetailed crash reports are ON. Turn them off?" } else { "Activer les rapports de plantage detailles de Windows pour DOA5LR ?`n`nSi le jeu plante, Windows garde un petit fichier .dmp qui montre OU il a plante. Il ne sera envoye que si tu coches la case dans `"Envoyer mes logs`". Demande les droits administrateur une fois.`n`nTurn on Windows detailed crash reports for DOA5LR? (admin rights asked once)" }
    if ([Windows.Forms.MessageBox]::Show($q, $Title, 'YesNo', 'Question') -ne 'Yes') { return }
    Set-Wer (!$on)
})
$bSend.Add_Click({
    if (!$game) { Say 'Jeu introuvable.'; return }
    $dlg = New-Object Windows.Forms.Form
    $dlg.Text = 'Envoyer mes logs / Send my logs'; $dlg.Size = '560,430'; $dlg.StartPosition = 'CenterParent'; $dlg.FormBorderStyle = 'FixedDialog'; $dlg.AutoScaleMode = 'Dpi'; $dlg.Font = $form.Font
    $l1 = New-Object Windows.Forms.Label; $l1.Location = '12,10'; $l1.Size = '520,34'; $l1.UseMnemonic = $false
    $l1.Text = "Ton pseudo Discord (facultatif) / Your Discord name (optional)"
    $name = New-Object Windows.Forms.TextBox; $name.Location = '12,44'; $name.Size = '520,24'; $name.MaxLength = 60
    $l2 = New-Object Windows.Forms.Label; $l2.Location = '12,76'; $l2.Size = '520,34'; $l2.UseMnemonic = $false
    $l2.Text = "Que s'est-il passe ? (map, 1er/2e combat, plantage ou gel, hote/invite, AutoLink on/off...)`nWhat happened? (map, 1st/2nd fight, crash or freeze, host/guest, AutoLink on/off...)"
    $desc = New-Object Windows.Forms.TextBox; $desc.Location = '12,112'; $desc.Size = '520,120'; $desc.Multiline = $true; $desc.MaxLength = 1200
    $chk = New-Object Windows.Forms.CheckBox; $chk.Location = '12,240'; $chk.Size = '520,56'
    $chk.Text = "Joindre un instantane du jeu (.dmp) : le dernier plantage, ou le jeu s'il est encore ouvert/fige. Contient un morceau de la memoire du jeu (peut inclure ton nom Steam). / Attach a game snapshot (.dmp)."
    $chk.Checked = $true
    $ok = New-Object Windows.Forms.Button; $ok.Text = 'Envoyer / Send'; $ok.Location = '300,320'; $ok.Size = '110,34'; $ok.DialogResult = 'OK'
    $ko = New-Object Windows.Forms.Button; $ko.Text = 'Annuler'; $ko.Location = '420,320'; $ko.Size = '110,34'; $ko.DialogResult = 'Cancel'
    $dlg.Controls.AddRange(@($l1, $name, $l2, $desc, $chk, $ok, $ko)); $dlg.AcceptButton = $ok; $dlg.CancelButton = $ko
    if ($dlg.ShowDialog($form) -ne 'OK') { return }
    $who = ($name.Text -replace '[@`]', '').Trim(); $what = ($desc.Text -replace '@', '(at)').Trim()
    $zip = Join-Path ([Environment]::GetFolderPath('Desktop')) ('DOA5LR-Logs-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.zip')
    $form.Cursor = 'WaitCursor'; Say 'Preparation des logs... / Collecting logs...'
    try { $files = New-LogZip $game ("$who : $what") $chk.Checked $zip } catch { $form.Cursor = 'Default'; Say ('Erreur : ' + $_.Exception.Message); return }
    $form.Cursor = 'Default'
    $size = [Math]::Round((Get-Item -LiteralPath $zip).Length / 1KB)
    $list = ($files | Select-Object -First 25) -join "`n"; if ($files.Count -gt 25) { $list += "`n... (+$($files.Count - 25))" }
    if ([Windows.Forms.MessageBox]::Show("Le ZIP ($size Ko) est sur ton Bureau :`n$zip`n`nContenu / Content :`n$list`n`nL'envoyer maintenant a FGCsnow sur Discord ? / Send it now?", $Title, 'YesNo', 'Question') -ne 'Yes') { Say "ZIP garde sur le Bureau : $zip"; return }
    $alOn = 'AutoLink ?'; $ini = Join-Path $game 'DInput8.ini'
    if (Test-Path -LiteralPath $ini) { $m = Select-String -LiteralPath $ini -Pattern '^\s*AutoLink\s*=\s*(\d)' | Select-Object -First 1; if ($m) { $alOn = 'AutoLink=' + $m.Matches[0].Groups[1].Value } }
    $text = "**Logs DOA5LR-Salons $(Get-PackVersion $game)** - $(if ($who) { $who } else { 'anonyme' }) - $alOn`n$what"
    $form.Cursor = 'WaitCursor'
    try { Send-LogZip $zip $text; Say 'Envoye, merci ! / Sent, thanks!' } catch { Say ('Envoi impossible : ' + $_.Exception.Message + ' Le ZIP reste sur ton Bureau, envoie-le a la main.') }
    $form.Cursor = 'Default'
})

Refresh-Game
Warn-AutoLinkStrays $false
if (!(Get-Webhook)) { Say 'Info : envoi automatique non configure, les logs seront seulement mis en ZIP sur le Bureau.' }
[void]$form.ShowDialog()
