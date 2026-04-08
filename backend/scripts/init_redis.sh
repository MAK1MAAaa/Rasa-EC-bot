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

CONTAINER_NAME="$(get_config_value "REDIS_DOCKER_CONTAINER_NAME" "rasa-redis")"
INIT_MARKER_KEY="$(get_config_value "REDIS_INIT_MARKER_KEY" "rasa_ec_bot:system:initialized_at")"
SCHEMA_KEY="$(get_config_value "REDIS_INIT_SCHEMA_KEY" "rasa_ec_bot:system:schema_version")"
SCHEMA_VERSION="$(get_config_value "REDIS_INIT_SCHEMA_VERSION" "1")"

RUNNING="$(docker ps --filter "name=^/${CONTAINER_NAME}$" --format "{{.Names}}" | head -n 1 || true)"
if [[ -z "${RUNNING}" ]]; then
  echo "Error: Redis container is not running: ${CONTAINER_NAME}. Run scripts/start_redis.sh first." >&2
  exit 1
fi

MAX_RETRIES=15
READY=0

for ((i=1; i<=MAX_RETRIES; i++)); do
  PONG="$(docker exec "${CONTAINER_NAME}" redis-cli ping 2>/dev/null || true)"
  if [[ "${PONG}" == "PONG" ]]; then
    READY=1
    break
  fi
  sleep 1
done

if [[ "${READY}" -ne 1 ]]; then
  echo "Error: Redis is not ready after ${MAX_RETRIES} retries." >&2
  exit 1
fi

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
docker exec "${CONTAINER_NAME}" redis-cli SET "${INIT_MARKER_KEY}" "${TIMESTAMP}" >/dev/null
docker exec "${CONTAINER_NAME}" redis-cli SETNX "${SCHEMA_KEY}" "${SCHEMA_VERSION}" >/dev/null

echo "Redis initialization complete."
echo "Container  : ${CONTAINER_NAME}"
echo "Marker key : ${INIT_MARKER_KEY} = ${TIMESTAMP}"
echo "Schema key : ${SCHEMA_KEY} = ${SCHEMA_VERSION} (set-once)"
