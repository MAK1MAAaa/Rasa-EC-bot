Param(
    [switch]$Recreate
)

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
$RepoRoot = Split-Path -Parent $BackendDir

$EnvPath = Join-Path $BackendDir ".env"
$SamplePath = Join-Path $BackendDir ".env.sample"
$EnvSource = if (Test-Path $EnvPath) { $EnvPath } else { $SamplePath }
$EnvLines = Get-Content -Path $EnvSource -ErrorAction Stop

$ContainerName = Get-ConfigValue -Lines $EnvLines -Key "REDIS_DOCKER_CONTAINER_NAME" -Default "rasa-redis"
$Image = Get-ConfigValue -Lines $EnvLines -Key "REDIS_DOCKER_IMAGE" -Default "redis:7"
$HostPort = Get-ConfigValue -Lines $EnvLines -Key "REDIS_DOCKER_HOST_PORT" -Default "6379"
$ContainerPort = Get-ConfigValue -Lines $EnvLines -Key "REDIS_DOCKER_CONTAINER_PORT" -Default "6379"
$DataDirRaw = Get-ConfigValue -Lines $EnvLines -Key "REDIS_DOCKER_DATA_DIR" -Default "../database/redisdata"
$AppendOnly = Get-ConfigValue -Lines $EnvLines -Key "REDIS_APPENDONLY" -Default "yes"
$BindAddress = Get-ConfigValue -Lines $EnvLines -Key "REDIS_BIND_ADDRESS" -Default "0.0.0.0"
$ProtectedMode = Get-ConfigValue -Lines $EnvLines -Key "REDIS_PROTECTED_MODE" -Default "yes"
$RedisPassword = Get-ConfigValue -Lines $EnvLines -Key "REDIS_PASSWORD" -Default ""

$DataDir = if ([System.IO.Path]::IsPathRooted($DataDirRaw)) {
    $DataDirRaw
} else {
    Join-Path $BackendDir $DataDirRaw
}
$DataDir = [System.IO.Path]::GetFullPath($DataDir)

if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

$Existing = docker ps -a --filter "name=^/$ContainerName$" --format "{{.Names}}"

if ($Existing -and $Recreate) {
    Write-Host "Removing existing container: $ContainerName"
    docker rm -f $ContainerName | Out-Null
    $Existing = ""
}

if (-not $Existing) {
    Write-Host "Creating redis container: $ContainerName"
    $RedisArgs = @("redis-server", "--appendonly", $AppendOnly, "--bind", $BindAddress, "--protected-mode", $ProtectedMode)
    if ($RedisPassword) {
        $RedisArgs += @("--requirepass", $RedisPassword)
    }
    docker run --name $ContainerName -p "${HostPort}:${ContainerPort}" -v "${DataDir}:/data" -d $Image @RedisArgs | Out-Null
} else {
    $Running = docker ps --filter "name=^/$ContainerName$" --format "{{.Names}}"
    if (-not $Running) {
        Write-Host "Starting existing redis container: $ContainerName"
        docker start $ContainerName | Out-Null
    } else {
        Write-Host "Redis container already running: $ContainerName"
    }
}

Write-Host "Redis docker setup complete."
Write-Host "Container: $ContainerName"
Write-Host "Data dir : $DataDir"
Write-Host "Port map : $HostPort -> $ContainerPort"
Write-Host "Bind addr: $BindAddress"
Write-Host "Protected: $ProtectedMode"
Write-Host ("Password : " + ($(if ($RedisPassword) { "configured" } else { "not configured" })))
