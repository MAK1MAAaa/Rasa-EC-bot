from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import random
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "backend" / "benchmarks" / "experiment.yaml"
DEFAULT_PROMPT_DIR = ROOT_DIR / "backend" / "benchmarks" / "prompts"

ORDER_ID_RE = re.compile(r"\bORD\d{6,}\b", flags=re.IGNORECASE)
CONFIRMATION_PATTERNS = [
    "确认",
    "请确认",
    "再次确认",
    "二次确认",
    "同意后",
    "确认后",
]
GENERIC_RECOMMENDATION_PATTERNS = [
    "请提供更多信息",
    "还有什么可以帮你",
    "我目前只能",
    "我无法直接推荐",
]


@dataclass(frozen=True)
class SampleRecord:
    sample_id: str
    scenario: str
    system_prompt: str
    context: str
    user_input: str
    requires_auth: bool
    requires_image: bool
    expected_capability: str
    checks: dict[str, Any]
    tags: list[str]
    image_case: str = ""


@dataclass(frozen=True)
class SystemTarget:
    name: str
    kind: str
    base_url: str
    path: str
    model: str
    auth_mode: str
    supports_image: bool
    supports_cards: bool
    requires_upload_step: bool
    upload_path: str = ""
    sender_id: str = "benchmark-user"
    login_url: str = ""
    me_url: str = ""


@dataclass(frozen=True)
class AuthConfig:
    login_url: str
    me_url: str
    customer_email: str
    customer_password: str


@dataclass
class AuthContext:
    token: str = ""
    user_id: str = ""
    email: str = ""
    username: str = ""

    @property
    def bearer_headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}


