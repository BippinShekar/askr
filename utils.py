def compress(text):
    lines = [line for line in text.split("\n") if line.strip()]
    if len(lines) <= 8:
        return "\n".join(lines)
    return "\n".join(lines[:8]) + "\n..."
