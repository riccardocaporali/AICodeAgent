import os, shutil

def init_run_session():
    """
    Initializes a new run session across predefined directories (diffs, backups, logs),
    using a shared run_id (e.g., run_001). Cleans up oldest runs if total exceeds 30.
    Returns the shared run_id (e.g., 'run_031').
    """
    base_dirs = {
        "diffs": "__ai_outputs__/diffs",
        "backups": "__ai_outputs__/backups",
        "logs": "__ai_outputs__/logs"
    }
    max_runs = 10

    # === Determine next shared run_id using 'diffs' as reference ===
    os.makedirs(base_dirs["diffs"], exist_ok=True)
    existing = sorted(d for d in os.listdir(base_dirs["diffs"]) if d.startswith("run_"))
    new_num = int(existing[-1].split("_")[1]) + 1 if existing else 1
    run_id = f"run_{new_num:03}"

    for base_dir in base_dirs.values():
        os.makedirs(base_dir, exist_ok=True)

        # === Cleanup old runs ===
        existing = sorted(d for d in os.listdir(base_dir) if d.startswith("run_"))
        if len(existing) >= max_runs:
            to_delete = existing[:len(existing) - max_runs + 1]
            for old in to_delete:
                shutil.rmtree(os.path.join(base_dir, old), ignore_errors=True)

        # === Create new run folder ===
        os.makedirs(os.path.join(base_dir, run_id), exist_ok=True)

    return run_id