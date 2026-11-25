import subprocess
from pathlib import Path

class GitError(RuntimeError):
    pass

def run_git(repo_path, *args, check=True):
    path = Path(repo_path)
    if not path.exists():
        raise GitError(f"Folder does not exist: {path}")
    proc = subprocess.run(
        ["git", "-C", str(path), *args],
        text=True, capture_output=True, encoding="utf-8", errors="replace"
    )
    if check and proc.returncode:
        raise GitError((proc.stderr or proc.stdout or "Git command failed").strip())
    return proc.stdout.strip()

def is_repo(path):
    try:
        return run_git(path, "rev-parse", "--is-inside-work-tree") == "true"
    except GitError:
        return False

def repo_info(path):
    branch = run_git(path, "branch", "--show-current", check=False) or "(detached)"
    remote = run_git(path, "remote", "get-url", "origin", check=False)
    status = run_git(path, "status", "--short", check=False)
    return {"branch": branch, "remote": remote, "status": status}

def clone_repo(url, destination):
    proc = subprocess.run(["git", "clone", url, str(destination)], text=True,
                          capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise GitError((proc.stderr or proc.stdout).strip())
    return str(destination)

def commit_push(path, message, remote="origin", branch=None):
    run_git(path, "add", "-A")
    run_git(path, "commit", "-m", message)
    branch = branch or run_git(path, "branch", "--show-current")
    if not branch:
        raise GitError("No current branch. Create or checkout a branch first.")
    run_git(path, "push", "-u", remote, branch)
    return branch

def publish_folder(path, remote_url, initial_message="Initial commit"):
    path = Path(path)
    if not (path / ".git").exists():
        run_git(path, "init")
    current = run_git(path, "branch", "--show-current", check=False)
    if current != "main":
        run_git(path, "branch", "-M", "main")
    remotes = run_git(path, "remote", check=False).splitlines()
    if "origin" in remotes:
        run_git(path, "remote", "set-url", "origin", remote_url)
    else:
        run_git(path, "remote", "add", "origin", remote_url)
    run_git(path, "add", "-A")
    # Initial publish can encounter an empty folder or no changes.
    run_git(path, "commit", "-m", initial_message, check=False)
    run_git(path, "push", "-u", "origin", "main")
