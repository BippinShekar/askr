import os
from unittest.mock import patch

from askr.voice import mac, tasks
from askr.voice.agent import Turn
from askr.voice.talker import Reply

from tests.test_voice_loop import _loop


def test_blocklist_refuses_even_when_confirmed():
    for cmd in ["sudo rm -rf /", "rm -rf ~", "rm -rf / ", "diskutil eraseDisk JHFS+ x disk2",
                "dd if=/dev/zero of=/dev/disk2", "shutdown -h now"]:
        assert mac.blocked(cmd), cmd
        assert mac.run_risky("shell", cmd).startswith("error: refused")
    for cmd in ["df -h ~", "rm -rf ./build", "ls ~/Downloads"]:
        assert not mac.blocked(cmd), cmd


def test_prepare_risky_summaries():
    assert mac.prepare_risky("shell", "df -h ~") == ("run df in the terminal", "")
    assert mac.prepare_risky("applescript", 'tell app "Finder" to empty trash')[0] == "run an AppleScript"
    assert mac.prepare_risky("shell", "sudo reboot")[1].startswith("error: refused")


class _ScriptedAgent:
    """Asks to run `df -h` on the first turn; summarizes the output on the second."""

    def __init__(self, loop):
        self.loop, self.calls = loop, []

    def respond(self, utterance, extra=""):
        self.calls.append(utterance)
        if len(self.calls) == 1:
            self.loop._tool_handlers()["run_on_mac"]({"kind": "shell", "code": "df -h ~"})
            return Turn("Want me to check disk space? OK?")
        return Turn("You've got 120 gigs free.")

    def note_update(self, spoken):
        pass


def _confirm_loop(tmp_path, answer):
    loop, talker, speaker, _ = _loop(tmp_path, "askr how much disk space do I have", Reply("x"))
    loop.agent = _ScriptedAgent(loop)
    loop.handle_utterance(b"a")
    loop.transcriber.text = answer
    with patch.object(mac, "run_risky", return_value="Filesystem Size Avail\n/dev/disk3 460G 120G") as run:
        loop.handle_utterance(b"a")
    return loop, speaker, run


def test_risky_action_runs_only_after_a_yes(tmp_path):
    loop, speaker, run = _confirm_loop(tmp_path, "yeah go ahead")
    run.assert_called_once_with("shell", "df -h ~", "")
    assert speaker.said == ["Want me to check disk space? OK?", "You've got 120 gigs free."]
    assert "Output:" in loop.agent.calls[-1]


def test_no_skips_it(tmp_path):
    loop, speaker, run = _confirm_loop(tmp_path, "no")
    run.assert_not_called()
    assert speaker.said[-1] == "Okay, skipped it."


def test_moving_on_drops_it(tmp_path):
    loop, speaker, run = _confirm_loop(tmp_path, "actually what's the weather")
    run.assert_not_called()
    assert loop._pending_action is None


def test_create_project_folder(tmp_path):
    with patch.object(tasks.os.path, "expanduser", side_effect=lambda p: p.replace("~", str(tmp_path))):
        path = tasks.create_project("screenshot renamer!")
    assert path == str(tmp_path / "Desktop" / "screenshot-renamer") and os.path.isdir(path)
