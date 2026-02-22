import os
import sys
import subprocess
import argparse

SUITES = {
    "unit":        "npm run test:unit",
    "integration": "npm run test:integration",
    "build":       "npm run build",
}

def run_command(cmd, cwd, ssh_target=None):
    if ssh_target:
        # Wrap the command in SSH
        full_cmd = f'ssh {ssh_target} "cd {cwd} && {cmd}"'
        print(f"Executing remote: {cmd} on {ssh_target}")
    else:
        full_cmd = cmd
        print(f"Executing: {full_cmd}")

    try:
        # We use shell=True to support npm scripts which are often shell commands
        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=None if ssh_target else cwd,
            shell=True,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        for line in process.stdout:
            print(f"  {line.rstrip()}")

        process.wait()
        return process.returncode
    except Exception as e:
        print(f"Error executing command: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="OpenClaw Test Runner")
    parser.add_argument("project_path", help="Path to the project")
    parser.add_argument("suite", nargs="?", default="all", choices=["unit", "integration", "build", "all"], help="Test suite to run")
    parser.add_argument("--ssh", help="SSH target (e.g. user@host) for remote execution")
    
    args = parser.parse_args()

    project_path = args.project_path
    suite = args.suite
    ssh_target = args.ssh

    if suite == "all":
        suites_to_run = ["unit", "build", "integration"]
    else:
        suites_to_run = [suite]

    print(f"\nStarting test execution for project: {os.path.basename(project_path)}")
    
    for s in suites_to_run:
        cmd = SUITES.get(s)
        if not cmd:
            print(f"Error: Command for suite '{s}' not found.")
            sys.exit(1)
            
        print(f"\nRunning: {s} tests...")
        retcode = run_command(cmd, project_path, ssh_target)
        
        if retcode != 0:
            print(f"\n{s.capitalize()} tests failed. Fix the above errors before committing.")
            sys.exit(1)
        
        print(f"Result: {s} passed successfully.")

    print("\nAll tests passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
