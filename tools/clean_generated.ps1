param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$build = Join-Path $root 'build'
$keep = @('build/full-zh-CN/rom.zar', 'build/original/rom.zar', 'build/text-layout-fix/original/rom.zar')
$tracked = @{}
git -C $root ls-files | ForEach-Object { $tracked[$_.Replace('\','/')] = $true }
# Never traverse junctions or operate outside this checkout.
$links = @(Get-ChildItem -LiteralPath $root -Recurse -Force -Attributes ReparsePoint)
if ($links.Count) { throw 'Reparse points present; inspect them before cleaning.' }
$files = @(Get-ChildItem -LiteralPath $build -Recurse -File -Force)
$targets = @($files | Where-Object {
    $rel = $_.FullName.Substring($root.Length + 1).Replace('\','/')
    -not $tracked.ContainsKey($rel) -and $rel -notin $keep -and
    $rel -notlike 'build/archive/*' -and
    $rel -notlike 'build/maintenance/*' -and (
        $rel -like 'build/toolchain/*' -or
        $_.Extension -eq '.zar' -or
        ($_.Length -gt 20MB -and $_.Extension -in @('.exe','.zip')) -or
        $rel -match '^build/(installer/(bin|obj|Installer-obj|Tests-obj|test-obj|publish)/|backup-layout-fix/(bin|obj)/)' )
})
$targets | Select-Object FullName,Length
$total = [long](($targets | Measure-Object Length -Sum).Sum)
Write-Output "CANDIDATES=$($targets.Count) BYTES=$total APPLY=$Apply"
if (-not $Apply) { return }
$report = Join-Path $build 'maintenance'
New-Item -ItemType Directory -Path $report -Force | Out-Null
# Freeze identities before deletion; source inputs and recipes regenerate copies.
$manifest = @($targets | ForEach-Object {
    [PSCustomObject]@{
        Path = $_.FullName
        RelativePath = $_.FullName.Substring($root.Length + 1).Replace('\','/')
        Length = $_.Length
        SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        Recovery = 'Regenerate from retained original, source tools and historical report.'
    }
})
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
ConvertTo-Json -InputObject $manifest -Depth 4 | Set-Content -LiteralPath (Join-Path $report ('deleted-files-' + $stamp + '.json')) -Encoding utf8
ConvertTo-Json -InputObject $manifest -Depth 4 | Set-Content -LiteralPath (Join-Path $report 'deleted-files.json') -Encoding utf8
foreach ($file in $targets) {
    $path = [IO.Path]::GetFullPath($file.FullName)
    if (-not $path.StartsWith($build + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Outside build: $path" }
    Remove-Item -LiteralPath $path -Force
}
Write-Output "DELETED=$($targets.Count) BYTES=$total"

$empty = @(Get-ChildItem -LiteralPath $build -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending)
foreach ($directory in $empty) {
    $path = [IO.Path]::GetFullPath($directory.FullName)
    if (-not $path.StartsWith($build + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Outside build: $path" }
    if (-not (Get-ChildItem -LiteralPath $path -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $path }
}
