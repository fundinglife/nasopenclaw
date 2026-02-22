import os
import sys
import json
import argparse
from datetime import datetime

# Path to the data file, defaults to local during dev/test if not on NAS
DEFAULT_NAS_PATH = "/volume1/docker/nasopenclaw/tasks.json"
DATA_FILE = os.getenv("OPENCLAW_TASKS_FILE", DEFAULT_NAS_PATH)

# Robust fallback to local file if the NAS path isn't writable/reachable
nas_dir = os.path.dirname(DATA_FILE)
if not os.path.exists(nas_dir):
    DATA_FILE = "tasks.json"

def load_tasks():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_tasks(tasks):
    # Keep only last 100
    tasks = tasks[-100:]
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        print(f"Error saving tasks: {e}")

def create_task(project, description, model):
    tasks = load_tasks()
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
    new_task = {
        "id": task_id,
        "project": project,
        "description": description,
        "model": model,
        "state": "queued",
        "created_at": datetime.now().isoformat() + "Z",
        "updated_at": datetime.now().isoformat() + "Z",
        "commit": None,
        "error": None
    }
    tasks.append(new_task)
    save_tasks(tasks)
    print(task_id)

def update_task(task_id, state=None, commit=None, error=None):
    tasks = load_tasks()
    found = False
    for task in tasks:
        if task["id"] == task_id:
            if state: task["state"] = state
            if commit: task["commit"] = commit
            if error: task["error"] = error
            task["updated_at"] = datetime.now().isoformat() + "Z"
            found = True
            break
    
    if not found:
        print(f"Error: Task {task_id} not found.")
        sys.exit(1)
        
    save_tasks(tasks)
    print(f"Task {task_id} updated.")

def list_tasks(project=None, state=None):
    tasks = load_tasks()
    filtered = tasks
    if project:
        filtered = [t for t in filtered if t["project"] == project]
    if state:
        filtered = [t for t in filtered if t["state"] == state]
    
    # Show newest first
    filtered.reverse()
    
    print(f"{'ID':<25} | {'Project':<20} | {'State':<10} | {'Updated'}")
    print("-" * 75)
    for t in filtered[:10]: # default to last 10 for list
        print(f"{t['id']:<25} | {t['project']:<20} | {t['state']:<10} | {t['updated_at']}")

def show_task(task_id):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            print(json.dumps(t, indent=2))
            return
    print(f"Error: Task {task_id} not found.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="OpenClaw Task Tracker")
    subparsers = parser.add_subparsers(dest="command")

    # Create
    p_create = subparsers.add_parser("create")
    p_create.add_argument("--project", required=True)
    p_create.add_argument("--description", required=True)
    p_create.add_argument("--model", required=True)

    # Update
    p_update = subparsers.add_parser("update")
    p_update.add_argument("task_id")
    p_update.add_argument("--state")
    p_update.add_argument("--commit")
    p_update.add_argument("--error")

    # List
    p_list = subparsers.add_parser("list")
    p_list.add_argument("--project")
    p_list.add_argument("--state")

    # Show
    p_show = subparsers.add_parser("show")
    p_show.add_argument("task_id")

    args = parser.parse_args()

    if args.command == "create":
        create_task(args.project, args.description, args.model)
    elif args.command == "update":
        update_task(args.task_id, args.state, args.commit, args.error)
    elif args.command == "list":
        list_tasks(args.project, args.state)
    elif args.command == "show":
        show_task(args.task_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
