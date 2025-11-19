import os
import shutil

from aicodeagent.functions.core.get_secure_path import get_secure_path
from aicodeagent.functions.core.get_versioned_path import get_versioned_path


def save_backup(original_path, file_name, backup_dir):
    """
    Save a versioned backup of a file under <PROJECT_ROOT>/__ai_outputs__/backups by default.
    Returns the absolute path of the created backup.
    """
    os.makedirs(backup_dir, exist_ok=True)
    file_name = os.path.basename(file_name)
    backup_path = get_secure_path(backup_dir, file_name)
    backup_path = get_versioned_path(backup_path)

    shutil.copy2(original_path, backup_path)
    return backup_path
