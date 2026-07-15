"""
Tests for usage_api.fetch_model_context_window() — the live Models API
lookup used to populate model_windows.py's cache on a genuine miss.
Authenticates via Claude Code's own OAuth session (same credential source
as get_quota_status()), not a separate ANTHROPIC_API_KEY, so every failure
mode here (no token, network error, malformed response) must fail open
(return None) rather than raise — this runs from the daemon's poll loop,
which must never crash on a bad lookup.
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import usage_api


def _mock_response(payload: dict):
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = False
    return cm


class FetchModelContextWindowTests(unittest.TestCase):
    def test_no_token_returns_none_without_network_call(self):
        with patch.object(usage_api, "_get_access_token", return_value=None), \
             patch("urllib.request.urlopen") as mock_urlopen:
            result = usage_api.fetch_model_context_window("claude-sonnet-5")
            self.assertIsNone(result)
            mock_urlopen.assert_not_called()

    def test_successful_lookup_returns_max_input_tokens(self):
        with patch.object(usage_api, "_get_access_token", return_value="tok"), \
             patch("urllib.request.urlopen", return_value=_mock_response(
                 {"id": "claude-sonnet-5", "max_input_tokens": 1_000_000, "max_tokens": 128_000}
             )):
            result = usage_api.fetch_model_context_window("claude-sonnet-5")
            self.assertEqual(result, 1_000_000)

    def test_missing_max_input_tokens_field_returns_none(self):
        with patch.object(usage_api, "_get_access_token", return_value="tok"), \
             patch("urllib.request.urlopen", return_value=_mock_response({"id": "claude-sonnet-5"})):
            result = usage_api.fetch_model_context_window("claude-sonnet-5")
            self.assertIsNone(result)

    def test_zero_max_input_tokens_returns_none(self):
        # Falsy-but-present value must not be treated as a valid window.
        with patch.object(usage_api, "_get_access_token", return_value="tok"), \
             patch("urllib.request.urlopen", return_value=_mock_response({"max_input_tokens": 0})):
            result = usage_api.fetch_model_context_window("claude-sonnet-5")
            self.assertIsNone(result)

    def test_network_error_returns_none_not_raise(self):
        with patch.object(usage_api, "_get_access_token", return_value="tok"), \
             patch("urllib.request.urlopen", side_effect=OSError("network down")):
            result = usage_api.fetch_model_context_window("claude-sonnet-5")
            self.assertIsNone(result)

    def test_malformed_json_response_returns_none(self):
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = b"not json{{{"
        cm.__exit__.return_value = False
        with patch.object(usage_api, "_get_access_token", return_value="tok"), \
             patch("urllib.request.urlopen", return_value=cm):
            result = usage_api.fetch_model_context_window("claude-sonnet-5")
            self.assertIsNone(result)

    def test_request_targets_correct_model_url(self):
        captured = {}

        def _capture(req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = req.headers
            return _mock_response({"max_input_tokens": 1_000_000})

        with patch.object(usage_api, "_get_access_token", return_value="tok-123"), \
             patch("urllib.request.urlopen", side_effect=_capture):
            usage_api.fetch_model_context_window("claude-sonnet-5")

        self.assertEqual(captured["url"], "https://api.anthropic.com/v1/models/claude-sonnet-5")
        self.assertEqual(captured["headers"].get("Authorization"), "Bearer tok-123")


if __name__ == "__main__":
    unittest.main()
