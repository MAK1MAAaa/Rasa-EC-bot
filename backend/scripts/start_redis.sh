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

RECREATE=0
if [[ "${1:-}" == "--recreate" ]]; then
  RECREATE=1
fi

CONTAINER_NAME="$(get_config_value "REDIS_DOCKER_CONTAINER_NAME" "rasa-redis")"
IMAGE="$(get_config_value "REDIS_DOCKER_IMAGE" "redis:7")"
HOST_PORT="$(get_config_value "REDIS_DOCKER_HOST_PORT" "6379")"
CONTAINER_PORT="$(get_config_value "REDIS_DOCKER_CONTAINER_PORT" "6379")"
DATA_DIR_RAW="$(get_config_value "REDIS_DOCKER_DATA_DIR" "../database/redisdata")"
APPENDONLY="$(get_config_value "REDIS_APPENDONLY" "yes")"
BIND_ADDRESS="$(get_config_value "REDIS_BIND_ADDRESS" "0.0.0.0")"
PROTECTED_MODE="$(get_config_value "REDIS_PROTECTED_MODE" "yes")"
REDIS_PASSWORD="$(get_config_value "REDIS_PASSWORD" "")"

if [[ "${DATA_DIR_RAW}" = /* ]]; then
  DATA_DIR="${DATA_DIR_RAW}"
else
  DATA_DIR="${BACKEND_DIR}/${DATA_DIR_RAW}"
fi

mkdir -p "${DATA_DIR}"
DATA_DIR="$(cd -- "${DATA_DIR}" && pwd)"

EXISTING="$(docker ps -a --filter "name=^/${CONTAINER_NAME}$" --format "{{.Names}}" | head -n 1 || true)"

if [[ -n "${EXISTING}" && "${RECREATE}" -eq 1 ]]; then
  echo "Removing existing container: ${CONTAINER_NAME}"
  docker rm -f "${CONTAINER_NAME}" >/dev/null
  EXISTING=""
fi

if [[ -z "${EXISTING}" ]]; then
  echo "Creating redis container: ${CONTAINER_NAME}"
  REDIS_ARGS=(
    redis-server
    --appendonly "${APPENDONLY}"
    --bind "${BIND_ADDRESS}"
    --protected-mode "${PROTECTED_MODE}"
  )
  if [[ -n "${REDIS_PASSWORD}" ]]; then
    REDIS_ARGS+=(--requirepass "${REDIS_PASSWORD}")
  fi
  docker run \
    --name "${CONTAINER_NAME}" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    -v "${DATA_DIR}:/data" \
    -d "${IMAGE}" \
    "${REDIS_ARGS[@]}" >/dev/null
else
  RUNNING="$(docker ps --filter "name=^/${CONTAINER_NAME}$" --format "{{.Names}}" | head -n 1 || true)"
  if [[ -z "${RUNNING}" ]]; then
    echo "Starting existing redis container: ${CONTAINER_NAME}"
    docker start "${CONTAINER_NAME}" >/dev/null
  else
    echo "Redis container already running: ${CONTAINER_NAME}"
  fi
fi

echo "Redis docker setup complete."
echo "Container: ${CONTAINER_NAME}"
echo "Data dir : ${DATA_DIR}"
echo "Port map : ${HOST_PORT} -> ${CONTAINER_PORT}"
echo "Bind addr: ${BIND_ADDRESS}"
echo "Protected: ${PROTECTED_MODE}"
if [[ -n "${REDIS_PASSWORD}" ]]; then
  echo "Password : configured"
else
  echo "Password : not configured"
fi
