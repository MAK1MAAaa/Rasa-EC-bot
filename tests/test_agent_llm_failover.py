from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"

backend_pkg = types.ModuleType("backend")
backend_pkg.__path__ = [str(BACKEND_DIR)]
app_pkg = types.ModuleType("backend.app")
app_pkg.__path__ = [str(APP_DIR)]
sys.modules.setdefault("backend", backend_pkg)
sys.modules.setdefault("backend.app", app_pkg)

MODULE_SPEC = importlib.util.spec_from_file_location("backend.app.llm_client", APP_DIR / "llm_client.py")
LLM_MODULE = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC and MODULE_SPEC.loader
sys.modules["backend.app.llm_client"] = LLM_MODULE
MODULE_SPEC.loader.exec_module(LLM_MODULE)


def make_http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://llm.example.test")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


class AgentLlmFailoverTests(unittest.IsolatedAsyncioTestCase):
    def test_deepseek_provider_alias_uses_openai_compatible_client(self) -> None:
        self.assertEqual(LLM_MODULE.normalize_llm_provider("DeepSeek"), "openai_compat")
        self.assertEqual(LLM_MODULE.normalize_llm_provider("deepseek"), "openai_compat")

    async def test_primary_500_uses_fallback_endpoint(self) -> None:
        primary = LLM_MODULE.LLMEndpointConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            model="primary-model",
            timeout_sec=10,
            name="primary",
        )
        fallback = LLM_MODULE.LLMEndpointConfig(
            provider="openai_compat",
            base_url="http://127.0.0.1:8002/v1",
            model="fallback-model",
            timeout_sec=10,
            name="fallback",
        )

        with patch.object(
            LLM_MODULE,
            "_generate_text_with_endpoint",
            new=AsyncMock(side_effect=[make_http_error(500), "fallback reply"]),
        ) as mocked_call:
            result = await LLM_MODULE.generate_text_with_failover(
                primary_endpoint=primary,
                fallback_endpoint=fallback,
                system_prompt="system",
                user_payload={"message": "hello"},
                temperature=0.2,
            )

        self.assertEqual(result, "fallback reply")
        self.assertEqual(mocked_call.await_count, 2)

    async def test_primary_empty_response_uses_fallback_endpoint(self) -> None:
        primary = LLM_MODULE.LLMEndpointConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            model="primary-model",
            timeout_sec=10,
            name="primary",
        )
        fallback = LLM_MODULE.LLMEndpointConfig(
            provider="openai_compat",
            base_url="http://127.0.0.1:8002/v1",
            model="fallback-model",
            timeout_sec=10,
            name="fallback",
        )

        with patch.object(
            LLM_MODULE,
            "_generate_text_with_endpoint",
            new=AsyncMock(
                side_effect=[LLM_MODULE.LLMInvocationError("primary LLM returned empty content"), "fallback reply"]
            ),
        ) as mocked_call:
            result = await LLM_MODULE.generate_text_with_failover(
                primary_endpoint=primary,
                fallback_endpoint=fallback,
                system_prompt="system",
                user_payload={"message": "hello"},
            )

        self.assertEqual(result, "fallback reply")
        self.assertEqual(mocked_call.await_count, 2)

    async def test_primary_400_does_not_use_fallback_endpoint(self) -> None:
        primary = LLM_MODULE.LLMEndpointConfig(
            provider="openai_compat",
            base_url="http://127.0.0.1:8002/v1",
            model="primary-model",
            timeout_sec=10,
            name="primary",
        )
        fallback = LLM_MODULE.LLMEndpointConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            model="fallback-model",
            timeout_sec=10,
            name="fallback",
        )

        with patch.object(
            LLM_MODULE,
            "_generate_text_with_endpoint",
            new=AsyncMock(side_effect=make_http_error(400)),
        ) as mocked_call:
            with self.assertRaises(LLM_MODULE.LLMInvocationError):
                await LLM_MODULE.generate_text_with_failover(
                    primary_endpoint=primary,
                    fallback_endpoint=fallback,
                    system_prompt="system",
                    user_payload={"message": "hello"},
                )

        self.assertEqual(mocked_call.await_count, 1)


if __name__ == "__main__":
    unittest.main()
