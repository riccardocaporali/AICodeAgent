import os

def prev_run_summary_path(current_run_id: str):
    try:
        n = int(current_run_id.split("_")[-1])
    except Exception:
        return None
    prev = n - 1
    if prev < 1:
        return None
    path = os.path.join("__ai_outputs__", f"run_{prev:03}", "run_summary.json")
    return path if os.path.isfile(path) else None
