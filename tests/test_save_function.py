import os
import shutil
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.internal.save_file import save_file

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
ORIGINAL_FILE = os.path.join(TEST_DIR, "original.txt")
BACKUP_DIR = os.path.join(TEST_DIR, "backups")
CONTENT_DIR = os.path.join(TEST_DIR, "generated")

def reset_test_env():
    """Deletes and recreates the test environment folder."""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)

# === LOGGING WRAPPER ===
def log_test(number, description, test_function):
    print(f"▶️ TEST {number}: {description}", flush=True)
    test_function()
    print(f"✅ TEST {number} PASSED", flush=True)

# === TEST DEFINITIONS ===

def test_1_copy_file():
    reset_test_env()
    with open(ORIGINAL_FILE, "w") as f:
        f.write("This is a test file.")
    save_file(BACKUP_DIR, file_name="original.txt", source_path=ORIGINAL_FILE)
    copied = os.path.join(BACKUP_DIR, "original.txt")
    assert os.path.exists(copied)
    with open(copied) as f:
        assert f.read() == "This is a test file."

def test_2_create_file_from_content():
    reset_test_env()
    content = "Generated content"
    save_file(CONTENT_DIR, file_name="generated.txt", content=content)
    path = os.path.join(CONTENT_DIR, "generated.txt")
    assert os.path.exists(path)
    with open(path) as f:
        assert f.read() == content

def test_3_fail_if_nothing_provided():
    reset_test_env()
    try:
        save_file(None, CONTENT_DIR)
    except Exception as e:
        assert "must be provided" in str(e)
    else:
        assert False, "Expected error was not raised"

def test_4_fail_if_filename_missing_and_no_source():
    reset_test_env()
    try:
        save_file(CONTENT_DIR, file_name=None, source_path=None)
    except ValueError as e:
        assert "file_name must be specified" in str(e)
    else:
        assert False, "Expected error was not raised"

def test_5_fail_if_source_path_not_found():
    reset_test_env()
    try:
        save_file(BACKUP_DIR, file_name="non_existent.txt", source_path="__test_env__/this_file_does_not_exist.txt")
    except FileNotFoundError:
        pass
    else:
        assert False, "Expected FileNotFoundError was not raised"

def test_6_custom_copy_file():
    reset_test_env()
    custom_file = os.path.join(TEST_DIR, "custom.txt")
    with open(custom_file, "w") as f:
        f.write("This is a different file.")
    save_file(BACKUP_DIR, file_name="custom_copy.txt", source_path=custom_file)
    copied = os.path.join(BACKUP_DIR, "custom_copy.txt")
    assert os.path.exists(copied)
    with open(copied) as f:
        assert f.read() == "This is a different file."

def test_7_persistent_write():
    # No reset: file should persist for manual inspection
    content = "Persistent content for manual verification"
    save_file(CONTENT_DIR, file_name="persistent.txt", content=content)
    path = os.path.join(CONTENT_DIR, "persistent.txt")
    assert os.path.exists(path)
    with open(path) as f:
        assert f.read() == content

# === ORDERED TEST EXECUTION ===
if __name__ == "__main__":
    log_test(1, "copy an existing file", test_1_copy_file)
    log_test(2, "create a new file from content", test_2_create_file_from_content)
    log_test(3, "fail when both content and source_path are None", test_3_fail_if_nothing_provided)
    log_test(4, "fail when file_name is missing and no source_path", test_4_fail_if_filename_missing_and_no_source)
    log_test(5, "fail when source_path does not exist", test_5_fail_if_source_path_not_found)
    log_test(6, "copy a different file without overwriting test 1", test_6_custom_copy_file)
    log_test(7, "write persistent file without reset (manual check)", test_7_persistent_write)

    print("🎉 All tests completed successfully!", flush=True)