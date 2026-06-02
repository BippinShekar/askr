import ast
import re
from pathlib import Path

_PATTERNS = {
    ".ts":    [r'from\s+[\'"]([^"\']+)[\'"]', r'require\s*\(\s*[\'"]([^"\']+)[\'"]\s*\)'],
    ".tsx":   [r'from\s+[\'"]([^"\']+)[\'"]', r'require\s*\(\s*[\'"]([^"\']+)[\'"]\s*\)'],
    ".js":    [r'from\s+[\'"]([^"\']+)[\'"]', r'require\s*\(\s*[\'"]([^"\']+)[\'"]\s*\)'],
    ".jsx":   [r'from\s+[\'"]([^"\']+)[\'"]', r'require\s*\(\s*[\'"]([^"\']+)[\'"]\s*\)'],
    ".go":    [r'"([^"]+)"'],
    ".rb":    [r'require\s+[\'"]([^"\']+)[\'"]'],
    ".rs":    [r'use\s+([\w:]+)', r'extern\s+crate\s+(\w+)'],
    ".swift": [r'import\s+(\w+)'],
    ".kt":    [r'import\s+([\w.]+)'],
    ".java":  [r'import\s+([\w.]+)'],
}


def _extract_imports(path):
    ext = Path(path).suffix
    try:
        content = open(path, errors="ignore").read()
    except Exception:
        return []

    if ext == ".py":
        try:
            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports += [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            return imports
        except Exception:
            return []

    patterns = _PATTERNS.get(ext, [])
    imports = []
    for pattern in patterns:
        imports += re.findall(pattern, content, re.MULTILINE)
    return imports


def build_graph(files):
    graph = {}
    reverse = {}

    for path in files:
        imports = _extract_imports(path)
        graph[path] = imports
        for imp in imports:
            reverse.setdefault(imp, []).append(path)

    return graph, reverse
