import os, json
from config import SNAPSHOT_DIR
from client_claude import call_claude

def summarize_file(path):
    content = open(path, "r", errors="ignore").read()[:2000]

    prompt = f"""
Summarize file:

- purpose
- key components
- dependencies

Also assign:
importance_score (0-10)

Return JSON.

{content}
"""
    res = call_claude("", prompt)

    try:
        return json.loads(res)
    except:
        return {"file": path, "importance_score": 5}

def build_snapshot():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    data = []

    for root, _, files in os.walk("."):
        for f in files:
            if f.endswith((".py", ".js", ".ts")):
                path = os.path.join(root, f)
                data.append(summarize_file(path))

    with open(f"{SNAPSHOT_DIR}/summary.json", "w") as f:
        json.dump(data, f)