import os
import shutil
from functions.internal.get_project_root import get_project_root

def reset_test_env(test_dir_name: str = "__test_env__") -> str:
    """
    Delete and recreate the test environment folder at the project root.
    Preserves .gitkeep if present.
    Returns absolute path of the reset test directory.
    """
    base_dir = get_project_root(__file__)
    test_dir = os.path.join(base_dir, test_dir_name)
    os.makedirs(test_dir, exist_ok=True)

    for item in os.listdir(test_dir):
        full_path = os.path.join(test_dir, item)
        if os.path.isfile(full_path) and item == ".gitkeep":
            continue
        if os.path.isfile(full_path):
            os.remove(full_path)
        else:
            shutil.rmtree(full_path, ignore_errors=True)

    return test_dir