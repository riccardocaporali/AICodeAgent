import os
import shutil

from aicodeagent.functions.internal.get_project_root import get_project_root
from aicodeagent.functions.internal.get_secure_path import get_secure_path
from aicodeagent.functions.internal.get_versioned_path import get_versioned_path


def save_backup(original_path, file_name, backup_dir=None):
    """
    Save a versioned backup of a file under <PROJECT_ROOT>/__ai_outputs__/backups by default.
    Returns the absolute path of the created backup.
    """
    project_root = get_project_root(__file__)
    if backup_dir is None:
        backup_dir = os.path.join(project_root, "__ai_outputs__", "backups")

    os.makedirs(backup_dir, exist_ok=True)
    file_name = os.path.basename(file_name)
    backup_path = get_secure_path(backup_dir, file_name)
    backup_path = get_versioned_path(backup_path)

    shutil.copy2(original_path, backup_path)
    return backup_path
