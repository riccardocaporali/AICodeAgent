import difflib
import os

from aicodeagent.functions.core.save_backup import save_backup
from aicodeagent.functions.core.save_diffs import save_diffs
from aicodeagent.functions.core.save_logs import save_logs
from aicodeagent.functions.core.save_summary_entry import save_summary_entry
from aicodeagent.functions.fs.get_project_root import get_project_root


def save_file(
    run_id,
    function_name,
    function_args,
    dry_run=True,
    file_name=None,
    source_path=None,
    content=None,
):
    """
    Save a file and record its backup, diff, log, and summary.

    - Writes under <PROJECT_ROOT>/__ai_outputs__/<run_id>/
    - If `content` is provided, writes that content.
    - If `source_path` is provided with `content`, computes diff and backup.
    """
    project_root = get_project_root(__file__)
    base_dir = os.path.join(project_root, "__ai_outputs__", run_id)
    backup_dir = os.path.join(base_dir, "backups")
    diff_dir = os.path.join(base_dir, "diffs")

    os.makedirs(base_dir, exist_ok=True)

    # Resolve file name
    if file_name is None:
        if source_path:
            file_name = os.path.basename(source_path)
        else:
            raise ValueError("file_name must be specified if source_path is None")
    file_name = os.path.basename(file_name)

    # Validate source path if provided
    if source_path is not None:
        original_path = os.path.abspath(source_path)
        if not os.path.isfile(original_path):
            raise ValueError(
                "Invalid usage: provide 'content', or both 'source_path' and 'content'"
            )
    else:
        original_path = None

    diff_lines = None

    # === Backups and diffs ===
    if source_path is not None and content is not None:
        if not dry_run:
            save_backup(original_path, file_name, backup_dir)

        with open(original_path, "r", encoding="utf-8") as f:
            original_lines = f.readlines()
        new_lines = content.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                original_lines,
                new_lines,
                fromfile=f"original/{file_name}",
                tofile=f"modified/{file_name}",
                lineterm="",
            )
        )

        save_diffs(diff_dir, diff_lines, file_name)

    elif content is not None:
        new_lines = content.splitlines(keepends=True)
        diff_lines = [f"+ {line}" for line in new_lines]
        save_diffs(diff_dir, diff_lines, file_name)

    elif source_path is not None:
        raise ValueError(
            "If source_path is provided, content must also be provided to compute diff"
        )
    else:
        raise ValueError("Either content or source_path must be provided")

    # === Logs ===
    log_line = save_logs(
        file_name, base_dir, function_name, source_path, content, dry_run, result="OK"
    )

    # === Summary ===
    if log_line and (source_path or content):
        save_summary_entry(
            base_dir,
            function_name,
            function_args,
            log_line=log_line,
            diff_lines=diff_lines,
        )