@dataclass
class BenchmarkEvent:
    timestamp: str
    system: str
    scenario: str
    sample_id: str
    repeat: int
    concurrency: int
    request_index: int
    requires_auth: bool
    requires_image: bool
    executed: bool
    unsupported: bool
    success: bool
    http_status: int | None
    error_type: str
    error_message: str
    latency_ms: float
    started_at: float
    finished_at: float
    response_text: str
    response_chars: int
    response_card_count: int
    response_action_count: int
    quality_status: str
    task_success: bool
    passed: bool
    quality_flags: dict[str, Any] = field(default_factory=dict)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="系统形态接口级 benchmark。")
    parser.add_argument("--systems", default="", help="逗号分隔，例如 rasa_only,llm_base_ollama")
    parser.add_argument("--scenarios", default="recommendation,after_sales,image_after_sales")
    parser.add_argument("--profile", choices=["quick", "medium", "high"], default="medium")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--results-root", type=Path, default=None)
    parser.add_argument("--requests-per-level", type=int, default=None)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--concurrency", default="", help="覆盖配置中的并发，例如 1,2,4")
    parser.add_argument("--timeout-sec", type=float, default=None)
    parser.add_argument("--warmup-requests", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def parse_csv_values(raw: str) -> list[str]:
    cleaned = raw.strip()
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def parse_concurrency_override(raw: str) -> list[int] | None:
    values = parse_csv_values(raw)
    if not values:
        return None
    parsed = [int(item) for item in values]
    if any(item <= 0 for item in parsed):
        raise ValueError("并发值必须大于 0。")
    return parsed


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("配置文件解析失败，请安装 pyyaml 或使用 JSON 风格 YAML。") from exc
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise RuntimeError("实验配置必须是对象。")
    return payload


def require_string(mapping: dict[str, Any], key: str, *, default: str = "") -> str:
    value = mapping.get(key, default)
    return str(value or "").strip()


def resolve_auth_config(config: dict[str, Any]) -> AuthConfig:
    auth_cfg = config.get("auth")
    if not isinstance(auth_cfg, dict):
        raise RuntimeError("缺少 auth 配置。")
    customer = auth_cfg.get("customer")
    if not isinstance(customer, dict):
        raise RuntimeError("缺少 auth.customer 配置。")
    return AuthConfig(
        login_url=require_string(auth_cfg, "login_url"),
        me_url=require_string(auth_cfg, "me_url"),
        customer_email=require_string(customer, "email"),
        customer_password=require_string(customer, "password"),
    )


def resolve_system_targets(config: dict[str, Any], requested_systems: list[str]) -> dict[str, SystemTarget]:
    systems_cfg = config.get("systems")
    if not isinstance(systems_cfg, dict):
        raise RuntimeError("缺少 systems 配置。")

    available_names = list(systems_cfg.keys())
    selected_names = requested_systems or available_names
    targets: dict[str, SystemTarget] = {}

    for name in selected_names:
        item = systems_cfg.get(name)
        if not isinstance(item, dict):
            raise RuntimeError(f"system 未配置: {name}")
        target = SystemTarget(
            name=name,
            kind=require_string(item, "kind"),
            base_url=require_string(item, "base_url"),
            path=require_string(item, "path"),
            model=require_string(item, "model"),
            auth_mode=require_string(item, "auth_mode", default="none"),
            supports_image=bool(item.get("supports_image", False)),
            supports_cards=bool(item.get("supports_cards", False)),
            requires_upload_step=bool(item.get("requires_upload_step", False)),
            upload_path=require_string(item, "upload_path"),
            sender_id=require_string(item, "sender_id", default=f"benchmark-{name}"),
            login_url=require_string(item, "login_url"),
            me_url=require_string(item, "me_url"),
        )
        if not target.kind or not target.base_url or not target.path:
            raise RuntimeError(f"system 配置不完整: {name}")
        targets[name] = target
    return targets


def load_dataset_file(path: Path) -> list[SampleRecord]:
    records: list[SampleRecord] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            record = SampleRecord(
                sample_id=str(payload.get("id") or f"{path.stem}-{line_no}"),
                scenario=str(payload.get("scenario") or path.stem),
                system_prompt=str(payload.get("system_prompt") or "").strip(),
                context=str(payload.get("context") or "").strip(),
                user_input=str(payload.get("user_input") or "").strip(),
                requires_auth=bool(payload.get("requires_auth", False)),
                requires_image=bool(payload.get("requires_image", False)),
                expected_capability=str(payload.get("expected_capability") or "").strip(),
                checks=dict(payload.get("checks") or {}),
                tags=[str(item).strip() for item in (payload.get("tags") or []) if str(item).strip()],
                image_case=str(payload.get("image_case") or "").strip(),
            )
            if not record.user_input:
                continue
            records.append(record)
    if not records:
        raise RuntimeError(f"数据集为空: {path}")
    return records


def resolve_dataset_files(dataset_arg: Path | None, scenarios: list[str]) -> dict[str, Path]:
    if dataset_arg is None:
        base_dir = DEFAULT_PROMPT_DIR
        return {scenario: (base_dir / f"{scenario}.jsonl").resolve() for scenario in scenarios}

    resolved = dataset_arg.resolve()
    if resolved.is_dir():
        return {scenario: (resolved / f"{scenario}.jsonl").resolve() for scenario in scenarios}

    if resolved.is_file() and len(scenarios) == 1:
        return {scenarios[0]: resolved}

    raise RuntimeError("--dataset 为文件时只能配合单一 scenario 使用；多场景请传目录。")


def resolve_image_path(config: dict[str, Any], sample: SampleRecord) -> Path:
    assets_dir = config.get("image_assets_dir")
    image_case_map = config.get("image_case_map")
    if not isinstance(assets_dir, str) or not assets_dir.strip():
        raise RuntimeError("缺少 image_assets_dir 配置。")
    if not isinstance(image_case_map, dict):
        raise RuntimeError("缺少 image_case_map 配置。")
    filename = image_case_map.get(sample.image_case)
    if not isinstance(filename, str) or not filename.strip():
        raise RuntimeError(f"图片 case 未配置: {sample.image_case}")
    path = (ROOT_DIR / assets_dir / filename).resolve()
    if not path.exists():
        raise RuntimeError(f"图片资源不存在: {path}")
    return path


async def login_for_auth_context(
    client: httpx.AsyncClient,
    auth_cfg: AuthConfig,
    *,
    login_url: str,
    me_url: str,
) -> AuthContext:
    login_response = await client.post(
        login_url,
        json={"email": auth_cfg.customer_email, "password": auth_cfg.customer_password},
    )
    login_response.raise_for_status()
    login_payload = login_response.json()
    if not isinstance(login_payload, dict) or not str(login_payload.get("access_token") or "").strip():
        raise RuntimeError("登录成功但未返回 access_token。")
    token = str(login_payload["access_token"]).strip()

    me_response = await client.get(me_url, headers={"Authorization": f"Bearer {token}"})
    me_response.raise_for_status()
    me_payload = me_response.json()
    if not isinstance(me_payload, dict):
        raise RuntimeError("auth/me 返回格式无效。")

    return AuthContext(
        token=token,
        user_id=str(me_payload.get("id") or "").strip(),
        email=str(me_payload.get("email") or "").strip(),
        username=str(me_payload.get("username") or "").strip(),
    )


def get_or_create_login_urls(auth_cfg: AuthConfig, system: SystemTarget) -> tuple[str, str]:
    login_url = system.login_url or auth_cfg.login_url
    me_url = system.me_url or auth_cfg.me_url
    if not login_url or not me_url:
        raise RuntimeError(f"system {system.name} 缺少登录相关配置。")
    return login_url, me_url


def compute_percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[lower], 2)
    weight = rank - lower
    interpolated = ordered[lower] + (ordered[upper] - ordered[lower]) * weight
    return round(interpolated, 2)


def contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords if keyword)


def build_rasa_metadata(sample: SampleRecord, auth_context: AuthContext) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "frontend_base_url": "http://localhost:5173",
    }
    if sample.requires_auth:
        metadata.update(
            {
                "is_authenticated": True,
                "user_id": auth_context.user_id,
                "user_email": auth_context.email,
                "username": auth_context.username or "benchmark-user",
            }
        )
    else:
        metadata["is_authenticated"] = False
    return metadata


def normalize_rasa_messages(payload: Any) -> tuple[str, int, int]:
    if not isinstance(payload, list):
        return "", 0, 0
    texts: list[str] = []
    cards_count = 0
    actions_count = 0
    for item in payload:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            texts.append(text)
        custom = item.get("custom")
        if isinstance(custom, dict):
            cards = custom.get("cards")
            actions = custom.get("actions")
            if isinstance(cards, list):
                cards_count += len(cards)
            if isinstance(actions, list):
                actions_count += len(actions)
    return "\n".join(texts).strip(), cards_count, actions_count


def normalize_backend_messages(payload: Any) -> tuple[str, int, int]:
    if not isinstance(payload, dict):
        return "", 0, 0
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return "", 0, 0
    texts: list[str] = []
    cards_count = 0
    actions_count = 0
    for item in messages:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            texts.append(text)
        cards = item.get("cards")
        actions = item.get("actions")
        if isinstance(cards, list):
            cards_count += len(cards)
        if isinstance(actions, list):
            actions_count += len(actions)
    return "\n".join(texts).strip(), cards_count, actions_count


def normalize_ollama_message(payload: Any) -> tuple[str, int, int]:
    if not isinstance(payload, dict):
        return "", 0, 0
    message = payload.get("message")
    if not isinstance(message, dict):
        return "", 0, 0
    text = str(message.get("content") or "").strip()
    return text, 0, 0


def build_ollama_messages(sample: SampleRecord) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if sample.system_prompt:
        messages.append({"role": "system", "content": sample.system_prompt})
    if sample.context:
        messages.append({"role": "system", "content": sample.context})
    messages.append({"role": "user", "content": sample.user_input})
    return messages


