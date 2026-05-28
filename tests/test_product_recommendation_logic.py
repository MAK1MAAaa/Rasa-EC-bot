from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"

backend_pkg = types.ModuleType("backend")
backend_pkg.__path__ = [str(BACKEND_DIR)]
app_pkg = types.ModuleType("backend.app")
app_pkg.__path__ = [str(APP_DIR)]
sys.modules.setdefault("backend", backend_pkg)
sys.modules.setdefault("backend.app", app_pkg)

pil_module = types.ModuleType("PIL")
pil_image_module = types.ModuleType("PIL.Image")
pil_module.Image = pil_image_module
sys.modules.setdefault("PIL", pil_module)
sys.modules.setdefault("PIL.Image", pil_image_module)

MAIN_SPEC = importlib.util.spec_from_file_location("backend.app.main", APP_DIR / "main.py")
MAIN_MODULE = importlib.util.module_from_spec(MAIN_SPEC)
assert MAIN_SPEC and MAIN_SPEC.loader
sys.modules["backend.app.main"] = MAIN_MODULE
MAIN_SPEC.loader.exec_module(MAIN_MODULE)

ORCHESTRATOR_SPEC = importlib.util.spec_from_file_location(
    "backend.app.nexau_orchestrator",
    APP_DIR / "nexau_orchestrator.py",
)
ORCHESTRATOR_MODULE = importlib.util.module_from_spec(ORCHESTRATOR_SPEC)
assert ORCHESTRATOR_SPEC and ORCHESTRATOR_SPEC.loader
sys.modules["backend.app.nexau_orchestrator"] = ORCHESTRATOR_MODULE
ORCHESTRATOR_SPEC.loader.exec_module(ORCHESTRATOR_MODULE)


def make_product(**overrides):
    shop_id = overrides.pop("shop_id", uuid4())
    payload = {
        "id": overrides.pop("id", uuid4()),
        "shop_id": shop_id,
        "shop_name": overrides.pop("shop_name", "测试店铺"),
        "shop_description": None,
        "shop_logo_url": None,
        "shop_rating": None,
        "shop_service_score": None,
        "shop_logistics_score": None,
        "shop_after_sales_score": None,
        "shop_shipping_city": None,
        "shop_featured_categories": [],
        "shop_service_tags": [],
        "name": "办公笔记本",
        "price": 4999.0,
        "description": "轻薄办公，适合日常使用",
        "image_url": None,
        "category": "笔记本电脑",
        "brand": "ThinkPro",
        "model": "Air 14",
        "sku_code": "SKU001",
        "original_price": 5599.0,
        "rating": 4.8,
        "review_count": 128,
        "monthly_sales": 300,
        "ship_in_hours": 24,
        "warranty_days": 365,
        "tags": ["轻薄", "办公推荐"],
        "spec_highlights": ["14 英寸", "16GB 内存"],
        "is_active": True,
        "stock": 25,
        "created_at": overrides.pop("created_at", MAIN_MODULE.datetime.utcnow()),
    }
    payload.update(overrides)
    return MAIN_MODULE.ProductRead(**payload)


def make_db_shop(**overrides):
    payload = {
        "id": overrides.pop("id", uuid4()),
        "owner_user_id": overrides.pop("owner_user_id", uuid4()),
        "name": overrides.pop("name", "测试店铺"),
        "description": None,
        "contact_email": None,
        "contact_phone": None,
        "featured_categories": [],
        "service_tags": [],
        "is_active": True,
        "created_at": overrides.pop("created_at", MAIN_MODULE.datetime.utcnow()),
    }
    payload.update(overrides)
    return MAIN_MODULE.Shop(**payload)


