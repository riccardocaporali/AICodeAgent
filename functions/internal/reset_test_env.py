import os
import shutil

def reset_test_env(TEST_DIR):
    """Deletes and recreates the test environment folder."""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)