from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
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
DEFAULT_ALLOWED_ORDER_IDS = ["ORD202603300001", "ORD202603300002"]
PENDING_ORDER_ID = "ORD202603300001"
SHIPPED_ORDER_ID = "ORD202603300002"


@dataclass(frozen=True)
class DatasetBuildStats:
    tier: str
    total_count: int
    family_counts: dict[str, int]


def clean_text(value: str) -> str:
    text = value.strip()
    return re.sub(r"\s+", " ", text)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


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
        if not match:
            continue
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
                if not isinstance(payload, dict):
                    continue
                prompt = payload.get("prompt")
                if isinstance(prompt, str):
                    cleaned = clean_text(prompt)
                    if cleaned:
                        prompts.append(cleaned)
    return prompts


def extract_rasa_categories(path: Path) -> list[str]:
    text = read_text(path)
    matches = re.findall(r"\[([^\]]+)\]\(category\)", text)
    categories = [clean_text(item) for item in matches if clean_text(item)]
    return deduplicate_keep_order(categories)


def turn_login(turn_id: str = "login") -> dict[str, Any]:
    return {"id": turn_id, "kind": "login"}


def turn_upload_image(image_case: str, *, turn_id: str = "upload_image") -> dict[str, Any]:
    return {"id": turn_id, "kind": "upload_image", "image_case": image_case}


def turn_chat_send(
    message: str,
    *,
    turn_id: str,
    use_uploaded_attachments: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": turn_id,
        "kind": "chat_send",
        "message": clean_text(message),
    }
    if use_uploaded_attachments:
        payload["use_uploaded_attachments"] = True
    return payload


def turn_pending_decision(decision: str, *, turn_id: str) -> dict[str, Any]:
    return {"id": turn_id, "kind": "pending_decision", "decision": decision.strip().lower()}


def turn_sleep(seconds: float, *, turn_id: str) -> dict[str, Any]:
    return {"id": turn_id, "kind": "sleep_until_expired", "sleep_seconds": max(0.0, float(seconds))}


def expected_outcomes(
    *,
    required_any_text_keywords: list[str],
    forbidden_text_keywords: list[str] | None = None,
    required_card_types: list[str] | None = None,
    required_action_types: list[str] | None = None,
    requires_confirmation_buttons: bool = False,
    should_return_order_id: bool = False,
    should_block_without_login: bool = False,
    should_be_unsupported: bool = False,
    must_avoid_hallucinated_order_id: bool = True,
    allowed_order_ids: list[str] | None = None,
    min_response_chars: int = 8,
) -> dict[str, Any]:
    return {
        "required_any_text_keywords": required_any_text_keywords,
        "forbidden_text_keywords": forbidden_text_keywords or [],
        "required_card_types": required_card_types or [],
        "required_action_types": required_action_types or [],
        "requires_confirmation_buttons": requires_confirmation_buttons,
        "should_return_order_id": should_return_order_id,
        "should_block_without_login": should_block_without_login,
        "should_be_unsupported": should_be_unsupported,
        "must_avoid_hallucinated_order_id": must_avoid_hallucinated_order_id,
        "allowed_order_ids": allowed_order_ids or [],
        "min_response_chars": min_response_chars,
    }


def build_conversation(
    *,
    sample_id: str,
    scenario_family: str,
    scenario: str,
    turns: list[dict[str, Any]],
    account: str,
    required_capabilities: list[str],
    preconditions: dict[str, Any],
    expected: dict[str, Any],
    tags: list[str],
    tier: str,
    repeatable: bool = True,
) -> dict[str, Any]:
    return {
        "id": sample_id,
        "scenario_family": scenario_family,
        "scenario": scenario,
        "turns": turns,
        "account": account,
        "required_capabilities": required_capabilities,
        "preconditions": preconditions,
        "expected_outcomes": expected,
        "tags": tags,
        "tier": tier,
        "repeatable": repeatable,
    }


