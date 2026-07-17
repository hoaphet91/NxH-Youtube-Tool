import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "git_push_config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    if not config.get("remote"):
        raise ValueError("git_push_config.json must define 'remote'.")
    if not config.get("branch"):
        raise ValueError("git_push_config.json must define 'branch'.")
    paths = config.get("paths")
    if paths is None:
        raise ValueError("git_push_config.json must define 'paths' as a list of files/folders.")
    if not isinstance(paths, list):
        raise ValueError("git_push_config.json 'paths' must be a list of files/folders.")
    interval = int(config.get("watch_interval_seconds", 3))
    return {
        "remote": config["remote"],
        "branch": config["branch"],
        "paths": paths,
        "interval": interval,
    }


def run_git(args, capture_output: bool = False, check: bool = True):
    result = subprocess.run(
        ["git"] + args,
        cwd=ROOT,
        text=True,
        capture_output=capture_output,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def is_git_repo() -> bool:
    return (ROOT / ".git").exists()


def ensure_git_repository(remote: str, branch: str) -> None:
    if not is_git_repo():
        print("Initializing local git repository...")
        run_git(["init"])

    remotes = run_git(["remote"], capture_output=True).stdout.splitlines()
    if "origin" not in remotes:
        print(f"Adding remote origin -> {remote}")
        run_git(["remote", "add", "origin", remote])
    else:
        existing = run_git(["remote", "get-url", "origin"], capture_output=True).stdout.strip()
        if existing != remote:
            print(f"Updating origin URL from {existing} to {remote}")
            run_git(["remote", "set-url", "origin", remote])

    head = run_git(["rev-parse", "--verify", "HEAD"], capture_output=True, check=False)
    if head.returncode != 0:
        branch_check = run_git(["ls-remote", "--heads", "origin", branch], capture_output=True)
        if branch_check.stdout.strip():
            print(f"Fetching remote branch origin/{branch}...")
            run_git(["fetch", "origin", branch])
            run_git(["checkout", "-b", branch, f"origin/{branch}"])
        else:
            print(f"Creating local branch '{branch}'...")
            run_git(["checkout", "-b", branch])
    else:
        current_branch = run_git(["branch", "--show-current"], capture_output=True).stdout.strip()
        if current_branch != branch:
            print(f"Switching to branch '{branch}'...")
            run_git(["checkout", "-B", branch])


def selected_status(paths: list[str]) -> str:
    result = run_git(["status", "--porcelain", "--"] + paths, capture_output=True)
    return result.stdout.strip()


def auto_push(paths: list[str], branch: str) -> None:
    if not paths:
        return

    status = selected_status(paths)
    if not status:
        return

    print(f"Changes detected in selected paths:\n{status}")
    print("Staging selected paths...")
    run_git(["add", "--"] + paths)
    commit_message = f"Auto-sync selected files at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    commit = run_git(["commit", "-m", commit_message], capture_output=True, check=False)
    if commit.returncode == 0:
        print(commit.stdout.strip())
        print(f"Pushing branch '{branch}' to origin...")
        run_git(["push", "--set-upstream", "origin", branch])
        print("Push complete.")
    else:
        output = (commit.stdout + commit.stderr).strip()
        if "nothing to commit" in output.lower():
            return
        raise RuntimeError(f"Git commit failed:\n{output}")


def main() -> int:
    try:
        config = load_config()
    except Exception as exc:
        print(f"Error loading config: {exc}")
        return 1

    try:
        ensure_git_repository(config["remote"], config["branch"])
    except Exception as exc:
        print(f"Git setup error: {exc}")
        return 2

    print("Watching selected paths for changes:")
    for path in config["paths"]:
        print(f" - {path}")
    print(f"Polling interval: {config['interval']}s")

    try:
        while True:
            try:
                auto_push(config["paths"], config["branch"])
            except Exception as exc:
                print(f"Auto push error: {exc}")
            time.sleep(config["interval"])
    except KeyboardInterrupt:
        print("Stopped by user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
