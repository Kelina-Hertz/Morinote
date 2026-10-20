$ErrorActionPreference = 'Stop'
$creatorRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$package = [IO.File]::ReadAllText((Join-Path $creatorRoot 'package.json')) | ConvertFrom-Json
$version = [string]$package.version
if ($version -notmatch '^[A-Za-z0-9._-]+$') { throw 'Invalid package version.' }
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $creatorRoot $package.build.directories.output))
if (-not $releaseRoot.StartsWith($creatorRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid release directory.' }
$unpacked = Join-Path $releaseRoot 'win-unpacked'
if (-not (Test-Path -LiteralPath (Join-Path $unpacked 'Morinote IDE.exe'))) { throw 'Build the portable IDE first.' }
$portableRoot = Join-Path $creatorRoot 'portable'
[IO.Directory]::CreateDirectory($portableRoot) | Out-Null
$archiveName = 'Morinote-IDE-' + $version + '-win-x64.zip'
$archivePath = Join-Path $portableRoot $archiveName
$temporaryArchive = Join-Path $portableRoot ('package-' + [guid]::NewGuid().ToString('N') + '.tmp')
Add-Type -AssemblyName System.IO.Compression.FileSystem
Write-Host 'Compressing the portable IDE and bundled runtimes...'
[IO.Compression.ZipFile]::CreateFromDirectory($unpacked, $temporaryArchive, [IO.Compression.CompressionLevel]::Optimal, $true)
$manifest = [ordered]@{
    version = $version
    platform = 'windows-x64'
    archive = $archiveName
    bytes = (Get-Item -LiteralPath $temporaryArchive).Length
    sha256 = (Get-FileHash -LiteralPath $temporaryArchive -Algorithm SHA256).Hash.ToLowerInvariant()
}
$manifestPath = Join-Path $portableRoot 'manifest.json'
$temporaryManifest = Join-Path $portableRoot ('manifest-' + [guid]::NewGuid().ToString('N') + '.tmp')
[IO.File]::WriteAllText($temporaryManifest, ($manifest | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $temporaryArchive -Destination $archivePath -Force
Move-Item -LiteralPath $temporaryManifest -Destination $manifestPath -Force
Write-Host ('Portable archive ready: ' + $archiveName)
