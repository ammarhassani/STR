# Grant a client PC access to the STR share.
#
# Workgroup SMB has no shared directory, so a client PC authenticates against a
# LOCAL account on the host. The share currently grants ENGAMMARPC\WinDows only
# -- the owner's own account -- so any other PC is refused. The fix is a
# dedicated least-privilege account that exists on the host and is used by the
# clients, NOT enabling guest access: Microsoft disables insecure guest logons
# by default because they drop authentication and SMB signing entirely, which
# is not acceptable for FIU data.
#
# The account gets Change / Modify, not Full: clients read the replica and drop
# command files in the queue. They never need to alter the share itself.
#
# Run elevated:  powershell -ExecutionPolicy Bypass -File deploy\grant_share_access.ps1
[CmdletBinding()]
param(
    [string]$ShareName = "STR_data",
    [string]$AccountName = "STR_client",
    [string]$Password,
    [string]$SharePath = "C:\STR_data"
)

$ErrorActionPreference = "Stop"

function Say($msg) { Write-Output "  $msg" }

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Output "This script must run elevated (it creates a local account and edits ACLs)."
    exit 1
}

if (-not $Password) {
    Write-Output "Pass -Password. Example:"
    Write-Output "  .\grant_share_access.ps1 -Password 'SomeStrongPassphrase'"
    exit 1
}

Write-Output "=== 1. local account ==="
$secure = ConvertTo-SecureString $Password -AsPlainText -Force
$existing = Get-LocalUser -Name $AccountName -ErrorAction SilentlyContinue
if ($existing) {
    Set-LocalUser -Name $AccountName -Password $secure
    Say "$AccountName already existed - password reset"
} else {
    # -Description is capped at 48 characters by Windows; longer throws.
    New-LocalUser -Name $AccountName -Password $secure `
        -FullName "STR client (SMB share access)" `
        -Description "STR client SMB access (least privilege)" `
        -PasswordNeverExpires | Out-Null
    Say "created $AccountName"
}
# Standard user only. Never add this account to Administrators.
$inUsers = (Get-LocalGroupMember -Group "Users" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "*\$AccountName" })
if (-not $inUsers) {
    Add-LocalGroupMember -Group "Users" -Member $AccountName -ErrorAction SilentlyContinue
    Say "added to Users"
}
$isAdmin = (Get-LocalGroupMember -Group "Administrators" -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "*\$AccountName" })
if ($isAdmin) {
    Say "WARNING: $AccountName is in Administrators - removing"
    Remove-LocalGroupMember -Group "Administrators" -Member $AccountName
}

Write-Output "=== 2. share permission ==="
$acct = "$env:COMPUTERNAME\$AccountName"
Revoke-SmbShareAccess -Name $ShareName -AccountName $acct -Force -ErrorAction SilentlyContinue | Out-Null
Grant-SmbShareAccess -Name $ShareName -AccountName $acct -AccessRight Change -Force | Out-Null
Say "granted Change on share '$ShareName' to $acct"

# Guest access must stay off. If it was ever switched on, this share would be
# readable by anything on the network.
$guest = Get-SmbShareAccess -Name $ShareName |
         Where-Object { $_.AccountName -match 'Everyone|Guest|ANONYMOUS' }
if ($guest) {
    Say "WARNING: share is also granted to $($guest.AccountName -join ', ') - review this"
}

Write-Output "=== 3. NTFS permission ==="
# Share permissions and NTFS permissions are ANDed; the weaker one wins, so
# both have to allow it or the client gets a confusing access-denied.
$acl = Get-Acl $SharePath
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $acct, "Modify",
    "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($rule)
Set-Acl -Path $SharePath -AclObject $acl
Say "granted Modify on $SharePath to $acct"

Write-Output ""
Write-Output "=== result ==="
Get-SmbShareAccess -Name $ShareName | Format-Table -AutoSize | Out-String
Write-Output "On each CLIENT PC, connect with these credentials:"
Write-Output "  user: $acct"
Write-Output "  (the password you passed to this script)"
Write-Output ""
Write-Output "Rotate the password any time with:"
Write-Output "  Set-LocalUser -Name $AccountName -Password (Read-Host -AsSecureString)"
