from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)


SUPPORTED_LLM_PROVIDERS = {"openai_compat", "ollama"}
LLM_PROVIDER_ALIASES = {
    "openai": "openai_compat",
    "deepseek": "openai_compat",
}


@dataclass(frozen=True)
class LLMEndpointConfig:
    provider: str
    base_url: str
    model: str
    timeout_sec: float
    api_key: str = ""
    name: str = "primary"

    def is_configured(self) -> bool:
        return bool(self.base_url.strip() and self.model.strip())


class LLMInvocationError(RuntimeError):
    pass


def normalize_llm_provider(provider: str) -> str:
    normalized = (provider or "ollama").strip().lower()
    normalized = LLM_PROVIDER_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(f"Unsupported llm_provider: {provider}")
    return normalized


def extract_openai_compat_message_text(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text_part = item.get("text")
            if isinstance(text_part, str) and text_part.strip():
                parts.append(text_part.strip())
        return "\n".join(parts).strip()
    return ""


def should_retry_with_fallback(exc: Exception) -> bool:
    if isinstance(exc, LLMInvocationError):
        return True
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code if exc.response is not None else None
        return status_code is not None and (status_code >= 500 or status_code in {408, 429})
    return False


async def _generate_text_with_endpoint(
    *,
    endpoint: LLMEndpointConfig,
    system_prompt: str,
    user_payload: dict[str, Any],
    temperature: float,
) -> str:
    if not endpoint.is_configured():
        raise LLMInvocationError(f"{endpoint.name} LLM endpoint is not fully configured")

    provider = normalize_llm_provider(endpoint.provider)
    serialized_payload = json.dumps(user_payload, ensure_ascii=False)

    if provider == "openai_compat":
        headers = {"Content-Type": "application/json"}
        if endpoint.api_key:
            headers["Authorization"] = f"Bearer {endpoint.api_key}"
        api_base = endpoint.base_url.rstrip("/")
        api_url = f"{api_base}/chat/completions" if api_base.endswith("/v1") else f"{api_base}/v1/chat/completions"
        body = {
            "model": endpoint.model,
            "temperature": temperature,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": serialized_payload},
            ],
        }
        async with httpx.AsyncClient(timeout=endpoint.timeout_sec) as client:
            response = await client.post(api_url, json=body, headers=headers)
        response.raise_for_status()
        content = extract_openai_compat_message_text(response.json())
        if not content:
            raise LLMInvocationError(f"{endpoint.name} LLM returned empty content")
        return content

    body = {
        "model": endpoint.model,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": serialized_payload},
        ],
    }
    async with httpx.AsyncClient(timeout=endpoint.timeout_sec) as client:
        response = await client.post(f"{endpoint.base_url.rstrip('/')}/api/chat", json=body)
    response.raise_for_status()
    response_payload = response.json() if response.content else {}
    if not isinstance(response_payload, dict):
        raise LLMInvocationError(f"{endpoint.name} LLM returned invalid payload")
    message_payload = response_payload.get("message")
    if not isinstance(message_payload, dict):
        raise LLMInvocationError(f"{endpoint.name} LLM payload is missing message field")
    content = str(message_payload.get("content") or "").strip()
    if not content:
        raise LLMInvocationError(f"{endpoint.name} LLM returned empty content")
    return content


async def generate_text_with_failover(
    *,
    primary_endpoint: LLMEndpointConfig,
    fallback_endpoint: LLMEndpointConfig | None,
    system_prompt: str,
    user_payload: dict[str, Any],
    temperature: float = 0.0,
) -> str:
    endpoints = [primary_endpoint]
    if fallback_endpoint and fallback_endpoint.is_configured():
        endpoints.append(fallback_endpoint)

    last_error: Exception | None = None
    for index, endpoint in enumerate(endpoints):
        try:
            return await _generate_text_with_endpoint(
                endpoint=endpoint,
                system_prompt=system_prompt,
                user_payload=user_payload,
                temperature=temperature,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            has_next_endpoint = index + 1 < len(endpoints)
            if not has_next_endpoint or not should_retry_with_fallback(exc):
                break
            next_endpoint = endpoints[index + 1]
            logger.warning(
                "LLM endpoint %s failed, switching to %s: %s",
                endpoint.name,
                next_endpoint.name,
                exc,
            )

    if last_error is None:
        raise LLMInvocationError("No LLM endpoint is available")
    raise LLMInvocationError(str(last_error)) from last_error
