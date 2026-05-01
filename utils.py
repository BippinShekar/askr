def compress(text, max_lines=8):
    result = []
    non_empty = 0
    for line in text.split("\n"):
        if line.strip():
            non_empty += 1
            if non_empty > max_lines:
                result.append("...")
                break
        result.append(line)
    # strip leading/trailing blank lines
    while result and not result[0].strip():
        result.pop(0)
    while result and not result[-1].strip():
        result.pop()
    return "\n".join(result)
