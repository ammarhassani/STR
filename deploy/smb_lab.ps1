<#
    smb_lab.ps1 -- set up and verify the REAL SMB share for a two-PC STR run.

    Why this exists: a loopback UNC path is not a share. Measured on the dev
    machine, \\localhost\C$, \\<own-LAN-IP>\C$ and \\<own-hostname>\C$ all run at
    1.0x local-disk speed -- Windows short-circuits a connection to itself. A test
    that "passed over SMB" that way proved nothing about locking, latency or a
    dropped session. The share has to be served by one PC and consumed by
    another.

    Run AS ADMINISTRATOR on the HOST pc:      .\smb_lab.ps1 -Role Host
    Run as a normal user on each CLIENT pc:   .\smb_lab.ps1 -Role Client -HostName VM-HOST

    -Role Host    creates C:\STR_data, shares it as STR_data, grants the given
                  users change rights, opens the firewall for file sharing, and
                  prints the UNC path to use.
    -Role Client  mounts the share, then runs the checks that actually matter:
                  can it write, does a rename land atomically, does it see a
                  file another PC just wrote, and how slow is it really.
#>
param(
    [ValidateSet('Host', 'Client')] [string] $Role = 'Host',
    [string] $HostName = $env:COMPUTERNAME,
    [string] $ShareName = 'STR_data',
    [string] $SharePath = 'C:\STR_data',
    [string[]] $AllowUsers = @('Everyone')
)

$ErrorActionPreference = 'Stop'

function Test-Admin {
    ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if ($Role -eq 'Host') {
    if (-not (Test-Admin)) {
        Write-Error "Creating a share needs an elevated PowerShell. Right-click > Run as administrator."
        exit 1
    }

    New-Item -ItemType Directory -Force -Path $SharePath | Out-Null
    if (Get-SmbShare -Name $ShareName -ErrorAction SilentlyContinue) {
        Write-Host "share '$ShareName' already exists -- leaving it alone"
    } else {
        New-SmbShare -Name $ShareName -Path $SharePath -FullAccess $AllowUsers | Out-Null
        Write-Host "created share '$ShareName' -> $SharePath"
    }

    # NTFS rights have to agree with the share rights or clients get
    # ERROR_ACCESS_DENIED on write, which looks exactly like a bug in the app.
    foreach ($u in $AllowUsers) {
        $acl = Get-Acl $SharePath
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $u, 'Modify', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.SetAccessRule($rule)
        Set-Acl -Path $SharePath -AclObject $acl
    }
    Enable-NetFirewallRule -DisplayGroup 'File and Printer Sharing' -ErrorAction SilentlyContinue

    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
           Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
           Select-Object -First 1 -ExpandProperty IPAddress)
    Write-Host ""
    Write-Host "HOST READY" -ForegroundColor Green
    Write-Host "  share path for the clients:  \\$env:COMPUTERNAME\$ShareName"
    Write-Host "  or by address:               \\$ip\$ShareName"
    Write-Host ""
    Write-Host "Next: point the STR setup wizard at that UNC path on this PC (mode=host)"
    Write-Host "      and on each client PC (mode=client), then run:"
    Write-Host "      .\smb_lab.ps1 -Role Client -HostName $env:COMPUTERNAME"
    exit 0
}

# ------------------------------------------------------------------ client
$unc = "\\$HostName\$ShareName"
Write-Host "checking $unc ..." -ForegroundColor Cyan

if (-not (Test-Path $unc)) {
    Write-Error "cannot reach $unc -- check the host is up, the share exists, and File and Printer Sharing is allowed through its firewall"
    exit 1
}

if ($HostName -eq $env:COMPUTERNAME) {
    Write-Warning "You are pointing at THIS machine. Windows short-circuits a connection to itself, so this will NOT exercise SMB. Run this from a different PC."
}

