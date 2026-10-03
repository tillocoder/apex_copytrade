$ips = @("192.168.1.133", "192.168.1.39", "192.168.1.40")
$ports = @(22, 80, 443, 5050, 8000, 8022, 8080, 9000, 5555)

foreach ($ip in $ips) {
    foreach ($p in $ports) {
        $c = New-Object System.Net.Sockets.TcpClient
        try {
            $iar = $c.BeginConnect($ip, $p, $null, $null)
            if ($iar.AsyncWaitHandle.WaitOne(200, $false) -and $c.Connected) {
                Write-Host "OPEN: $ip : $p"
                $c.EndConnect($iar)
            }
        } catch {}
        $c.Close()
    }
}