def build_core_conversations() -> list[dict[str, Any]]:
    return [
        build_conversation(
            sample_id="recommendation_basic_core",
            scenario_family="recommendation",
            scenario="basic_recommendation",
            turns=[
                turn_chat_send("给我推荐几款适合通勤和日常办公的轻薄笔记本。", turn_id="ask_recommendation"),
            ],
            account="anonymous",
            required_capabilities=[],
            preconditions={"notes": ["匿名用户推荐场景"]},
            expected=expected_outcomes(
                required_any_text_keywords=["推荐", "适合", "笔记本"],
                forbidden_text_keywords=["无法帮助", "请先登录"],
                min_response_chars=16,
            ),
            tags=["core", "recommendation", "anonymous"],
            tier="core",
        ),
        build_conversation(
            sample_id="recommendation_budget_core",
            scenario_family="recommendation",
            scenario="budget_recommendation",
            turns=[
                turn_chat_send("预算 3000 元左右，推荐一款适合追剧和轻度游戏的平板或轻薄本。", turn_id="ask_budget"),
            ],
            account="anonymous",
            required_capabilities=[],
            preconditions={"notes": ["带预算约束的推荐"]},
            expected=expected_outcomes(
                required_any_text_keywords=["预算", "推荐", "适合"],
                forbidden_text_keywords=["请先登录", "已为你下单"],
                min_response_chars=18,
            ),
            tags=["core", "recommendation", "budget"],
            tier="core",
        ),
        build_conversation(
            sample_id="recommendation_preference_core",
            scenario_family="recommendation",
            scenario="preference_recommendation",
            turns=[
                turn_chat_send("我比较看重续航和屏幕，想买一款适合出差携带的手机。", turn_id="ask_preference"),
            ],
            account="anonymous",
            required_capabilities=[],
            preconditions={"notes": ["带偏好约束的推荐"]},
            expected=expected_outcomes(
                required_any_text_keywords=["续航", "屏幕", "推荐"],
                forbidden_text_keywords=["无法帮助", "请先登录"],
                min_response_chars=18,
            ),
            tags=["core", "recommendation", "preference"],
            tier="core",
        ),
        build_conversation(
            sample_id="order_query_recent_core",
            scenario_family="order_query",
            scenario="recent_order_query",
            turns=[
                turn_login(),
                turn_chat_send("帮我看看最近的订单。", turn_id="query_recent_order"),
            ],
            account="customer",
            required_capabilities=["supports_auth_queries", "supports_cards"],
            preconditions={"allowed_order_ids": DEFAULT_ALLOWED_ORDER_IDS},
            expected=expected_outcomes(
                required_any_text_keywords=["订单"],
                required_card_types=["order"],
                should_return_order_id=True,
                allowed_order_ids=DEFAULT_ALLOWED_ORDER_IDS,
                min_response_chars=10,
            ),
            tags=["core", "order_query", "recent"],
            tier="core",
        ),
        build_conversation(
            sample_id="order_query_specific_core",
            scenario_family="order_query",
            scenario="specific_order_query",
            turns=[
                turn_login(),
                turn_chat_send(f"帮我查询订单 {PENDING_ORDER_ID} 的状态。", turn_id="query_specific_order"),
            ],
            account="customer",
            required_capabilities=["supports_auth_queries", "supports_cards"],
            preconditions={"allowed_order_ids": [PENDING_ORDER_ID]},
            expected=expected_outcomes(
                required_any_text_keywords=["订单", "待发货"],
                required_card_types=["order"],
                should_return_order_id=True,
                allowed_order_ids=[PENDING_ORDER_ID],
                min_response_chars=10,
            ),
            tags=["core", "order_query", "specific"],
            tier="core",
        ),
        build_conversation(
            sample_id="order_query_requires_login_core",
            scenario_family="order_query",
            scenario="login_required_order_query",
            turns=[
                turn_chat_send("帮我看看我的订单。", turn_id="query_without_login"),
            ],
            account="anonymous",
            required_capabilities=["supports_auth_queries"],
            preconditions={},
            expected=expected_outcomes(
                required_any_text_keywords=["登录"],
                forbidden_text_keywords=["订单已创建"],
                should_block_without_login=True,
                min_response_chars=10,
            ),
            tags=["core", "order_query", "login_required"],
            tier="core",
        ),
        build_conversation(
            sample_id="logistics_query_recent_core",
            scenario_family="logistics_query",
            scenario="recent_logistics_query",
            turns=[
                turn_login(),
                turn_chat_send("帮我看一下最近订单的物流进度。", turn_id="query_recent_logistics"),
            ],
            account="customer",
            required_capabilities=["supports_auth_queries", "supports_cards"],
            preconditions={"allowed_order_ids": [SHIPPED_ORDER_ID]},
            expected=expected_outcomes(
                required_any_text_keywords=["物流", "在途"],
                required_card_types=["logistics"],
                should_return_order_id=True,
                allowed_order_ids=[SHIPPED_ORDER_ID],
                min_response_chars=10,
            ),
            tags=["core", "logistics_query", "recent"],
            tier="core",
        ),
        build_conversation(
            sample_id="logistics_query_specific_core",
            scenario_family="logistics_query",
            scenario="specific_logistics_query",
            turns=[
                turn_login(),
                turn_chat_send(f"查询订单 {SHIPPED_ORDER_ID} 的物流进度。", turn_id="query_specific_logistics"),
            ],
            account="customer",
            required_capabilities=["supports_auth_queries", "supports_cards"],
            preconditions={"allowed_order_ids": [SHIPPED_ORDER_ID]},
            expected=expected_outcomes(
                required_any_text_keywords=["物流", "上海"],
                required_card_types=["logistics"],
                should_return_order_id=True,
                allowed_order_ids=[SHIPPED_ORDER_ID],
                min_response_chars=10,
            ),
            tags=["core", "logistics_query", "specific"],
            tier="core",
        ),
        build_conversation(
            sample_id="logistics_query_no_record_core",
            scenario_family="logistics_query",
            scenario="missing_logistics_record_query",
            turns=[
                turn_login(),
                turn_chat_send(f"查询订单 {PENDING_ORDER_ID} 的物流。", turn_id="query_missing_logistics"),
            ],
            account="customer",
            required_capabilities=["supports_auth_queries"],
            preconditions={"allowed_order_ids": [PENDING_ORDER_ID]},
            expected=expected_outcomes(
                required_any_text_keywords=["未发货", "物流"],
                should_return_order_id=True,
                allowed_order_ids=[PENDING_ORDER_ID],
                min_response_chars=10,
            ),
            tags=["core", "logistics_query", "missing"],
            tier="core",
        ),
        build_conversation(
            sample_id="after_sales_progress_core",
            scenario_family="after_sales_query",
            scenario="after_sales_progress_query",
            turns=[
                turn_login(),
                turn_chat_send(f"查询订单 {SHIPPED_ORDER_ID} 的售后进度。", turn_id="query_after_sales_progress"),
            ],
            account="customer",
            required_capabilities=["supports_auth_queries", "supports_cards"],
            preconditions={"allowed_order_ids": [SHIPPED_ORDER_ID]},
            expected=expected_outcomes(
                required_any_text_keywords=["售后", "已完成"],
                required_card_types=["after_sales"],
                should_return_order_id=True,
                allowed_order_ids=[SHIPPED_ORDER_ID],
                min_response_chars=10,
            ),
            tags=["core", "after_sales_query", "progress"],
            tier="core",
        ),
        build_conversation(
            sample_id="after_sales_policy_core",
            scenario_family="after_sales_query",
            scenario="after_sales_policy_query",
            turns=[
                turn_chat_send("订单已经发货但还没签收，能直接申请退货吗？", turn_id="query_policy"),
            ],
            account="anonymous",
            required_capabilities=["supports_kb_policy"],
            preconditions={"knowledge_seed": ["policy"]},
            expected=expected_outcomes(
                required_any_text_keywords=["签收", "退货", "售后"],
                forbidden_text_keywords=["请先登录", "已退款成功"],
                min_response_chars=18,
            ),
            tags=["core", "after_sales_query", "policy"],
            tier="core",
        ),
        build_conversation(
            sample_id="manual_query_core",
            scenario_family="knowledge_and_multimodal",
            scenario="manual_knowledge_query",
            turns=[
                turn_chat_send("智能门锁怎么恢复出厂设置？", turn_id="query_manual"),
            ],
            account="anonymous",
            required_capabilities=["supports_kb_manual"],
            preconditions={"knowledge_seed": ["manual"]},
            expected=expected_outcomes(
                required_any_text_keywords=["恢复出厂设置", "长按", "设置"],
                forbidden_text_keywords=["请先登录"],
                min_response_chars=16,
            ),
            tags=["core", "knowledge_and_multimodal", "manual"],
            tier="core",
        ),
        build_conversation(
            sample_id="image_after_sales_core",
            scenario_family="knowledge_and_multimodal",
            scenario="image_after_sales_query",
            turns=[
                turn_login(),
                turn_upload_image("broken_screen"),
                turn_chat_send(
                    "我上传了一张屏幕裂开的图片，帮我判断售后应该怎么处理。",
                    turn_id="ask_image_after_sales",
                    use_uploaded_attachments=True,
                ),
            ],
            account="customer",
            required_capabilities=["supports_auth_queries", "supports_attachments", "supports_image_analysis"],
            preconditions={"image_cases": ["broken_screen"]},
            expected=expected_outcomes(
                required_any_text_keywords=["屏幕", "售后", "申请"],
                forbidden_text_keywords=["图片上传失败", "无法读取图片"],
                min_response_chars=18,
            ),
            tags=["core", "knowledge_and_multimodal", "image"],
            tier="core",
        ),
        build_conversation(
            sample_id="transaction_update_shipping_confirm_core",
            scenario_family="transactional_action",
            scenario="update_shipping_confirm",
            turns=[
                turn_login(),
                turn_chat_send(
                    f"修改地址 {PENDING_ORDER_ID} 地址: 北京市海淀区中关村软件园二期 8 号楼，邮箱: test1@example.com",
                    turn_id="draft_update_shipping",
                ),
                turn_pending_decision("confirm", turn_id="confirm_update_shipping"),
            ],
            account="customer",
            required_capabilities=[
                "supports_auth_queries",
                "supports_pending_action",
                "supports_pending_decision",
                "supports_cards",
            ],
            preconditions={"allowed_order_ids": [PENDING_ORDER_ID]},
            expected=expected_outcomes(
                required_any_text_keywords=["修改", "收货信息", "已更新"],
                required_card_types=["pending_action", "order"],
                required_action_types=["pending_action_decision"],
                requires_confirmation_buttons=True,
                should_return_order_id=True,
                allowed_order_ids=[PENDING_ORDER_ID],
                min_response_chars=12,
            ),
            tags=["core", "transactional_action", "confirm"],
            tier="core",
        ),
        build_conversation(
            sample_id="transaction_cancel_draft_cancel_core",
            scenario_family="transactional_action",
            scenario="cancel_order_then_cancel_draft",
            turns=[
                turn_login(),
                turn_chat_send(f"取消订单 {PENDING_ORDER_ID}。", turn_id="draft_cancel_order"),
                turn_pending_decision("cancel", turn_id="cancel_pending_action"),
            ],
            account="customer",
            required_capabilities=[
                "supports_auth_queries",
                "supports_pending_action",
                "supports_pending_decision",
                "supports_cards",
            ],
            preconditions={"allowed_order_ids": [PENDING_ORDER_ID]},
            expected=expected_outcomes(
                required_any_text_keywords=["取消订单", "已取消本次自动操作"],
                required_card_types=["pending_action"],
                required_action_types=["pending_action_decision"],
                requires_confirmation_buttons=True,
                allowed_order_ids=[PENDING_ORDER_ID],
                min_response_chars=12,
            ),
            tags=["core", "transactional_action", "cancel"],
            tier="core",
        ),
    ]


