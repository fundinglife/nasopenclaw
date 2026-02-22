import os
import json
import sys
from datetime import datetime

def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def read_file(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python load_project_context.py <project_path>")
        sys.exit(1)

    project_path = sys.argv[1]
    
    # Path variations
    factory_json_path = os.path.join(project_path, ".factory.json")
    tailor_json_path = os.path.join(project_path, ".tailor.json")
    capabilities_path = os.path.join(project_path, "SYSTEM_CAPABILITIES.md")
    ownership_path = os.path.join(project_path, "AGENT_OWNERSHIP.md")

    # Load data
    factory_data = load_json(factory_json_path) or {}
    tailor_data = load_json(tailor_json_path) or {}
    capabilities = read_file(capabilities_path)
    ownership = read_file(ownership_path)

    project_name = os.path.basename(project_path.rstrip(os.sep))
    
    # Extract fields with defaults
    proj_type = factory_data.get("type", "unknown")
    db_info = factory_data.get("db", "none")
    db_namespaces = factory_data.get("db_info", {}).get("namespaces", {})
    locked = factory_data.get("locked", False)
    
    template_name = tailor_data.get("template", "unknown")
    template_version = tailor_data.get("version", "unknown")
    applied_at = tailor_data.get("applied_at", "unknown")

    environments = factory_data.get("environments", {})

    # Start Output
    print("=== PROJECT CONTEXT ===")
    print(f"Project: {project_name}")
    print(f"Type: {proj_type}")
    print(f"Template: {template_name} (v{template_version}, applied {applied_at})")
    
    if db_info != "none":
        ns_str = "/".join(db_namespaces.values()) if db_namespaces else "unknown"
        print(f"Database: {db_info} (namespaces: {ns_str})")
    else:
        print("Database: none")
        
    print(f"Locked: {'true' if locked else 'false'} (push to development only — never staging or master)")
    print("")
    
    if environments:
        print("Environments:")
        for env, url in environments.items():
            print(f"  {env.capitalize().ljust(12)}: {url}")
        print("")

    if ownership:
        print("Folder conventions:")
        for line in ownership.splitlines():
            if line.strip():
                print(f"  {line.strip()}")
    else:
        # Default conventions if no ownership file
        print("Folder conventions:")
        print("  src/components/  — UI components")
        print("  src/services/    — Pure TypeScript business logic")
        print("  src/content/     — Schemas, data, config")
        print("  src/pages/       — LOCKED (pre-written by template, do not modify)")
        print("  src/lib/         — LOCKED (shared utilities, request changes explicitly)")
        print("  astro.config.mjs — LOCKED (set by template, do not modify)")
    
    print("")
    print("Git: Always commit to development branch. Never push to staging or master.")
    print("=== END PROJECT CONTEXT ===")

if __name__ == "__main__":
    main()
