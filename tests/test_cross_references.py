import os
import re
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(relpath):
    with open(os.path.join(PROJECT_ROOT, relpath), encoding="utf-8") as f:
        return f.read()


class TestComposeConfigConsistency(unittest.TestCase):
    """Verify docker-compose.yml references match actual files."""

    @classmethod
    def setUpClass(cls):
        cls.compose = read_file("docker-compose.yml")

    def test_config_volume_mounts_reference_existing_files(self):
        config_refs = re.findall(r'configs/(openclaw\.[a-z]+\.json)', self.compose)
        for name in config_refs:
            path = os.path.join(PROJECT_ROOT, "configs", name)
            self.assertTrue(os.path.exists(path),
                            f"Compose references configs/{name} but file doesn't exist")

    def test_all_config_files_referenced_in_compose(self):
        """Every config in configs/ should be referenced somewhere in compose."""
        config_dir = os.path.join(PROJECT_ROOT, "configs")
        for name in os.listdir(config_dir):
            if name.endswith(".json"):
                # openclaw.o.json is not mounted (uses onboarding)
                # openclaw.all.json is not mounted (config lives in data-all/)
                if name in ("openclaw.o.json", "openclaw.all.json"):
                    continue
                self.assertIn(name, self.compose,
                              f"configs/{name} exists but is not referenced in compose")


class TestComposeEnvVarConsistency(unittest.TestCase):
    """Verify env vars in docker-compose are defined in .env.example."""

    @classmethod
    def setUpClass(cls):
        cls.compose = read_file("docker-compose.yml")
        cls.env_example = read_file(".env.example")

    def test_env_vars_defined_in_env_example(self):
        # Extract ${VAR} references from compose
        compose_vars = set(re.findall(r'\$\{(\w+)\}', self.compose))
        # Extract VAR= definitions from .env.example
        env_vars = set(re.findall(r'^(\w+)=', self.env_example, re.MULTILINE))
        for var in compose_vars:
            self.assertIn(var, env_vars,
                          f"${{{var}}} used in compose but not defined in .env.example")


class TestReadmeNasConsistency(unittest.TestCase):
    """Verify README-NAS.md references match actual project state."""

    @classmethod
    def setUpClass(cls):
        cls.readme = read_file("README-NAS.md")

    def test_directory_layout_lists_existing_configs(self):
        config_dir = os.path.join(PROJECT_ROOT, "configs")
        for name in os.listdir(config_dir):
            if name.endswith(".json"):
                self.assertIn(name, self.readme,
                              f"configs/{name} not shown in README-NAS.md directory layout")

    def test_provider_table_ports_match_compose(self):
        compose = read_file("docker-compose.yml")
        # Extract expected ports from README table
        port_map = {"a": "18790", "o": "18791", "g": "18792", "z": "18793"}
        for profile, port in port_map.items():
            self.assertIn(port, self.readme,
                          f"Port {port} for profile {profile} not in README-NAS.md")
            self.assertIn(f"{port}:18789", compose,
                          f"Port {port}:18789 not in docker-compose.yml")

    def test_referenced_scripts_exist(self):
        scripts_mentioned = re.findall(r'scripts/(\S+\.sh)', self.readme)
        for script in scripts_mentioned:
            path = os.path.join(PROJECT_ROOT, "scripts", script)
            self.assertTrue(os.path.exists(path),
                            f"README-NAS.md references scripts/{script} but it doesn't exist")


class TestAgentPromptsConsistency(unittest.TestCase):
    """Verify AGENT_PROMPTS.md references tools that exist."""

    @classmethod
    def setUpClass(cls):
        cls.prompts = read_file("AGENT_PROMPTS.md")

    def test_referenced_tools_exist(self):
        tool_names = re.findall(r'tools/(\w+\.py)', self.prompts)
        tools_dir = os.path.join(PROJECT_ROOT, "tools")
        for name in tool_names:
            path = os.path.join(tools_dir, name)
            self.assertTrue(os.path.exists(path),
                            f"AGENT_PROMPTS.md references tools/{name} but it doesn't exist")


class TestGitignoreConsistency(unittest.TestCase):
    """Verify .gitignore doesn't accidentally ignore tracked files."""

    @classmethod
    def setUpClass(cls):
        cls.gitignore = read_file(".gitignore")

    def test_does_not_ignore_configs(self):
        self.assertNotIn("configs/", self.gitignore)

    def test_does_not_ignore_tools(self):
        self.assertNotIn("tools/", self.gitignore)

    def test_does_not_ignore_scripts(self):
        self.assertNotIn("scripts/", self.gitignore)

    def test_ignores_env_file(self):
        self.assertIn(".env", self.gitignore)

    def test_ignores_test_fixtures(self):
        self.assertIn("tests/fixtures/", self.gitignore)


if __name__ == "__main__":
    unittest.main()
