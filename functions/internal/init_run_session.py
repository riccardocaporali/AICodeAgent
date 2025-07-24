import os
import shutil

def init_run_session(max_runs=10, max_global_runs=1000):
    """
    Initializes a new run session across multiple directories using a shared run_id (e.g., run_001).
    - Keeps only the last `max_runs` runs per directory.
    - After `max_global_runs`, resets everything and restarts from run_001.
    """
    base_dirs = {
        "diffs": "__ai_outputs__/diffs",
        "logs": "__ai_outputs__/logs",
        "backups": "__ai_outputs__/backups",
        "summary": "__ai_outputs__/summary"
    }
    counter_file = os.path.join("__ai_outputs__", "run_counter.txt")
    os.makedirs("__ai_outputs__", exist_ok=True)

    # === Load counter ===
    if os.path.exists(counter_file):
        with open(counter_file, "r") as f:
            content = f.read().strip()
            count = int(content) if content.isdigit() else 0
    else:
        count = 0

    # === Increment counter ===
    count += 1

    # === Reset if over global limit ===
    if count > max_global_runs:
        print(f"🔁 Reached max run limit ({max_global_runs}), wiping all runs...")
        for folder in base_dirs.values():
            shutil.rmtree(folder, ignore_errors=True)
        count = 1  # restart from run_001

    # === Save updated counter ===
    with open(counter_file, "w") as f:
        f.write(str(count))

    run_id = f"run_{count:03}"

    # === Create folders and cleanup old ones if needed ===
    for base_dir in base_dirs.values():
        os.makedirs(base_dir, exist_ok=True)

        # Cleanup old runs
        existing = sorted(d for d in os.listdir(base_dir) if d.startswith("run_"))
        if len(existing) >= max_runs:
            to_delete = existing[:len(existing) - max_runs + 1]
            for old in to_delete:
                shutil.rmtree(os.path.join(base_dir, old), ignore_errors=True)

        # Create current run folder
        os.makedirs(os.path.join(base_dir, run_id), exist_ok=True)

    return run_id