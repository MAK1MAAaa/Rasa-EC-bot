param(
    [string]$ContainerName = "rasa-postgres",
    [string]$DatabaseName = ""
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

function Get-DatabaseNameFromUrl {
    param(
        [string]$DatabaseUrl
    )

    if (-not $DatabaseUrl) {
        return "rasa_ec_bot"
    }

    if ($DatabaseUrl -match "/([^/?]+)(?:\?.*)?$") {
        return $Matches[1]
    }

    return "rasa_ec_bot"
}

$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptsDir

$EnvPath = Join-Path $BackendDir ".env"
$SamplePath = Join-Path $BackendDir ".env.sample"
$EnvSource = if (Test-Path $EnvPath) { $EnvPath } else { $SamplePath }

if (-not (Test-Path $EnvSource)) {
    throw "Missing backend .env and .env.sample."
}

$EnvLines = Get-Content -Path $EnvSource -Encoding UTF8 -ErrorAction Stop

if (-not $DatabaseName) {
    $DatabaseUrl = Get-ConfigValue -Lines $EnvLines -Key "DATABASE_URL" -Default "postgresql+asyncpg://postgres:postgres@localhost:5432/rasa_ec_bot"
    $DatabaseName = Get-DatabaseNameFromUrl -DatabaseUrl $DatabaseUrl
}

if ($DatabaseName -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
    throw "Unsafe database name: $DatabaseName"
}

$InitSqlPath = Join-Path $BackendDir "db\init_db.sql"
$SeedSqlPath = Join-Path $BackendDir "db\seed_data.sql"

if (-not (Test-Path $InitSqlPath)) {
    throw "Missing file: $InitSqlPath"
}

if (-not (Test-Path $SeedSqlPath)) {
    throw "Missing file: $SeedSqlPath"
}

$Running = docker ps --filter "name=^/$ContainerName$" --format "{{.Names}}"
if (-not $Running) {
    throw "PostgreSQL container is not running: $ContainerName"
}

$MaxRetries = 30
$Ready = $false
for ($i = 1; $i -le $MaxRetries; $i++) {
    docker exec $ContainerName pg_isready -U postgres | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $Ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $Ready) {
    throw "PostgreSQL is not ready after $MaxRetries retries."
}

$Exists = docker exec $ContainerName psql -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName'"
if ($Exists.Trim() -ne "1") {
    docker exec $ContainerName psql -v ON_ERROR_STOP=1 -U postgres -d postgres -c "CREATE DATABASE $DatabaseName"
}

docker cp $InitSqlPath "${ContainerName}:/tmp/init_db.sql"
docker cp $SeedSqlPath "${ContainerName}:/tmp/seed_data.sql"

docker exec $ContainerName psql -v ON_ERROR_STOP=1 -U postgres -d $DatabaseName -f /tmp/init_db.sql
docker exec $ContainerName psql -v ON_ERROR_STOP=1 -U postgres -d $DatabaseName -f /tmp/seed_data.sql

Write-Host "PostgreSQL initialization complete."
Write-Host "Container : $ContainerName"
Write-Host "Database  : $DatabaseName"
Write-Host "Source    : /tmp/init_db.sql, /tmp/seed_data.sql"
