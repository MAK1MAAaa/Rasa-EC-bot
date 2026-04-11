from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "backend" / "benchmarks" / "prompts"
DEFAULT_RASA_NLU = ROOT_DIR / "rasa" / "data" / "nlu.yml"
DEFAULT_LORA_JSONL = [
    ROOT_DIR / "LoRA" / "data" / "processed" / "eval_prompts_20.jsonl",
]
DEFAULT_IMAGE_CASES = ["damaged_package", "broken_screen", "wrong_item"]

SYSTEM_PROMPT = (
    "你是电商平台的中文客服助手。回答时不要编造订单号、物流状态或退款结果，"
    "优先给出明确建议和下一步操作。"
)

RECOMMENDATION_CATEGORIES = [
    "手机",
    "电脑",
    "显示器",
    "耳机",
    "键盘",
    "智能手表",
    "空气炸锅",
    "路由器",
]
RECOMMENDATION_BUDGETS = ["2000 元内", "3000 元左右", "4500 元左右", "6000 元内", "8000 元内"]
RECOMMENDATION_NEEDS = [
    "上网课和写论文",
    "日常办公和轻度剪辑",
    "宿舍追剧和打游戏",
    "给家里长辈日常使用",
    "出差时轻便携带",
]
AFTER_SALES_TOPICS = [
    "退货",
    "换货",
    "退款进度",
    "已发货还能不能退",
    "商品收到后有瑕疵",
]
AFTER_SALES_ACTION_REQUESTS = [
    "我想申请{topic}，应该怎么走流程？",
    "这个情况要怎么发起{topic}？",
    "如果我现在要处理{topic}，需要准备什么？",
]
AFTER_SALES_CONFIRMATION_REQUESTS = [
    "你直接帮我把这笔订单做{topic}吧。",
    "现在就帮我发起{topic}，别再让我自己点了。",
]
IMAGE_PROMPTS = {
    "damaged_package": "我上传了一张包裹外箱破损的图片，帮我判断该怎么走售后。",
    "broken_screen": "我上传了一张商品屏幕开裂的图片，想知道售后应该怎么处理。",
    "wrong_item": "我上传了一张实物图，收到的好像不是我下单的款式，帮我看下怎么申请售后。",
}


@dataclass(frozen=True)
class DatasetBuildStats:
    recommendation_count: int
    after_sales_count: int
    image_after_sales_count: int
    source_prompt_pool: int
    source_categories: int


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def clean_text(value: str) -> str:
    text = value.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def deduplicate_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = item.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(item.strip())
    return output


def extract_rasa_categories(path: Path) -> list[str]:
    text = read_text(path)
    matches = re.findall(r"\[([^\]]+)\]\(category\)", text)
    categories = [clean_text(item) for item in matches if clean_text(item)]
    return deduplicate_keep_order(categories)