def score_response(
    *,
    sample: SampleRecord,
    response_text: str,
    response_card_count: int,
    unsupported: bool,
    upload_ok: bool,
) -> tuple[str, bool, bool, dict[str, Any]]:
    if unsupported:
        flags = {
            "supported": False,
            "missing_required_keywords": False,
            "contains_forbidden_keywords": False,
            "missing_confirmation": False,
            "format_error": False,
            "image_flow_ok": False,
            "hallucinated_order_id": False,
            "missing_next_step": False,
            "generic_response": False,
        }
        return "na", False, False, flags

    checks = sample.checks
    required_any_keywords = [str(item) for item in checks.get("required_any_keywords", [])]
    forbidden_keywords = [str(item) for item in checks.get("forbidden_keywords", [])]
    generic_rejection_keywords = [str(item) for item in checks.get("generic_rejection_keywords", [])]
    next_step_keywords = [str(item) for item in checks.get("next_step_keywords", [])]
    requires_confirmation = bool(checks.get("requires_confirmation", False))
    must_have_next_step = bool(checks.get("must_have_next_step", False))
    min_response_chars = int(checks.get("min_response_chars", 1))
    must_not_hallucinate_order_id = bool(checks.get("must_not_hallucinate_order_id", False))

    response_text = response_text.strip()
    format_error = len(response_text) < min_response_chars
    missing_required_keywords = bool(required_any_keywords) and response_card_count <= 0 and not contains_any(
        response_text,
        required_any_keywords,
    )
    contains_forbidden_keywords = contains_any(response_text, forbidden_keywords)
    missing_confirmation = requires_confirmation and not contains_any(response_text, CONFIRMATION_PATTERNS)
    missing_next_step = must_have_next_step and not contains_any(response_text, next_step_keywords)
    generic_response = sample.scenario == "recommendation" and contains_any(
        response_text,
        [*GENERIC_RECOMMENDATION_PATTERNS, *generic_rejection_keywords],
    )
    hallucinated_order_id = False
    if must_not_hallucinate_order_id and ORDER_ID_RE.search(response_text) and not ORDER_ID_RE.search(sample.user_input):
        hallucinated_order_id = True

    image_flow_ok = (not sample.requires_image) or upload_ok
    task_success = not any(
        [
            format_error,
            missing_required_keywords,
            missing_confirmation,
            missing_next_step,
            generic_response,
            hallucinated_order_id,
            contains_forbidden_keywords,
            not image_flow_ok,
        ]
    )
    flags = {
        "supported": True,
        "missing_required_keywords": missing_required_keywords,
        "contains_forbidden_keywords": contains_forbidden_keywords,
        "missing_confirmation": missing_confirmation,
        "format_error": format_error,
        "image_flow_ok": image_flow_ok,
        "hallucinated_order_id": hallucinated_order_id,
        "missing_next_step": missing_next_step,
        "generic_response": generic_response,
    }
    return ("pass" if task_success else "fail"), task_success, task_success, flags


async def execute_single_request(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    sample: SampleRecord,
    auth_context: AuthContext,
    config: dict[str, Any],
    repeat: int,
    concurrency: int,
    request_index: int,
) -> BenchmarkEvent:
    timestamp = now_iso()
    started_at = time.time()
    perf_started = time.perf_counter()

    if sample.requires_image and not system.supports_image:
        quality_status, task_success, passed, quality_flags = score_response(
            sample=sample,
            response_text="",
            response_card_count=0,
            unsupported=True,
            upload_ok=False,
        )
        finished_at = time.time()
        return BenchmarkEvent(
            timestamp=timestamp,
            system=system.name,
            scenario=sample.scenario,
            sample_id=sample.sample_id,
            repeat=repeat,
            concurrency=concurrency,
            request_index=request_index,
            requires_auth=sample.requires_auth,
            requires_image=sample.requires_image,
            executed=False,
            unsupported=True,
            success=False,
            http_status=None,
            error_type="unsupported_capability",
            error_message="system does not support image workflow",
            latency_ms=0.0,
            started_at=started_at,
            finished_at=finished_at,
            response_text="",
            response_chars=0,
            response_card_count=0,
            response_action_count=0,
            quality_status=quality_status,
            task_success=task_success,
            passed=passed,
            quality_flags=quality_flags,
        )

    upload_ok = False
    attachments: list[str] = []
    status_code: int | None = None
    error_type = ""
    error_message = ""
    response_text = ""
    response_card_count = 0
    response_action_count = 0
    success = False

    try:
        if sample.requires_image:
            if system.kind != "backend_chat" or not system.requires_upload_step or not system.upload_path:
                raise RuntimeError(f"system {system.name} 未配置图片上传链路。")
            image_path = resolve_image_path(config, sample)
            upload_url = f"{system.base_url.rstrip('/')}/{system.upload_path.lstrip('/')}"
            upload_headers = auth_context.bearer_headers if sample.requires_auth else {}
            upload_response = await client.post(
                upload_url,
                headers=upload_headers,
                files={"file": (image_path.name, image_path.read_bytes(), "image/png")},
            )
            status_code = upload_response.status_code
            upload_response.raise_for_status()
            upload_payload = upload_response.json()
            if not isinstance(upload_payload, dict) or not str(upload_payload.get("attachment_id") or "").strip():
                raise RuntimeError("图片上传成功但未返回 attachment_id。")
            attachments.append(str(upload_payload["attachment_id"]).strip())
            upload_ok = True

        if system.kind == "rasa_rest":
            url = f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}"
            payload = {
                "sender": system.sender_id,
                "message": sample.user_input,
                "metadata": build_rasa_metadata(sample, auth_context),
            }
            response = await client.post(url, json=payload)
            status_code = response.status_code
            response.raise_for_status()
            payload_json = response.json()
            response_text, response_card_count, response_action_count = normalize_rasa_messages(payload_json)
            success = True

        elif system.kind == "ollama_chat":
            url = f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}"
            payload = {
                "model": system.model,
                "stream": False,
                "messages": build_ollama_messages(sample),
                "options": {"temperature": 0},
            }
            response = await client.post(url, json=payload)
            status_code = response.status_code
            response.raise_for_status()
            payload_json = response.json()
            response_text, response_card_count, response_action_count = normalize_ollama_message(payload_json)
            success = True

        elif system.kind == "backend_chat":
            url = f"{system.base_url.rstrip('/')}/{system.path.lstrip('/')}"
            headers = auth_context.bearer_headers if sample.requires_auth else {}
            payload = {
                "message": sample.user_input,
                "sender_id": system.sender_id,
                "attachments": attachments,
            }
            response = await client.post(url, json=payload, headers=headers)
            status_code = response.status_code
            response.raise_for_status()
            payload_json = response.json()
            response_text, response_card_count, response_action_count = normalize_backend_messages(payload_json)
            success = True

        else:
            raise RuntimeError(f"不支持的 system.kind: {system.kind}")

    except httpx.TimeoutException:
        error_type = "timeout"
        error_message = "request timeout"
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        error_type = "http_status_error"
        try:
            error_message = json.dumps(exc.response.json(), ensure_ascii=False)
        except Exception:
            error_message = exc.response.text.strip()
    except httpx.HTTPError as exc:
        error_type = "http_error"
        error_message = str(exc)
    except Exception as exc:  # noqa: BLE001
        error_type = "runtime_error"
        error_message = str(exc)

    latency_ms = round((time.perf_counter() - perf_started) * 1000, 2)
    finished_at = time.time()
    quality_status, task_success, passed, quality_flags = score_response(
        sample=sample,
        response_text=response_text,
        response_card_count=response_card_count,
        unsupported=False,
        upload_ok=upload_ok,
    )
    if not success and error_type:
        quality_status = "fail"
        task_success = False
        passed = False
        quality_flags["format_error"] = True

    return BenchmarkEvent(
        timestamp=timestamp,
        system=system.name,
        scenario=sample.scenario,
        sample_id=sample.sample_id,
        repeat=repeat,
        concurrency=concurrency,
        request_index=request_index,
        requires_auth=sample.requires_auth,
        requires_image=sample.requires_image,
        executed=True,
        unsupported=False,
        success=success,
        http_status=status_code,
        error_type=error_type,
        error_message=error_message,
        latency_ms=latency_ms,
        started_at=started_at,
        finished_at=finished_at,
        response_text=response_text,
        response_chars=len(response_text),
        response_card_count=response_card_count,
        response_action_count=response_action_count,
        quality_status=quality_status,
        task_success=task_success,
        passed=passed,
        quality_flags=quality_flags,
    )


