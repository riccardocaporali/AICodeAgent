import os
from functions.internal.make_human_readable_diff import make_human_readable_diff

def save_summary_entry(log_line, diff_lines, run_id=None):

    # Define the summary directory (with optional run_id subfolder)
    base_dir = os.path.abspath("__ai_outputs__")
    summary_dir = os.path.join(base_dir, "summary", run_id) if run_id else os.path.join(base_dir, "summary")
    os.makedirs(summary_dir, exist_ok=True)

    # Define the summary file path
    summary_path = os.path.join(summary_dir, "summary.txt")

    # Convert diff lines to a human-readable format
    readable_diff = make_human_readable_diff(diff_lines) if diff_lines else ""

    # Write the log line and corresponding diff to the summary file
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(log_line)
        if readable_diff:
            f.write(readable_diff + "\n\n")