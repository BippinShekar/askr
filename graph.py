import ast

def build_graph(files):
    graph = {}
    reverse = {}

    for file in files:
        try:
            tree = ast.parse(open(file).read())
        except:
            continue

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports += [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        graph[file] = imports

        for imp in imports:
            reverse.setdefault(imp, []).append(file)

    return graph, reverse