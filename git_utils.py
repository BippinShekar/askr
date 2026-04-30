import subprocess

def get_last_commit():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"]
    ).decode().strip()

def get_changed_files():
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD~1"]
    ).decode()
    return [f for f in out.split("\n") if f]