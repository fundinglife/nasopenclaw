import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(PROJECT_ROOT, "tools", "validate_shared_files.py")


class TestValidateSharedFiles(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="nasopenclaw_test_vsf_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, mode, project_path=None):
        args = [sys.executable, TOOL, mode]
        if project_path:
            args.append(project_path)
        return subprocess.run(args, capture_output=True, text=True, timeout=30)

    def _write(self, relpath, content="default content"):
        fullpath = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(fullpath, mode) as f:
            f.write(content)

    def _snapshot_path(self):
        return os.path.join(self.tmpdir, ".openclaw_snapshot.json")

    def _read_snapshot(self):
        with open(self._snapshot_path()) as f:
            return json.load(f)

    def _sha256(self, content):
        if isinstance(content, str):
            content = content.encode()
        return hashlib.sha256(content).hexdigest()

    # ── Snapshot mode ───────────────────────────────────────────────────

    def test_snapshot_creates_file(self):
        self._write("astro.config.mjs", "export default {}")
        self._write("tsconfig.json", "{}")
        r = self._run("snapshot", self.tmpdir)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(self._snapshot_path()))

    def test_snapshot_contains_correct_hashes(self):
        content = "export default {}"
        self._write("astro.config.mjs", content)
        self._run("snapshot", self.tmpdir)
        snap = self._read_snapshot()
        self.assertEqual(snap["astro.config.mjs"], self._sha256(content))

    def test_snapshot_walks_directories_recursively(self):
        self._write("src/lib/util.ts", "a")
        self._write("src/lib/sub/deep.ts", "b")
        self._write("src/pages/index.astro", "c")
        self._run("snapshot", self.tmpdir)
        snap = self._read_snapshot()
        self.assertIn("src/lib/util.ts", snap)
        self.assertIn("src/lib/sub/deep.ts", snap)
        self.assertIn("src/pages/index.astro", snap)

    def test_snapshot_normalizes_paths_forward_slash(self):
        self._write("src/lib/file.ts", "x")
        self._run("snapshot", self.tmpdir)
        snap = self._read_snapshot()
        for key in snap:
            self.assertNotIn("\\", key, f"Path contains backslash: {key}")

    def test_non_protected_files_excluded(self):
        self._write("src/components/foo.ts", "component")
        self._write("src/services/bar.ts", "service")
        self._write("package.json", "{}")
        self._write("astro.config.mjs", "config")
        self._run("snapshot", self.tmpdir)
        snap = self._read_snapshot()
        self.assertNotIn("src/components/foo.ts", snap)
        self.assertNotIn("src/services/bar.ts", snap)
        self.assertNotIn("package.json", snap)
        self.assertIn("astro.config.mjs", snap)

    def test_empty_project_empty_snapshot(self):
        self._run("snapshot", self.tmpdir)
        snap = self._read_snapshot()
        self.assertEqual(snap, {})

    def test_binary_file_hashing(self):
        binary_data = bytes(range(256))
        self._write("src/lib/binary.wasm", binary_data)
        self._run("snapshot", self.tmpdir)
        snap = self._read_snapshot()
        self.assertEqual(snap["src/lib/binary.wasm"], self._sha256(binary_data))

    def test_hash_deterministic(self):
        self._write("astro.config.mjs", "same content")
        self._run("snapshot", self.tmpdir)
        snap1 = self._read_snapshot()
        os.remove(self._snapshot_path())
        self._run("snapshot", self.tmpdir)
        snap2 = self._read_snapshot()
        self.assertEqual(snap1, snap2)

    # ── Gitignore handling ──────────────────────────────────────────────

    def test_snapshot_creates_gitignore_if_missing(self):
        self._run("snapshot", self.tmpdir)
        gitignore = os.path.join(self.tmpdir, ".gitignore")
        self.assertTrue(os.path.exists(gitignore))
        with open(gitignore) as f:
            self.assertIn(".openclaw_snapshot.json", f.read())

    def test_snapshot_appends_to_existing_gitignore(self):
        self._write(".gitignore", "node_modules/\n")
        self._run("snapshot", self.tmpdir)
        with open(os.path.join(self.tmpdir, ".gitignore")) as f:
            content = f.read()
        self.assertIn("node_modules/", content)
        self.assertIn(".openclaw_snapshot.json", content)

    def test_snapshot_no_duplicate_gitignore_entry(self):
        self._write(".gitignore", ".openclaw_snapshot.json\n")
        self._run("snapshot", self.tmpdir)
        with open(os.path.join(self.tmpdir, ".gitignore")) as f:
            content = f.read()
        self.assertEqual(content.count(".openclaw_snapshot.json"), 1)

    def test_snapshot_adds_newline_before_entry(self):
        self._write(".gitignore", "node_modules/")  # no trailing newline
        self._run("snapshot", self.tmpdir)
        with open(os.path.join(self.tmpdir, ".gitignore")) as f:
            content = f.read()
        self.assertNotIn("node_modules/.openclaw", content)  # must be on separate line

    # ── Check mode ──────────────────────────────────────────────────────

    def test_check_no_changes_exits_0(self):
        self._write("astro.config.mjs", "original")
        self._run("snapshot", self.tmpdir)
        r = self._run("check", self.tmpdir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("All protected files unchanged", r.stdout)

    def test_check_detects_modified_file(self):
        self._write("astro.config.mjs", "original")
        self._run("snapshot", self.tmpdir)
        self._write("astro.config.mjs", "modified!")
        r = self._run("check", self.tmpdir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("astro.config.mjs", r.stdout)

    def test_check_detects_added_file(self):
        self._write("src/lib/existing.ts", "a")
        self._run("snapshot", self.tmpdir)
        self._write("src/lib/new_file.ts", "b")
        r = self._run("check", self.tmpdir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("new_file.ts", r.stdout)

    def test_check_detects_removed_file(self):
        self._write("tsconfig.json", "{}")
        self._run("snapshot", self.tmpdir)
        os.remove(os.path.join(self.tmpdir, "tsconfig.json"))
        r = self._run("check", self.tmpdir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("tsconfig.json", r.stdout)

    def test_check_no_snapshot_exits_1(self):
        r = self._run("check", self.tmpdir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Snapshot file", r.stdout)

    # ── Error handling ──────────────────────────────────────────────────

    def test_unknown_mode_exits_1(self):
        r = self._run("foobar", self.tmpdir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Unknown mode", r.stdout)

    def test_no_args_exits_1(self):
        r = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
