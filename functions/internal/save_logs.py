import os
from datetime import datetime

def save_logs(file_name, log_dir, source_path=None, content=None, dry_run=True):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "actions.log")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if source_path is not None and content is not None:
        if dry_run:
            log_line = f"[{timestamp}] DRY-RUN PROPOSE CHANGES TO {file_name} (no file written, diff only)\n"
        else:
            log_line = f"[{timestamp}] MODIFIED {file_name} (backup: yes, diff: yes)\n"


    elif content is not None:
        if dry_run:
            log_line = f"[{timestamp}] DRY-RUN PROPOSE CREATION OF {file_name} (not written, diff only)\n"
        else:
            log_line = f"[{timestamp}] CREATED {file_name}\n"


    else:
        log_line = f"[{timestamp}] UNKNOWN ACTION on {file_name}\n"

    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(log_line)
        
    return log_line