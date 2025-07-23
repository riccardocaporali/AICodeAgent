import os

snapshot_file = "project_snapshot.txt"
tree_file = "project_tree.txt"
base_dirs = ["functions", "tests", "__ai_outputs__", "main.py", "README.md"]
excluded_dirs = {"__pycache__", ".venv", ".git", ".mypy_cache"}
valid_ext = (".py", ".md", ".txt", ".log")

def is_text_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read()
        return True
    except:
        return False

def explore_directory(path, snapshot_out, tree_out, prefix=""):
    if os.path.isfile(path):
        if path.endswith(valid_ext) and is_text_file(path):
            snapshot_out.write(f"\n--- File: {path} ---\n")
            with open(path, "r", encoding="utf-8") as f:
                snapshot_out.write(f.read())
        tree_out.write(f"{prefix}📄 {path}\n")
        return

    for root, dirs, files in os.walk(path):
        level = root.replace(path, "").count(os.sep)
        indent = "│   " * level + "├── "

        tree_out.write(f"{indent}📁 {os.path.basename(root)}/\n")

        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        for file in files:
            if not file.endswith(valid_ext) or file.startswith(".") or file == ".gitkeep":
                continue
            file_path = os.path.join(root, file)
            if is_text_file(file_path):
                snapshot_out.write(f"\n--- File: {file_path} ---\n")
                with open(file_path, "r", encoding="utf-8") as f:
                    snapshot_out.write(f.read())
            tree_out.write(f"{'│   ' * (level + 1)}📄 {file}\n")

# Scrittura dei due file
with open(snapshot_file, "w", encoding="utf-8") as snapshot_out, \
     open(tree_file, "w", encoding="utf-8") as tree_out:
    for item in base_dirs:
        if os.path.exists(item):
            explore_directory(item, snapshot_out, tree_out)
        else:
            snapshot_out.write(f"\n[Path non trovato: {item}]\n")
            tree_out.write(f"🚫 Path non trovato: {item}\n")

print("✅ Snapshot e struttura ad albero generati.")