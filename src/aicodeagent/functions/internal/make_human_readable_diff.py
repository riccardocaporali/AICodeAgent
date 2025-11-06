def make_human_readable_diff(diff_lines):
    readable = []
    for line in diff_lines:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue  # skip metadata
        elif line.startswith('-'):
            readable.append(f"# - Removed: {line[1:].strip()}")
        elif line.startswith('+'):
            readable.append(f"# + Added:   {line[1:].strip()}")
    return "\n".join(readable)