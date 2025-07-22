import os
import shutil
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.internal.save_file import save_file
from functions.internal.clear_output_dirs import clear_output_dirs

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
TEST_FILE_PREFIX = "test_file_"

def reset_test_env():
    """Deletes and recreates the test environment folder."""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)

# === LOGGING WRAPPER ===
def log_test(number, description, test_function):
    print(f"\u25B6\uFE0F TEST {number}: {description}", flush=True)
    test_function()
    print(f"✅ TEST {number} PASSED", flush=True)

# === TEST DEFINITIONS ===

# NOTE: from now on, all files are saved inside __ai_outputs__/diffs or /backups,

# Test 1: Create a new file using provided content
def test_1_create_file_from_content():
    content = "Generated content"
    name = TEST_FILE_PREFIX+"generated.txt"
    save_file(file_name=name, content=content)
    path = os.path.abspath(f"__ai_outputs__/diffs/{name}")
    assert os.path.exists(path)
    with open(path) as f:
        assert f.read() == content

# Test 2: Copy an existing file
def test_2_copy_file():
    reset_test_env()
    name = TEST_FILE_PREFIX+"original.txt"
    original_path = os.path.join(TEST_DIR, "original.txt")
    with open(original_path, "w") as f:
        f.write("line 1\nline 2\nline 3\nline 4\n")
    
    modified_content = "line 1\nline 2 MODIFIED\nline 3\nline 4\n"
    
    save_file(file_name=name, source_path=original_path, content=modified_content)
    
    # Check backup created
    backup_path = os.path.abspath(f"__ai_outputs__/backups/{name}")
    assert os.path.exists(backup_path)
    
    # Check diff created
    diff_path = os.path.abspath(f"__ai_outputs__/diffs/{name}")
    assert os.path.exists(diff_path)
    
    with open(diff_path) as f:
        diff = f.read()
        assert "-line 2\n" in diff
        assert "+line 2 MODIFIED\n" in diff

# Test 3: Use basename of source_path if file_name is not provided
def test_3_source_path_only_uses_basename():
    reset_test_env()
    name = TEST_FILE_PREFIX+"auto.txt"
    auto_path = os.path.join(TEST_DIR,name)
    with open(auto_path, "w") as f:
        f.write("Auto content\nline2\n")

    with open(auto_path, "r") as f:
        content = f.read()

    save_file(source_path=auto_path, content=content)

    expected_backup = os.path.abspath(f"__ai_outputs__/backups/{name}")
    expected_diff = os.path.abspath(f"__ai_outputs__/diffs/{name}")

    # Check backup and diff both exist
    assert os.path.exists(expected_backup)
    assert os.path.exists(expected_diff)

    # Check backup content
    with open(expected_backup) as f:
        assert f.read() == content


# Test 4: Raise error if both source_path and content are None
def test_4_fail_if_source_and_content_missing():
    name = TEST_FILE_PREFIX+"auto.txt"
    try:
        save_file(file_name=name)
    except ValueError as e:
        assert "must be provided" in str(e)
    else:
        assert False, "Expected error was not raised"


# Test 5: Raise FileNotFoundError if source file doesn't exist
def test_5_fail_if_source_not_found():
    name = TEST_FILE_PREFIX+"ghost.txt"
    try:
        save_file(file_name=name, source_path="ghost_path.txt", content="placeholder")
    except ValueError as e:
        assert "Invalid usage" in str(e)
    else:
        assert False, "Expected ValueError was not raised"

# Test 6: Use custom filename when copying, persistent file
def test_6_custom_copy():
    reset_test_env()
    name = TEST_FILE_PREFIX+"custom.txt"
    source = os.path.join(TEST_DIR, "src.txt")
    with open(source, "w") as f:
        f.write("alpha\nbeta\ngamma\ndelta\n")

    new_content = "alpha\nbeta\nGAMMA MODIFIED\ndelta\n"
    
    save_file(file_name=name, source_path=source, content=new_content)

    # Check backup created
    backup_path = os.path.abspath(f"__ai_outputs__/backups/{name}")
    assert os.path.exists(backup_path)

    # Check diff created
    diff_path = os.path.abspath(f"__ai_outputs__/diffs/{name}")
    assert os.path.exists(diff_path)

    with open(diff_path) as f:
        diff = f.read()
        assert "-gamma\n" in diff
        assert "+GAMMA MODIFIED\n" in diff

# Test 7: Manual test, persistent file
def test_7_persistent_write():
    content = "Manual test content"
    name = TEST_FILE_PREFIX+"manual.txt"
    save_file(file_name=name, content=content)
    path = os.path.abspath(f"__ai_outputs__/diffs/{name}")
    assert os.path.exists(path)
    with open(path) as f:
        assert f.read() == content

# Try exit the working directory
def test_8_escape_attempt_fails():
    try:
        save_file(file_name="../escape.txt", content="Malicious attempt")
    except PermissionError as e:
        assert "Invalid filename" in str(e)
    else:
        assert False, "Expected PermissionError was not raised"

# === ORDERED TEST EXECUTION ===
if __name__ == "__main__":
    log_test(1, "create file from content", test_1_create_file_from_content)
    log_test(2, "copy existing file", test_2_copy_file)
    log_test(3, "source path only, name inferred", test_3_source_path_only_uses_basename)
    log_test(4, "fail if content and source are both None", test_4_fail_if_source_and_content_missing)
    log_test(5, "fail if source file doesn't exist", test_5_fail_if_source_not_found)
    log_test(6, "custom filename for copy", test_6_custom_copy)
    log_test(7, "manual persistent write", test_7_persistent_write)
    log_test(8, "prevent directory escape with ../ in filename", test_8_escape_attempt_fails)
    print("\U0001F389 All tests completed successfully!", flush=True)

    # Clear ai_ouputs sub directories if clear specified
    if "--clear" in sys.argv:
        clear_output_dirs()
