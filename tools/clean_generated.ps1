param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$build = Join-Path $root 'build'
$keep = @('build/full-zh-CN/rom.zar', 'build/full-zh-CN/Dementium II.exe',
          'build/original/rom.zar', 'build/original/Dementium II.exe',
          'build/text-layout-fix/original/rom.zar')
$tracked = @{}
git -C $root ls-files | ForEach-Object { $tracked[$_.Replace('\','/')] = $true }
# Never traverse junctions or operate outside this checkout.
$links = @(Get-ChildItem -LiteralPath $root -Recurse -Force -Attributes ReparsePoint)
if ($links.Count) { throw 'Reparse points present; inspect them before cleaning.' }
$cacheDirectories = @(foreach ($area in @('tools', 'tests')) {
    Get-ChildItem -LiteralPath (Join-Path $root $area) -Directory -Recurse -Force -Filter '__pycache__'
})
$files = @(Get-ChildItem -LiteralPath $build -Recurse -File -Force) + @(
    $cacheDirectories | ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -File -Filter '*.pyc' }
)
$targets = @($files | Where-Object {
    $rel = $_.FullName.Substring($root.Length + 1).Replace('\','/')
    -not $tracked.ContainsKey($rel) -and $rel -notin $keep -and
    $rel -notlike 'build/archive/*' -and
    $rel -notlike 'build/maintenance/*' -and (
        $rel -like 'build/toolchain/*' -or
        $rel -match '^build/repro-[0-9]+/' -or
        $rel -match '^(tools|tests)/(?:[^/]+/)*__pycache__/[^/]+\.pyc$' -or
        $rel -like 'build/inputs/releases/*' -or
        $rel -match '^build/installer/(recovered-v[^/]+|real-fixture-[^/]+|resource-real-[^/]+|resource-older-[^/]+|material-unit-fixtures|build-smoke-fixtures|tests)/' -or
        $rel -match '^build/update-[0-9]+/(archive-restore-test|rollback-copy)/' -or
        $rel -match '^build/full-zh-CN/(rollback-shell|rollback-test)/' -or
        $rel -match '^build/update-[0-9]+/native/(fixed\.exe|modified\.exe|[0-9a-f]{64}\.pkl|matching\.(json|log)|match_native\.py|replay-map\.json|replay-v104\.log)$' -or
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
    $rel = $path.Substring($root.Length + 1).Replace('\','/')
    $cache = $path.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -and
             $rel -match '^(tools|tests)/(?:[^/]+/)*__pycache__/[^/]+\.pyc$'
    if (-not $path.StartsWith($build + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -and -not $cache) { throw "Outside generated roots: $path" }
    Remove-Item -LiteralPath $path -Force
}
Write-Output "DELETED=$($targets.Count) BYTES=$total"

$empty = @(Get-ChildItem -LiteralPath $build -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending)
foreach ($directory in $empty) {
    $path = [IO.Path]::GetFullPath($directory.FullName)
    if (-not $path.StartsWith($build + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Outside build: $path" }
    if (-not (Get-ChildItem -LiteralPath $path -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $path }
}
foreach ($directory in $cacheDirectories) {
    $path = [IO.Path]::GetFullPath($directory.FullName)
    if (-not $path.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or $directory.Name -ne '__pycache__') { throw "Outside cache root: $path" }
    if (-not (Get-ChildItem -LiteralPath $path -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $path }
}
