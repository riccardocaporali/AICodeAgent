import os
import shutil

def clear_output_dirs():
    print("\u25B6\uFE0F Running clear_output_dirs...")
    base_dir = os.path.abspath("__ai_outputs__")
    cleared = 0

    # Iterate over each directory
    for subdir in ["diffs", "backups", "logs", "summary"]:
        path = os.path.join(base_dir, subdir)
        
        if not os.path.exists(path):
            continue  # Skip non-existent folders
        
        # Iterate over each file
        for entry in os.listdir(path):
            full_path = os.path.join(path, entry)

            # Remove file
            if os.path.isdir(full_path) and entry.startswith("run_"):
                shutil.rmtree(full_path, ignore_errors=True)
                cleared += 1

    print(f"\n✅ Clear finished. Run directories removed: {cleared}\n", flush=True)

# Enable uv launch from shell
if __name__ == "__main__":
    clear_output_dirs()