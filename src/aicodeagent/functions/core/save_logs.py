import os
from datetime import datetime

from aicodeagent.functions.fs.get_project_root import get_project_root


# Function to cut log after MAX characters
def _clip(s):
    MAX = 500
    return s if len(s) <= MAX else s[:MAX] + " [truncated]"


def save_logs(
    file_name,
    log_dir,
    function_name,
    source_path=None,
    content=None,
    dry_run=True,
    list_data=None,
    result=None,  # "OK" | "ERROR" | "TIMEOUT"
    details=None,
):
    """
    Save a log entry under <PROJECT_ROOT>/__ai_outputs__/<run_id>/actions.log
    Logs all tool operations, file actions, and results.
    """
    project_root = get_project_root(__file__)
    if not os.path.isabs(log_dir):
        log_dir = os.path.join(project_root, "__ai_outputs__", log_dir)

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "actions.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_line = None

    if function_name in ("propose_changes", "conclude_edit"):
        if source_path is not None and content is not None:
            if dry_run:
                log_line = (
                    f"\n[{timestamp}] Function {function_name}: "
                    f"dry-run propose changes to {file_name} (no file written, diff only)\n"
                    f" Result: {result}\n"
                )
                if details:
                    log_line += f"   + details: {details}\n"
            else:
                log_line = (
                    f"\n[{timestamp}] Function {function_name}: "
                    f"modified {file_name} (backup: yes, diff: yes)\n"
                    f" Result: {result}\n"
                )
                if details:
                    log_line += f"   + details: {details}\n"
        elif content is not None:
            if dry_run:
                log_line = (
                    f"\n[{timestamp}] Function {function_name}: "
                    f"dry-run propose creation of {file_name} (not written, diff only)\n"
                    f" Result: {result}\n"
                )
                if details:
                    log_line += f"   + details: {details}\n"
            else:
                log_line = (
                    f"\n[{timestamp}] Function {function_name}: "
                    f"created {file_name}\n"
                    f" Result: {result}\n"
                )
                if details:
                    log_line += f"   + details: {details}\n"
        else:
            log_line = (
                f"\n[{timestamp}] Function {function_name}: "
                f"unknown action on {file_name}\n"
                f" Result: {result}\n"
            )
            if details:
                log_line += f"   + details: {details}\n"

    elif function_name == "get_file_content":
        log_line = (
            f"\n[{timestamp}] Function {function_name}: "
            f"read file content of: {file_name}\n"
            f" Result: {result}\n"
        )
        if details:
            log_line += f"   + details: {details}\n"

    elif function_name == "get_files_info":
        log_line = (
            f"\n[{timestamp}] Function {function_name}: "
            f"get content of directory: {file_name}\n"
            f" Result: {result}\n"
        )
        if details:
            log_line += f"   + details: {details}\n"
        if list_data:
            for data in list_data:
                s = _clip(str(data).rstrip("\n"))
                log_line += f"   + {s}\n"

    elif function_name == "run_python_file":
        log_line = (
            f"\n[{timestamp}] Function {function_name}: "
            f"run the file: {file_name}\n"
            f" Result: {result}\n"
        )
        if details:
            if result == "ERROR":
                log_line += f"   + details: {details}\n"
            else:
                log_line += "   + details:\n"
                for k, v in details.items():
                    s = _clip(f"{k}: {str(v).rstrip()}")
                    log_line += f"     + {s}\n"

    # Write to log file
    if log_line:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(log_line)

    return log_line
