param([switch]$PrepareOnly, [switch]$PreferLocalBuild)
$ErrorActionPreference = 'Stop'
function Get-ArchiveHash([string]$File) {
    $stream = [IO.File]::OpenRead($File)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}
try {
    $creatorRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $localElectron = Join-Path $creatorRoot 'node_modules/electron/dist/electron.exe'
    $localRenderer = Join-Path $creatorRoot 'dist/index.html'
    $localMain = Join-Path $creatorRoot 'electron/main.cjs'
    $localSdk = if ($env:CREATOR_RENPY_SDK) { $env:CREATOR_RENPY_SDK } else { Join-Path $creatorRoot '../renpy-8.5.3-sdk' }
    $localPython = Join-Path $localSdk 'lib/py3-windows-x86_64/python.exe'
    if ($PreferLocalBuild -and -not $PrepareOnly -and (Test-Path -LiteralPath $localElectron) -and (Test-Path -LiteralPath $localRenderer) -and (Test-Path -LiteralPath $localMain) -and (Test-Path -LiteralPath $localPython)) {
        Write-Host 'Starting the current local IDE build...'
        Start-Process -FilePath $localElectron -ArgumentList ('"' + $creatorRoot + '"') -WorkingDirectory $creatorRoot -WindowStyle Normal
        exit 0
    }
    $portableRoot = Join-Path $creatorRoot 'portable'
    $manifestPath = Join-Path $portableRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw 'Portable package is missing. Pull the repository including Git LFS files, or build the IDE. See creator/README.md.'
    }
    $manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
    $archiveName = [string]$manifest.archive
    $expectedHash = [string]$manifest.sha256
    if ($archiveName -ne [IO.Path]::GetFileName($archiveName) -or $archiveName -notlike '*.zip' -or $expectedHash -notmatch '^[a-fA-F0-9]{64}$') {
        throw 'Invalid portable package manifest.'
    }
    $archivePath = Join-Path $portableRoot $archiveName
    if (-not (Test-Path -LiteralPath $archivePath)) {
        throw 'Portable archive is missing. Run git lfs install and git lfs pull in the repository.'
    }
    $archiveSize = (Get-Item -LiteralPath $archivePath).Length
    if ($archiveSize -lt 1024 -and [IO.File]::ReadAllText($archivePath).StartsWith('version https://git-lfs.github.com/spec/v1')) {
        throw 'Only a Git LFS pointer was downloaded. Run git lfs install and git lfs pull, then start again.'
    }
    if ($archiveSize -ne [long]$manifest.bytes) { throw 'Portable archive is incomplete. Run git lfs pull again.' }

    $cacheRoot = Join-Path $creatorRoot '.portable'
    $cacheName = $expectedHash.Substring(0, 16).ToLowerInvariant()
    $extractedRoot = Join-Path $cacheRoot $cacheName
    $executable = Join-Path $extractedRoot 'win-unpacked/Morinote IDE.exe'
    $markerPath = Join-Path $extractedRoot '.complete'
    if (-not ((Test-Path -LiteralPath $executable) -and (Test-Path -LiteralPath $markerPath) -and [IO.File]::ReadAllText($markerPath).Trim() -eq $expectedHash)) {
        Write-Host 'Preparing Morinote IDE. First launch extracts the bundled runtime; please wait...'
        if ((Get-ArchiveHash $archivePath) -ne $expectedHash) {
            throw 'Portable archive checksum does not match. Download it again with git lfs pull.'
        }
        [IO.Directory]::CreateDirectory($cacheRoot) | Out-Null
        $temporaryRoot = Join-Path $cacheRoot ('extract-' + [guid]::NewGuid().ToString('N'))
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [IO.Compression.ZipFile]::ExtractToDirectory($archivePath, $temporaryRoot)
        if (-not (Test-Path -LiteralPath (Join-Path $temporaryRoot 'win-unpacked/Morinote IDE.exe'))) {
            throw 'The archive does not contain the IDE executable.'
        }
        [IO.File]::WriteAllText((Join-Path $temporaryRoot '.complete'), $expectedHash)
        if (Test-Path -LiteralPath $extractedRoot) {
            $oldRoot = Join-Path $cacheRoot ('incomplete-' + [guid]::NewGuid().ToString('N'))
            foreach ($candidate in @($extractedRoot, $oldRoot)) {
                if (-not [IO.Path]::GetFullPath($candidate).StartsWith($cacheRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid cache destination.' }
            }
            Move-Item -LiteralPath $extractedRoot -Destination $oldRoot -ErrorAction Stop
        }
        foreach ($candidate in @($temporaryRoot, $extractedRoot)) {
            if (-not [IO.Path]::GetFullPath($candidate).StartsWith($cacheRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid cache destination.' }
        }
        Move-Item -LiteralPath $temporaryRoot -Destination $extractedRoot -ErrorAction Stop
    }
    if ($PrepareOnly) { Write-Output $executable; exit 0 }
    Start-Process -FilePath $executable -WorkingDirectory (Split-Path -Parent $executable) -WindowStyle Normal
} catch {
    Write-Host ('Unable to start Morinote IDE: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
