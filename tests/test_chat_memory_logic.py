from __future__ import annotations

import importlib.util
import sys
import tempfile
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

MODULE_SPEC = importlib.util.spec_from_file_location("backend.app.chat_memory", APP_DIR / "chat_memory.py")
MEMORY_MODULE = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC and MODULE_SPEC.loader
sys.modules["backend.app.chat_memory"] = MEMORY_MODULE
MODULE_SPEC.loader.exec_module(MEMORY_MODULE)


class ChatMemoryLogicTests(unittest.TestCase):
    def test_resolve_chat_session_ref_uses_frontend_sender_suffix(self) -> None:
        user_id = uuid4()
        with tempfile.TemporaryDirectory() as temp_dir:
            ref = MEMORY_MODULE.resolve_chat_session_ref(
                user_id=user_id,
                sender_id=f"{user_id}:s-20260416-demo",
                config=MEMORY_MODULE.ChatMemoryConfig(root_dir=Path(temp_dir)),
            )

            self.assertIsNotNone(ref)
            self.assertEqual(ref.session_id, "s-20260416-demo")
            self.assertEqual(ref.sender_id, f"{user_id}:s-20260416-demo")

    def test_resolve_chat_session_ref_falls_back_to_default_when_prefix_mismatch(self) -> None:
        user_id = uuid4()
        with tempfile.TemporaryDirectory() as temp_dir:
            ref = MEMORY_MODULE.resolve_chat_session_ref(
                user_id=user_id,
                sender_id=f"{uuid4()}:s-other",
                config=MEMORY_MODULE.ChatMemoryConfig(root_dir=Path(temp_dir)),
            )

            self.assertIsNotNone(ref)
            self.assertEqual(ref.session_id, MEMORY_MODULE.DEFAULT_CHAT_SESSION_ID)
            self.assertEqual(ref.sender_id, f"{user_id}:{MEMORY_MODULE.DEFAULT_CHAT_SESSION_ID}")

    def test_attach_and_extract_pending_action_context_preserves_session(self) -> None:
        user_id = uuid4()
        with tempfile.TemporaryDirectory() as temp_dir:
            config = MEMORY_MODULE.ChatMemoryConfig(root_dir=Path(temp_dir))
            ref = MEMORY_MODULE.resolve_chat_session_ref(
                user_id=user_id,
                sender_id=f"{user_id}:s-memory",
                config=config,
            )

            payload = MEMORY_MODULE.attach_pending_action_context({"type": "cancel_order"}, ref)
            restored = MEMORY_MODULE.extract_session_ref_from_pending_payload(
                user_id=user_id,
                payload=payload,
                config=config,
            )

            self.assertEqual(restored.session_id, "s-memory")
            self.assertEqual(restored.sender_id, f"{user_id}:s-memory")

    def test_extract_memory_facts_from_texts_collects_preferences(self) -> None:
        facts = MEMORY_MODULE.extract_memory_facts_from_texts(
            [
                "推荐一台白色 27 寸显示器，预算 2500 元，主要办公和剪视频。",
                "我更偏向联想或者华硕。",
            ]
        )

        self.assertIn("2500元", facts["budgets"])
        self.assertIn("白色", facts["colors"])
        self.assertIn("联想", facts["brands"])
        self.assertIn("办公", facts["scenarios"])
        self.assertIn("product", facts["topics"])

    def test_should_compact_history_when_threshold_hit_or_file_missing(self) -> None:
        config = MEMORY_MODULE.ChatMemoryConfig(compact_message_threshold=3, compact_char_threshold=9999)
        messages = [
            {"sequence_no": 1, "message_text": "a"},
            {"sequence_no": 2, "message_text": "b"},
            {"sequence_no": 3, "message_text": "c"},
        ]

        self.assertTrue(
            MEMORY_MODULE.should_compact_history(
                latest_snapshot_end_sequence=0,
                all_messages=messages,
                config=config,
                context_file_exists=False,
            )
        )
        self.assertTrue(
            MEMORY_MODULE.should_compact_history(
                latest_snapshot_end_sequence=0,
                all_messages=messages,
                config=config,
                context_file_exists=True,
            )
        )
        self.assertFalse(
            MEMORY_MODULE.should_compact_history(
                latest_snapshot_end_sequence=3,
                all_messages=messages,
                config=config,
                context_file_exists=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
