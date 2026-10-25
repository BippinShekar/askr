from askr.session import usage_api


def _no_local_creds(monkeypatch, creds=None):
    monkeypatch.setattr(usage_api.platform, "system", lambda: "Linux")
    monkeypatch.setattr(usage_api, "_read_creds_file", lambda: creds)


def test_env_token_used_when_no_local_creds(monkeypatch):
    _no_local_creds(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat-env")
    assert usage_api._get_access_token() == "sk-ant-oat-env"


def test_creds_file_wins_over_env(monkeypatch):
    _no_local_creds(monkeypatch, '{"claudeAiOauth": {"accessToken": "from-file"}}')
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat-env")
    assert usage_api._get_access_token() == "from-file"


def test_none_when_nothing_available(monkeypatch):
    _no_local_creds(monkeypatch)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    assert usage_api._get_access_token() is None
