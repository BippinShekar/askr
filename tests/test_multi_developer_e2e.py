"""
E2E test for multi-developer collaboration on a shared askr_state/ directory.

Models two developers (alice, bob) on separate machines who each clone the
repo and run `askr init`, then push/pull askr_state/ via git. Since git is
not exercised here, both developers' init/goal/decision writes are applied
to the same directory in sequence to verify the on-disk contract that makes
union-merge safe: per-developer files never collide, shared append-only
files never lose entries, and team.json accumulates without duplicates.

Scope: init + shared-state accumulation only. Does NOT cover task-queue
claim/execution or the --dangerously-skip-permissions approval gate -- those
remain open, separately tracked blockers (queue drain system, permission
model) and are out of scope here.

This was a hard zero in test coverage (see askr_state/decisions.jsonl:
"team-add flow exists but lacks validation; multi-dev state synchronization
is untested") and a named blocker to confident deployment on a teammate's
machine.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.cli.askr import _register_team_member, _create_skeleton_files
from askr.state.config import state_path
from askr.state import goals
from askr.session.checkpoint import _append_failed_approaches, _write_decisions_from_handover


class MultiDeveloperE2ETests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        self.state_dir = os.path.join(self.project_dir, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)

        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def _team_members(self):
        with open(state_path("team.json")) as f:
            return json.load(f)["members"]

    def test_two_developers_init_without_clobbering_each_other(self):
        _register_team_member("alice")
        _create_skeleton_files("alice")

        _register_team_member("bob")
        _create_skeleton_files("bob")

        self.assertEqual(self._team_members(), ["alice", "bob"])

        # Per-developer files are isolated
        for dev in ("alice", "bob"):
            self.assertTrue(os.path.exists(state_path(f"handover_{dev}.md")))
            self.assertTrue(os.path.exists(state_path(f"implementation_{dev}.jsonl")))
            self.assertTrue(os.path.exists(state_path(f"tasks/queue_{dev}.jsonl")))

        with open(state_path("handover_alice.md")) as f:
            self.assertIn("alice", f.read())
        with open(state_path("handover_bob.md")) as f:
            self.assertIn("bob", f.read())

        # Shared file is created once, not duplicated per developer
        self.assertTrue(os.path.exists(state_path("goals.jsonl")))

    def test_rerunning_init_for_one_developer_does_not_touch_the_others_files(self):
        _register_team_member("alice")
        _create_skeleton_files("alice")
        _register_team_member("bob")
        _create_skeleton_files("bob")

        bob_handover_path = state_path("handover_bob.md")
        with open(bob_handover_path) as f:
            bob_before = f.read()
        bob_mtime_before = os.path.getmtime(bob_handover_path)

        # alice re-runs `askr init` on her machine after bob already pushed his state
        _register_team_member("alice")
        created, skipped = _create_skeleton_files("alice")

        self.assertEqual(self._team_members(), ["alice", "bob"])  # no duplicate roster entry
        self.assertIn("handover_alice.md", skipped)

        with open(bob_handover_path) as f:
            bob_after = f.read()
        self.assertEqual(bob_before, bob_after)
        self.assertEqual(os.path.getmtime(bob_handover_path), bob_mtime_before)

    def test_shared_goals_file_accumulates_across_developers_without_loss(self):
        _create_skeleton_files("alice")

        goals.add_goal("alice's goal")
        goals.add_goal("bob's goal")

        open_goals = goals.load_open_goals()
        self.assertIn("alice's goal", open_goals)
        self.assertIn("bob's goal", open_goals)
        self.assertEqual(len(open_goals), 2)

    def test_shared_decisions_and_failed_approaches_accumulate_across_developers(self):
        alice_handover = {
            "decisions": [{"decision": "use JSONL for shared state", "reason": "union-merge friendly"}],
            "failed_approaches": [{"approach": "single shared handover.md", "reason": "machine-specific content collided"}],
        }
        bob_handover = {
            "decisions": [{"decision": "per-dev handover files", "reason": "avoids cross-machine clobbering"}],
            "failed_approaches": [{"approach": "global developer name", "reason": "two machines need independent identities"}],
        }

        _write_decisions_from_handover(alice_handover, self.state_dir, "alice")
        _write_decisions_from_handover(bob_handover, self.state_dir, "bob")
        _append_failed_approaches(alice_handover, self.state_dir)
        _append_failed_approaches(bob_handover, self.state_dir)

        with open(os.path.join(self.state_dir, "decisions.jsonl")) as f:
            decision_lines = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(decision_lines), 2)
        self.assertEqual({d["dev"] for d in decision_lines}, {"alice", "bob"})

        with open(os.path.join(self.state_dir, "failed_approaches.md")) as f:
            failed_text = f.read()
        self.assertIn("single shared handover.md", failed_text)
        self.assertIn("global developer name", failed_text)


if __name__ == "__main__":
    unittest.main()
