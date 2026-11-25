import os
from unittest.mock import patch

from askr.voice import tasks


def test_hidden_claude_never_gets_an_api_key():
    # 2026-11-02: an inherited ANTHROPIC_API_KEY (from askr's .env) made every
    # background task fail with "Credit balance is too low".
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-x", "ANTHROPIC_AUTH_TOKEN": "t", "PATH": "/bin"}):
        env = tasks.claude_env()
    assert "ANTHROPIC_API_KEY" not in env and "ANTHROPIC_AUTH_TOKEN" not in env
    assert env["PATH"] == "/bin"


def test_run_passes_the_clean_env(tmp_path):
    class Proc:
        returncode, stdout, stderr = 0, '{"result": "391", "is_error": false}', ""

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-x"}), \
         patch.object(tasks.subprocess, "run", return_value=Proc()) as run:
        ok, result = tasks._run_claude("17*23?", str(tmp_path))
    assert (ok, result) == (True, "391")
    assert "ANTHROPIC_API_KEY" not in run.call_args.kwargs["env"]


def test_resolve_project_by_name_or_path(tmp_path):
    proj = tmp_path / "Leaps"
    proj.mkdir()
    with patch.object(tasks.os.path, "expanduser", side_effect=lambda p: p.replace("~", str(tmp_path))):
        assert tasks.resolve_project("~/Desktop/missing") == ""
    assert tasks.resolve_project(str(proj)) == str(proj)
    assert tasks.resolve_project("") == ""


def test_heavy_work_runs_inside_the_project(tmp_path):
    seen = []
    t = tasks.Tasks(runner=lambda task, folder, cwd: (seen.append(cwd), (True, "ok"))[1])
    with patch.object(tasks, "TASKS_DIR", str(tmp_path / "logs")):
        t.start("refactor the backend", cwd=str(tmp_path))
        t.finished.get(timeout=5)
        t.start("look something up")
        t.finished.get(timeout=5)
    assert seen[0] == str(tmp_path)                       # in the project
    assert seen[1].startswith(str(tmp_path / "logs"))     # no project: its own folder
