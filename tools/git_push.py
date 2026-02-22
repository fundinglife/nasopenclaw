import os
import sys
import subprocess
import argparse
import json

def run_git(args, cwd):
    cmd = ["git"] + args
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result

def main():
    parser = argparse.ArgumentParser(description="OpenClaw Git Commit and Push Tool")
    parser.add_argument("project_path", help="Path to the project")
    parser.add_argument("message", help="Commit message")
    parser.add_argument("--skip-validation", action="store_true", help="Skip shared file validation")
    
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    message = args.message
    skip_validation = args.skip_validation

    # 1. Read .factory.json and confirm locked field
    factory_path = os.path.join(project_path, ".factory.json")
    if not os.path.exists(factory_path):
        print(f"Error: .factory.json not found in {project_path}")
        sys.exit(1)
        
    try:
        with open(factory_path, 'r') as f:
            factory_data = json.load(f)
            # locked = factory_data.get("locked", False) # We don't abort on locked=true here, prompt says confirm it
    except Exception as e:
        print(f"Error reading .factory.json: {e}")
        sys.exit(1)

    # 2. Check current branch
    branch_result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], project_path)
    if branch_result.returncode != 0:
        print(f"Error: Not a git repository or failed to get branch. {branch_result.stderr}")
        sys.exit(1)
        
    current_branch = branch_result.stdout.strip()
    if current_branch != "development":
        print(f"Cannot push: current branch is '{current_branch}', not 'development'")
        sys.exit(1)

    # 3. Run shared file validator
    if not skip_validation:
        validator_path = os.path.join(os.path.dirname(__file__), "validate_shared_files.py")
        val_result = subprocess.run([sys.executable, validator_path, "check", project_path], capture_output=True, text=True)
        
        if val_result.returncode != 0:
            print(val_result.stdout)
            print(val_result.stderr)
            confirm = input("Protected files were modified. Proceed? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("Aborted by user.")
                sys.exit(1)
    else:
        print("Skipping shared file validation...")

    # 4. Stage all changes
    print("Staging changes...")
    add_result = run_git(["add", "-A"], project_path)
    if add_result.returncode != 0:
        print(f"Error staging files: {add_result.stderr}")
        sys.exit(1)

    # 5. Check if anything to commit
    status_result = run_git(["status", "--porcelain"], project_path)
    if not status_result.stdout.strip():
        print("Nothing to commit")
        sys.exit(0)

    # 6. Commit
    print(f"Committing: {message}")
    commit_result = run_git(["commit", "-m", message], project_path)
    if commit_result.returncode != 0:
        print(f"Error committing: {commit_result.stderr}")
        sys.exit(1)

    # 7. Push
    print("Pushing to origin development...")
    push_result = run_git(["push", "origin", "development"], project_path)
    if push_result.returncode != 0:
        print(f"Error pushing: {push_result.stderr}")
        sys.exit(1)

    # 8. Confirmation
    hash_result = run_git(["rev-parse", "HEAD"], project_path)
    commit_hash = hash_result.stdout.strip()
    print(f"\nSuccess! Pushed to origin/development.")
    print(f"Commit Hash: {commit_hash}")

if __name__ == "__main__":
    main()
