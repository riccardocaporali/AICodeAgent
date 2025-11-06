import os
import shutil
from aicodeagent.functions.internal.get_project_root import get_project_root

ENV_OUTPUT_DIR = "AICODEAGENT_OUTPUT_DIR"

def _resolve_output_dir(base_dir: str | None = None) -> str:
    """
    Resolve the output directory with the following precedence:
    1) explicit `base_dir` argument
    2) env var AICODEAGENT_OUTPUT_DIR
    3) <PROJECT_ROOT>/__ai_outputs__
    """
    if base_dir:
        return os.path.abspath(base_dir)
    env = os.getenv(ENV_OUTPUT_DIR)
    if env:
        return os.path.abspath(env)
    return os.path.join(get_project_root(__file__), "__ai_outputs__")

def init_run_session(max_runs: int = 10,
                     max_global_runs: int = 1000,
                     base_dir: str | None = None) -> str:
    """
    Initialize a new run session:
      - Base directory is resolved to the project root by default.
      - Creates __ai_outputs__/run_XXX
      - Maintains a global counter with rollover at `max_global_runs`
      - Keeps only the latest `max_runs` run directories

    Returns: run_id
    """
    base_dir = _resolve_output_dir(base_dir)
    os.makedirs(base_dir, exist_ok=True)

    counter_file = os.path.join(base_dir, "run_counter.txt")

    # Load or init counter
    try:
        with open(counter_file, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            count = int(raw) if raw else 0
    except FileNotFoundError:
        count = 0
    except Exception:
        count = 0

    # Increment
    count += 1

    # Rollover: wipe old runs and restart from 1
    if count > max_global_runs:
        print(f"🔁 Reached max run limit ({max_global_runs}), wiping all runs...")
        for d in os.listdir(base_dir):
            full_path = os.path.join(base_dir, d)
            if os.path.isdir(full_path) and d.startswith("run_"):
                shutil.rmtree(full_path, ignore_errors=True)
        count = 1

    # Persist counter
    with open(counter_file, "w", encoding="utf-8") as f:
        f.write(str(count))

    run_id = f"run_{count:03}"
    run_path = os.path.join(base_dir, run_id)
    os.makedirs(run_path, exist_ok=True)

    # Trim oldest runs beyond `max_runs`
    runs = sorted(
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d)) and d.startswith("run_")
    )
    if len(runs) > max_runs:
        to_delete = runs[:len(runs) - max_runs]
        for d in to_delete:
            shutil.rmtree(os.path.join(base_dir, d), ignore_errors=True)

    return run_id

if __name__ == "__main__":
    rid = init_run_session()
    print(f"Initialized: {rid}")