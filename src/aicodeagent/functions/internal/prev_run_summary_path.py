import os
from aicodeagent.functions.internal.get_project_root import get_project_root

def prev_run_summary_path(current_run_id: str):
    """
    Return absolute path to the previous run summary JSON
    under <PROJECT_ROOT>/__ai_outputs__/run_XXX/run_summary.json.
    """
    try:
        n = int(current_run_id.split("_")[-1])
    except Exception:
        return None

    prev = n - 1
    if prev < 1:
        return None

    base_dir = os.path.join(get_project_root(__file__), "__ai_outputs__")
    path = os.path.join(base_dir, f"run_{prev:03}", "run_summary.json")
    return path if os.path.isfile(path) else None