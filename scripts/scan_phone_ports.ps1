$ports = 1000..10000 | Where-Object { $_ % 100 -eq 0 -or $_ -in @(8000, 8022, 8080, 8888, 5000, 5050, 3000, 9000, 9090, 7000, 6997, 20241) }
foreach ($p in $ports) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $c.BeginConnect('192.168.1.133', $p, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne(80, $false) -and $c.Connected) {
            Write-Host "OPEN PORT ON 192.168.1.133: $p"
            $c.EndConnect($iar)
        }
    } catch {}
    $c.Close()
}
