import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(PROJECT_ROOT, "tools", "load_project_context.py")


class TestLoadProjectContext(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="nasopenclaw_test_lpc_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *args):
        cmd = [sys.executable, TOOL] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    def _write_json(self, filename, data):
        with open(os.path.join(self.tmpdir, filename), "w") as f:
            json.dump(data, f)

    def _write_file(self, filename, content):
        path = os.path.join(self.tmpdir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    # ── Happy path ──────────────────────────────────────────────────────

    def test_full_output_with_all_fields(self):
        self._write_json(".factory.json", {
            "type": "astro-website", "db": "sqld", "locked": True,
            "db_info": {"namespaces": {"dev": "proj_dev", "prod": "proj_prod"}},
            "environments": {
                "development": "https://d-proj.example.com",
                "production": "https://proj.example.com",
            },
        })
        self._write_json(".tailor.json", {
            "template": "directory", "version": "2.0.0", "applied_at": "2026-01-01",
        })
        r = self._run(self.tmpdir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("=== PROJECT CONTEXT ===", r.stdout)
        self.assertIn("=== END PROJECT CONTEXT ===", r.stdout)
        self.assertIn("Type: astro-website", r.stdout)
        self.assertIn("Template: directory (v2.0.0, applied 2026-01-01)", r.stdout)
        self.assertIn("Database: sqld (namespaces: proj_dev/proj_prod)", r.stdout)
        self.assertIn("Locked: true", r.stdout)
        self.assertIn("https://d-proj.example.com", r.stdout)
        self.assertIn("https://proj.example.com", r.stdout)

    def test_project_name_from_directory(self):
        self._write_json(".factory.json", {"type": "test"})
        r = self._run(self.tmpdir)
        dirname = os.path.basename(self.tmpdir)
        self.assertIn(f"Project: {dirname}", r.stdout)

    # ── Missing files ───────────────────────────────────────────────────

    def test_missing_factory_json_uses_defaults(self):
        self._write_json(".tailor.json", {"template": "t", "version": "1", "applied_at": "x"})
        r = self._run(self.tmpdir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Type: unknown", r.stdout)
        self.assertIn("Database: none", r.stdout)
        self.assertIn("Locked: false", r.stdout)

    def test_missing_tailor_json_uses_defaults(self):
        self._write_json(".factory.json", {"type": "astro-website"})
        r = self._run(self.tmpdir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Template: unknown (vunknown, applied unknown)", r.stdout)

    def test_empty_directory_shows_defaults(self):
        r = self._run(self.tmpdir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Type: unknown", r.stdout)
        self.assertIn("Database: none", r.stdout)
        self.assertIn("src/components/", r.stdout)  # default conventions

    # ── Folder conventions ──────────────────────────────────────────────

    def test_custom_ownership_overrides_defaults(self):
        self._write_json(".factory.json", {"type": "astro-website"})
        self._write_file("AGENT_OWNERSHIP.md", "custom/dir/ — My custom rule\nanother/ — Rule 2")
        r = self._run(self.tmpdir)
        self.assertIn("custom/dir/", r.stdout)
        self.assertIn("another/", r.stdout)
        self.assertNotIn("src/components/", r.stdout)  # defaults suppressed

    def test_no_ownership_shows_default_conventions(self):
        self._write_json(".factory.json", {"type": "astro-website"})
        r = self._run(self.tmpdir)
        self.assertIn("src/components/", r.stdout)
        self.assertIn("src/pages/", r.stdout)
        self.assertIn("LOCKED", r.stdout)

    # ── Locked field ────────────────────────────────────────────────────

    def test_locked_true(self):
        self._write_json(".factory.json", {"type": "t", "locked": True})
        r = self._run(self.tmpdir)
        self.assertIn("Locked: true", r.stdout)

    def test_locked_false(self):
        self._write_json(".factory.json", {"type": "t", "locked": False})
        r = self._run(self.tmpdir)
        self.assertIn("Locked: false", r.stdout)

    def test_locked_missing_defaults_false(self):
        self._write_json(".factory.json", {"type": "t"})
        r = self._run(self.tmpdir)
        self.assertIn("Locked: false", r.stdout)

    # ── Database ────────────────────────────────────────────────────────

    def test_db_none(self):
        self._write_json(".factory.json", {"type": "t", "db": "none"})
        r = self._run(self.tmpdir)
        self.assertIn("Database: none", r.stdout)

    def test_db_with_namespaces(self):
        self._write_json(".factory.json", {
            "type": "t", "db": "sqld",
            "db_info": {"namespaces": {"dev": "ns_dev", "stg": "ns_stg"}},
        })
        r = self._run(self.tmpdir)
        self.assertIn("Database: sqld", r.stdout)
        self.assertIn("ns_dev/ns_stg", r.stdout)

    def test_db_without_namespaces(self):
        self._write_json(".factory.json", {"type": "t", "db": "sqld"})
        r = self._run(self.tmpdir)
        self.assertIn("Database: sqld (namespaces: unknown)", r.stdout)

    # ── Environments ────────────────────────────────────────────────────

    def test_environments_present(self):
        self._write_json(".factory.json", {
            "type": "t",
            "environments": {"development": "https://dev.test", "production": "https://prod.test"},
        })
        r = self._run(self.tmpdir)
        self.assertIn("Environments:", r.stdout)
        self.assertIn("https://dev.test", r.stdout)
        self.assertIn("https://prod.test", r.stdout)

    def test_no_environments_section_absent(self):
        self._write_json(".factory.json", {"type": "t"})
        r = self._run(self.tmpdir)
        self.assertNotIn("Environments:", r.stdout)

    # ── Error handling ──────────────────────────────────────────────────

    def test_no_args_exits_1(self):
        r = self._run()
        self.assertEqual(r.returncode, 1)

    def test_malformed_json_does_not_crash(self):
        with open(os.path.join(self.tmpdir, ".factory.json"), "w") as f:
            f.write("{{{bad json")
        r = self._run(self.tmpdir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Type: unknown", r.stdout)

    # ── Non-astro project type ──────────────────────────────────────────

    def test_non_astro_type(self):
        self._write_json(".factory.json", {"type": "python-api"})
        r = self._run(self.tmpdir)
        self.assertIn("Type: python-api", r.stdout)


if __name__ == "__main__":
    unittest.main()
