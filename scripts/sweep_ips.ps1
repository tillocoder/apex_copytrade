$targets = 1..254 | ForEach-Object { "192.168.1.$_" }
$jobs = New-Object System.Collections.ArrayList

foreach ($ip in $targets) {
    $script = {
        param($ip)
        $p = New-Object System.Net.NetworkInformation.Ping
        try {
            $reply = $p.Send($ip, 120)
            if ($reply.Status -eq "Success") {
                return $ip
            }
        } catch {}
        return $null
    }
    $ps = [powershell]::Create().AddScript($script).AddArgument($ip)
    [void]$jobs.Add($ps)
}

$handles = $jobs | ForEach-Object { $_.BeginInvoke() }

for ($i = 0; $i -lt $jobs.Count; $i++) {
    $res = $jobs[$i].EndInvoke($handles[$i])
    if ($res) {
        Write-Host "LIVE_IP: $res"
    }
    $jobs[$i].Dispose()
}
