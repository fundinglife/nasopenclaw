import json
import os
import re
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGS_DIR = os.path.join(PROJECT_ROOT, "configs")

# JSONC files use JS object syntax (unquoted keys, trailing commas)
JSONC_FILES = {"openclaw.a.json", "openclaw.o.json"}
STRICT_JSON_FILES = {"openclaw.g.json", "openclaw.z.json", "openclaw.all.json"}
ALL_CONFIG_FILES = JSONC_FILES | STRICT_JSON_FILES


def strip_jsonc(text):
    """Strip // and /* */ comments from JSON text."""
    result = []
    i = 0
    in_string = False
    while i < len(text):
        if in_string and text[i] == '\\':
            result.append(text[i:i+2])
            i += 2
            continue
        if text[i] == '"':
            in_string = not in_string
            result.append(text[i])
            i += 1
            continue
        if not in_string:
            if text[i:i+2] == '//':
                while i < len(text) and text[i] != '\n':
                    i += 1
                continue
            if text[i:i+2] == '/*':
                i += 2
                while i < len(text) and text[i:i+2] != '*/':
                    i += 1
                i += 2
                continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def read_config(name):
    with open(os.path.join(CONFIGS_DIR, name), encoding="utf-8") as f:
        return f.read()


def parse_strict_config(name):
    raw = read_config(name)
    return json.loads(strip_jsonc(raw))


class TestConfigFilesExist(unittest.TestCase):

    def test_all_config_files_exist(self):
        for name in ALL_CONFIG_FILES:
            path = os.path.join(CONFIGS_DIR, name)
            self.assertTrue(os.path.exists(path), f"Missing config: {name}")


class TestStrictJsonConfigs(unittest.TestCase):
    """Tests for configs that use strict JSON (g, z, all)."""

    def test_g_parses(self):
        parse_strict_config("openclaw.g.json")

    def test_z_parses(self):
        parse_strict_config("openclaw.z.json")

    def test_all_parses(self):
        parse_strict_config("openclaw.all.json")

    def test_g_has_required_keys(self):
        cfg = parse_strict_config("openclaw.g.json")
        self.assertIn("gateway", cfg)
        self.assertIn("port", cfg["gateway"])
        self.assertIn("models", cfg)
        self.assertIn("providers", cfg["models"])
        self.assertIn("agents", cfg)
        self.assertIn("channels", cfg)
        self.assertIn("whatsapp", cfg["channels"])

    def test_z_has_required_keys(self):
        cfg = parse_strict_config("openclaw.z.json")
        self.assertIn("gateway", cfg)
        self.assertIn("models", cfg)
        self.assertIn("agents", cfg)
        self.assertIn("channels", cfg)

    def test_all_has_required_keys(self):
        cfg = parse_strict_config("openclaw.all.json")
        self.assertIn("gateway", cfg)
        self.assertIn("models", cfg)
        self.assertIn("agents", cfg)
        self.assertIn("channels", cfg)

    def test_gateway_ports(self):
        for name, expected_port in [("openclaw.g.json", 18789),
                                     ("openclaw.z.json", 18789),
                                     ("openclaw.all.json", 18795)]:
            cfg = parse_strict_config(name)
            self.assertEqual(cfg["gateway"]["port"], expected_port,
                             f"{name} has wrong port")

    def test_provider_names(self):
        g = parse_strict_config("openclaw.g.json")
        self.assertIn("cliproxy", g["models"]["providers"])
        z = parse_strict_config("openclaw.z.json")
        self.assertIn("anthropic", z["models"]["providers"])
        a = parse_strict_config("openclaw.all.json")
        self.assertIn("cliproxy", a["models"]["providers"])

    def test_all_config_has_multiple_models(self):
        cfg = parse_strict_config("openclaw.all.json")
        models = cfg["models"]["providers"]["cliproxy"]["models"]
        self.assertGreaterEqual(len(models), 6, "openclaw.all.json should have 6+ models")

    def test_whatsapp_uses_env_var(self):
        for name in STRICT_JSON_FILES:
            cfg = parse_strict_config(name)
            allow_from = cfg["channels"]["whatsapp"]["allowFrom"]
            self.assertIn("${WHATSAPP_NUMBER}", allow_from,
                          f"{name} allowFrom should reference WHATSAPP_NUMBER")

    def test_whatsapp_dm_policy_allowlist(self):
        for name in STRICT_JSON_FILES:
            cfg = parse_strict_config(name)
            self.assertEqual(cfg["channels"]["whatsapp"]["dmPolicy"], "allowlist",
                             f"{name} should use allowlist dmPolicy")


class TestJsoncConfigs(unittest.TestCase):
    """Tests for configs that use JS object syntax (a, o)."""

    def test_a_file_readable(self):
        raw = read_config("openclaw.a.json")
        self.assertGreater(len(raw), 0)

    def test_o_file_readable(self):
        raw = read_config("openclaw.o.json")
        self.assertGreater(len(raw), 0)

    def test_a_has_comments(self):
        raw = read_config("openclaw.a.json")
        self.assertTrue(raw.lstrip().startswith("//"), "a.json should start with // comment")

    def test_o_has_comments(self):
        raw = read_config("openclaw.o.json")
        self.assertTrue(raw.lstrip().startswith("//"), "o.json should start with // comment")

    def test_a_contains_structural_keys(self):
        raw = read_config("openclaw.a.json")
        for key in ["gateway", "models", "agents", "channels", "whatsapp"]:
            self.assertIn(key, raw, f"openclaw.a.json missing key reference: {key}")

    def test_o_contains_structural_keys(self):
        raw = read_config("openclaw.o.json")
        for key in ["gateway", "models", "agents", "channels", "whatsapp"]:
            self.assertIn(key, raw, f"openclaw.o.json missing key reference: {key}")

    def test_a_references_anthropic(self):
        raw = read_config("openclaw.a.json")
        self.assertIn("anthropic", raw.lower())

    def test_o_references_openai(self):
        raw = read_config("openclaw.o.json")
        self.assertIn("openai", raw.lower())


class TestNoHardcodedSecrets(unittest.TestCase):

    def test_no_real_api_keys_in_configs(self):
        """Ensure configs only use ${VAR} references, not real keys."""
        patterns = [
            r'sk-ant-api\d{2}-[A-Za-z0-9]',   # Anthropic key pattern
            r'sk-[A-Za-z0-9]{20,}',             # OpenAI key pattern
            r'AIzaSy[A-Za-z0-9_-]{30,}',        # Google API key pattern
        ]
        for name in ALL_CONFIG_FILES:
            raw = read_config(name)
            for pat in patterns:
                matches = re.findall(pat, raw)
                self.assertEqual(len(matches), 0,
                                 f"{name} contains what looks like a real API key: {matches}")


if __name__ == "__main__":
    unittest.main()