def choose_prompt_hint(prompt_pool: list[str], rng: random.Random, fallback: str) -> str:
    if not prompt_pool:
        return fallback
    return prompt_pool[rng.randrange(0, len(prompt_pool))]


def build_extended_recommendations(
    *,
    rng: random.Random,
    categories: list[str],
    prompt_pool: list[str],
    count: int,
) -> list[dict[str, Any]]:
    category_pool = deduplicate_keep_order(categories + ["手机", "笔记本", "显示器", "路由器", "耳机"])
    needs = [
        "宿舍追剧和轻度游戏",
        "长时间办公和网课",
        "出差便携和续航",
        "送长辈日常使用",
        "拍照和视频会议",
    ]
    budgets = ["2000 元内", "3000 元左右", "4500 元左右", "6000 元内", "8000 元内"]
    records: list[dict[str, Any]] = []
    for index in range(1, count + 1):
        category = category_pool[rng.randrange(0, len(category_pool))]
        need = needs[rng.randrange(0, len(needs))]
        budget = budgets[rng.randrange(0, len(budgets))]
        hint = choose_prompt_hint(prompt_pool, rng, "推荐几款销量高、评价好的商品")
        records.append(
            build_conversation(
                sample_id=f"recommendation_extended_{index:03d}",
                scenario_family="recommendation",
                scenario="extended_recommendation",
                turns=[turn_chat_send(f"想买{category}，预算 {budget}，主要需求是 {need}。{hint}", turn_id="ask_extended")],
                account="anonymous",
                required_capabilities=[],
                preconditions={"notes": ["扩展推荐集"]},
                expected=expected_outcomes(
                    required_any_text_keywords=["推荐", "适合"],
                    forbidden_text_keywords=["请先登录", "无法帮助"],
                    min_response_chars=16,
                ),
                tags=["extended", "recommendation", category],
                tier="extended",
            )
        )
    return records


