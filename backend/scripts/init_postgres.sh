#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

ENV_PATH="${BACKEND_DIR}/.env"
SAMPLE_PATH="${BACKEND_DIR}/.env.sample"
ENV_SOURCE="${ENV_PATH}"

if [[ ! -f "${ENV_SOURCE}" ]]; then
  ENV_SOURCE="${SAMPLE_PATH}"
fi

if [[ ! -f "${ENV_SOURCE}" ]]; then
  echo "Error: .env and .env.sample are both missing in backend directory." >&2
  exit 1
fi

get_config_value() {
  local key="$1"
  local default_value="${2:-}"
  local line

  line="$(grep -E "^[[:space:]]*${key}=" "${ENV_SOURCE}" | tail -n 1 || true)"
  if [[ -z "${line}" ]]; then
    echo "${default_value}"
    return
  fi

  line="${line#*=}"
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"

  if [[ "${line}" =~ ^\".*\"$ ]]; then
    line="${line:1:-1}"
  elif [[ "${line}" =~ ^\'.*\'$ ]]; then
    line="${line:1:-1}"
  fi

  echo "${line}"
}

CONTAINER_NAME="${1:-rasa-postgres}"
DATABASE_URL_VALUE="$(get_config_value "DATABASE_URL" "postgresql+asyncpg://postgres:postgres@localhost:5432/rasa_ec_bot")"
DATABASE_NAME="${DATABASE_URL_VALUE##*/}"
DATABASE_NAME="${DATABASE_NAME%%\?*}"

if [[ ! "${DATABASE_NAME}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  echo "Error: unsafe database name: ${DATABASE_NAME}" >&2
  exit 1
fi

INIT_SQL_PATH="${BACKEND_DIR}/db/init_db.sql"
SEED_SQL_PATH="${BACKEND_DIR}/db/seed_data.sql"

if [[ ! -f "${INIT_SQL_PATH}" ]]; then
  echo "Error: missing file: ${INIT_SQL_PATH}" >&2
  exit 1
fi

if [[ ! -f "${SEED_SQL_PATH}" ]]; then
  echo "Error: missing file: ${SEED_SQL_PATH}" >&2
  exit 1
fi

RUNNING="$(docker ps --filter "name=^/${CONTAINER_NAME}$" --format "{{.Names}}" | head -n 1 || true)"
if [[ -z "${RUNNING}" ]]; then
  echo "Error: PostgreSQL container is not running: ${CONTAINER_NAME}" >&2
  exit 1
fi

MAX_RETRIES=30
READY=0

for ((i=1; i<=MAX_RETRIES; i++)); do
  if docker exec "${CONTAINER_NAME}" pg_isready -U postgres >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [[ "${READY}" -ne 1 ]]; then
  echo "Error: PostgreSQL is not ready after ${MAX_RETRIES} retries." >&2
  exit 1
fi

EXISTS="$(docker exec "${CONTAINER_NAME}" psql -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${DATABASE_NAME}'" | tr -d '[:space:]')"
if [[ "${EXISTS}" != "1" ]]; then
  docker exec "${CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U postgres -d postgres -c "CREATE DATABASE ${DATABASE_NAME}"
fi

docker cp "${INIT_SQL_PATH}" "${CONTAINER_NAME}:/tmp/init_db.sql"
docker cp "${SEED_SQL_PATH}" "${CONTAINER_NAME}:/tmp/seed_data.sql"

docker exec "${CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U postgres -d "${DATABASE_NAME}" -f /tmp/init_db.sql
docker exec "${CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U postgres -d "${DATABASE_NAME}" -f /tmp/seed_data.sql

echo "PostgreSQL initialization complete."
echo "Container : ${CONTAINER_NAME}"
echo "Database  : ${DATABASE_NAME}"
echo "Source    : /tmp/init_db.sql, /tmp/seed_data.sql"
