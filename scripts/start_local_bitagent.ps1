param(
    [Parameter(Mandatory=$true)][string]$Config,
    [Parameter(Mandatory=$true)][string]$RuntimeDir
)
$ErrorActionPreference = 'Stop'
$runtimeConfig = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$notBefore = [DateTimeOffset]::Parse($runtimeConfig.gpu_not_before_utc)
if ([DateTimeOffset]::UtcNow -lt $notBefore) {
    throw "GPU reservation is active until $($notBefore.ToString('o')); server was not started."
}
if (-not (Test-Path -LiteralPath $runtimeConfig.server_exe)) { throw 'Pinned llama-server executable missing.' }
foreach ($artifactName in @('base', 'adapter')) {
    $artifact = $runtimeConfig.$artifactName
    if (-not (Test-Path -LiteralPath $artifact.path)) { throw "Missing $artifactName artifact." }
    if ((Get-Item -LiteralPath $artifact.path).Length -ne $artifact.bytes) { throw "$artifactName byte count mismatch." }
    $actualDigest = (Get-FileHash -LiteralPath $artifact.path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualDigest -ne $artifact.sha256) { throw "$artifactName checksum mismatch." }
}
if ((Get-FileHash -LiteralPath $runtimeConfig.server_exe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $runtimeConfig.server_sha256) {
    throw 'Pinned llama-server executable checksum mismatch.'
}
$gpuLines = & nvidia-smi --query-gpu=memory.free,memory.total --format=csv,noheader,nounits
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify GPU availability; server was not started.' }
$memoryFields = ($gpuLines | Select-Object -First 1) -split ','
$freeMiB = [int]$memoryFields[0].Trim()
if ($freeMiB -lt $runtimeConfig.minimum_free_vram_mib) { throw "GPU has only $freeMiB MiB free; leaving it untouched." }
$computeApps = & nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader,nounits
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify active compute processes; server was not started.' }
if ($computeApps -and ($computeApps | Where-Object { $_.Trim() -and $_ -notmatch 'No running' })) {
    throw 'GPU compute processes are still active; server was not started.'
}
$endpointUri = [Uri]$runtimeConfig.endpoint
if ($endpointUri.Host -ne '127.0.0.1') { throw 'Server must bind to loopback.' }
$listener = [Net.Sockets.TcpClient]::new()
try {
    $pending = $listener.BeginConnect('127.0.0.1', $endpointUri.Port, $null, $null)
    if ($pending.AsyncWaitHandle.WaitOne(400) -and $listener.Connected) { throw 'Selected port is already in use; refusing takeover.' }
} finally { $listener.Dispose() }
New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
$serverArguments = @(
    '--host', '127.0.0.1', '--port', [string]$endpointUri.Port,
    '-m', $runtimeConfig.base.path, '--lora', $runtimeConfig.adapter.path,
    '--alias', $runtimeConfig.model_alias, '-c', [string]$runtimeConfig.context,
    '--device', 'CUDA0', '-ngl', '99', '-t', '4', '-tb', '4', '-b', '128', '-ub', '64',
    '-ctk', 'q8_0', '-ctv', 'q8_0', '-fa', 'on', '--no-webui'
)
$serverProcess = Start-Process -FilePath $runtimeConfig.server_exe -ArgumentList $serverArguments `
    -WorkingDirectory (Split-Path -Parent $runtimeConfig.server_exe) -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $RuntimeDir 'server.stdout.log') `
    -RedirectStandardError (Join-Path $RuntimeDir 'server.stderr.log') -PassThru
[ordered]@{
    pid = $serverProcess.Id
    started_at = [DateTimeOffset]::UtcNow.ToString('o')
    executable = $runtimeConfig.server_exe
    arguments = $serverArguments
    preflight_free_vram_mib = $freeMiB
    config_sha256 = (Get-FileHash -LiteralPath $Config -Algorithm SHA256).Hash.ToLowerInvariant()
    authority = 'benchmark_inference_only'
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $RuntimeDir 'owned-server.json') -Encoding utf8
Write-Output "Started owned BitAgent server PID $($serverProcess.Id) at $($runtimeConfig.endpoint)."
