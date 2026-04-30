import subprocess


def get_last_commit():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
    ).decode().strip()


def get_changed_files():
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD~1"], stderr=subprocess.DEVNULL
        ).decode()
        return [f for f in out.split("\n") if f]
    except subprocess.CalledProcessError:
        return []


def get_diff_summary(max_chars=1500):
    try:
        out = subprocess.check_output(
            ["git", "diff", "HEAD~1", "--stat"], stderr=subprocess.DEVNULL
        ).decode()
        diff = subprocess.check_output(
            ["git", "diff", "HEAD~1", "--", "*.py", "*.ts", "*.js"],
            stderr=subprocess.DEVNULL
        ).decode()
        combined = out + "\n" + diff
        return combined[:max_chars]
    except subprocess.CalledProcessError:
        return ""