def pick_samples(samples: list[SampleRecord], count: int, seed: int) -> list[SampleRecord]:
    rng = random.Random(seed)
    return [samples[rng.randrange(0, len(samples))] for _ in range(count)]


async def warmup_system(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    sample: SampleRecord,
    auth_context: AuthContext,
    config: dict[str, Any],
    warmup_requests: int,
) -> None:
    if warmup_requests <= 0:
        return
    for request_index in range(warmup_requests):
        await execute_single_request(
            client=client,
            system=system,
            sample=sample,
            auth_context=auth_context,
            config=config,
            repeat=0,
            concurrency=1,
            request_index=request_index,
        )


async def execute_batch(
    *,
    client: httpx.AsyncClient,
    system: SystemTarget,
    samples: list[SampleRecord],
    auth_context: AuthContext,
    config: dict[str, Any],
    repeat: int,
    concurrency: int,
) -> list[BenchmarkEvent]:
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(item: tuple[int, SampleRecord]) -> BenchmarkEvent:
        request_index, sample = item
        async with semaphore:
            return await execute_single_request(
                client=client,
                system=system,
                sample=sample,
                auth_context=auth_context,
                config=config,
                repeat=repeat,
                concurrency=concurrency,
                request_index=request_index,
            )

    return await asyncio.gather(*(guarded(item) for item in enumerate(samples, start=1)))


