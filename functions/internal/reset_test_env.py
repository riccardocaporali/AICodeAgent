import os
import shutil

def reset_test_env(TEST_DIR):
    """Deletes and recreates the test environment folder, preserving .gitkeep if present."""
    os.makedirs(TEST_DIR, exist_ok=True)
    for item in os.listdir(TEST_DIR):
        full_path = os.path.join(TEST_DIR, item)
        if os.path.isfile(full_path) and item == ".gitkeep":
            continue  # don't delete .gitkeep
        if os.path.isfile(full_path):
            os.remove(full_path)
        else:
            shutil.rmtree(full_path)