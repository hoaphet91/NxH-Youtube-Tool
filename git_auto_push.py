import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "git_push_config.json"


def load_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    remote = cfg.get("remote")
    branch = cfg.get("branch")
    paths = cfg.get("paths")
    interval = int(cfg.get("watch_interval_seconds", 5))

    if not remote:
        raise ValueError("git_push_config.json must define 'remote'.")
    if not branch:
        raise ValueError("git_push_config.json must define 'branch'.")
    if not isinstance(paths, list) or not paths:
        raise ValueError("git_push_config.json must define 'paths' as a non-empty list.")

    return {"remote": remote, "branch": branch, "paths": paths, "interval": interval}


def run_git(args, capture_output=False, check=True):
    result = subprocess.run(["git"] + args, cwd=ROOT, text=True, capture_output=capture_output)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def is_git_repo():
    return (ROOT / ".git").is_dir()


def ensure_repo(remote, branch):
    if not is_git_repo():
        print("Initializing git repository...")
        run_git(["init"])

    existing_remotes = run_git(["remote"], capture_output=True).stdout.splitlines()
    if "origin" not in existing_remotes:
        print(f"Setting remote origin to {remote}")
        run_git(["remote", "add", "origin", remote])
    else:
        current_url = run_git(["remote", "get-url", "origin"], capture_output=True).stdout.strip()
        if current_url != remote:
            print(f"Updating remote origin from {current_url} to {remote}")
            run_git(["remote", "set-url", "origin", remote])

    branch_name = run_git(["rev-parse", "--abbrev-ref", "HEAD"], capture_output=True).stdout.strip()
    if branch_name != branch:
        print(f"Switching to branch '{branch}'...")
        run_git(["checkout", "-B", branch])

    if branch_name == branch:
        if run_git(["rev-parse", "--verify", "HEAD"], capture_output=True, check=False).returncode != 0:
            track = run_git(["ls-remote", "--heads", "origin", branch], capture_output=True).stdout.strip()
            if track:
                print(f"Fetching origin/{branch}...")
                run_git(["fetch", "origin", branch])
                run_git(["reset", "--hard", f"origin/{branch}"])


def paths_status(paths):
    result = run_git(["status", "--porcelain", "--"] + paths, capture_output=True)
    return result.stdout.strip()


def commit_and_push(paths, branch):
    status = paths_status(paths)
    if not status:
        return False

    print("Detected changes in selected paths:")
    print(status)
    run_git(["add", "--"] + paths)
    message = f"Auto-sync selected files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    commit = run_git(["commit", "-m", message], capture_output=True, check=False)
    if commit.returncode != 0:
        output = (commit.stdout or "") + (commit.stderr or "")
        if "nothing to commit" in output.lower():
            return False
        raise RuntimeError(f"Git commit failed:\n{output}")

    print(commit.stdout.strip())
    run_git(["push", "-u", "origin", branch])
    return True


def main():
    config = load_config()
    ensure_repo(config["remote"], config["branch"])
    print("Auto-push watcher running.")
    print("Selected paths:")
    for p in config["paths"]:
        print(f" - {p}")
    print(f"Polling every {config['interval']} seconds.")

    try:
        while True:
            try:
                if commit_and_push(config["paths"], config["branch"]):
                    print("Push succeeded.")
            except Exception as e:
                print(f"Auto-push error: {e}")
            time.sleep(config["interval"])
    except KeyboardInterrupt:
        print("Stopped by user.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
