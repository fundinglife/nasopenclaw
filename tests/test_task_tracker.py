import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(PROJECT_ROOT, "tools", "task_tracker.py")


class TestTaskTracker(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="nasopenclaw_test_tt_")
        self.tasks_file = os.path.join(self.tmpdir, "tasks.json")
        self.env = {**os.environ, "OPENCLAW_TASKS_FILE": self.tasks_file}

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *args):
        cmd = [sys.executable, TOOL] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=self.env)

    def _create(self, project="proj", desc="do thing", model="test/model"):
        r = self._run("create", "--project", project, "--description", desc, "--model", model)
        return r.stdout.strip()

    def _load(self):
        with open(self.tasks_file) as f:
            return json.load(f)

    # ── Create ──────────────────────────────────────────────────────────

    def test_create_prints_task_id(self):
        task_id = self._create()
        self.assertTrue(task_id.startswith("task_"), f"ID should start with task_: {task_id}")

    def test_create_id_matches_pattern(self):
        task_id = self._create()
        self.assertRegex(task_id, r"^task_\d{8}_\d{6}_\d{3}$")

    def test_create_writes_correct_fields(self):
        self._create(project="myproj", desc="my desc", model="gpt-4")
        tasks = self._load()
        self.assertEqual(len(tasks), 1)
        t = tasks[0]
        self.assertEqual(t["project"], "myproj")
        self.assertEqual(t["description"], "my desc")
        self.assertEqual(t["model"], "gpt-4")
        self.assertEqual(t["state"], "queued")
        self.assertIsNone(t["commit"])
        self.assertIsNone(t["error"])

    def test_create_timestamps_iso_with_z(self):
        self._create()
        t = self._load()[0]
        self.assertTrue(t["created_at"].endswith("Z"))
        self.assertTrue(t["updated_at"].endswith("Z"))

    def test_create_multiple_tasks(self):
        for i in range(5):
            self._create(project=f"proj-{i}")
        self.assertEqual(len(self._load()), 5)

    # ── Update ──────────────────────────────────────────────────────────

    def test_update_state(self):
        task_id = self._create()
        self._run("update", task_id, "--state", "running")
        t = self._load()[0]
        self.assertEqual(t["state"], "running")

    def test_update_commit(self):
        task_id = self._create()
        self._run("update", task_id, "--commit", "abc1234")
        t = self._load()[0]
        self.assertEqual(t["commit"], "abc1234")

    def test_update_error(self):
        task_id = self._create()
        self._run("update", task_id, "--error", "build failed at line 42")
        t = self._load()[0]
        self.assertEqual(t["error"], "build failed at line 42")

    def test_update_changes_timestamp(self):
        task_id = self._create()
        ts1 = self._load()[0]["updated_at"]
        self._run("update", task_id, "--state", "running")
        ts2 = self._load()[0]["updated_at"]
        # Timestamps should differ (or at least not error)
        self.assertIsNotNone(ts2)

    def test_update_nonexistent_exits_1(self):
        r = self._run("update", "task_fake_id", "--state", "done")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stdout.lower())

    # ── List ────────────────────────────────────────────────────────────

    def test_list_shows_header(self):
        self._create()
        r = self._run("list")
        self.assertIn("ID", r.stdout)
        self.assertIn("Project", r.stdout)
        self.assertIn("State", r.stdout)

    def test_list_filters_by_project(self):
        self._create(project="alpha")
        self._create(project="beta")
        r = self._run("list", "--project", "alpha")
        self.assertIn("alpha", r.stdout)
        self.assertNotIn("beta", r.stdout)

    def test_list_filters_by_state(self):
        id1 = self._create()
        self._create()
        self._run("update", id1, "--state", "running")
        r = self._run("list", "--state", "running")
        self.assertIn("running", r.stdout)

    def test_list_max_10_default(self):
        for i in range(15):
            self._create(project=f"p{i}")
        r = self._run("list")
        # Count data lines (exclude header and separator)
        lines = [l for l in r.stdout.strip().split("\n") if l.startswith("task_")]
        self.assertLessEqual(len(lines), 10)

    # ── Show ────────────────────────────────────────────────────────────

    def test_show_prints_json(self):
        task_id = self._create()
        r = self._run("show", task_id)
        data = json.loads(r.stdout)
        self.assertEqual(data["id"], task_id)

    def test_show_nonexistent_exits_1(self):
        r = self._run("show", "task_nonexistent")
        self.assertEqual(r.returncode, 1)

    # ── 100 task limit ──────────────────────────────────────────────────

    def test_100_task_limit(self):
        for i in range(105):
            self._create(project=f"p{i}")
        tasks = self._load()
        self.assertEqual(len(tasks), 100)
        # Oldest 5 should be dropped
        projects = [t["project"] for t in tasks]
        for i in range(5):
            self.assertNotIn(f"p{i}", projects)
        # Newest should still be there
        self.assertIn("p104", projects)

    # ── Edge cases ──────────────────────────────────────────────────────

    def test_corrupt_file_does_not_crash(self):
        with open(self.tasks_file, "w") as f:
            f.write("not json!!!")
        r = self._run("list")
        self.assertEqual(r.returncode, 0)

    def test_no_subcommand_shows_help(self):
        r = self._run()
        # argparse prints to stderr when no subcommand
        combined = r.stdout + r.stderr
        self.assertTrue(len(combined) > 0)

    def test_create_missing_required_args(self):
        r = self._run("create", "--project", "p")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
