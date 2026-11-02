param(
    [Parameter(Mandatory=$true)][string]$Root,
    [Parameter(Mandatory=$true)][ValidatePattern('^S-1-4-\d+-\d+$')][string]$WriteSid
)
$ErrorActionPreference='Stop'
$snapshotRoot=[IO.Path]::GetFullPath($Root)
if ([IO.Path]::GetFileName($snapshotRoot) -ne 'project' -or
    -not (Test-Path -LiteralPath ([IO.Path]::Combine([IO.Path]::GetDirectoryName($snapshotRoot),'task.json')) -PathType Leaf)) {
    throw 'Only a registered private execution snapshot can receive the read capability.'
}
if ((Get-Item -LiteralPath $snapshotRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'A snapshot capability cannot target a link.'
}
$identity=[Security.Principal.SecurityIdentifier]::new($WriteSid)
$rule=[Security.AccessControl.FileSystemAccessRule]::new(
    $identity,
    [Security.AccessControl.FileSystemRights]::ReadAndExecute,
    ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit),
    [Security.AccessControl.PropagationFlags]::None,
    [Security.AccessControl.AccessControlType]::Allow
)
$permissions=Get-Acl -LiteralPath $snapshotRoot
[void]$permissions.AddAccessRule($rule)
# An elevated snapshot may inherit Administrators + OWNER RIGHTS only. The
# SDK's LUA token disables that administrator membership. Give the launching
# user RX in this private tree as well; no other user or authored path changes.
$reader=[Security.AccessControl.FileSystemAccessRule]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent().User,
    [Security.AccessControl.FileSystemRights]::ReadAndExecute,
    ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit),
    [Security.AccessControl.PropagationFlags]::None,
    [Security.AccessControl.AccessControlType]::Allow
)
[void]$permissions.AddAccessRule($reader)
Set-Acl -LiteralPath $snapshotRoot -AclObject $permissions
