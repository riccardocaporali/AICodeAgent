import os
import shutil
from functions.internal.get_project_root import get_project_root

def clear_output_dirs():
    """
    Remove all run_* directories and reset run_counter.txt
    inside <PROJECT_ROOT>/__ai_outputs__.
    """
    print("▶️ Running clear_output_dirs...")
    base_dir = os.path.join(get_project_root(__file__), "__ai_outputs__")
    cleared = 0

    if not os.path.exists(base_dir):
        print("__ai_outputs__ does not exist.")
        return

    # Remove run directories (run_XXX)
    for entry in os.listdir(base_dir):
        full_path = os.path.join(base_dir, entry)
        if os.path.isdir(full_path) and entry.startswith("run_"):
            shutil.rmtree(full_path, ignore_errors=True)
            cleared += 1

    # Reset run_counter.txt
    counter_file = os.path.join(base_dir, "run_counter.txt")
    if os.path.exists(counter_file):
        with open(counter_file, "w", encoding="utf-8") as f:
            f.write("0")

    print(f"\n✅ Clear finished. Run directories removed: {cleared}, run counter reset to 0.\n", flush=True)

if __name__ == "__main__":
    clear_output_dirs()