def make_db_product(**overrides):
    payload = {
        "id": overrides.pop("id", uuid4()),
        "shop_id": overrides.pop("shop_id", uuid4()),
        "name": overrides.pop("name", "银翼 Air 13 轻薄本"),
        "price": overrides.pop("price", 4999.0),
        "description": overrides.pop("description", "银色轻薄笔记本，适合论文写作和轻量开发"),
        "image_url": None,
        "category": overrides.pop("category", "笔记本电脑"),
        "brand": overrides.pop("brand", "银翼"),
        "model": overrides.pop("model", "Air 13"),
        "sku_code": overrides.pop("sku_code", "SKU001"),
        "original_price": overrides.pop("original_price", 5599.0),
        "rating": overrides.pop("rating", 4.8),
        "review_count": overrides.pop("review_count", 128),
        "monthly_sales": overrides.pop("monthly_sales", 300),
        "ship_in_hours": overrides.pop("ship_in_hours", 24),
        "warranty_days": overrides.pop("warranty_days", 365),
        "tags": overrides.pop("tags", ["银色", "轻薄本", "办公"]),
        "spec_highlights": overrides.pop("spec_highlights", ["16GB 内存", "1TB SSD"]),
        "is_active": overrides.pop("is_active", True),
        "stock": overrides.pop("stock", 25),
        "created_at": overrides.pop("created_at", MAIN_MODULE.datetime.utcnow()),
    }
    payload.update(overrides)
    return MAIN_MODULE.Product(**payload)


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return FakeScalarResult(self._rows)


class FakeRecommendationSession:
    def __init__(self, *result_batches):
        self._result_batches = list(result_batches)

    async def execute(self, _statement):
        if not self._result_batches:
            raise AssertionError("unexpected database execute")
        return FakeExecuteResult(self._result_batches.pop(0))


