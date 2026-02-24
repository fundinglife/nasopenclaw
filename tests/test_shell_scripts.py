import os
import subprocess
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRIPTS = {
    "setup-nas": os.path.join(PROJECT_ROOT, "scripts", "setup-nas.sh"),
    "update": os.path.join(PROJECT_ROOT, "scripts", "update.sh"),
    "install-nas": os.path.join(PROJECT_ROOT, "scripts", "install-nas.sh"),
    "install": os.path.join(PROJECT_ROOT, "install.sh"),
    "uninstall": os.path.join(PROJECT_ROOT, "uninstall.sh"),
}


@unittest.skipIf(os.name == "nt", "bash -n cannot resolve Windows paths")
class TestShellScriptSyntax(unittest.TestCase):
    """Validate shell scripts parse without errors (bash -n)."""

    def _check_syntax(self, script_path):
        r = subprocess.run(["bash", "-n", script_path],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0,
                         f"Syntax error in {os.path.basename(script_path)}: {r.stderr}")

    def test_setup_nas_syntax(self):
        self._check_syntax(SCRIPTS["setup-nas"])

    def test_update_syntax(self):
        self._check_syntax(SCRIPTS["update"])

    def test_install_nas_syntax(self):
        self._check_syntax(SCRIPTS["install-nas"])

    def test_install_syntax(self):
        self._check_syntax(SCRIPTS["install"])

    def test_uninstall_syntax(self):
        self._check_syntax(SCRIPTS["uninstall"])


class TestShellScriptStructure(unittest.TestCase):
    """Validate structural expectations of shell scripts via text analysis."""

    @classmethod
    def setUpClass(cls):
        cls.contents = {}
        for key, path in SCRIPTS.items():
            with open(path, encoding="utf-8") as f:
                cls.contents[key] = f.read()

    def test_all_have_shebang(self):
        for key, content in self.contents.items():
            self.assertTrue(content.startswith("#!/bin/bash"),
                            f"{key} missing #!/bin/bash shebang")

    def test_all_use_set_e(self):
        # update.sh intentionally omits set -e — it must continue
        # when no container is running to print usage guidance
        for key, content in self.contents.items():
            if key == "update":
                continue
            self.assertIn("set -e", content,
                          f"{key} should use 'set -e' for fail-fast")

    # ── Flag handling ───────────────────────────────────────────────────

    def test_install_nas_has_help_flag(self):
        self.assertIn("--help", self.contents["install-nas"])
        self.assertIn("-h", self.contents["install-nas"])

    def test_install_nas_has_no_start_flag(self):
        self.assertIn("--no-start", self.contents["install-nas"])

    def test_install_nas_has_skip_onboard_flag(self):
        self.assertIn("--skip-onboard", self.contents["install-nas"])

    def test_install_has_help_flag(self):
        self.assertIn("--help", self.contents["install"])

    def test_install_has_pull_only_flag(self):
        self.assertIn("--pull-only", self.contents["install"])

    def test_install_has_skip_onboard_flag(self):
        self.assertIn("--skip-onboard", self.contents["install"])

    def test_install_has_no_start_flag(self):
        self.assertIn("--no-start", self.contents["install"])

    def test_install_has_install_dir_flag(self):
        self.assertIn("--install-dir", self.contents["install"])

    def test_uninstall_has_help_flag(self):
        self.assertIn("--help", self.contents["uninstall"])

    def test_uninstall_has_keep_data_flag(self):
        self.assertIn("--keep-data", self.contents["uninstall"])

    def test_uninstall_has_keep_image_flag(self):
        self.assertIn("--keep-image", self.contents["uninstall"])

    def test_uninstall_has_force_flag(self):
        self.assertIn("--force", self.contents["uninstall"])

    # ── Content checks ──────────────────────────────────────────────────

    def test_update_loops_over_all_profiles(self):
        content = self.contents["update"]
        self.assertIn("a o g z all", content,
                      "update.sh should loop over all profiles")

    def test_setup_nas_creates_data_dirs(self):
        content = self.contents["setup-nas"]
        for d in ["data-a", "data-o", "data-g", "data-z", "data-all", "workspace", "configs"]:
            self.assertIn(d, content,
                          f"setup-nas.sh should create {d}")

    def test_setup_nas_references_correct_image(self):
        self.assertIn("ghcr.io/phioranex/openclaw-docker:latest",
                      self.contents["setup-nas"])

    def test_update_references_correct_image(self):
        self.assertIn("ghcr.io/phioranex/openclaw-docker:latest",
                      self.contents["update"])


if __name__ == "__main__":
    unittest.main()
