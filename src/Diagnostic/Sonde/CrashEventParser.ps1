# Pure XML-to-summary parser. Never return raw EventData, paths or report IDs.
function ConvertFrom-DoaCrashEventXml {
    param([Parameter(Mandatory=$true)][string]$EventXml,
          [string]$ExpectedGamePath='', [string]$ExpectedGameTimestamp='5a1faa36')
    try {
        $settings=New-Object System.Xml.XmlReaderSettings
        $settings.DtdProcessing=[System.Xml.DtdProcessing]::Prohibit
        $settings.XmlResolver=$null
        $reader=[System.Xml.XmlReader]::Create((New-Object IO.StringReader($EventXml)),$settings)
        try { $xml=New-Object System.Xml.XmlDocument; $xml.XmlResolver=$null; $xml.Load($reader) } finally { $reader.Dispose() }
        $ns=New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
        $ns.AddNamespace('e','http://schemas.microsoft.com/win/2004/08/events/event')
        $id=[int]$xml.SelectSingleNode('/e:Event/e:System/e:EventID',$ns).InnerText
        $provider=$xml.SelectSingleNode('/e:Event/e:System/e:Provider',$ns).GetAttribute('Name')
        $expectedProviders=@{1000='Application Error';1001='Windows Error Reporting';1002='Application Hang'}
        if (!$expectedProviders.ContainsKey($id) -or $provider -ne $expectedProviders[$id]) { return }
        $utc=[DateTimeOffset]::Parse($xml.SelectSingleNode('/e:Event/e:System/e:TimeCreated',$ns).GetAttribute('SystemTime'),[Globalization.CultureInfo]::InvariantCulture)
        $data=@{}
        foreach($node in $xml.SelectNodes('/e:Event/e:EventData/e:Data',$ns)) {
            $name=$node.GetAttribute('Name')
            if($name) { $data[$name]=$node.InnerText }
        }
        $app=''; $path=''; $stamp=''; $module=''; $code=''; $offset=''
        if($id -eq 1000) {
            $app=$data['AppName']; $path=$data['AppPath']; $stamp=$data['AppTimeStamp']
            $module=$data['ModuleName']; $code=$data['ExceptionCode']; $offset=$data['FaultingOffset']
        } elseif($id -eq 1001) {
            # WER problem-signature positions depend on the event category.
            if($data['EventName'] -notin @('APPCRASH','BEX','BEX64','AppHangB1','AppHangB2','AppHangXProcB1')) { return }
            $app=$data['P1']; $stamp=$data['P3']; $path=$data['AppPath']
            if($data['EventName'] -eq 'APPCRASH') {
                $module=$data['P4']; $code=$data['P7']; $offset=$data['P8']
            } elseif($data['EventName'] -in @('BEX','BEX64')) {
                $module=$data['P4']; $code=$data['P8']; $offset=$data['P7']
            }
        } else {
            $app=$data['AppName']; $path=$data['ExeFileName']; $stamp=$data['AppTimeStamp']
            if(!$path) { $path=$data['AppPath'] }
        }
        if($app -ine 'game.exe') { return }
        # A supplied path must match even when the timestamp matches. A bare
        # game.exe without a matching path OR executable timestamp is ambiguous.
        if($path) {
            $normalized=$path.Replace('/','\').Trim('"')
            if($ExpectedGamePath) {
                if($normalized -ine $ExpectedGamePath.Replace('/','\').Trim('"')) { return }
            } elseif($normalized -notmatch '(?i)\\Dead or Alive 5 Last Round\\game\.exe$') { return }
        } elseif(!$stamp -or ($stamp -replace '^(?i)0x','') -ine $ExpectedGameTimestamp) { return }
        # Allow only a conventional module basename; all other free text is dropped.
        $module=($module -split '[\\/]')[-1]
        if($module -notmatch '^[A-Za-z0-9_ .+()\-]{1,120}\.(dll|exe|asi)$') { $module=$null }
        if($code -match '^(?i)(?:0x)?([0-9a-f]{8})$') { $code='0x'+$Matches[1].ToUpperInvariant() } else { $code=$null }
        if($offset -match '^(?i)(?:0x)?([0-9a-f]{1,16})$') { $offset='0x'+$Matches[1].ToUpperInvariant() } else { $offset=$null }
        [pscustomobject][ordered]@{
            time_utc=$utc.ToUniversalTime().ToString('o'); event_id=$id; application='game.exe'
            module=$module; exception_code=$code; fault_offset=$offset
        }
    } catch { return }
}
