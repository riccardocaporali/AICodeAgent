import os

from aicodeagent.functions.internal.get_project_root import get_project_root
from aicodeagent.functions.internal.get_secure_path import get_secure_path
from aicodeagent.functions.internal.get_versioned_path import get_versioned_path


def save_diffs(diff_dir=None, diff_content=None, file_name="diff.txt"):
    """
    Save versioned diff output under <PROJECT_ROOT>/__ai_outputs__/diffs by default.
    Returns the absolute path of the created diff file.
    """
    project_root = get_project_root(__file__)
    if diff_dir is None:
        diff_dir = os.path.join(project_root, "__ai_outputs__", "diffs")

    os.makedirs(diff_dir, exist_ok=True)
    file_name = os.path.basename(file_name)
    diff_path = get_secure_path(diff_dir, file_name)
    diff_path = get_versioned_path(diff_path)

    with open(diff_path, "w", encoding="utf-8") as f:
        f.writelines(diff_content or [])

    return diff_path
