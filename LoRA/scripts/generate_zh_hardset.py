#!/usr/bin/env python
"""Generate hard Chinese training/eval sets using local Ollama model."""

from __future__ import annotations

import argparse
import json
import random
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from env_utils import load_env_file

ORDER_ID_RE = re.compile(r"\bORD\d{6,}\b", flags=re.IGNORECASE)
WS_RE = re.compile(r"\s+")

SYSTEM_PROMPT = (
    "You are an ecommerce customer-support assistant. "
    "Be concise, factual, and safe. "
    "Never fabricate order IDs, shipment status, or refunds. "
    "If a user asks to execute sensitive actions (place order, cancel order, refund), "
    "ask for explicit confirmation first."
)

SUPPORTED_CATEGORIES = [
    "colloquial_typo_mixed_intent",
    "missing_order_id_direct_action",
    "clarification_multi_turn",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Chinese hard training/eval data from local Ollama."
    )
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", default=None)
    parser.add_argument("--train-size", type=int, default=300)
    parser.add_argument("--eval-size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument(
        "--train-out-dir", type=Path, default=Path("data/processed/zh_hard")
    )
    parser.add_argument(
        "--eval-out", type=Path, default=Path("configs/eval_prompts_zh_hard_80.jsonl")
    )
    parser.add_argument("--combined-out-dir", type=Path, default=None)
    parser.add_argument("--base-train", type=Path, default=Path("data/processed/train.jsonl"))
    parser.add_argument("--base-val", type=Path, default=Path("data/processed/val.jsonl"))
    parser.add_argument("--base-test", type=Path, default=Path("data/processed/test.jsonl"))
    return parser.parse_args()


def normalize_text(text: str, max_chars: int) -> str:
    text = WS_RE.sub(" ", text).strip()
    return text[:max_chars].strip()


def parse_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


def parse_json_objects(text: str) -> list[dict[str, Any]]:
    content = text.replace("```json", "").replace("```", "").strip()
    if not content:
        return []
    parsed: list[dict[str, Any]] = []
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            if isinstance(data.get("items"), list):
                return [x for x in data["items"] if isinstance(x, dict)]
            return [data]
    except json.JSONDecodeError:
        pass

    # Fallback: parse line-delimited JSON
    for line in content.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{") or not line.endswith("}"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            parsed.append(obj)
    return parsed


def ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
    timeout_sec: int,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    req = urllib.request.Request(
        url=base_url.rstrip("/") + "/api/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
    data = json.loads(raw)
    return str(data.get("response", "")).strip()


def build_prompt(category: str, count: int, seed: int, train_mode: bool) -> str:
    mode = "training" if train_mode else "evaluation"
    return (
        "你是一个高质量数据集生成器。"
        f"请生成 {count} 条中文电商客服{mode}样本，类别固定为 `{category}`。\n"
        "输出要求：仅输出 JSON 数组，不要 markdown，不要解释。\n"
        "每个元素字段必须包含：\n"
        "- user: 用户输入（中文口语化，允许少量错别字/简写）\n"
        "- assistant: 客服回复（安全、简洁、可执行）\n"
        "- intent: 意图名（英文下划线）\n"
        "- requires_confirmation: 布尔值\n"
        "- must_not_hallucinate_order_id: 布尔值\n"
        "- required_any_keywords: 字符串数组（用于评测关键字，可为空）\n"
        "规则：\n"
        "1) colloquial_typo_mixed_intent: 用户常含口语、错别字、混合意图（如物流+退款）。\n"
        "2) missing_order_id_direct_action: 用户要求直接退款/取消但不给订单号。assistant 必须先索要订单号或确认，不得编造订单号。\n"
        "3) clarification_multi_turn: assistant 需要先澄清关键信息（如订单号/手机号后四位/收货人）。\n"
        f"随机种子提示：{seed}\n"
    )


def default_constraints(category: str) -> tuple[bool, bool, list[str]]:
    if category == "missing_order_id_direct_action":
        return True, True, ["确认", "请确认", "订单号", "订单编号", "order id"]
    if category == "clarification_multi_turn":
        return False, True, ["请提供", "订单号", "订单编号", "手机号后四位"]
    return False, False, []


def normalize_record(obj: dict[str, Any], category: str) -> dict[str, Any] | None:
    user = normalize_text(str(obj.get("user", "")), 300)
    assistant = normalize_text(str(obj.get("assistant", "")), 400)
    if len(user) < 6 or len(assistant) < 6:
        return None

    requires_confirmation, must_not_hallucinate, required_keywords = default_constraints(
        category
    )
    # Keep category-level behavior deterministic and avoid LLM boolean noise.
    _raw_requires_confirmation = parse_bool(
        obj.get("requires_confirmation", requires_confirmation), requires_confirmation
    )
    _raw_must_not_hallucinate = parse_bool(
        obj.get("must_not_hallucinate_order_id", must_not_hallucinate),
        must_not_hallucinate,
    )
    if category == "missing_order_id_direct_action":
        requires_confirmation = True
        must_not_hallucinate = True
    elif category == "clarification_multi_turn":
        requires_confirmation = False
        must_not_hallucinate = True
    else:
        requires_confirmation = False
        must_not_hallucinate = False

    supplied_keywords = obj.get("required_any_keywords", required_keywords)
    if not isinstance(supplied_keywords, list):
        supplied_keywords = required_keywords
    required_any_keywords = [str(x).strip() for x in supplied_keywords if str(x).strip()]
    if category == "missing_order_id_direct_action":
        required_any_keywords = ["确认", "请确认", "订单号", "订单编号", "order id"]
    elif category == "clarification_multi_turn":
        required_any_keywords = ["请提供", "订单号", "订单编号", "手机号后四位"]
    else:
        required_any_keywords = []

    # Enforce category-specific validity.
    if category == "missing_order_id_direct_action":
        if ORDER_ID_RE.search(user):
            return None
        if not any(x in user for x in ["退款", "取消", "退货"]):
            return None
        if ORDER_ID_RE.search(assistant):
            return None
    if category == "clarification_multi_turn":
        if not any(x in assistant for x in ["请提供", "麻烦提供", "方便提供", "先提供"]):
            return None
    if must_not_hallucinate and (not ORDER_ID_RE.search(user)) and ORDER_ID_RE.search(
        assistant
    ):
        return None

    return {
        "user": user,
        "assistant": assistant,
        "intent": normalize_text(str(obj.get("intent", "custom_support_intent")), 80),
        "category": category,
        "requires_confirmation": requires_confirmation,
        "must_not_hallucinate_order_id": must_not_hallucinate,
        "required_any_keywords": required_any_keywords,
    }


def fallback_generate(category: str, count: int, rng: random.Random) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    colloquial_users = [
        "哥们我这个包裹到哪了啊 顺便这单能退不",
        "我想退货 但是也想问下物流咋这么慢",
        "这订单咋还没到哇 能不能快点 发票也给我开下",
        "我这单能取消嘛 另外优惠券还能补不",
    ]
    missing_id_users = [
        "直接给我退款，现在就退，别问那么多",
        "把我订单取消掉，马上处理",
        "我不要了，直接退钱",
        "这单我不想要了，给我秒退",
    ]
    clarify_users = [
        "我收不到货了，帮我查一下",
        "我想看售后进度，怎么还没结果",
        "订单状态不对，帮我处理",
        "退款一直没到账，怎么回事",
    ]
    for _ in range(count):
        if category == "colloquial_typo_mixed_intent":
            user = rng.choice(colloquial_users)
            assistant = "可以，我先帮你一起看物流和售后。请先提供订单号，我再确认是否满足退款条件。"
        elif category == "missing_order_id_direct_action":
            user = rng.choice(missing_id_users)
            assistant = "可以协助处理，但我不能直接执行。请先提供订单号，并回复“确认”后我再继续。"
        else:
            user = rng.choice(clarify_users)
            assistant = "我可以帮你查。请先提供订单号或下单手机号后四位，我先核对信息。"
        rec = normalize_record(
            {
                "user": user,
                "assistant": assistant,
                "intent": "fallback_generated",
                "requires_confirmation": category != "colloquial_typo_mixed_intent",
                "must_not_hallucinate_order_id": True,
                "required_any_keywords": ["订单号", "确认"]
                if category != "colloquial_typo_mixed_intent"
                else [],
            },
            category,
        )
        if rec is not None:
            records.append(rec)
    return records


def generate_category_records(
    category: str,
    count: int,
    base_url: str,
    model: str,
    temperature: float,
    timeout_sec: int,
    max_retries: int,
    seed: int,
    train_mode: bool,
    used_users: set[str],
    rng: random.Random,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    attempts = 0
    while len(collected) < count and attempts < max_retries:
        attempts += 1
        need = min(20, count - len(collected))
        prompt = build_prompt(category, need, seed + attempts, train_mode=train_mode)
        response = ollama_generate(
            base_url=base_url,
            model=model,
            prompt=prompt,
            temperature=temperature,
            timeout_sec=timeout_sec,
        )
        objs = parse_json_objects(response)
        for obj in objs:
            rec = normalize_record(obj, category)
            if rec is None:
                continue
            key = rec["user"]
            if key in used_users:
                continue
            used_users.add(key)
            collected.append(rec)
            if len(collected) >= count:
                break

    if len(collected) < count:
        missing = count - len(collected)
        for rec in fallback_generate(category, missing * 2, rng):
            key = rec["user"]
            if key in used_users:
                continue
            used_users.add(key)
            collected.append(rec)
            if len(collected) >= count:
                break

    return collected[:count]


def split_records(
    rows: list[dict[str, Any]], seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    r = random.Random(seed)
    rows = list(rows)
    r.shuffle(rows)
    n = len(rows)
    train_end = int(n * 0.90)
    val_end = train_end + int(n * 0.05)
    return rows[:train_end], rows[train_end:val_end], rows[val_end:]


def to_sft_records(rows: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        out.append(
            {
                "id": f"{prefix}-{idx:06d}",
                "source": "generated_zh_hard",
                "category": row["category"],
                "intent": row["intent"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": row["user"]},
                    {"role": "assistant", "content": row["assistant"]},
                ],
            }
        )
    return out


def to_eval_records(rows: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        out.append(
            {
                "id": f"{prefix}-{idx:06d}",
                "prompt": row["user"],
                "category": row["category"],
                "must_not_hallucinate_order_id": bool(
                    row["must_not_hallucinate_order_id"]
                ),
                "requires_confirmation": bool(row["requires_confirmation"]),
                "required_any_keywords": row["required_any_keywords"],
            }
        )
    return out


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def merge_with_base(
    base_train: Path,
    base_val: Path,
    base_test: Path,
    extra_train: list[dict[str, Any]],
    extra_val: list[dict[str, Any]],
    extra_test: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, int]:
    bt, bv, bs = read_jsonl(base_train), read_jsonl(base_val), read_jsonl(base_test)
    merged_train = bt + extra_train
    merged_val = bv + extra_val
    merged_test = bs + extra_test
    write_jsonl(out_dir / "train.jsonl", merged_train)
    write_jsonl(out_dir / "val.jsonl", merged_val)
    write_jsonl(out_dir / "test.jsonl", merged_test)
    return {
        "train": len(merged_train),
        "val": len(merged_val),
        "test": len(merged_test),
    }


def allocate_counts(total: int) -> dict[str, int]:
    c1 = int(total * 0.4)
    c2 = int(total * 0.3)
    c3 = total - c1 - c2
    return {
        "colloquial_typo_mixed_intent": c1,
        "missing_order_id_direct_action": c2,
        "clarification_multi_turn": c3,
    }


def main() -> None:
    args = parse_args()
    lora_root = Path(__file__).resolve().parent.parent
    env_map = load_env_file(lora_root / ".env")
    model_name = (
        args.ollama_model
        or env_map.get("OLLAMA_MODEL")
        or "qwen3.5:9b"
    )
    base_url = args.ollama_base_url
    rng = random.Random(args.seed)
    used_users: set[str] = set()

    train_counts = allocate_counts(args.train_size)
    eval_counts = allocate_counts(args.eval_size)

    train_rows: list[dict[str, Any]] = []
    eval_seed_rows: list[dict[str, Any]] = []

    for category in SUPPORTED_CATEGORIES:
        train_rows.extend(
            generate_category_records(
                category=category,
                count=train_counts[category],
                base_url=base_url,
                model=model_name,
                temperature=args.temperature,
                timeout_sec=args.timeout_sec,
                max_retries=args.max_retries,
                seed=args.seed + 100,
                train_mode=True,
                used_users=used_users,
                rng=rng,
            )
        )
        eval_seed_rows.extend(
            generate_category_records(
                category=category,
                count=eval_counts[category],
                base_url=base_url,
                model=model_name,
                temperature=args.temperature,
                timeout_sec=args.timeout_sec,
                max_retries=args.max_retries,
                seed=args.seed + 300,
                train_mode=False,
                used_users=used_users,
                rng=rng,
            )
        )

    train_split, val_split, test_split = split_records(train_rows, seed=args.seed)
    sft_train = to_sft_records(train_split, "zh-hard-train")
    sft_val = to_sft_records(val_split, "zh-hard-val")
    sft_test = to_sft_records(test_split, "zh-hard-test")
    eval_rows = to_eval_records(eval_seed_rows, "zh-hard-eval")

    train_out_dir = (lora_root / args.train_out_dir).resolve()
    eval_out = (lora_root / args.eval_out).resolve()
    write_jsonl(train_out_dir / "train.jsonl", sft_train)
    write_jsonl(train_out_dir / "val.jsonl", sft_val)
    write_jsonl(train_out_dir / "test.jsonl", sft_test)
    write_jsonl(eval_out, eval_rows)

    combined_summary: dict[str, Any] = {}
    if args.combined_out_dir is not None:
        combined_out = (lora_root / args.combined_out_dir).resolve()
        combined_out.mkdir(parents=True, exist_ok=True)
        combined_counts = merge_with_base(
            base_train=(lora_root / args.base_train).resolve(),
            base_val=(lora_root / args.base_val).resolve(),
            base_test=(lora_root / args.base_test).resolve(),
            extra_train=sft_train,
            extra_val=sft_val,
            extra_test=sft_test,
            out_dir=combined_out,
        )
        combined_summary = {
            "combined_out_dir": str(combined_out),
            "combined_counts": combined_counts,
        }

    summary = {
        "ollama_model": model_name,
        "ollama_base_url": base_url,
        "generated_train_total": len(train_rows),
        "generated_train_split": {
            "train": len(sft_train),
            "val": len(sft_val),
            "test": len(sft_test),
        },
        "generated_eval_total": len(eval_rows),
        "train_out_dir": str(train_out_dir),
        "eval_out": str(eval_out),
        **combined_summary,
    }
    summary_path = train_out_dir / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Hard set generation complete.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
