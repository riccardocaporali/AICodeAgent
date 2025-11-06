import os
from functions.internal.get_project_root import get_project_root

# === Output files live in the project root ===
SNAPSHOT_NAME = "project_snapshot.txt"
TREE_NAME = "project_tree.txt"

# Items to capture from the new structure: some inside src/, others in root
BASE_ITEMS = [
    "src",
    "tests",
    "__ai_outputs__",
    "code_to_fix",
    "README.md",
    "pyproject.toml",
]

# Exclusions while walking
EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".idea", ".vscode"}
VALID_EXT = (".py", ".md", ".txt", ".log", ".toml", ".cfg", ".ini", ".yml", ".yaml", ".json")

def is_text_file(path):
    """Try to open the file as UTF-8. If it fails, treat it as non-text."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read()
        return True
    except Exception:
        return False

def explore(path_abs, root_abs, snapshot_out, tree_out, prefix=""):
    """Explore directories and record file tree and snapshots relative to project root."""
    rel = os.path.relpath(path_abs, root_abs)

    if os.path.isfile(path_abs):
        if path_abs.endswith(VALID_EXT) and is_text_file(path_abs):
            snapshot_out.write(f"\n--- File: {rel} ---\n")
            with open(path_abs, "r", encoding="utf-8") as f:
                snapshot_out.write(f.read())
        tree_out.write(f"{prefix}📄 {rel}\n")
        return

    for current, dirs, files in os.walk(path_abs):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        level = os.path.relpath(current, path_abs).count(os.sep)
        indent = "│   " * level + "├── "
        rel_current = os.path.relpath(current, root_abs)
        tree_out.write(f"{indent}📁 {rel_current}/\n")

        for filename in files:
            if filename.startswith(".") or not filename.endswith(VALID_EXT):
                continue
            file_path = os.path.join(current, filename)
            rel_file = os.path.relpath(file_path, root_abs)
            if is_text_file(file_path):
                snapshot_out.write(f"\n--- File: {rel_file} ---\n")
                with open(file_path, "r", encoding="utf-8") as f:
                    snapshot_out.write(f.read())
            tree_out.write(f"{'│   ' * (level + 1)}📄 {filename}\n")

def main():
    root = get_project_root(__file__)
    snapshot_path = os.path.join(root, SNAPSHOT_NAME)
    tree_path = os.path.join(root, TREE_NAME)

    with open(snapshot_path, "w", encoding="utf-8") as snapshot_out, \
         open(tree_path, "w", encoding="utf-8") as tree_out:
        for item in BASE_ITEMS:
            abs_item = os.path.join(root, item)
            if os.path.exists(abs_item):
                explore(abs_item, root, snapshot_out, tree_out)
            else:
                rel_item = os.path.relpath(abs_item, root)
                msg = f"[Path not found: {rel_item}]"
                snapshot_out.write(f"\n{msg}\n")
                tree_out.write(f"🚫 {msg}\n")

    print("✅ Snapshot and directory tree generated at project root.")

if __name__ == "__main__":
    main()