Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ConfigValue {
    param(
        [string[]]$Lines,
        [string]$Key,
        [string]$Default = ""
    )

    foreach ($line in $Lines) {
        if ($line -match "^\s*$Key=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $Default
}

$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptsDir

$EnvPath = Join-Path $BackendDir ".env"
$SamplePath = Join-Path $BackendDir ".env.sample"
$EnvSource = if (Test-Path $EnvPath) { $EnvPath } else { $SamplePath }
$EnvLines = Get-Content -Path $EnvSource -ErrorAction Stop

$ContainerName = Get-ConfigValue -Lines $EnvLines -Key "REDIS_DOCKER_CONTAINER_NAME" -Default "rasa-redis"
$InitMarkerKey = Get-ConfigValue -Lines $EnvLines -Key "REDIS_INIT_MARKER_KEY" -Default "rasa_ec_bot:system:initialized_at"
$SchemaKey = Get-ConfigValue -Lines $EnvLines -Key "REDIS_INIT_SCHEMA_KEY" -Default "rasa_ec_bot:system:schema_version"
$SchemaVersion = Get-ConfigValue -Lines $EnvLines -Key "REDIS_INIT_SCHEMA_VERSION" -Default "1"

$Running = docker ps --filter "name=^/$ContainerName$" --format "{{.Names}}"
if (-not $Running) {
    throw "Redis container is not running: $ContainerName. Run scripts/start_redis.ps1 first."
}

$MaxRetries = 15
$Ready = $false
for ($i = 1; $i -le $MaxRetries; $i++) {
    $pong = docker exec $ContainerName redis-cli ping 2>$null
    if ($pong -match "PONG") {
        $Ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $Ready) {
    throw "Redis is not ready after $MaxRetries retries."
}

$timestamp = [DateTime]::UtcNow.ToString("o")
docker exec $ContainerName redis-cli SET $InitMarkerKey $timestamp | Out-Null
docker exec $ContainerName redis-cli SETNX $SchemaKey $SchemaVersion | Out-Null

Write-Host "Redis initialization complete."
Write-Host "Container: $ContainerName"
Write-Host "Marker key: $InitMarkerKey = $timestamp"
Write-Host "Schema key: $SchemaKey = $SchemaVersion (set-once)"
