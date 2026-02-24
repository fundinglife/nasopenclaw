import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(PROJECT_ROOT, "tools", "run_tests.py")


class TestRunTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="nasopenclaw_test_rt_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *args):
        cmd = [sys.executable, TOOL] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    def _make_project(self, scripts):
        pkg = {"name": "test-proj", "scripts": scripts}
        with open(os.path.join(self.tmpdir, "package.json"), "w") as f:
            json.dump(pkg, f)

    # ── Single suite ────────────────────────────────────────────────────

    def test_unit_suite_pass(self):
        self._make_project({"test:unit": "echo unit-ok && exit 0"})
        r = self._run(self.tmpdir, "unit")
        self.assertEqual(r.returncode, 0)
        self.assertIn("passed successfully", r.stdout)

    def test_build_suite_pass(self):
        self._make_project({"build": "echo build-ok && exit 0"})
        r = self._run(self.tmpdir, "build")
        self.assertEqual(r.returncode, 0)
        self.assertIn("passed successfully", r.stdout)

    def test_integration_suite_pass(self):
        self._make_project({"test:integration": "echo int-ok && exit 0"})
        r = self._run(self.tmpdir, "integration")
        self.assertEqual(r.returncode, 0)
        self.assertIn("passed successfully", r.stdout)

    def test_unit_suite_fail(self):
        self._make_project({"test:unit": "echo FAIL && exit 1"})
        r = self._run(self.tmpdir, "unit")
        self.assertEqual(r.returncode, 1)
        self.assertIn("failed", r.stdout.lower())

    # ── All suites ──────────────────────────────────────────────────────

    def test_all_suites_pass(self):
        self._make_project({
            "test:unit": "echo u-ok && exit 0",
            "build": "echo b-ok && exit 0",
            "test:integration": "echo i-ok && exit 0",
        })
        r = self._run(self.tmpdir, "all")
        self.assertEqual(r.returncode, 0)
        self.assertIn("All tests passed", r.stdout)

    def test_all_suites_stop_on_first_failure(self):
        self._make_project({
            "test:unit": "echo u-ok && exit 0",
            "build": "echo BUILD-FAIL && exit 1",
            "test:integration": "echo SHOULD-NOT-RUN && exit 0",
        })
        r = self._run(self.tmpdir, "all")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("SHOULD-NOT-RUN", r.stdout)

    def test_all_suites_order_unit_build_integration(self):
        self._make_project({
            "test:unit": "echo STEP1 && exit 0",
            "build": "echo STEP2 && exit 0",
            "test:integration": "echo STEP3 && exit 0",
        })
        r = self._run(self.tmpdir, "all")
        pos1 = r.stdout.find("STEP1")
        pos2 = r.stdout.find("STEP2")
        pos3 = r.stdout.find("STEP3")
        self.assertGreater(pos2, pos1, "build should run after unit")
        self.assertGreater(pos3, pos2, "integration should run after build")

    # ── Output labels ───────────────────────────────────────────────────

    def test_output_includes_suite_labels(self):
        self._make_project({
            "test:unit": "echo ok && exit 0",
            "build": "echo ok && exit 0",
            "test:integration": "echo ok && exit 0",
        })
        r = self._run(self.tmpdir, "all")
        self.assertIn("unit", r.stdout.lower())
        self.assertIn("build", r.stdout.lower())
        self.assertIn("integration", r.stdout.lower())

    # ── Error handling ──────────────────────────────────────────────────

    def test_invalid_suite_rejected(self):
        r = self._run(self.tmpdir, "foobar")
        self.assertNotEqual(r.returncode, 0)

    def test_no_args_exits_error(self):
        r = self._run()
        self.assertNotEqual(r.returncode, 0)

    # ── SSH flag ────────────────────────────────────────────────────────

    def test_ssh_flag_in_output(self):
        self._make_project({"test:unit": "echo ok && exit 0"})
        r = self._run(self.tmpdir, "unit", "--ssh", "user@host")
        self.assertIn("remote", r.stdout.lower())


if __name__ == "__main__":
    unittest.main()
