import io
import json
from unittest.mock import patch

from askr.voice import events
from askr.voice.talker import Reply

from tests.test_voice_loop import _loop


def test_spoken_lines_are_short_and_say_where():
    perm = {"kind": "permission_prompt", "message": "Claude needs your permission to use Bash", "cwd": "/x/grid"}
    assert events.spoken(perm, True) == "It needs your OK to use Bash"
    assert events.spoken(perm, False) == "Over in grid, it needs your OK to use Bash"
    assert events.spoken({"kind": "idle_prompt", "message": "Claude is waiting for your input"}, True) == \
        "It's waiting on you"


def test_drain_takes_each_event_once_and_drops_stale():
    events.post("s1", "permission_prompt", "Claude needs your permission to use Bash")
    assert len(events.drain()) == 1 and events.drain() == []
    events.post("s1", "idle_prompt", "x")
    assert events.drain(now=10 ** 12) == []  # far in the future: stale


def test_loop_speaks_blocking_events_but_not_a_repeat_idle(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "", Reply("x"))
    events.post(loop.session_id, "permission_prompt", "Claude needs your permission to use Bash")
    loop.speak_events()
    assert speaker.said == ["It needs your OK to use Bash"]
    events.post(loop.session_id, "idle_prompt", "Claude is waiting for your input")
    loop.speak_events()                      # it just spoke: "waiting on you" would be a repeat
    assert len(speaker.said) == 1


def test_notification_hook_posts_for_a_running_daemon(tmp_path):
    from askr.hooks import notification
    from askr.voice import daemon
    payload = {"session_id": "s1", "notification_type": "permission_prompt",
               "message": "Claude needs your permission to use Bash", "cwd": str(tmp_path)}
    with patch.object(daemon, "running_pid", return_value=123), \
         patch("sys.stdin", io.StringIO(json.dumps(payload))):
        notification.main()
    (event,) = events.drain()
    assert event["kind"] == "permission_prompt" and event["session_id"] == "s1"
