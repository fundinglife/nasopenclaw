import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "validate_config.js")


class TestValidateConfigJS(unittest.TestCase):

    def _run_real(self):
        return subprocess.run(["node", SCRIPT], capture_output=True, text=True, timeout=30)

    # ── Real configs ────────────────────────────────────────────────────

    def test_all_configs_valid_exit_0(self):
        r = self._run_real()
        self.assertEqual(r.returncode, 0, f"stdout: {r.stdout}\nstderr: {r.stderr}")

    def test_jsonc_files_report_skip(self):
        r = self._run_real()
        self.assertIn("openclaw.a.json", r.stdout)
        self.assertIn("JS object syntax (JSONC)", r.stdout)
        self.assertIn("openclaw.o.json", r.stdout)

    def test_strict_json_files_report_primary(self):
        r = self._run_real()
        for name in ["openclaw.g.json", "openclaw.z.json", "openclaw.all.json"]:
            self.assertIn(name, r.stdout)
            # These should show primary= (not JSONC skip)
        self.assertIn("primary=", r.stdout)

    def test_providers_listed_for_strict_files(self):
        r = self._run_real()
        self.assertIn("providers=", r.stdout)

    def test_all_five_configs_appear(self):
        r = self._run_real()
        for name in ["openclaw.a.json", "openclaw.o.json", "openclaw.g.json",
                      "openclaw.z.json", "openclaw.all.json"]:
            self.assertIn(name, r.stdout)

    # ── Failure cases (temp dir copies) ─────────────────────────────────

    def _make_temp_validator(self, configs_dict):
        """Create a temp directory with scripts/validate_config.js and configs/."""
        tmpdir = tempfile.mkdtemp(prefix="nasopenclaw_test_vcj_")
        scripts_dir = os.path.join(tmpdir, "scripts")
        configs_dir = os.path.join(tmpdir, "configs")
        os.makedirs(scripts_dir)
        os.makedirs(configs_dir)
        # Copy the real validator script
        shutil.copy(SCRIPT, os.path.join(scripts_dir, "validate_config.js"))
        # Write test configs
        for name, content in configs_dict.items():
            with open(os.path.join(configs_dir, name), "w") as f:
                f.write(content)
        return tmpdir, os.path.join(scripts_dir, "validate_config.js")

    def test_missing_required_key_reports_invalid(self):
        # Config missing gateway.port
        config = json.dumps({
            "models": {"providers": {"test": {}}},
            "agents": {"defaults": {"model": {"primary": "test/m"}}},
            "channels": {"whatsapp": {}},
        })
        tmpdir, script = self._make_temp_validator({
            "openclaw.g.json": config,
            "openclaw.z.json": config,
            "openclaw.all.json": config,
        })
        try:
            r = subprocess.run(["node", script], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("INVALID", r.stderr)
            self.assertIn("gateway.port", r.stderr)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_broken_json_reports_invalid(self):
        tmpdir, script = self._make_temp_validator({
            "openclaw.g.json": "{{{not json",
            "openclaw.z.json": "{}",
            "openclaw.all.json": "{}",
        })
        try:
            r = subprocess.run(["node", script], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(r.returncode, 0)
            combined = r.stdout + r.stderr
            self.assertIn("INVALID", combined)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_missing_config_file_reports_invalid(self):
        # Only provide 2 of the expected configs
        config = json.dumps({
            "gateway": {"port": 1}, "models": {"providers": {"t": {}}},
            "agents": {"defaults": {"model": {"primary": "t"}}},
            "channels": {"whatsapp": {}},
        })
        tmpdir, script = self._make_temp_validator({
            "openclaw.g.json": config,
            # openclaw.z.json missing
            # openclaw.all.json missing
        })
        try:
            r = subprocess.run(["node", script], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(r.returncode, 0)
            combined = r.stdout + r.stderr
            self.assertIn("INVALID", combined)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
