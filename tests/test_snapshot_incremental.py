"""
Tests for askr/qa/snapshot.py's Phase 3.14 additions ("Incremental Snapshot
as Architecture Source" — roadmap.md S1-S7): the reverse-dependency index,
the batched Haiku update (with its two mandatory risk mitigations —
token-count-based call splitting and empty-`purpose` discard-and-rescan),
deleted/renamed file reconciliation, and the deterministic architecture.md
renderer.

call_claude is always mocked — no real network/OAuth calls. Git-dependent
pieces (prune/rename detection) use a real throwaway git repo under
tempfile.TemporaryDirectory() rather than mocking subprocess, so the tests
exercise the actual git plumbing (name-status parsing, similarity scores).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.qa import snapshot


def _run(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _init_repo(path):
    _run("init", "-q", cwd=path)
    _run("config", "user.email", "a@b.com", cwd=path)
    _run("config", "user.name", "a", cwd=path)


def _commit(path, msg="commit"):
    _run("add", "-A", cwd=path)
    _run("commit", "-q", "-m", msg, cwd=path)


def _head(path):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path).decode().strip()


class ResolveImportTests(unittest.TestCase):
    def test_python_absolute_dotted_module_resolves(self):
        file_set = {"./askr/state/config.py"}
        resolved = snapshot._resolve_import("./askr/session/guard.py", "askr.state.config", file_set)
        self.assertEqual(resolved, "./askr/state/config.py")

    def test_python_package_init_resolves(self):
        file_set = {"./askr/qa/__init__.py"}
        resolved = snapshot._resolve_import("./ask.py", "askr.qa", file_set)
        self.assertEqual(resolved, "./askr/qa/__init__.py")

    def test_python_unresolvable_external_module_is_none(self):
        file_set = {"./askr/state/config.py"}
        self.assertIsNone(snapshot._resolve_import("./ask.py", "os.path", file_set))

    def test_js_relative_import_resolves_with_extension(self):
        file_set = {"./src/utils/helpers.ts"}
        resolved = snapshot._resolve_import("./src/app.ts", "./utils/helpers", file_set)
        self.assertEqual(resolved, "./src/utils/helpers.ts")

    def test_js_relative_import_resolves_via_index(self):
        file_set = {"./src/components/index.tsx"}
        resolved = snapshot._resolve_import("./src/app.ts", "./components", file_set)
        self.assertEqual(resolved, "./src/components/index.tsx")

    def test_js_bare_package_import_is_none(self):
        file_set = {"./src/app.ts"}
        self.assertIsNone(snapshot._resolve_import("./src/app.ts", "react", file_set))

    def test_unresolvable_relative_import_is_none(self):
        file_set = {"./src/other.ts"}
        self.assertIsNone(snapshot._resolve_import("./src/app.ts", "./missing", file_set))


class RdepIndexTests(unittest.TestCase):
    """build_full_rdep_index / update_rdep_index_incremental — real files on
    disk so build_graph's own AST/regex import extraction runs for real."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        os.makedirs("pkg", exist_ok=True)
        with open("pkg/base.py", "w") as f:
            f.write("X = 1\n")
        with open("pkg/user.py", "w") as f:
            f.write("import pkg.base\n")
        with open("pkg/other_user.py", "w") as f:
            f.write("from pkg.base import X\n")
        self._rdep_path = os.path.join(self._tmp.name, "rdep.json")
        self._patches = [
            patch.object(snapshot, "RDEP_PATH", self._rdep_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_full_index_maps_file_to_importers(self):
        all_files = ["./pkg/base.py", "./pkg/user.py", "./pkg/other_user.py"]
        idx = snapshot.build_full_rdep_index(all_files)
        self.assertEqual(
            sorted(idx.get("./pkg/base.py", [])),
            ["./pkg/other_user.py", "./pkg/user.py"],
        )

    def test_get_importers_collects_across_multiple_changed_files(self):
        idx = {"./pkg/base.py": ["./pkg/user.py"], "./pkg/other.py": ["./pkg/user2.py"]}
        result = snapshot.get_importers(["./pkg/base.py", "./pkg/other.py"], idx)
        self.assertEqual(result, {"./pkg/user.py", "./pkg/user2.py"})

    def test_incremental_update_only_touches_rescanned_files(self):
        all_files = {"./pkg/base.py", "./pkg/user.py", "./pkg/other_user.py"}
        snapshot.save_rdep_index(snapshot.build_full_rdep_index(list(all_files)))

        # user.py stops importing base.py entirely.
        with open("pkg/user.py", "w") as f:
            f.write("X = 2\n")

        snapshot.update_rdep_index_incremental(["./pkg/user.py"], all_files)
        idx = snapshot.load_rdep_index()
        # other_user.py's edge (untouched file) must survive the incremental update.
        self.assertIn("./pkg/other_user.py", idx.get("./pkg/base.py", []))
        self.assertNotIn("./pkg/user.py", idx.get("./pkg/base.py", []))

    def test_persist_and_reload_rdep_json(self):
        idx = {"./pkg/base.py": ["./pkg/user.py"]}
        snapshot.save_rdep_index(idx)
        self.assertTrue(os.path.exists(self._rdep_path))
        self.assertEqual(snapshot.load_rdep_index(), idx)

    def test_load_rdep_index_missing_file_returns_empty_dict(self):
        self.assertEqual(snapshot.load_rdep_index(), {})


class IsTrackableFileTests(unittest.TestCase):
    """_changed_files_since() (git-diff based) has no extension/SKIP_DIRS
    filter of its own, unlike _collect_files() at init time — sync must
    apply the same criteria itself so a non-code file that shows up in a
    diff (a binary, or .llm_snapshot/*.json if it were ever accidentally
    committed) never gets sent to Haiku as if it were source."""

    def test_python_file_is_trackable(self):
        self.assertTrue(snapshot._is_trackable_file("./askr/qa/snapshot.py"))

    def test_non_code_extension_is_not_trackable(self):
        self.assertFalse(snapshot._is_trackable_file("./.llm_snapshot/summary.json"))
        self.assertFalse(snapshot._is_trackable_file("./assets/logo.png"))

    def test_file_under_skip_dir_is_not_trackable(self):
        self.assertFalse(snapshot._is_trackable_file("./.llm_snapshot/rdep.json.py"))
        self.assertFalse(snapshot._is_trackable_file("./node_modules/pkg/index.js"))

    def test_file_under_hidden_dir_is_not_trackable(self):
        self.assertFalse(snapshot._is_trackable_file("./.github/workflows/ci.py"))


class SplitIntoBatchesTests(unittest.TestCase):
    """Token-count check before batching — split into <=2 calls when the
    estimated total approaches the threshold (roadmap.md Phase 3.14 honest
    risk #1)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._files = []
        for i in range(6):
            path = os.path.join(self._tmp.name, f"f{i}.py")
            with open(path, "w") as f:
                f.write("x = 1\n" * 50)
            self._files.append(path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_small_batch_stays_unsplit(self):
        batches = snapshot._split_into_batches(self._files)
        self.assertEqual(len(batches), 1)
        self.assertEqual(sorted(batches[0]), sorted(self._files))

    def test_large_batch_splits_into_at_most_two(self):
        with patch.object(snapshot, "_TOKEN_SPLIT_THRESHOLD", 10):
            batches = snapshot._split_into_batches(self._files)
        self.assertLessEqual(len(batches), 2)
        self.assertGreater(len(batches), 1)
        # every file accounted for exactly once, none dropped or duplicated
        all_files_out = sorted(f for b in batches for f in b)
        self.assertEqual(all_files_out, sorted(self._files))

    def test_empty_input_returns_no_batches(self):
        self.assertEqual(snapshot._split_into_batches([]), [])


class UpdateSnapshotBatchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        os.makedirs(".llm_snapshot", exist_ok=True)
        self._summary_path = os.path.join(self._tmp.name, ".llm_snapshot", "summary.json")
        self._patches = [patch.object(snapshot, "SUMMARY_PATH", self._summary_path)]
        for p in self._patches:
            p.start()
        self._files = []
        for name in ("a.py", "b.py"):
            with open(name, "w") as f:
                f.write("x = 1\n")
            self._files.append(f"./{name}")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def _write_existing_summary(self, entries):
        with open(self._summary_path, "w") as f:
            json.dump(entries, f)

    def test_successful_batch_updates_all_files(self):
        batch_response = json.dumps([
            {"file": "./a.py", "purpose": "does a", "importance_score": 7},
            {"file": "./b.py", "purpose": "does b", "importance_score": 4},
        ])
        with patch.object(snapshot, "call_claude", return_value=batch_response) as mock_call:
            result = snapshot.update_snapshot_batch(self._files)
        mock_call.assert_called_once()
        self.assertEqual(sorted(result["updated"]), ["./a.py", "./b.py"])
        self.assertEqual(result["rescanned"], [])
        self.assertEqual(result["dropped"], [])
        with open(self._summary_path) as f:
            saved = {e["file"]: e for e in json.load(f)}
        self.assertEqual(saved["./a.py"]["purpose"], "does a")
        self.assertEqual(saved["./b.py"]["purpose"], "does b")

    def test_empty_purpose_entry_is_discarded_and_rescanned(self):
        batch_response = json.dumps([
            {"file": "./a.py", "purpose": "does a", "importance_score": 7},
            {"file": "./b.py", "purpose": "", "importance_score": 4},  # corrupted
        ])
        rescan_response = json.dumps({"file": "./b.py", "purpose": "does b (rescanned)", "importance_score": 5})

        with patch.object(snapshot, "call_claude", side_effect=[batch_response, rescan_response]):
            result = snapshot.update_snapshot_batch(self._files)

        self.assertIn("./a.py", result["updated"])
        self.assertIn("./b.py", result["updated"])
        self.assertEqual(result["rescanned"], ["./b.py"])
        self.assertEqual(result["dropped"], [])
        with open(self._summary_path) as f:
            saved = {e["file"]: e for e in json.load(f)}
        self.assertEqual(saved["./b.py"]["purpose"], "does b (rescanned)")

    def test_missing_file_in_batch_response_is_rescanned(self):
        # Batch response silently drops b.py entirely (truncation, model
        # skipped it, etc.) — must be treated the same as an empty purpose.
        batch_response = json.dumps([{"file": "./a.py", "purpose": "does a", "importance_score": 7}])
        rescan_response = json.dumps({"file": "./b.py", "purpose": "does b (rescanned)", "importance_score": 5})
        with patch.object(snapshot, "call_claude", side_effect=[batch_response, rescan_response]):
            result = snapshot.update_snapshot_batch(self._files)
        self.assertEqual(result["rescanned"], ["./b.py"])

    def test_still_empty_after_rescan_is_dropped_not_stored(self):
        batch_response = json.dumps([{"file": "./a.py", "purpose": "does a", "importance_score": 7}])
        rescan_response = json.dumps({"file": "./b.py", "purpose": "", "importance_score": 5})
        with patch.object(snapshot, "call_claude", side_effect=[batch_response, rescan_response]):
            result = snapshot.update_snapshot_batch(self._files)
        self.assertEqual(result["dropped"], ["./b.py"])
        with open(self._summary_path) as f:
            saved = {e["file"] for e in json.load(f)}
        self.assertNotIn("./b.py", saved)

    def test_malformed_json_response_falls_back_to_individual_rescan(self):
        rescan_a = json.dumps({"file": "./a.py", "purpose": "a rescanned", "importance_score": 5})
        rescan_b = json.dumps({"file": "./b.py", "purpose": "b rescanned", "importance_score": 5})
        with patch.object(snapshot, "call_claude", side_effect=["not json at all", rescan_a, rescan_b]):
            result = snapshot.update_snapshot_batch(self._files)
        self.assertEqual(sorted(result["rescanned"]), ["./a.py", "./b.py"])

    def test_preserves_score_of_untouched_pre_existing_entry(self):
        self._write_existing_summary([{"file": "./c.py", "purpose": "existing", "_score": 0.9}])
        with open("c.py", "w") as f:
            f.write("y = 1\n")
        batch_response = json.dumps([{"file": "./a.py", "purpose": "does a", "importance_score": 7}])
        with patch.object(snapshot, "call_claude", side_effect=[batch_response]):
            snapshot.update_snapshot_batch(["./a.py"])
        with open(self._summary_path) as f:
            saved = {e["file"]: e for e in json.load(f)}
        self.assertEqual(saved["./c.py"]["_score"], 0.9)

    def test_nonexistent_files_are_skipped(self):
        result = snapshot.update_snapshot_batch(["./does_not_exist.py"])
        self.assertEqual(result, {"updated": [], "rescanned": [], "dropped": []})


class PruneDeletedEntriesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        os.makedirs(".llm_snapshot", exist_ok=True)
        self._summary_path = os.path.join(self._tmp.name, ".llm_snapshot", "summary.json")
        self._rdep_path = os.path.join(self._tmp.name, ".llm_snapshot", "rdep.json")
        self._patches = [
            patch.object(snapshot, "SUMMARY_PATH", self._summary_path),
            patch.object(snapshot, "RDEP_PATH", self._rdep_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_removes_entry_for_file_missing_from_disk(self):
        with open("present.py", "w") as f:
            f.write("x = 1\n")
        with open(self._summary_path, "w") as f:
            json.dump([
                {"file": "./present.py", "purpose": "here"},
                {"file": "./gone.py", "purpose": "gone"},
            ], f)
        removed = snapshot.prune_deleted_entries()
        self.assertEqual(removed, ["./gone.py"])
        with open(self._summary_path) as f:
            remaining = {e["file"] for e in json.load(f)}
        self.assertEqual(remaining, {"./present.py"})

    def test_uncommitted_deletion_is_still_caught(self):
        # This is the exact gap `git ls-files` has (it only reflects the
        # staged index): a file removed from the working tree but never
        # `git rm`'d/committed still appears in `git ls-files` output, so
        # detection must not depend on it. os.path.exists doesn't have this
        # gap.
        _init_repo(self._tmp.name)
        with open("tracked.py", "w") as f:
            f.write("x = 1\n")
        _commit(self._tmp.name)
        os.remove("tracked.py")
        with open(self._summary_path, "w") as f:
            json.dump([{"file": "./tracked.py", "purpose": "was here"}], f)
        removed = snapshot.prune_deleted_entries()
        self.assertEqual(removed, ["./tracked.py"])

    def test_new_uncommitted_file_is_not_pruned(self):
        with open("brand_new.py", "w") as f:
            f.write("x = 1\n")
        with open(self._summary_path, "w") as f:
            json.dump([{"file": "./brand_new.py", "purpose": "new"}], f)
        removed = snapshot.prune_deleted_entries()
        self.assertEqual(removed, [])

    def test_no_deletions_returns_empty_and_leaves_files_untouched(self):
        with open("a.py", "w") as f:
            f.write("x = 1\n")
        original = [{"file": "./a.py", "purpose": "here", "_score": 0.5}]
        with open(self._summary_path, "w") as f:
            json.dump(original, f)
        removed = snapshot.prune_deleted_entries()
        self.assertEqual(removed, [])
        with open(self._summary_path) as f:
            self.assertEqual(json.load(f), original)

    def test_removed_files_dropped_from_rdep_index(self):
        with open("present.py", "w") as f:
            f.write("x = 1\n")
        with open(self._summary_path, "w") as f:
            json.dump([
                {"file": "./present.py", "purpose": "here"},
                {"file": "./gone.py", "purpose": "gone"},
            ], f)
        snapshot.save_rdep_index({
            "./gone.py": ["./present.py"],
            "./present.py": ["./gone.py"],
        })
        snapshot.prune_deleted_entries()
        idx = snapshot.load_rdep_index()
        self.assertNotIn("./gone.py", idx)
        self.assertNotIn("./gone.py", idx.get("./present.py", []))


class RenameDetectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)
        _init_repo(self._tmp.name)
        os.makedirs(".llm_snapshot", exist_ok=True)
        self._summary_path = os.path.join(self._tmp.name, ".llm_snapshot", "summary.json")
        self._rdep_path = os.path.join(self._tmp.name, ".llm_snapshot", "rdep.json")
        self._patches = [
            patch.object(snapshot, "SUMMARY_PATH", self._summary_path),
            patch.object(snapshot, "RDEP_PATH", self._rdep_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_pure_rename_is_detected_with_full_similarity(self):
        with open("old_name.py", "w") as f:
            f.write("def foo():\n    return 1\n" * 5)
        _commit(self._tmp.name)
        before = _head(self._tmp.name)
        _run("mv", "old_name.py", "new_name.py", cwd=self._tmp.name)
        _commit(self._tmp.name, "rename")
        after = _head(self._tmp.name)

        renames = snapshot._git_renames_since(before, after)
        self.assertEqual(len(renames), 1)
        old, new, score = renames[0]
        self.assertEqual(old, "./old_name.py")
        self.assertEqual(new, "./new_name.py")
        self.assertEqual(score, 100)

    def test_apply_renames_relocates_entry_preserving_purpose(self):
        with open(self._summary_path, "w") as f:
            json.dump([{"file": "./old_name.py", "purpose": "original purpose", "_score": 0.7}], f)
        needs_rescan = snapshot.apply_renames([("./old_name.py", "./new_name.py", 100)])
        self.assertEqual(needs_rescan, [])
        with open(self._summary_path) as f:
            entries = {e["file"]: e for e in json.load(f)}
        self.assertNotIn("./old_name.py", entries)
        self.assertEqual(entries["./new_name.py"]["purpose"], "original purpose")
        self.assertEqual(entries["./new_name.py"]["_score"], 0.7)

    def test_rename_with_content_change_is_queued_for_rescan(self):
        with open(self._summary_path, "w") as f:
            json.dump([{"file": "./old_name.py", "purpose": "stale purpose"}], f)
        needs_rescan = snapshot.apply_renames([("./old_name.py", "./new_name.py", 87)])
        self.assertEqual(needs_rescan, ["./new_name.py"])

    def test_rename_relocates_rdep_index_edges(self):
        snapshot.save_rdep_index({"./old_name.py": ["./importer.py"]})
        snapshot.apply_renames([("./old_name.py", "./new_name.py", 100)])
        idx = snapshot.load_rdep_index()
        self.assertNotIn("./old_name.py", idx)
        self.assertEqual(idx.get("./new_name.py"), ["./importer.py"])

    def test_rename_updates_importer_references_pointing_at_old_path(self):
        # old_name.py used to import target.py; after rename its importer
        # entry in target.py's reverse-dep list must follow it.
        snapshot.save_rdep_index({"./target.py": ["./old_name.py"]})
        snapshot.apply_renames([("./old_name.py", "./new_name.py", 100)])
        idx = snapshot.load_rdep_index()
        self.assertEqual(idx.get("./target.py"), ["./new_name.py"])

    def test_rename_with_no_prior_entry_is_queued_for_rescan(self):
        # Renamed file has no existing snapshot entry (e.g. snapshot built
        # after the rename already happened) — treat it like a new file.
        needs_rescan = snapshot.apply_renames([("./old_name.py", "./new_name.py", 100)])
        self.assertEqual(needs_rescan, ["./new_name.py"])

    def test_empty_renames_list_is_a_no_op(self):
        self.assertEqual(snapshot.apply_renames([]), [])


class RenderArchitectureMdTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._rdep_path = os.path.join(self._tmp.name, "rdep.json")
        self._patch = patch.object(snapshot, "RDEP_PATH", self._rdep_path)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_empty_entries_returns_empty_string(self):
        self.assertEqual(snapshot.render_architecture_md([]), "")

    def test_groups_by_top_level_directory(self):
        entries = [
            {"file": "./askr/qa/snapshot.py", "purpose": "snapshot builder", "_score": 0.5},
            {"file": "./ask.py", "purpose": "entry point", "_score": 0.9},
        ]
        rendered = snapshot.render_architecture_md(entries)
        self.assertIn("## askr/", rendered)
        self.assertIn("## (root)/", rendered)
        self.assertIn("snapshot builder", rendered)
        self.assertIn("entry point", rendered)

    def test_high_importer_count_is_tagged_core_shared(self):
        snapshot.save_rdep_index({"./askr/state/config.py": ["a.py", "b.py", "c.py"]})
        entries = [{"file": "./askr/state/config.py", "purpose": "config", "_score": 0.5}]
        rendered = snapshot.render_architecture_md(entries)
        self.assertIn("core/shared", rendered)

    def test_low_importer_count_is_not_tagged(self):
        snapshot.save_rdep_index({"./askr/state/config.py": ["a.py"]})
        entries = [{"file": "./askr/state/config.py", "purpose": "config", "_score": 0.5}]
        rendered = snapshot.render_architecture_md(entries)
        self.assertNotIn("core/shared", rendered)


class LoadArchitectureFromSnapshotTests(unittest.TestCase):
    """askr/state/reader.py's load_architecture() — S6: reads snapshot
    entries directly instead of a maintained architecture.md file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def test_falls_back_to_legacy_file_when_no_snapshot(self):
        from askr.state import reader as reader_mod
        legacy_path = os.path.join(self._tmp.name, "architecture.md")
        with open(legacy_path, "w") as f:
            f.write("# Architecture\n\nLegacy content.\n")
        with patch.object(reader_mod, "_load_snapshot_entries", return_value={}), \
             patch.object(reader_mod, "state_path", return_value=legacy_path):
            result = reader_mod.load_architecture()
        self.assertIn("Legacy content", result)

    def test_uses_snapshot_entries_when_present(self):
        from askr.state import reader as reader_mod
        entries = {"./a.py": {"file": "./a.py", "purpose": "does a", "_score": 0.5}}
        with patch.object(reader_mod, "_load_snapshot_entries", return_value=entries):
            result = reader_mod.load_architecture()
        self.assertIn("does a", result)
        self.assertIn("./a.py", result)


if __name__ == "__main__":
    unittest.main()
