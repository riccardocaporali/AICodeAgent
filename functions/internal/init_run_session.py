import os
import shutil

def init_run_session(max_runs=10, max_global_runs=1000):
    """
    Initializes a new run session: __ai_outputs__/run_001, run_002, ...
    Cleans up old runs and resets counter if max_global_runs is exceeded.
    """
    base_dir = "__ai_outputs__"
    counter_file = os.path.join(base_dir, "run_counter.txt")
    os.makedirs(base_dir, exist_ok=True)

    # === Load or init counter ===
    if os.path.exists(counter_file):
        with open(counter_file, "r") as f:
            count = int(f.read().strip() or 0)
    else:
        count = 0

    # === Increment counter ===
    count += 1

    # === Reset everything if over limit ===
    if count > max_global_runs:
        print(f"🔁 Reached max run limit ({max_global_runs}), wiping all runs...")
        for d in os.listdir(base_dir):
            full_path = os.path.join(base_dir, d)
            if os.path.isdir(full_path) and d.startswith("run_"):
                shutil.rmtree(full_path, ignore_errors=True)
        count = 1

    # === Save new counter ===
    with open(counter_file, "w") as f:
        f.write(str(count))

    run_id = f"run_{count:03}"
    run_path = os.path.join(base_dir, run_id)
    os.makedirs(run_path, exist_ok=True)

    # Cleanup oldest runs
    runs = sorted(d for d in os.listdir(base_dir) if d.startswith("run_"))
    if len(runs) > max_runs:
        to_delete = runs[:len(runs) - max_runs]
        for d in to_delete:
            shutil.rmtree(os.path.join(base_dir, d), ignore_errors=True)

    return run_id