def write_jsonl(path: Path, records: list[BenchmarkEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_summary_rows(events: list[BenchmarkEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int, int], list[BenchmarkEvent]] = {}
    for event in events:
        key = (event.system, event.scenario, event.concurrency, event.repeat)
        groups.setdefault(key, []).append(event)

    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, scenario, concurrency, repeat = key
        batch_events = groups[key]
        executed_events = [event for event in batch_events if event.executed]
        successful_events = [event for event in executed_events if event.success]
        eligible_events = [event for event in batch_events if not event.unsupported]
        latency_values = [event.latency_ms for event in executed_events]
        throughput_rps = 0.0
        if executed_events:
            started_at = min(event.started_at for event in executed_events)
            finished_at = max(event.finished_at for event in executed_events)
            elapsed = max(finished_at - started_at, 1e-6)
            throughput_rps = round(len(executed_events) / elapsed, 4)

        rows.append(
            {
                "system": system,
                "scenario": scenario,
                "concurrency": concurrency,
                "repeat": repeat,
                "requests": len(batch_events),
                "executed_requests": len(executed_events),
                "successful_requests": len(successful_events),
                "success_rate": round(len(successful_events) / max(1, len(executed_events)), 4),
                "unsupported_rate": round(
                    sum(1 for event in batch_events if event.unsupported) / max(1, len(batch_events)),
                    4,
                ),
                "task_success_rate": round(
                    sum(1 for event in eligible_events if event.task_success) / max(1, len(eligible_events)),
                    4,
                ),
                "quality_pass_rate": round(
                    sum(1 for event in eligible_events if event.passed) / max(1, len(eligible_events)),
                    4,
                ),
                "p50_ms": compute_percentile(latency_values, 0.50),
                "p90_ms": compute_percentile(latency_values, 0.90),
                "p95_ms": compute_percentile(latency_values, 0.95),
                "p99_ms": compute_percentile(latency_values, 0.99),
                "throughput_rps": throughput_rps,
                "avg_response_chars": round(
                    statistics.mean(event.response_chars for event in successful_events),
                    2,
                )
                if successful_events
                else 0.0,
                "avg_card_count": round(
                    statistics.mean(event.response_card_count for event in successful_events),
                    2,
                )
                if successful_events
                else 0.0,
            }
        )
    return rows


def build_quality_rows(events: list[BenchmarkEvent]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[BenchmarkEvent]] = {}
    for event in events:
        key = (event.system, event.scenario)
        groups.setdefault(key, []).append(event)

    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        system, scenario = key
        batch_events = groups[key]
        eligible = [event for event in batch_events if not event.unsupported]
        rows.append(
            {
                "system": system,
                "scenario": scenario,
                "requests": len(batch_events),
                "eligible_requests": len(eligible),
                "unsupported_requests": sum(1 for event in batch_events if event.unsupported),
                "task_success_requests": sum(1 for event in eligible if event.task_success),
                "passed_requests": sum(1 for event in eligible if event.passed),
                "missing_required_keywords": sum(
                    1 for event in eligible if bool(event.quality_flags.get("missing_required_keywords"))
                ),
                "contains_forbidden_keywords": sum(
                    1 for event in eligible if bool(event.quality_flags.get("contains_forbidden_keywords"))
                ),
                "missing_confirmation": sum(
                    1 for event in eligible if bool(event.quality_flags.get("missing_confirmation"))
                ),
                "format_error": sum(1 for event in eligible if bool(event.quality_flags.get("format_error"))),
                "image_flow_failures": sum(
                    1 for event in eligible if not bool(event.quality_flags.get("image_flow_ok", True))
                ),
                "hallucinated_order_id": sum(
                    1 for event in eligible if bool(event.quality_flags.get("hallucinated_order_id"))
                ),
                "missing_next_step": sum(
                    1 for event in eligible if bool(event.quality_flags.get("missing_next_step"))
                ),
                "generic_response": sum(
                    1 for event in eligible if bool(event.quality_flags.get("generic_response"))
                ),
            }
        )
    return rows


def build_system_matrix(events: list[BenchmarkEvent], scenarios: list[str]) -> list[dict[str, Any]]:
    systems = sorted({event.system for event in events})
    rows: list[dict[str, Any]] = []

    for system in systems:
        row: dict[str, Any] = {"system": system}
        for scenario in scenarios:
            scoped_events = [event for event in events if event.system == system and event.scenario == scenario]
            eligible_events = [event for event in scoped_events if not event.unsupported]
            executed_events = [event for event in scoped_events if event.executed]
            row[f"{scenario}_quality_pass_rate"] = round(
                sum(1 for event in eligible_events if event.passed) / max(1, len(eligible_events)),
                4,
            )
            row[f"{scenario}_task_success_rate"] = round(
                sum(1 for event in eligible_events if event.task_success) / max(1, len(eligible_events)),
                4,
            )
            row[f"{scenario}_p95_ms"] = compute_percentile([event.latency_ms for event in executed_events], 0.95)
            row[f"{scenario}_unsupported_rate"] = round(
                sum(1 for event in scoped_events if event.unsupported) / max(1, len(scoped_events)),
                4,
            )
        rows.append(row)
    return rows


def build_stability_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in summary_rows:
        key = (str(row["system"]), str(row["scenario"]), int(row["concurrency"]))
        groups.setdefault(key, []).append(row)

    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        scoped_rows = groups[key]
        if len(scoped_rows) < 2:
            continue
        p95_values = [float(row["p95_ms"]) for row in scoped_rows]
        pass_values = [float(row["quality_pass_rate"]) for row in scoped_rows]
        rows.append(
            {
                "system": key[0],
                "scenario": key[1],
                "concurrency": key[2],
                "repeat_count": len(scoped_rows),
                "p95_variation_pct": round(
                    ((max(p95_values) - min(p95_values)) / max(statistics.mean(p95_values), 1.0)) * 100,
                    2,
                ),
                "quality_pass_variation_pct": round(
                    ((max(pass_values) - min(pass_values)) / max(statistics.mean(pass_values), 0.0001)) * 100,
                    2,
                ),
            }
        )
    return rows


def render_markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_无数据_"
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


def build_report(
    *,
    output_dir: Path,
    config_path: Path,
    dataset_files: dict[str, Path],
    systems: list[str],
    scenarios: list[str],
    profile: str,
    auth_cfg: AuthConfig,
    summary_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    matrix_rows: list[dict[str, Any]],
    stability_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# 接口级 Benchmark 报告")
    lines.append("")
    lines.append(f"- 生成时间：{now_iso()}")
    lines.append(f"- profile：{profile}")
    lines.append(f"- 配置文件：{config_path}")
    lines.append(f"- 结果目录：{output_dir}")
    lines.append(f"- Python：{sys.version.split()[0]}")
    lines.append(f"- 系统矩阵：{', '.join(systems)}")
    lines.append(f"- 业务场景：{', '.join(scenarios)}")
    lines.append(f"- 测试账号：{auth_cfg.customer_email}")
    lines.append("")
    lines.append("## 数据集")
    dataset_rows = [{"scenario": scenario, "path": path} for scenario, path in dataset_files.items()]
    lines.append(render_markdown_table(dataset_rows))
    lines.append("")
    lines.append("## 论文主表")
    lines.append(render_markdown_table(matrix_rows))
    lines.append("")
    lines.append("## 批次摘要")
    lines.append(render_markdown_table(summary_rows))
    lines.append("")
    lines.append("## 质量统计")
    lines.append(render_markdown_table(quality_rows))
    lines.append("")
    lines.append("## 稳定性")
    lines.append(render_markdown_table(stability_rows) if stability_rows else "_重复次数不足，未生成稳定性统计。_")
    lines.append("")
    lines.append("## 说明")
    lines.append("- `success_rate` 只按实际发出的请求统计，不把图片不支持记为接口错误。")
    lines.append("- `quality_pass_rate` 与 `task_success_rate` 只按可评测样本统计；图片不支持记为 `unsupported/na`。")
    lines.append("- `system_matrix.csv` 适合作为论文中的系统形态对照主表。")
    return "\n".join(lines)


async def execute_benchmark(args: argparse.Namespace) -> Path:
    config_path = args.config.resolve()
    config = load_config(config_path)
    auth_cfg = resolve_auth_config(config)
    selected_systems = parse_csv_values(args.systems)
    selected_scenarios = parse_csv_values(args.scenarios) or ["recommendation", "after_sales", "image_after_sales"]
    system_targets = resolve_system_targets(config, selected_systems)
    dataset_files = resolve_dataset_files(args.dataset, selected_scenarios)
    dataset_map = {scenario: load_dataset_file(path) for scenario, path in dataset_files.items()}

    profile_cfg = config.get("profiles", {}).get(args.profile)
    if not isinstance(profile_cfg, dict):
        raise RuntimeError(f"profile 不存在: {args.profile}")

    concurrency_levels = (
        parse_concurrency_override(args.concurrency)
        or [int(item) for item in profile_cfg.get("concurrency", []) if int(item) > 0]
    )
    if not concurrency_levels:
        raise RuntimeError("并发配置为空。")

    requests_per_level = (
        int(args.requests_per_level)
        if args.requests_per_level is not None
        else int(profile_cfg.get("requests_per_level", 30))
    )
    repeats = int(args.repeats) if args.repeats is not None else int(profile_cfg.get("repeats", 1))
    timeout_sec = float(args.timeout_sec) if args.timeout_sec is not None else float(config.get("timeout_sec", 60))
    warmup_requests = (
        int(args.warmup_requests)
        if args.warmup_requests is not None
        else int(config.get("warmup_requests", 1))
    )
    seed = int(args.seed) if args.seed is not None else int(config.get("seed", 20260411))

    configured_results_root = config.get("results_dir", "backend/benchmarks/results")
    results_root = args.results_root if args.results_root is not None else (ROOT_DIR / configured_results_root)
    if not results_root.is_absolute():
        results_root = (ROOT_DIR / results_root).resolve()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = results_root / f"{timestamp}_{args.profile}_system_benchmark"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_events: list[BenchmarkEvent] = []

    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        auth_cache: dict[tuple[str, str], AuthContext] = {}

        for system_name, system in system_targets.items():
            if args.verbose:
                print(f"[benchmark] system={system_name}")
            for scenario in selected_scenarios:
                samples = dataset_map[scenario]
                requires_auth = any(item.requires_auth for item in samples)
                auth_context = AuthContext()
                if requires_auth and system.auth_mode in {"bearer", "metadata"}:
                    login_url, me_url = get_or_create_login_urls(auth_cfg, system)
                    cache_key = (login_url, me_url)
                    if cache_key not in auth_cache:
                        auth_cache[cache_key] = await login_for_auth_context(
                            client,
                            auth_cfg,
                            login_url=login_url,
                            me_url=me_url,
                        )
                    auth_context = auth_cache[cache_key]

                await warmup_system(
                    client=client,
                    system=system,
                    sample=samples[0],
                    auth_context=auth_context,
                    config=config,
                    warmup_requests=warmup_requests,
                )

                for repeat in range(1, repeats + 1):
                    for concurrency in concurrency_levels:
                        planned_samples = pick_samples(
                            samples,
                            requests_per_level,
                            seed + repeat * 100 + concurrency * 7 + sum(ord(ch) for ch in system_name + scenario),
                        )
                        batch_events = await execute_batch(
                            client=client,
                            system=system,
                            samples=planned_samples,
                            auth_context=auth_context,
                            config=config,
                            repeat=repeat,
                            concurrency=concurrency,
                        )
                        all_events.extend(batch_events)
                        if args.verbose:
                            print(
                                f"[benchmark] system={system_name} scenario={scenario} "
                                f"repeat={repeat} concurrency={concurrency} requests={len(batch_events)}"
                            )

    summary_rows = build_summary_rows(all_events)
    quality_rows = build_quality_rows(all_events)
    matrix_rows = build_system_matrix(all_events, selected_scenarios)
    stability_rows = build_stability_rows(summary_rows)

    raw_events_path = output_dir / "raw_events.jsonl"
    summary_path = output_dir / "summary.csv"
    quality_path = output_dir / "scenario_quality.csv"
    matrix_path = output_dir / "system_matrix.csv"
    report_path = output_dir / "report.md"

    write_jsonl(raw_events_path, all_events)
    write_csv(summary_path, summary_rows)
    write_csv(quality_path, quality_rows)
    write_csv(matrix_path, matrix_rows)
    report_path.write_text(
        build_report(
            output_dir=output_dir,
            config_path=config_path,
            dataset_files=dataset_files,
            systems=list(system_targets.keys()),
            scenarios=selected_scenarios,
            profile=args.profile,
            auth_cfg=auth_cfg,
            summary_rows=summary_rows,
            quality_rows=quality_rows,
            matrix_rows=matrix_rows,
            stability_rows=stability_rows,
        ),
        encoding="utf-8",
    )

    print(json.dumps({"output_dir": str(output_dir), "events": len(all_events)}, ensure_ascii=False))
    return output_dir


def main() -> None:
    args = parse_args()
    asyncio.run(execute_benchmark(args))


if __name__ == "__main__":
    main()
