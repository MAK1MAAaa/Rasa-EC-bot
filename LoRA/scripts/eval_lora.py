#!/usr/bin/env python
"""Evaluate LoRA model against base model on fixed ecommerce prompts."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import torch
from env_utils import load_env_file
from peft import AutoPeftModelForCausalLM, PeftConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

ORDER_ID_RE = re.compile(r"\bORD\d{6,}\b", flags=re.IGNORECASE)
CONFIRMATION_PATTERNS = [
    "confirm",
    "confirmation",
    "confirmation code",
    "please confirm",
    "second confirmation",
    "确认",
    "请确认",
    "二次确认",
    "确认码",
    "回复确认",
    "回复“确认”",
    "回复\"确认\"",
    "同意继续",
    "同意处理",
]

DEFAULT_BASE_MODEL = "Qwen/Qwen3.5-2B"
DEFAULT_SYSTEM = (
    "You are an ecommerce support assistant. "
    "Never fabricate order IDs. "
    "Request explicit confirmation before executing sensitive actions."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate LoRA model behavior.")
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--test-file", required=True, type=Path)
    parser.add_argument("--report-file", required=True, type=Path)
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=180)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_model_and_tokenizer(
    model_ref: str | Path,
) -> tuple[AutoModelForCausalLM, AutoTokenizer]:
    model_ref = str(model_ref)
    model_path = Path(model_ref)
    if model_path.exists() and (model_path / "adapter_config.json").exists():
        peft_cfg = PeftConfig.from_pretrained(model_ref)
        tokenizer = AutoTokenizer.from_pretrained(model_ref, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoPeftModelForCausalLM.from_pretrained(
            model_ref,
            dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        if not peft_cfg.base_model_name_or_path:
            raise RuntimeError("Adapter config missing base model name.")
        return model, tokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_ref, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_ref,
        dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
    return model, tokenizer


def generate_reply(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    prompt: str,
    max_new_tokens: int,
) -> str:
    messages = [
        {"role": "system", "content": DEFAULT_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    chat_prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(chat_prompt, return_tensors="pt").to(model.device)
    prompt_len = inputs["input_ids"].shape[-1]
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    generated_ids = outputs[0][prompt_len:]
    generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    if generated_text:
        return generated_text
    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    return full_text


def has_confirmation(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in CONFIRMATION_PATTERNS)


def check_constraints(row: dict[str, Any], response: str) -> dict[str, bool]:
    prompt = str(row["prompt"])
    prompt_has_id = bool(ORDER_ID_RE.search(prompt))
    must_not_hallucinate = bool(row.get("must_not_hallucinate_order_id", False))
    requires_confirmation = bool(row.get("requires_confirmation", False))
    required_any_keywords = row.get("required_any_keywords", []) or []
    if not isinstance(required_any_keywords, list):
        required_any_keywords = []
    forbidden_keywords = row.get("forbidden_keywords", []) or []
    if not isinstance(forbidden_keywords, list):
        forbidden_keywords = []

    response_lower = response.lower()
    hallucinated = must_not_hallucinate and (not prompt_has_id) and bool(
        ORDER_ID_RE.search(response)
    )
    missing_confirmation = requires_confirmation and (not has_confirmation(response))
    missing_required_keywords = False
    if required_any_keywords:
        missing_required_keywords = not any(
            str(keyword).lower() in response_lower for keyword in required_any_keywords
        )
    contains_forbidden_keywords = any(
        str(keyword).lower() in response_lower for keyword in forbidden_keywords
    )
    return {
        "hallucinated_order_id": hallucinated,
        "missing_confirmation": missing_confirmation,
        "missing_required_keywords": missing_required_keywords,
        "contains_forbidden_keywords": contains_forbidden_keywords,
        "passed_constraints": (
            (not hallucinated)
            and (not missing_confirmation)
            and (not missing_required_keywords)
            and (not contains_forbidden_keywords)
        ),
    }


def evaluate_model(
    model_ref: str | Path, test_rows: list[dict[str, Any]], max_new_tokens: int
) -> dict[str, Any]:
    model, tokenizer = load_model_and_tokenizer(model_ref)
    details: list[dict[str, Any]] = []
    for row in test_rows:
        prompt = str(row["prompt"])
        response = generate_reply(model, tokenizer, prompt, max_new_tokens=max_new_tokens)
        constraints = check_constraints(row, response)
        details.append(
            {
                "id": row.get("id", ""),
                "category": row.get("category", "unknown"),
                "prompt": prompt,
                "response": response,
                **constraints,
            }
        )

    total = len(details)
    pass_count = sum(1 for d in details if d["passed_constraints"])
    hallucination_count = sum(1 for d in details if d["hallucinated_order_id"])
    missing_confirm_count = sum(1 for d in details if d["missing_confirmation"])
    missing_required_count = sum(1 for d in details if d["missing_required_keywords"])
    forbidden_count = sum(1 for d in details if d["contains_forbidden_keywords"])
    avg_chars = round(sum(len(d["response"]) for d in details) / max(1, total), 2)

    return {
        "model_ref": str(model_ref),
        "total_prompts": total,
        "passed_constraints": pass_count,
        "constraint_pass_rate": round(pass_count / max(1, total), 4),
        "hallucinated_order_id": hallucination_count,
        "missing_confirmation": missing_confirm_count,
        "missing_required_keywords": missing_required_count,
        "contains_forbidden_keywords": forbidden_count,
        "avg_response_chars": avg_chars,
        "details": details,
    }


def main() -> None:
    args = parse_args()
    lora_root = Path(__file__).resolve().parent.parent
    load_env_file(lora_root / ".env")
    model_dir = args.model_dir.resolve()
    test_file = args.test_file.resolve()
    report_file = args.report_file.resolve()
    report_file.parent.mkdir(parents=True, exist_ok=True)
    base_model = args.base_model or os.getenv("BASE_MODEL_PATH", "").strip() or DEFAULT_BASE_MODEL

    test_rows = load_jsonl(test_file)
    base_result = evaluate_model(base_model, test_rows, args.max_new_tokens)
    tuned_result = evaluate_model(model_dir, test_rows, args.max_new_tokens)

    report = {
        "base_model": base_result,
        "tuned_model": tuned_result,
        "summary": {
            "base_pass_rate": base_result["constraint_pass_rate"],
            "tuned_pass_rate": tuned_result["constraint_pass_rate"],
            "pass_rate_delta": round(
                tuned_result["constraint_pass_rate"] - base_result["constraint_pass_rate"],
                4,
            ),
            "base_hallucinated_order_id": base_result["hallucinated_order_id"],
            "tuned_hallucinated_order_id": tuned_result["hallucinated_order_id"],
            "base_missing_confirmation": base_result["missing_confirmation"],
            "tuned_missing_confirmation": tuned_result["missing_confirmation"],
            "base_missing_required_keywords": base_result["missing_required_keywords"],
            "tuned_missing_required_keywords": tuned_result["missing_required_keywords"],
            "base_contains_forbidden_keywords": base_result[
                "contains_forbidden_keywords"
            ],
            "tuned_contains_forbidden_keywords": tuned_result[
                "contains_forbidden_keywords"
            ],
        },
    }
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Evaluation complete.")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    main()
