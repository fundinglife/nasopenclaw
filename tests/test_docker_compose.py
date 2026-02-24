import os
import re
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE_FILE = os.path.join(PROJECT_ROOT, "docker-compose.yml")


class TestDockerCompose(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(COMPOSE_FILE, encoding="utf-8") as f:
            cls.content = f.read()
        cls.lines = cls.content.splitlines()

    def _service_block(self, service_name):
        """Extract lines belonging to a service block."""
        in_block = False
        indent = 0
        block = []
        for line in self.lines:
            if re.match(rf"^\s+{re.escape(service_name)}:", line):
                in_block = True
                indent = len(line) - len(line.lstrip())
                block.append(line)
                continue
            if in_block:
                if line.strip() == "" or line.startswith(" " * (indent + 1)):
                    block.append(line)
                elif line.strip().startswith("#"):
                    block.append(line)
                else:
                    # Check if this is a new service at same indent
                    cur_indent = len(line) - len(line.lstrip())
                    if cur_indent <= indent and line.strip():
                        break
                    block.append(line)
        return "\n".join(block)

    # ── File basics ─────────────────────────────────────────────────────

    def test_file_exists(self):
        self.assertTrue(os.path.exists(COMPOSE_FILE))

    def test_version_defined(self):
        self.assertIn('version:', self.content)

    # ── Services ────────────────────────────────────────────────────────

    def test_all_services_defined(self):
        for svc in ["nasopenclaw-a", "nasopenclaw-o", "nasopenclaw-g",
                     "nasopenclaw-z", "nasopenclaw-all"]:
            self.assertIn(f"{svc}:", self.content, f"Service {svc} not defined")

    def test_profiles(self):
        expected = {
            "nasopenclaw-a": "a",
            "nasopenclaw-o": "o",
            "nasopenclaw-g": "g",
            "nasopenclaw-z": "z",
            "nasopenclaw-all": "all",
        }
        for svc, profile in expected.items():
            block = self._service_block(svc)
            self.assertIn(f'"{profile}"', block,
                          f"{svc} should have profile '{profile}'")

    def test_container_names_match_services(self):
        for svc in ["nasopenclaw-a", "nasopenclaw-o", "nasopenclaw-g",
                     "nasopenclaw-z", "nasopenclaw-all"]:
            block = self._service_block(svc)
            self.assertIn(f"container_name: {svc}", block)

    # ── Ports ───────────────────────────────────────────────────────────

    def test_port_mappings(self):
        expected = {
            "nasopenclaw-a": "18790:18789",
            "nasopenclaw-o": "18791:18789",
            "nasopenclaw-g": "18792:18789",
            "nasopenclaw-z": "18793:18789",
            "nasopenclaw-all": "18795:18795",
        }
        for svc, port in expected.items():
            block = self._service_block(svc)
            self.assertIn(port, block, f"{svc} should map port {port}")

    def test_no_duplicate_host_ports(self):
        ports = re.findall(r'"(\d+):\d+"', self.content)
        self.assertEqual(len(ports), len(set(ports)),
                         f"Duplicate host ports found: {ports}")

    # ── Image ───────────────────────────────────────────────────────────

    def test_uses_phioranex_image(self):
        self.assertIn("ghcr.io/phioranex/openclaw-docker:latest", self.content)

    # ── Volumes ─────────────────────────────────────────────────────────

    def test_workspace_volume_in_all_services(self):
        for svc in ["nasopenclaw-a", "nasopenclaw-o", "nasopenclaw-g",
                     "nasopenclaw-z", "nasopenclaw-all"]:
            block = self._service_block(svc)
            self.assertIn("/workspace:/home/node/.openclaw/workspace", block,
                          f"{svc} missing workspace volume")

    def test_config_readonly_for_a_g_z(self):
        for svc in ["nasopenclaw-a", "nasopenclaw-g", "nasopenclaw-z"]:
            block = self._service_block(svc)
            self.assertIn("openclaw.json:ro", block,
                          f"{svc} config should be mounted read-only")

    def test_config_files_in_mounts_exist(self):
        """Config filenames referenced in volume mounts should exist on disk."""
        config_refs = re.findall(r'configs/(openclaw\.[a-z]+\.json)', self.content)
        configs_dir = os.path.join(PROJECT_ROOT, "configs")
        for name in config_refs:
            path = os.path.join(configs_dir, name)
            self.assertTrue(os.path.exists(path),
                            f"Config {name} referenced in compose but missing from configs/")

    # ── Commands ────────────────────────────────────────────────────────

    def test_all_services_command_gateway(self):
        for svc in ["nasopenclaw-a", "nasopenclaw-o", "nasopenclaw-g",
                     "nasopenclaw-z", "nasopenclaw-all"]:
            block = self._service_block(svc)
            self.assertIn("gateway", block,
                          f"{svc} should have gateway command")

    # ── Environment variables ───────────────────────────────────────────

    def test_whatsapp_number_in_all_services(self):
        for svc in ["nasopenclaw-a", "nasopenclaw-o", "nasopenclaw-g",
                     "nasopenclaw-z", "nasopenclaw-all"]:
            block = self._service_block(svc)
            self.assertIn("WHATSAPP_NUMBER", block,
                          f"{svc} missing WHATSAPP_NUMBER")

    def test_anthropic_key_in_service_a(self):
        block = self._service_block("nasopenclaw-a")
        self.assertIn("ANTHROPIC_API_KEY", block)

    def test_zai_key_in_service_z(self):
        block = self._service_block("nasopenclaw-z")
        self.assertIn("ZAI_API_KEY", block)

    def test_zai_key_in_service_all(self):
        block = self._service_block("nasopenclaw-all")
        self.assertIn("ZAI_API_KEY", block)

    def test_git_config_in_all_services(self):
        for svc in ["nasopenclaw-a", "nasopenclaw-o", "nasopenclaw-g",
                     "nasopenclaw-z", "nasopenclaw-all"]:
            block = self._service_block(svc)
            self.assertIn("GIT_AUTHOR_NAME", block, f"{svc} missing GIT_AUTHOR_NAME")
            self.assertIn("GIT_AUTHOR_EMAIL", block, f"{svc} missing GIT_AUTHOR_EMAIL")


if __name__ == "__main__":
    unittest.main()
