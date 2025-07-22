import os

def clear_output_dirs():
    base_dir = os.path.abspath("__ai_outputs__")
    cleared = 0

    # Include also the logs folder
    for subdir in ["diffs", "backups", "logs"]:
        path = os.path.join(base_dir, subdir)
        
        if not os.path.exists(path):
            continue  # Skip non-existent folders
        
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)

            if filename != ".gitkeep":
                os.remove(file_path)
                cleared += 1

    print(f"\n✅ Clear finished. Files removed: {cleared}\n", flush=True)