$probe = Join-Path $unc ("probe_" + $env:COMPUTERNAME)
Remove-Item $probe -Recurse -Force -ErrorAction SilentlyContinue   # start clean
New-Item -ItemType Directory -Force $probe | Out-Null
$fails = 0
function Check($label, $ok, $detail = '') {
    if ($ok) { Write-Host "  ok   $label" }
    else { Write-Host "  FAIL $label  $detail" -ForegroundColor Red; $script:fails++ }
}

# 1. plain write/read
$f = Join-Path $probe 'w.txt'
Set-Content -Path $f -Value 'hello from client' -Encoding utf8
Check 'client can write to the share' ((Get-Content $f) -eq 'hello from client')

# 2. atomic rename -- the operation the replica publish and the queue depend on
$tmp = Join-Path $probe 't.tmp'; $dst = Join-Path $probe 't.json'
Set-Content -Path $tmp -Value 'v1' -Encoding utf8
[System.IO.File]::Move($tmp, $dst)
Check 'rename lands on the share' (Test-Path $dst)

# 3. rename ONTO an open file -- the case that fails on Windows and not on POSIX
$tmp2 = Join-Path $probe 't2.tmp'
Set-Content -Path $tmp2 -Value 'v2' -Encoding utf8
$held = [System.IO.File]::Open($dst, 'Open', 'Read', 'Read')
try {
    try {
        # replace-over-existing, .NET Framework style
        [System.IO.File]::Delete($dst)
        [System.IO.File]::Move($tmp2, $dst)
        $moved = $true
    } catch { $moved = $false; $moveErr = $_.Exception.Message }
} finally { $held.Close() }
if ($moved) {
    Write-Host "  note: this share allowed a replace over an open file"
} else {
    Write-Host "  note: replace over an open file was refused ($moveErr)"
    Write-Host "        this is the case utils/atomic_replace.replace_with_retry exists for"
}
Remove-Item $tmp2 -ErrorAction SilentlyContinue

# 4. how slow is it really -- the number that tells you it is a real share
$payload = [byte[]]::new(65536)
$sw = [Diagnostics.Stopwatch]::StartNew()
for ($i = 0; $i -lt 40; $i++) {
    $p = Join-Path $probe "b$i.bin"
    [System.IO.File]::WriteAllBytes($p, $payload)
    [System.IO.File]::Move($p, "$p.done")
    Remove-Item "$p.done"
}
$sw.Stop()
$perOp = $sw.Elapsed.TotalMilliseconds / 40
Write-Host ("  share write+rename: {0:N2} ms/op" -f $perOp)
if ($HostName -eq $env:COMPUTERNAME) {
    Write-Host "  (timing is meaningless against your own machine -- Windows short-circuits it)"
} elseif ($perOp -lt 1.5) {
    Write-Warning "  that is local-disk speed for a REMOTE host, which is suspicious -- check you are not hitting a local cache or a mapped folder"
} else {
    Write-Host "  looks like a genuine remote share" -ForegroundColor Green
}

# 5. cross-PC visibility: leave a marker and list everyone else's
try {
    Set-Content -Path (Join-Path $unc "seen_by_$env:COMPUTERNAME.txt") `
                -Value (Get-Date -Format o) -Encoding utf8 -ErrorAction Stop
} catch {
    Check 'client can write to the SHARE ROOT (STR needs this for str_bus)' $false $_.Exception.Message
}
$others = @(Get-ChildItem $unc -Filter 'seen_by_*.txt' -ErrorAction SilentlyContinue |
            ForEach-Object { $_.Name })
Write-Host "  PCs that have run this check: $($others -join ', ')"
Check 'this PC sees at least one other PC on the share' ($others.Count -ge 2) `
      '(run this on a second PC too)'

Remove-Item $probe -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ""
if ($fails) { Write-Host "$fails CHECK(S) FAILED" -ForegroundColor Red; exit 1 }
Write-Host "SHARE IS USABLE -- now run the checklist in docs/TEST_DAY.md" -ForegroundColor Green
exit 0
