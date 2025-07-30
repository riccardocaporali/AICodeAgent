import os
from functions.internal.get_secure_path import get_secure_path
from functions.internal.get_versioned_path import get_versioned_path

def save_diffs(diff_dir, diff_content, file_name):
    os.makedirs(diff_dir, exist_ok=True)
    diff_path = get_secure_path(diff_dir, file_name)
    diff_path = get_versioned_path(diff_path)

    with open(diff_path, "w", encoding="utf-8") as f:
        f.writelines(diff_content)