"""
Tests for per-session scratch handovers (2026-07-16).

create_handover_only() runs on EVERY turn of EVERY concurrently-active
session and used to write straight to the shared handover_<dev>.json/.md —
so N sessions x M turns each meant the canonical file flip-flopped between
sessions' content constantly, with no merge. Confirmed in production: a
degraded, single-session handover hiding 21 uncommitted files' worth of
sibling sessions' work.

Scratch files are per-session (handover_<dev>_<session_id>.scratch.json) so
no session can ever clobber another's. Only the smart-merge step in
create_checkpoint() ever writes the canonical file.
"""

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.state import writer


class ScratchHandoverPathTests(unittest.TestCase):
    def test_path_is_session_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path_a = writer.scratch_handover_path("dev", "sess-a", state_dir=tmp)
            path_b = writer.scratch_handover_path("dev", "sess-b", state_dir=tmp)
        self.assertNotEqual(path_a, path_b)
        self.assertIn("sess-a", path_a)
        self.assertIn("sess-b", path_b)

    def test_path_never_collides_with_canonical_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            scratch = writer.scratch_handover_path("dev", "sess-a", state_dir=tmp)
        self.assertNotEqual(os.path.basename(scratch), "handover_dev.json")
        self.assertNotEqual(os.path.basename(scratch), "handover_dev.md")


class WriteSessionScratchHandoverTests(unittest.TestCase):
    def test_writes_valid_json_and_never_touches_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = writer.write_session_scratch_handover({"task": "did a thing"}, "dev", "sess-a", state_dir=tmp)
            with open(path) as f:
                self.assertEqual(json.load(f), {"task": "did a thing"})
            self.assertFalse(os.path.exists(os.path.join(tmp, "handover_dev.json")))

    def test_two_sessions_writing_do_not_clobber_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer.write_session_scratch_handover({"task": "session A's work"}, "dev", "sess-a", state_dir=tmp)
            writer.write_session_scratch_handover({"task": "session B's work"}, "dev", "sess-b", state_dir=tmp)

            with open(writer.scratch_handover_path("dev", "sess-a", state_dir=tmp)) as f:
                self.assertEqual(json.load(f)["task"], "session A's work")
            with open(writer.scratch_handover_path("dev", "sess-b", state_dir=tmp)) as f:
                self.assertEqual(json.load(f)["task"], "session B's work")


class LoadFreshSiblingScratchesTests(unittest.TestCase):
    def test_excludes_own_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer.write_session_scratch_handover({"task": "mine"}, "dev", "sess-self", state_dir=tmp)
            writer.write_session_scratch_handover({"task": "sibling"}, "dev", "sess-other", state_dir=tmp)

            siblings = writer.load_fresh_sibling_scratches("dev", "sess-self", state_dir=tmp)
        self.assertEqual(len(siblings), 1)
        self.assertEqual(siblings[0]["task"], "sibling")

    def test_excludes_stale_scratches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = writer.write_session_scratch_handover({"task": "old"}, "dev", "sess-old", state_dir=tmp)
            old_time = time.time() - 7200  # 2 hours ago, past the 1h default
            os.utime(path, (old_time, old_time))
            writer.write_session_scratch_handover({"task": "fresh"}, "dev", "sess-fresh", state_dir=tmp)

            siblings = writer.load_fresh_sibling_scratches("dev", "sess-self", state_dir=tmp)
        self.assertEqual(len(siblings), 1)
        self.assertEqual(siblings[0]["task"], "fresh")

    def test_no_siblings_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            siblings = writer.load_fresh_sibling_scratches("dev", "sess-self", state_dir=tmp)
        self.assertEqual(siblings, [])

    def test_corrupt_scratch_file_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = writer.scratch_handover_path("dev", "sess-bad", state_dir=tmp)
            with open(path, "w") as f:
                f.write("not valid json{{{")
            siblings = writer.load_fresh_sibling_scratches("dev", "sess-self", state_dir=tmp)
        self.assertEqual(siblings, [])


class CleanupStaleScratchesTests(unittest.TestCase):
    def test_removes_only_stale_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = writer.write_session_scratch_handover({"task": "fresh"}, "dev", "sess-fresh", state_dir=tmp)
            stale = writer.write_session_scratch_handover({"task": "stale"}, "dev", "sess-stale", state_dir=tmp)
            old_time = time.time() - 7200
            os.utime(stale, (old_time, old_time))

            removed = writer.cleanup_stale_scratches("dev", state_dir=tmp)

            self.assertEqual(removed, 1)
            self.assertTrue(os.path.exists(fresh))
            self.assertFalse(os.path.exists(stale))


if __name__ == "__main__":
    unittest.main()
