def compress(text, max_lines=8):
    lines = [line for line in text.split("\n") if line.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + "\n..."
