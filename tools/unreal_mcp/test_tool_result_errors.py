# SPDX-License-Identifier: MIT
"""Portable offline tests of the active auditor's error propagation.

Fixtures are literal completed replies. No local manifest, stage, editor,
_Session constructor, transport, native tool, or socket is invoked.
"""
import json
import unittest
from unittest.mock import Mock

from tools.unreal_mcp import asset_receipt_audit as active_audit
from tools.unreal_mcp.transport import TransportFailure


RETAINED_NATIVE_ERROR = "UserRaisedError in ObjectTools.set_properties"
# Observed complete response at create-requests.jsonl JSONRPC id17, HTTP200.
RETAINED_JOURNAL_SHA256 = "b70231cdeadf82c56dc579cbc00ef4f32041e9f1fa96c16ca76226b2d525949b"


class ToolResultErrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = active_audit
        if not issubclass(cls.audit.McpToolError, ValueError):
            raise AssertionError("active McpToolError must preserve the ValueError contract")

    def session(self, result=None, error=None):
        session = object.__new__(self.audit._Session)
        session.exchange = Mock(return_value=result, side_effect=error)
        return session

    def test_observed_native_error_is_complete_but_effects_are_not_proven(self):
        session = self.session({"content": [{"type": "text", "text": RETAINED_NATIVE_ERROR}], "isError": True})
        with self.assertRaises(self.audit.McpToolError) as raised:
            session.meta("call_tool", {"tool_name": "set_properties", "arguments": {"secret": "never-echo-this"}})
        error = raised.exception
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.content_text, RETAINED_NATIVE_ERROR)
        self.assertEqual(error.tool_name, "set_properties")
        self.assertTrue(error.response_complete)
        self.assertFalse(error.operation_effects_proven)
        self.assertEqual(error.data["effect_state"], "unknown")
        self.assertFalse(error.retryable)
        self.assertFalse(error.replayed)
        self.assertNotIn("never-echo-this", str(error))
        self.assertNotIn("secret", json.dumps(error.data))
        session.exchange.assert_called_once()

    def test_valid_success_text_is_unchanged(self):
        for flag in ({}, {"isError": False}):
            session = self.session({"content": [{"type": "text", "text": "exact success text"}], **flag})
            self.assertEqual(session.meta("list_toolsets", {}), "exact success text")

    def test_malformed_content_is_complete_but_never_a_success(self):
        for content in (None, [], [{"type": "text", "text": 123}],
                        [{"text": "missing type"}], [{"type": "image", "data": "hidden"}],
                        [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}]):
            for error_flag in (True, False):
                with self.subTest(content=content, error=error_flag):
                    session = self.session({"content": content, "isError": error_flag})
                    with self.assertRaises(self.audit.McpToolError) as raised:
                        session.meta("call_tool", {"tool_name": "set_properties"})
                    self.assertTrue(raised.exception.data["response_complete"])
                    self.assertFalse(raised.exception.data["content_valid"])
                    self.assertFalse(raised.exception.data["operation_effects_proven"])

    def test_nonboolean_error_flag_cannot_look_successful(self):
        for flag in (0, 1, None, "false"):
            session = self.session({"content": [{"type": "text", "text": "text"}], "isError": flag})
            with self.subTest(flag=flag), self.assertRaises(self.audit.McpToolError):
                session.meta("call_tool", {})

    def test_unknown_transport_failure_is_not_reclassified_as_complete_reply(self):
        failure = TransportFailure("body_read", "partial response", 25, 100)
        session = self.session(error=failure)
        with self.assertRaises(TransportFailure) as raised:
            session.meta("call_tool", {"tool_name": "set_properties"})
        self.assertIs(raised.exception, failure)
        self.assertEqual(failure.data["outcome"], "unknown")
        self.assertNotIsInstance(failure, self.audit.McpToolError)
        session.exchange.assert_called_once()

    def test_returned_diagnostics_and_tool_label_are_bounded(self):
        session = self.session({"content": [{"type": "text", "text": "x" * 3000 + "\x00"}], "isError": True})
        with self.assertRaises(self.audit.McpToolError) as raised:
            session.meta("call_tool", {"tool_name": "y" * 400})
        self.assertEqual(len(raised.exception.tool_name), 160)
        self.assertEqual(len(raised.exception.content_text), 1024)
        self.assertTrue(raised.exception.data["diagnostic_truncated"])


if __name__ == "__main__":
    unittest.main()