class ProductRecommendationLogicTests(unittest.TestCase):
    def test_default_product_recommendation_limit_is_single_item(self) -> None:
        self.assertEqual(MAIN_MODULE.DEFAULT_PRODUCT_RECOMMENDATION_LIMIT, 1)

    def test_extract_recommendation_terms_removes_prompt_words(self) -> None:
        terms = MAIN_MODULE.extract_recommendation_query_terms("帮我推荐几款办公笔记本")
        self.assertIn("办公笔记本", terms)
        self.assertNotIn("推荐", terms)

    def test_extract_recommendation_terms_split_color_and_category_constraints(self) -> None:
        terms = MAIN_MODULE.extract_recommendation_query_terms("帮我推荐一款白色的4000元以下的手机")
        self.assertIn("白", terms)
        self.assertIn("手机", terms)

    def test_extract_recommendation_constraints_parse_budget_and_color(self) -> None:
        constraints = MAIN_MODULE.extract_recommendation_query_constraints("帮我推荐一款白色的4000元以下的手机")
        self.assertEqual(constraints.max_price, 4000.0)
        self.assertIn("白", constraints.required_terms)

    def test_infer_explicit_category_prefers_longest_match(self) -> None:
        category = MAIN_MODULE.infer_explicit_category_from_query(
            "推荐几款笔记本电脑",
            ["电脑", "笔记本电脑", "手机"],
        )
        self.assertEqual(category, "笔记本电脑")

    def test_history_score_prefers_matching_profile(self) -> None:
        shop_id = uuid4()
        profile = MAIN_MODULE.RecommendationHistoryProfile(
            recent_product_ids=[],
            category_scores={"笔记本电脑": 3},
            brand_scores={"thinkpro": 2},
            tag_scores={"办公推荐": 2},
            shop_scores={shop_id: 1},
        )
        matched = make_product(shop_id=shop_id)
        unmatched = make_product(
            shop_id=uuid4(),
            category="手机",
            brand="PhoneX",
            tags=["拍照"],
        )

        matched_score = MAIN_MODULE.compute_product_history_score(matched, profile)
        unmatched_score = MAIN_MODULE.compute_product_history_score(unmatched, profile)
        self.assertGreater(matched_score, unmatched_score)

    def test_constraint_filter_excludes_products_outside_budget_or_color(self) -> None:
        constraints = MAIN_MODULE.extract_recommendation_query_constraints("帮我推荐一款白色的4000元以下的手机")
        matched = make_product(
            category="手机",
            price=3520.0,
            tags=["月岩白", "长续航"],
            spec_highlights=["月岩白", "12GB+512GB"],
            name="曜石 Note Air",
        )
        wrong_color = make_product(
            category="手机",
            price=3760.0,
            tags=["海盐蓝", "手游旗舰"],
            spec_highlights=["海盐蓝", "12GB+256GB"],
            name="曜石 Note Max",
        )
        over_budget = make_product(
            category="手机",
            price=4020.0,
            tags=["月岩白", "轻薄"],
            spec_highlights=["月岩白", "12GB+256GB"],
            name="星云 X1 Ultra",
        )

        self.assertTrue(MAIN_MODULE.product_matches_recommendation_constraints(matched, constraints))
        self.assertFalse(MAIN_MODULE.product_matches_recommendation_constraints(wrong_color, constraints))
        self.assertFalse(MAIN_MODULE.product_matches_recommendation_constraints(over_budget, constraints))

    def test_query_score_reads_spec_highlights(self) -> None:
        with_spec = make_product(
            category="显示器",
            name="护眼显示器",
            tags=["护眼"],
            spec_highlights=["27寸", "Type-C"],
        )
        without_spec = make_product(
            category="显示器",
            name="护眼显示器",
            tags=["护眼"],
            spec_highlights=[],
        )
        query_terms = MAIN_MODULE.extract_recommendation_query_terms("推荐一款 27 寸 Type-C 显示器")

        with_spec_score = MAIN_MODULE.compute_product_query_score(
            with_spec,
            query="推荐一款 27 寸 Type-C 显示器",
            query_terms=query_terms,
            explicit_category="显示器",
        )
        without_spec_score = MAIN_MODULE.compute_product_query_score(
            without_spec,
            query="推荐一款 27 寸 Type-C 显示器",
            query_terms=query_terms,
            explicit_category="显示器",
        )

        self.assertGreater(with_spec_score, without_spec_score)

    def test_recommendation_query_detection(self) -> None:
        self.assertTrue(ORCHESTRATOR_MODULE.is_product_recommendation_query("推荐几款适合办公的显示器"))
        self.assertFalse(ORCHESTRATOR_MODULE.is_product_recommendation_query("显示器说明书怎么下载"))

    def test_agent_product_recommendation_plan_requests_single_item(self) -> None:
        endpoint = ORCHESTRATOR_MODULE.LLMEndpointConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            model="qwen3.5:2b",
            timeout_sec=1,
        )
        orchestrator = ORCHESTRATOR_MODULE.NexAUAgentOrchestrator(
            primary_llm=endpoint,
            fallback_llm=None,
            frontend_base_url="http://localhost:5173",
        )

        plan = orchestrator._build_tool_plan(
            message="推荐一台银色笔记本",
            user_id=str(uuid4()),
            domains={"product"},
            is_authenticated=True,
            attachments=[],
        )

        recommendation_step = next(item for item in plan if item["name"] == "query_product_recommendations")
        self.assertEqual(recommendation_step["args"]["limit"], 1)

    def test_explicit_recommendation_limit_can_still_return_multiple_items(self) -> None:
        async def run_case(limit: int):
            shop = make_db_shop()
            products = [
                make_db_product(
                    shop_id=shop.id,
                    name="凌云 Air 14 轻薄本",
                    brand="凌云",
                    model="Air 14",
                    monthly_sales=280,
                ),
                make_db_product(
                    shop_id=shop.id,
                    name="银翼 Air 13 轻薄本",
                    brand="银翼",
                    model="Air 13",
                    monthly_sales=180,
                ),
            ]
            session = FakeRecommendationSession(products, [shop])
            return await MAIN_MODULE.get_personalized_product_recommendations(
                session,
                user_id=None,
                query="推荐银色笔记本",
                category="笔记本电脑",
                limit=limit,
            )

        default_response = asyncio.run(run_case(MAIN_MODULE.DEFAULT_PRODUCT_RECOMMENDATION_LIMIT))
        explicit_response = asyncio.run(run_case(2))

        self.assertEqual(len(default_response.items), 1)
        self.assertEqual(len(explicit_response.items), 2)


if __name__ == "__main__":
    unittest.main()