def build_extended_conversations(rng: random.Random, prompt_pool: list[str], categories: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    records.extend(
        [
            build_conversation(
                sample_id="knowledge_policy_price_protection_extended",
                scenario_family="knowledge_and_multimodal",
                scenario="price_protection_policy_query",
                turns=[turn_chat_send("平台支持保价吗？如果活动后降价了应该怎么处理？", turn_id="query_price_protection")],
                account="anonymous",
                required_capabilities=["supports_kb_policy"],
                preconditions={"knowledge_seed": ["policy"]},
                expected=expected_outcomes(
                    required_any_text_keywords=["保价", "降价", "活动"],
                    min_response_chars=18,
                ),
                tags=["extended", "knowledge_and_multimodal", "policy"],
                tier="extended",
            ),
            build_conversation(
                sample_id="image_after_sales_rule_fusion_extended",
                scenario_family="knowledge_and_multimodal",
                scenario="image_and_policy_fusion_query",
                turns=[
                    turn_login(),
                    turn_upload_image("damaged_package"),
                    turn_chat_send(
                        "我上传了一个外箱破损的图片，如果里面也有损坏，平台售后一般怎么处理？",
                        turn_id="ask_image_and_policy",
                        use_uploaded_attachments=True,
                    ),
                ],
                account="customer",
                required_capabilities=[
                    "supports_auth_queries",
                    "supports_attachments",
                    "supports_image_analysis",
                    "supports_kb_policy",
                ],
                preconditions={"knowledge_seed": ["policy"], "image_cases": ["damaged_package"]},
                expected=expected_outcomes(
                    required_any_text_keywords=["包装", "售后", "申请"],
                    min_response_chars=18,
                ),
                tags=["extended", "knowledge_and_multimodal", "fusion"],
                tier="extended",
            ),
            build_conversation(
                sample_id="transaction_after_sales_draft_extended",
                scenario_family="transactional_action",
                scenario="after_sales_draft_only",
                turns=[
                    turn_login(),
                    turn_chat_send(
                        f"申请退款 {PENDING_ORDER_ID} 原因: 尺寸不合适。",
                        turn_id="draft_after_sales",
                    ),
                ],
                account="customer",
                required_capabilities=["supports_auth_queries", "supports_pending_action", "supports_cards"],
                preconditions={"allowed_order_ids": [PENDING_ORDER_ID]},
                expected=expected_outcomes(
                    required_any_text_keywords=["售后", "草案", "确认"],
                    required_card_types=["pending_action"],
                    required_action_types=["pending_action_decision"],
                    requires_confirmation_buttons=True,
                    should_return_order_id=True,
                    allowed_order_ids=[PENDING_ORDER_ID],
                    min_response_chars=12,
                ),
                tags=["extended", "transactional_action", "after_sales_draft"],
                tier="extended",
            ),
            build_conversation(
                sample_id="transaction_logistics_complaint_draft_extended",
                scenario_family="transactional_action",
                scenario="logistics_complaint_draft_only",
                turns=[
                    turn_login(),
                    turn_chat_send(
                        f"投诉物流 {SHIPPED_ORDER_ID} 原因: 包裹长时间未更新。",
                        turn_id="draft_logistics_complaint",
                    ),
                ],
                account="customer",
                required_capabilities=["supports_auth_queries", "supports_pending_action", "supports_cards"],
                preconditions={"allowed_order_ids": [SHIPPED_ORDER_ID]},
                expected=expected_outcomes(
                    required_any_text_keywords=["投诉", "物流", "确认"],
                    required_card_types=["pending_action"],
                    required_action_types=["pending_action_decision"],
                    requires_confirmation_buttons=True,
                    should_return_order_id=True,
                    allowed_order_ids=[SHIPPED_ORDER_ID],
                    min_response_chars=12,
                ),
                tags=["extended", "transactional_action", "logistics_complaint_draft"],
                tier="extended",
            ),
            build_conversation(
                sample_id="transaction_pending_action_expired_extended",
                scenario_family="transactional_action",
                scenario="pending_action_expired",
                turns=[
                    turn_login(),
                    turn_chat_send(f"取消订单 {PENDING_ORDER_ID}。", turn_id="draft_cancel_for_expiry"),
                    turn_sleep(305, turn_id="wait_until_expired"),
                    turn_pending_decision("confirm", turn_id="confirm_after_expired"),
                ],
                account="customer",
                required_capabilities=[
                    "supports_auth_queries",
                    "supports_pending_action",
                    "supports_pending_decision",
                    "supports_cards",
                ],
                preconditions={
                    "allowed_order_ids": [PENDING_ORDER_ID],
                    "notes": ["需要后端 CHAT_ACTION_TTL_SEC 使用默认 300 秒或更短值"],
                },
                expected=expected_outcomes(
                    required_any_text_keywords=["待确认", "已过期"],
                    required_card_types=["pending_action"],
                    required_action_types=["pending_action_decision"],
                    requires_confirmation_buttons=True,
                    allowed_order_ids=[PENDING_ORDER_ID],
                    min_response_chars=12,
                ),
                tags=["extended", "transactional_action", "expired"],
                tier="extended",
                repeatable=False,
            ),
        ]
    )
    records.extend(
        build_extended_recommendations(
            rng=rng,
            categories=categories,
            prompt_pool=prompt_pool,
            count=12,
        )
    )
    return records


def split_by_family(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["scenario_family"])].append(record)
    return dict(grouped)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def compute_stats(tier: str, records: list[dict[str, Any]]) -> DatasetBuildStats:
    family_counts: dict[str, int] = defaultdict(int)
    for record in records:
        family_counts[str(record["scenario_family"])] += 1
    return DatasetBuildStats(
        tier=tier,
        total_count=len(records),
        family_counts=dict(sorted(family_counts.items())),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成客服链路多轮 benchmark 数据集。")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--rasa-nlu", type=Path, default=DEFAULT_RASA_NLU)
    parser.add_argument("--lora-jsonl", nargs="*", type=Path, default=DEFAULT_LORA_JSONL)
    parser.add_argument("--seed", type=int, default=20260412)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    rasa_prompt_pool = extract_prompt_pool(args.rasa_nlu) if args.rasa_nlu.exists() else []
    lora_prompt_pool = extract_lora_prompts(list(args.lora_jsonl))
    prompt_pool = deduplicate_keep_order([*rasa_prompt_pool, *lora_prompt_pool])
    categories = extract_rasa_categories(args.rasa_nlu) if args.rasa_nlu.exists() else []

    core_records = build_core_conversations()
    extended_records = [*core_records, *build_extended_conversations(rng, prompt_pool, categories)]

    outputs: dict[str, dict[str, str]] = {"core": {}, "extended": {}}
    for tier, grouped in [("core", split_by_family(core_records)), ("extended", split_by_family(extended_records))]:
        for family, records in grouped.items():
            path = args.output_dir / tier / f"{family}.jsonl"
            write_jsonl(path, records)
            outputs[tier][family] = str(path)

    core_stats = compute_stats("core", core_records)
    extended_stats = compute_stats("extended", extended_records)
    manifest = {
        "seed": args.seed,
        "outputs": outputs,
        "sources": {
            "rasa_nlu": str(args.rasa_nlu),
            "lora_jsonl": [str(path) for path in args.lora_jsonl],
            "image_cases": DEFAULT_IMAGE_CASES,
            "allowed_order_ids": DEFAULT_ALLOWED_ORDER_IDS,
        },
        "stats": {
            "core": {"total_count": core_stats.total_count, "family_counts": core_stats.family_counts},
            "extended": {"total_count": extended_stats.total_count, "family_counts": extended_stats.family_counts},
        },
    }
    manifest_path = args.output_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
