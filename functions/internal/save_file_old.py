import os, sys
import difflib
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.get_secure_path import get_secure_path
from functions.internal.get_versioned_path import get_versioned_path
from functions.internal.save_summary_entry import save_summary_entry
from functions.internal.save_backup import save_backup
from functions.internal.save_logs import save_logs


def save_file(file_name=None, source_path=None, content=None, log_changes=True, backup=True, run_id=None):
    """
    Saves a file to a specified directory.

    - If `content` is provided, it writes that content directly.
    - If `source_path` is provided and `content` is None, it copies the content from the source file.
    - `file_name` is required if `source_path` is None.
    """

    # If no file name is specified, it is automatically extracted from the file path otherwise --> error
    if file_name is None:
        if source_path:
            file_name = os.path.basename(source_path)
        else:
            raise ValueError("file_name must be specified if source_path is None")
    
    # Check is source path is a valid file path
    if source_path is not None:
        original_path = os.path.abspath(source_path)
        if not os.path.isfile(original_path):
            raise ValueError("Invalid usage: provide 'content', or both 'source_path' and 'content'")

    # Define directories
    base_dir = os.path.abspath("__ai_outputs__")
    if run_id is not None:
        backup_dir = os.path.join(base_dir, "backups", run_id) if run_id else os.path.join(base_dir, "backups")
        diff_dir   = os.path.join(base_dir, "diffs", run_id)   if run_id else os.path.join(base_dir, "diffs")
        log_dir    = os.path.join(base_dir, "logs", run_id)    if run_id else os.path.join(base_dir, "logs")
    else:
        backup_dir = os.path.join(base_dir, "backups")
        diff_dir = os.path.join(base_dir, "diffs")
        log_dir = os.path.join(base_dir, "logs")

    # BACKUPS AND DIFFS
    # Create special cases for saving an existing file or save a new file with a specified content
    if source_path is not None and content is not None:
        # 1. Backup
        if backup:
            save_backup(original_path, file_name, backup_dir)

        # 2. Compute difference row by row
        with open(original_path, "r", encoding="utf-8") as f:
            original_lines = f.readlines()
        new_lines = content.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"original/{file_name}",
            tofile=f"modified/{file_name}",
            lineterm=''  # evita doppio newline
        ))
        
        # Create diff file
        diff_path = get_secure_path(diff_dir, file_name)
        diff_path = get_versioned_path(diff_path)

        with open(diff_path, "w", encoding="utf-8") as f:
            f.writelines(diff_lines)

    # Case of new file creation
    elif content is not None:

        # Create diff file
        diff_path = get_secure_path(diff_dir, file_name)
        diff_path = get_versioned_path(diff_path)
        with open(diff_path, "w", encoding="utf-8") as f:
            f.write(content)

    # Error handling
    elif source_path is not None:
        raise ValueError("If source_path is provided, content must also be provided to compute diff")

    else:
        raise ValueError("Either content or source_path must be provided")
    
    # LOGS 
    if log_changes:
         log_line = save_logs(file_name, log_dir, source_path, content, backup)
    else:
        log_line = None

    # SUMMARY
    # Solo se c'è un diff associato
    if log_line and (source_path or content):
        save_summary_entry(log_line, diff_lines if source_path else content.splitlines(keepends=True), run_id)