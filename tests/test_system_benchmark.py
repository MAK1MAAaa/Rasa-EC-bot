from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT_DIR / "backend" / "scripts" / "run_system_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_system_benchmark", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["run_system_benchmark"] = MODULE
SPEC.loader.exec_module(MODULE)


def make_sample(*, scenario: str, user_input: str, checks: dict, requires_image: bool = False):
    return MODULE.SampleRecord(
        sample_id="sample-1",
        scenario=scenario,
        system_prompt="",
        context="",
        user_input=user_input,
        requires_auth=scenario != "recommendation",
        requires_image=requires_image,
        expected_capability="test",
        checks=checks,
        tags=["test"],
        image_case="damaged_package" if requires_image else "",
    )


class SystemBenchmarkScoreTests(unittest.TestCase):
    def test_recommendation_passes_with_keywords(self) -> None:
        sample = make_sample(
            scenario="recommendation",
            user_input="给我推荐一款轻薄本",
            checks={
                "required_any_keywords": ["推荐", "适合"],
                "forbidden_keywords": [],
                "generic_rejection_keywords": [],
                "must_not_hallucinate_order_id": True,
                "requires_confirmation": False,
                "must_have_next_step": False,
                "min_response_chars": 8,
                "next_step_keywords": [],
            },
        )
        status, task_success, passed, flags = MODULE.score_response(
            sample=sample,
            response_text="可以看看这几款轻薄本，比较适合办公。",
            response_card_count=0,
            unsupported=False,
            upload_ok=False,
        )
        self.assertEqual(status, "pass")
        self.assertTrue(task_success)
        self.assertTrue(passed)
        self.assertFalse(flags["generic_response"])

    def test_recommendation_generic_response_fails(self) -> None:
        sample = make_sample(
            scenario="recommendation",
            user_input="推荐几款耳机",
            checks={
                "required_any_keywords": ["推荐", "适合"],
                "forbidden_keywords": [],
                "generic_rejection_keywords": ["请提供更多信息"],
                "must_not_hallucinate_order_id": True,
                "requires_confirmation": False,
                "must_have_next_step": False,
                "min_response_chars": 8,
                "next_step_keywords": [],
            },
        )
        status, task_success, passed, flags = MODULE.score_response(
            sample=sample,
            response_text="请提供更多信息，我再帮你判断。",
            response_card_count=0,
            unsupported=False,
            upload_ok=False,
        )
        self.assertEqual(status, "fail")
        self.assertFalse(task_success)
        self.assertFalse(passed)
        self.assertTrue(flags["generic_response"])

    def test_after_sales_missing_confirmation_fails(self) -> None:
        sample = make_sample(
            scenario="after_sales",
            user_input="你直接帮我退货吧",
            checks={
                "required_any_keywords": ["退货", "订单"],
                "forbidden_keywords": [],
                "generic_rejection_keywords": [],
                "must_not_hallucinate_order_id": True,
                "requires_confirmation": True,
                "must_have_next_step": True,
                "min_response_chars": 8,
                "next_step_keywords": ["申请", "提交", "确认"],
            },
        )
        status, task_success, passed, flags = MODULE.score_response(
            sample=sample,
            response_text="你可以进入订单页提交退货申请。",
            response_card_count=0,
            unsupported=False,
            upload_ok=False,
        )
        self.assertEqual(status, "fail")
        self.assertFalse(task_success)
        self.assertFalse(passed)
        self.assertTrue(flags["missing_confirmation"])

    def test_after_sales_hallucinated_order_id_fails(self) -> None:
        sample = make_sample(
            scenario="after_sales",
            user_input="我想看退款进度",
            checks={
                "required_any_keywords": ["退款", "查看"],
                "forbidden_keywords": [],
                "generic_rejection_keywords": [],
                "must_not_hallucinate_order_id": True,
                "requires_confirmation": False,
                "must_have_next_step": True,
                "min_response_chars": 8,
                "next_step_keywords": ["查看", "订单"],
            },
        )
        status, task_success, passed, flags = MODULE.score_response(
            sample=sample,
            response_text="订单 ORD202699990001 正在退款中，你可以在订单页查看。",
            response_card_count=0,
            unsupported=False,
            upload_ok=False,
        )
        self.assertEqual(status, "fail")
        self.assertFalse(task_success)
        self.assertFalse(passed)
        self.assertTrue(flags["hallucinated_order_id"])

    def test_image_unsupported_is_na(self) -> None:
        sample = make_sample(
            scenario="image_after_sales",
            user_input="我上传了一张破损图片，帮我看下售后",
            requires_image=True,
            checks={
                "required_any_keywords": ["图片", "售后"],
                "forbidden_keywords": [],
                "generic_rejection_keywords": [],
                "must_not_hallucinate_order_id": True,
                "requires_confirmation": False,
                "must_have_next_step": True,
                "min_response_chars": 8,
                "next_step_keywords": ["申请", "售后"],
            },
        )
        status, task_success, passed, flags = MODULE.score_response(
            sample=sample,
            response_text="",
            response_card_count=0,
            unsupported=True,
            upload_ok=False,
        )
        self.assertEqual(status, "na")
        self.assertFalse(task_success)
        self.assertFalse(passed)
        self.assertFalse(flags["supported"])

    def test_summary_excludes_unsupported_from_success_rate(self) -> None:
        unsupported_event = MODULE.BenchmarkEvent(
            timestamp="",
            system="llm_base_ollama",
            scenario="image_after_sales",
            sample_id="s1",
            repeat=1,
            concurrency=1,
            request_index=1,
            requires_auth=True,
            requires_image=True,
            executed=False,
            unsupported=True,
            success=False,
            http_status=None,
            error_type="unsupported_capability",
            error_message="",
            latency_ms=0.0,
            started_at=1.0,
            finished_at=1.0,
            response_text="",
            response_chars=0,
            response_card_count=0,
            response_action_count=0,
            quality_status="na",
            task_success=False,
            passed=False,
            quality_flags={"supported": False},
        )
        success_event = MODULE.BenchmarkEvent(
            timestamp="",
            system="llm_base_ollama",
            scenario="image_after_sales",
            sample_id="s2",
            repeat=1,
            concurrency=1,
            request_index=2,
            requires_auth=True,
            requires_image=True,
            executed=True,
            unsupported=False,
            success=True,
            http_status=200,
            error_type="",
            error_message="",
            latency_ms=120.0,
            started_at=2.0,
            finished_at=2.2,
            response_text="建议联系售后提交图片凭证。",
            response_chars=13,
            response_card_count=0,
            response_action_count=0,
            quality_status="pass",
            task_success=True,
            passed=True,
            quality_flags={"supported": True, "image_flow_ok": True},
        )
        rows = MODULE.build_summary_rows([unsupported_event, success_event])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["success_rate"], 1.0)
        self.assertEqual(rows[0]["unsupported_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