def extract_prompt_pool(path: Path) -> list[str]:
    text = read_text(path)
    prompts: list[str] = []
    in_examples_block = False
    block_indent = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if re.match(r"^\s*examples\s*:\s*\|\s*$", line):
            in_examples_block = True
            block_indent = indent
            continue

        if not in_examples_block:
            continue
        if not stripped:
            continue
        if indent <= block_indent:
            in_examples_block = False
            continue
        match = re.match(r"^\s*-\s+(.*)$", line)
        if match:
            cleaned = clean_text(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", match.group(1)))
            if cleaned:
                prompts.append(cleaned)
    return prompts


def extract_lora_prompts(paths: list[Path]) -> list[str]:
    prompts: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                prompt = payload.get("prompt") if isinstance(payload, dict) else None
                if isinstance(prompt, str):
                    cleaned = clean_text(prompt)
                    if cleaned:
                        prompts.append(cleaned)
    return prompts


def choose_prompt_hint(prompt_pool: list[str], rng: random.Random, fallback: str) -> str:
    if not prompt_pool:
        return fallback
    return prompt_pool[rng.randrange(0, len(prompt_pool))]


def build_recommendation_records(
    *,
    count: int,
    rng: random.Random,
    categories: list[str],
    prompt_pool: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    category_pool = deduplicate_keep_order([*categories, *RECOMMENDATION_CATEGORIES])
    for index in range(1, count + 1):
        category = category_pool[rng.randrange(0, len(category_pool))]
        budget = RECOMMENDATION_BUDGETS[rng.randrange(0, len(RECOMMENDATION_BUDGETS))]
        need = RECOMMENDATION_NEEDS[rng.randrange(0, len(RECOMMENDATION_NEEDS))]
        source_hint = choose_prompt_hint(prompt_pool, rng, "给我推荐几款热门商品")
        user_input = f"想买{category}，预算 {budget}，主要需求是 {need}。{source_hint}"
        records.append(
            {
                "id": f"recommendation-{index:04d}",
                "scenario": "recommendation",
                "system_prompt": SYSTEM_PROMPT,
                "context": "用户未登录，希望得到清晰的商品推荐建议。",
                "user_input": user_input,
                "requires_auth": False,
                "requires_image": False,
                "expected_capability": "product_recommendation",
                "checks": {
                    "required_any_keywords": ["推荐", "适合", "可以看看", "商品", "款"],
                    "forbidden_keywords": ["无法帮助", "图片售后", "退款成功"],
                    "generic_rejection_keywords": [
                        "请提供更多信息",
                        "还有什么可以帮你",
                        "我目前只能",
                    ],
                    "must_not_hallucinate_order_id": True,
                    "requires_confirmation": False,
                    "must_have_next_step": False,
                    "min_response_chars": 16,
                    "next_step_keywords": [],
                },
                "tags": ["recommendation", category, "anonymous"],
            }
        )
    return records


def build_after_sales_records(
    *,
    count: int,
    rng: random.Random,
    prompt_pool: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index in range(1, count + 1):
        topic = AFTER_SALES_TOPICS[rng.randrange(0, len(AFTER_SALES_TOPICS))]
        if index % 3 == 0:
            template = AFTER_SALES_CONFIRMATION_REQUESTS[rng.randrange(0, len(AFTER_SALES_CONFIRMATION_REQUESTS))]
            requires_confirmation = True
        else:
            template = AFTER_SALES_ACTION_REQUESTS[rng.randrange(0, len(AFTER_SALES_ACTION_REQUESTS))]
            requires_confirmation = False
        source_hint = choose_prompt_hint(prompt_pool, rng, "售后在哪里看")
        user_input = f"{template.format(topic=topic)} {source_hint}"
        records.append(
            {
                "id": f"after-sales-{index:04d}",
                "scenario": "after_sales",
                "system_prompt": SYSTEM_PROMPT,
                "context": "用户已登录，希望了解退货、换货或退款相关流程。",
                "user_input": user_input,
                "requires_auth": True,
                "requires_image": False,
                "expected_capability": "after_sales_guidance",
                "checks": {
                    "required_any_keywords": ["退货", "换货", "售后", "退款", "订单", "申请", "处理"],
                    "forbidden_keywords": ["已退款成功", "已经退货成功", "已经换货成功", "物流单号已生成"],
                    "generic_rejection_keywords": [],
                    "must_not_hallucinate_order_id": True,
                    "requires_confirmation": requires_confirmation,
                    "must_have_next_step": True,
                    "min_response_chars": 18,
                    "next_step_keywords": ["申请", "提交", "确认", "查看", "联系", "上传", "凭证", "订单"],
                },
                "tags": ["after_sales", topic, "authenticated"],
            }
        )
    return records


def build_image_after_sales_records(*, count: int, rng: random.Random) -> list[dict[str, Any]]:
    image_case_keys = list(IMAGE_PROMPTS.keys())
    records: list[dict[str, Any]] = []
    for index in range(1, count + 1):
        image_case = image_case_keys[(index - 1) % len(image_case_keys)]
        user_input = IMAGE_PROMPTS[image_case]
        records.append(
            {
                "id": f"image-after-sales-{index:04d}",
                "scenario": "image_after_sales",
                "system_prompt": SYSTEM_PROMPT,
                "context": "用户已登录，并提交了一张售后相关图片，希望获得处理建议。",
                "user_input": user_input,
                "requires_auth": True,
                "requires_image": True,
                "image_case": image_case,
                "expected_capability": "image_after_sales_analysis",
                "checks": {
                    "required_any_keywords": ["图片", "售后", "建议", "处理", "破损", "损坏", "包装", "屏幕"],
                    "forbidden_keywords": ["无法读取图片", "图片上传失败", "已退款成功"],
                    "generic_rejection_keywords": [],
                    "must_not_hallucinate_order_id": True,
                    "requires_confirmation": False,
                    "must_have_next_step": True,
                    "min_response_chars": 18,
                    "next_step_keywords": ["申请", "提交", "联系", "售后", "凭证", "处理", "确认"],
                },
                "tags": ["image_after_sales", image_case, "authenticated"],
            }
        )
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成系统形态接口级 benchmark 语料。")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--rasa-nlu", type=Path, default=DEFAULT_RASA_NLU)
    parser.add_argument("--lora-jsonl", nargs="*", type=Path, default=DEFAULT_LORA_JSONL)
    parser.add_argument("--recommendation-count", type=int, default=180)
    parser.add_argument("--after-sales-count", type=int, default=180)
    parser.add_argument("--image-after-sales-count", type=int, default=180)
    parser.add_argument("--seed", type=int, default=20260411)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    rasa_prompt_pool = extract_prompt_pool(args.rasa_nlu) if args.rasa_nlu.exists() else []
    lora_prompt_pool = extract_lora_prompts(list(args.lora_jsonl))
    prompt_pool = deduplicate_keep_order([*rasa_prompt_pool, *lora_prompt_pool])
    categories = extract_rasa_categories(args.rasa_nlu) if args.rasa_nlu.exists() else []

    recommendation_records = build_recommendation_records(
        count=args.recommendation_count,
        rng=rng,
        categories=categories,
        prompt_pool=prompt_pool,
    )
    after_sales_records = build_after_sales_records(
        count=args.after_sales_count,
        rng=rng,
        prompt_pool=prompt_pool,
    )
    image_records = build_image_after_sales_records(
        count=args.image_after_sales_count,
        rng=rng,
    )

    recommendation_path = args.output_dir / "recommendation.jsonl"
    after_sales_path = args.output_dir / "after_sales.jsonl"
    image_path = args.output_dir / "image_after_sales.jsonl"

    write_jsonl(recommendation_path, recommendation_records)
    write_jsonl(after_sales_path, after_sales_records)
    write_jsonl(image_path, image_records)

    stats = DatasetBuildStats(
        recommendation_count=len(recommendation_records),
        after_sales_count=len(after_sales_records),
        image_after_sales_count=len(image_records),
        source_prompt_pool=len(prompt_pool),
        source_categories=len(categories),
    )
    manifest = {
        "seed": args.seed,
        "outputs": {
            "recommendation": str(recommendation_path),
            "after_sales": str(after_sales_path),
            "image_after_sales": str(image_path),
        },
        "sources": {
            "rasa_nlu": str(args.rasa_nlu),
            "lora_jsonl": [str(path) for path in args.lora_jsonl],
            "image_cases": DEFAULT_IMAGE_CASES,
        },
        "stats": {
            "recommendation_count": stats.recommendation_count,
            "after_sales_count": stats.after_sales_count,
            "image_after_sales_count": stats.image_after_sales_count,
            "source_prompt_pool": stats.source_prompt_pool,
            "source_categories": stats.source_categories,
        },
    }
    manifest_path = args.output_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
