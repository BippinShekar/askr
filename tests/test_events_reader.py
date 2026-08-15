"""
Tests for askr/state/events_reader.py — reconstructing the session-spawn
tree from events.jsonl for the `askr graph` command (2026-08-15).

trigger_fired rows are the only source of real tree edges (they carry both
session_id and parent_session_id); companion_spawned rows don't know the
child's session_id yet, so they attach to their parent as activity, not a
separate node.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.state import events_reader


class LoadEventsTests(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(events_reader.load_events(os.path.join(tmp, "askr_state")), [])

    def test_reads_valid_jsonl_in_file_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = os.path.join(tmp, "askr_state")
            os.makedirs(state_dir)
            with open(os.path.join(state_dir, "events.jsonl"), "w") as f:
                f.write(json.dumps({"event_type": "trigger_fired", "session_id": "a"}) + "\n")
                f.write(json.dumps({"event_type": "trigger_fired", "session_id": "b"}) + "\n")
            events = events_reader.load_events(state_dir)
            self.assertEqual([e["session_id"] for e in events], ["a", "b"])

    def test_malformed_lines_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = os.path.join(tmp, "askr_state")
            os.makedirs(state_dir)
            with open(os.path.join(state_dir, "events.jsonl"), "w") as f:
                f.write("not json\n")
                f.write(json.dumps({"event_type": "trigger_fired", "session_id": "a"}) + "\n")
            try:
                events = events_reader.load_events(state_dir)
            except Exception as e:
                self.fail(f"load_events raised: {e}")
            self.assertEqual(len(events), 1)

    def test_blank_lines_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = os.path.join(tmp, "askr_state")
            os.makedirs(state_dir)
            with open(os.path.join(state_dir, "events.jsonl"), "w") as f:
                f.write("\n")
                f.write(json.dumps({"event_type": "trigger_fired", "session_id": "a"}) + "\n")
                f.write("\n")
            self.assertEqual(len(events_reader.load_events(state_dir)), 1)


def _trigger(session_id, parent_session_id=None, project_path="/proj", trigger_type="context", **kw):
    return {
        "event_type": "trigger_fired", "session_id": session_id,
        "parent_session_id": parent_session_id, "project_path": project_path,
        "trigger_type": trigger_type, **kw,
    }


def _spawn(parent_session_id, project_path="/proj", trigger_type="context"):
    return {
        "event_type": "companion_spawned", "session_id": None,
        "parent_session_id": parent_session_id, "project_path": project_path,
        "trigger_type": trigger_type,
    }


class BuildSessionTreeTests(unittest.TestCase):
    def test_single_session_no_parent_is_a_root(self):
        tree = events_reader.build_session_tree([_trigger("a")])
        self.assertEqual(tree["roots"], ["a"])
        self.assertEqual(tree["sessions"]["a"]["children"], [])

    def test_parent_child_edge_from_trigger_fired(self):
        tree = events_reader.build_session_tree([
            _trigger("a"),
            _trigger("b", parent_session_id="a"),
        ])
        self.assertEqual(tree["roots"], ["a"])
        self.assertEqual(tree["sessions"]["a"]["children"], ["b"])
        self.assertEqual(tree["sessions"]["b"]["parent_session_id"], "a")

    def test_three_generation_chain(self):
        tree = events_reader.build_session_tree([
            _trigger("a"),
            _trigger("b", parent_session_id="a"),
            _trigger("c", parent_session_id="b"),
        ])
        self.assertEqual(tree["roots"], ["a"])
        self.assertEqual(tree["sessions"]["a"]["children"], ["b"])
        self.assertEqual(tree["sessions"]["b"]["children"], ["c"])
        self.assertEqual(tree["sessions"]["c"]["children"], [])

    def test_orphaned_parent_reference_becomes_its_own_root(self):
        # "a" is referenced as a parent but never itself fired a trigger —
        # must not be silently dropped, must surface as a root instead.
        tree = events_reader.build_session_tree([
            _trigger("b", parent_session_id="a"),
        ])
        self.assertIn("b", tree["roots"])
        self.assertNotIn("a", tree["sessions"])

    def test_companion_spawned_attaches_to_parent_not_a_new_node(self):
        tree = events_reader.build_session_tree([
            _trigger("a"),
            _spawn("a", trigger_type="quota"),
        ])
        self.assertEqual(list(tree["sessions"].keys()), ["a"])
        self.assertEqual(len(tree["sessions"]["a"]["spawns"]), 1)
        self.assertEqual(tree["sessions"]["a"]["spawns"][0]["trigger_type"], "quota")

    def test_companion_spawned_without_matching_trigger_still_creates_parent_node(self):
        # The parent session itself may not have fired ITS OWN trigger yet
        # (e.g. this is its first-ever trigger, captured only as the source
        # of the spawn) — the spawn event alone must still surface it.
        tree = events_reader.build_session_tree([_spawn("a")])
        self.assertIn("a", tree["sessions"])
        self.assertEqual(len(tree["sessions"]["a"]["spawns"]), 1)
        self.assertEqual(tree["sessions"]["a"]["triggers"], [])

    def test_multiple_triggers_for_same_session_all_recorded(self):
        tree = events_reader.build_session_tree([
            _trigger("a", trigger_type="context"),
            _trigger("a", trigger_type="idle"),
        ])
        self.assertEqual(len(tree["sessions"]["a"]["triggers"]), 2)

    def test_project_path_carried_from_first_event_seen(self):
        tree = events_reader.build_session_tree([
            _trigger("a", project_path="/leaps"),
        ])
        self.assertEqual(tree["sessions"]["a"]["project_path"], "/leaps")

    def test_events_missing_session_id_are_ignored_for_trigger_fired(self):
        try:
            tree = events_reader.build_session_tree([
                {"event_type": "trigger_fired", "session_id": None, "parent_session_id": None},
            ])
        except Exception as e:
            self.fail(f"build_session_tree raised: {e}")
        self.assertEqual(tree["sessions"], {})
        self.assertEqual(tree["roots"], [])

    def test_empty_events_returns_empty_tree(self):
        tree = events_reader.build_session_tree([])
        self.assertEqual(tree["sessions"], {})
        self.assertEqual(tree["roots"], [])

    def test_multiple_children_of_the_same_parent(self):
        tree = events_reader.build_session_tree([
            _trigger("a"),
            _trigger("b", parent_session_id="a"),
            _trigger("c", parent_session_id="a"),
        ])
        self.assertEqual(sorted(tree["sessions"]["a"]["children"]), ["b", "c"])


if __name__ == "__main__":
    unittest.main()
