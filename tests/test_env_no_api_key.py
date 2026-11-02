import os
from unittest.mock import patch

from askr.utils import env


def test_env_files_never_export_an_anthropic_api_key(tmp_path):
    # Everything bills the Claude subscription; a key from .env would be
    # inherited by every claude askr launches and take precedence over it.
    f = tmp_path / ".env"
    f.write_text("ANTHROPIC_API_KEY=sk-ant-from-file\nANTHROPIC_AUTH_TOKEN=t\nOPENAI_API_KEY=sk-openai\n")
    with patch.dict(os.environ, {"ASKR_ENV": str(f)}, clear=False):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
        os.environ.pop("OPENAI_API_KEY", None)
        env.load()
        assert "ANTHROPIC_API_KEY" not in os.environ
        assert "ANTHROPIC_AUTH_TOKEN" not in os.environ
        assert os.environ["OPENAI_API_KEY"] == "sk-openai"


def test_ask_uses_the_subscription_transport():
    from askr.qa import pipeline
    from askr.clients import claude
    assert pipeline.call_claude is claude.call_claude
    assert pipeline.call_claude_web is claude.call_claude_web
    assert not hasattr(claude, "call_claude_api_key")
