param([Parameter(Mandatory=$true)][string]$SessionDirectory,[string]$ExpectedGamePath='')
# Read-only Windows Application event query. The only write is this compact report.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'CrashEventParser.ps1')
$report=[ordered]@{format_version=1; status='unavailable'; window_start_utc=$null; window_end_utc=$null; events=@(); note=''}
try {
    $directory=[IO.Path]::GetFullPath($SessionDirectory)
    if(!(Test-Path -LiteralPath $directory -PathType Container)) { throw 'Session directory unavailable' }
    $log=Join-Path $directory 'session.log'
    $first=$null; $last=$null
    $stream=New-Object IO.StreamReader($log)
    try {
        while(($line=$stream.ReadLine()) -ne $null) {
            if($line -match '^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s') {
                $time=[DateTimeOffset]::Parse($Matches[1],[Globalization.CultureInfo]::InvariantCulture)
                if($null -eq $first -or $time -lt $first) { $first=$time }
                if($null -eq $last -or $time -gt $last) { $last=$time }
            }
        }
    } finally { $stream.Dispose() }
    if($null -eq $first -or $null -eq $last) {
        $report.status='session_time_unavailable'; $report.note='Horaires absents du journal : aucune recherche dans Windows.'
    } else {
        $start=$first.AddMinutes(-2); $end=$last.AddMinutes(3)
        $report.window_start_utc=$start.ToUniversalTime().ToString('o')
        $report.window_end_utc=$end.ToUniversalTime().ToString('o')
        $queryErrors=@()
        $raw=@(Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000,1001,1002;StartTime=$start.LocalDateTime;EndTime=$end.LocalDateTime} -ErrorAction SilentlyContinue -ErrorVariable queryErrors)
        $summaries=@(foreach($event in $raw) {
            ConvertFrom-DoaCrashEventXml -EventXml $event.ToXml() -ExpectedGamePath $ExpectedGamePath
        })
        $failures=@($queryErrors | Where-Object { $_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*' })
        $report.events=@($summaries | Sort-Object time_utc,event_id)
        if($failures.Count -gt 0) {
            $report.status='event_log_unavailable'; $report.note='Lecture du journal Windows incomplete ou refusee. Aucun detail prive de l erreur n est exporte.'
        } elseif($summaries.Count -eq 0) {
            $report.status='no_matching_event'; $report.note='Aucun evenement DOA5LR identifiable dans cette plage sur cet ordinateur. Cela n exclut pas un gel ou un plantage.'
        } else {
            $report.status='ok'; $report.note='Evenements du PC sur lequel cet outil est execute. Le module signale par Windows ne prouve pas a lui seul la cause du bug.'
        }
    }
} catch {
    $report.status='collection_unavailable'; $report.note='Session ou journal Windows inaccessible. La recuperation des autres logs peut continuer.'
}
try {
    if($directory -and (Test-Path -LiteralPath $directory -PathType Container)) {
        $json=$report | ConvertTo-Json -Depth 5
        [IO.File]::WriteAllText((Join-Path $directory 'plantage-windows.json'),$json,(New-Object Text.UTF8Encoding($false)))
    }
} catch { Write-Warning 'Le rapport Windows n a pas pu etre enregistre. Les autres logs restent disponibles.' }
Write-Host ('Diagnostic Windows : '+$report.status+' ('+$report.events.Count+' evenement(s)).')
