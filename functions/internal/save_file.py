import os, sys
import difflib
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.save_summary_entry import save_summary_entry
from functions.internal.save_backup import save_backup
from functions.internal.save_logs import save_logs
from functions.internal.save_diffs import save_diffs


def save_file(run_id, function_name, function_args, dry_run=True, file_name=None, source_path=None, content=None, log_changes=True):
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
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    if run_id is not None:
        backup_dir = os.path.join(base_dir, "backups") 
        diff_dir   = os.path.join(base_dir, "diffs")  

    # Initialize diff_lines variable 
    diff_lines = None
 
    # BACKUPS AND DIFFS
    # Create special cases for saving an existing file or save a new file with a specified content
    if source_path is not None and content is not None:
        # 1. Backup if dry run is false
        if dry_run == False:
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
        
        save_diffs(diff_dir, diff_lines, file_name)

    # Case of new file creation
    elif content is not None:
        new_lines = content.splitlines(keepends=True)
        diff_lines = [
            f"+ {line}" for line in new_lines
        ]
        save_diffs(diff_dir, diff_lines, file_name)

    # Error handling
    elif source_path is not None:
        raise ValueError("If source_path is provided, content must also be provided to compute diff")

    else:
        raise ValueError("Either content or source_path must be provided")

    # LOGS 
    if log_changes:
         log_line = save_logs(file_name, base_dir, function_name, source_path, content, dry_run)
    else:
        log_line = None

    # SUMMARY
    # Solo se c'è un diff associato
    if log_line and (source_path or content):
        save_summary_entry(base_dir, function_name, function_args, log_line=log_line, diff_lines=diff_lines)