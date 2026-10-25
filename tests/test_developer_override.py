from askr.state import config


def test_env_override_wins(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text('{"developer": "alice"}')
    monkeypatch.setattr(config, "CONFIG_PATH", str(cfg))
    monkeypatch.setenv("ASKR_DEVELOPER", "slack-bob")
    assert config.load_developer() == "slack-bob"


def test_falls_back_to_config(monkeypatch, tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text('{"developer": "alice"}')
    monkeypatch.setattr(config, "CONFIG_PATH", str(cfg))
    monkeypatch.delenv("ASKR_DEVELOPER", raising=False)
    assert config.load_developer() == "alice"


def test_blank_override_ignored(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("ASKR_DEVELOPER", "  ")
    assert config.load_developer() == "dev"
