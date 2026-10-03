$targets = 1..254 | ForEach-Object { "192.168.1.$_" }
$jobs = @()

foreach ($ip in $targets) {
    $script = {
        param($ip)
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($ip, 8022, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne(200, $false) -and $client.Connected) {
            $client.EndConnect($iar)
            $client.Close()
            return $ip
        }
        $client.Close()
        return $null
    }
    $jobs += [powershell]::Create().AddScript($script).AddArgument($ip)
}

$handles = $jobs | ForEach-Object { $_.BeginInvoke() }

for ($i = 0; $i -lt $jobs.Count; $i++) {
    $res = $jobs[$i].EndInvoke($handles[$i])
    if ($res) {
        Write-Host "PORT_8022_OPEN: $res"
    }
    $jobs[$i].Dispose()
}
