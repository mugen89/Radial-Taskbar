# Builds Radial Taskbar and its installer into .\dist
param([switch]$Clean)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$build = Join-Path $root 'build'
$dist = Join-Path $root 'dist'

foreach ($tool in 'cmake', 'ninja', 'g++', 'windres') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool was not found on PATH. Install WinLibs: winget install BrechtSanders.WinLibs.POSIX.UCRT"
    }
}
if ($Clean -and (Test-Path $build)) { Remove-Item $build -Recurse -Force }

if (-not (Test-Path (Join-Path $root 'res\app.ico'))) {
    python (Join-Path $root 'tools\make_icon.py')
}

cmake -S $root -B $build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=g++ | Out-Null
if ($LASTEXITCODE) { throw 'CMake configuration failed' }
cmake --build $build
if ($LASTEXITCODE) { throw 'Build failed' }

New-Item -ItemType Directory -Force $dist | Out-Null
Copy-Item (Join-Path $build 'RadialTaskbar.exe') $dist -Force
Copy-Item (Join-Path $build 'RadialTaskbar-Setup.exe') $dist -Force
$skins = Join-Path $dist 'skins'
New-Item -ItemType Directory -Force $skins | Out-Null
Get-ChildItem $skins -Filter *.rskin | Remove-Item -Force
Copy-Item (Join-Path $build 'pak\*.rskin') $skins -Force
Copy-Item (Join-Path $root 'SKINS.md') $dist -Force

# Skins that are not part of the setup: single files to import
$import = Join-Path $dist 'skins to import'
New-Item -ItemType Directory -Force $import | Out-Null
Get-ChildItem $import -Filter *.rskin | Remove-Item -Force
Get-ChildItem (Join-Path $root 'skins-extra') -Directory | ForEach-Object {
    $p = Start-Process -FilePath (Join-Path $build 'RadialTaskbar.exe') -ArgumentList '--pack-skin', "`"$($_.FullName)`"", "`"$(Join-Path $import ($_.Name + '.rskin'))`"" -Wait -PassThru -WindowStyle Hidden
    if ($p.ExitCode) { throw "could not pack $($_.Name)" }
}
Get-ChildItem $dist -Filter *.exe | ForEach-Object { '{0,-28} {1,8:N0} KB' -f $_.Name, ($_.Length / 1KB) }
