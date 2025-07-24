import os
import shutil
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.save_file import save_file
from functions.internal.clear_output_dirs import clear_output_dirs
from functions.internal.reset_test_env import reset_test_env
from functions.internal.init_run_session import init_run_session

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
TEST_FILE_PREFIX = "test_file_"
reset_test_env(TEST_DIR)
# Get the run_ids to create the backup/diffs/logs directory 
run_id = init_run_session()

# === LOGGING WRAPPER ===
def log_test(number, description, test_function):
    print(f"\n\u25B6\uFE0F TEST {number}: {description}", flush=True)
    test_function()
    print(f"✅ TEST {number} PASSED", flush=True)

# === TEST DEFINITIONS ===

# NOTE: from now on, all files are saved inside __ai_outputs__/diffs or /backups,

# Test 1: Create a new file using provided content
def test_1_create_file_from_content():
    content = "Generated content"
    name = TEST_FILE_PREFIX+"generated.txt"
    save_file(file_name=name, content=content, run_id=run_id)
    path = os.path.abspath(f"__ai_outputs__/diffs/{run_id}/{name}")
    assert os.path.exists(path)
    with open(path) as f:
        assert f.read() == content

# Test 2: Copy an existing file
def test_2_copy_file():
    reset_test_env(TEST_DIR)
    name = TEST_FILE_PREFIX+"original.txt"
    original_path = os.path.join(TEST_DIR, "original.txt")
    with open(original_path, "w") as f:
        f.write("line 1\nline 2\nline 3\nline 4\n")
    
    modified_content = "line 1\nline 2 MODIFIED\nline 3\nline 4\n"
    
    save_file(file_name=name, source_path=original_path, content=modified_content, run_id=run_id)
    
    # Check backup created
    backup_path = os.path.abspath(f"__ai_outputs__/backups/{run_id}/{name}")
    assert os.path.exists(backup_path)
    
    # Check diff created
    diff_path = os.path.abspath(f"__ai_outputs__/diffs/{run_id}/{name}")
    assert os.path.exists(diff_path)
    
    with open(diff_path) as f:
        diff = f.read()
        assert "-line 2\n" in diff
        assert "+line 2 MODIFIED\n" in diff

# Test 3: Use basename of source_path if file_name is not provided
def test_3_source_path_only_uses_basename():
    reset_test_env(TEST_DIR)
    name = TEST_FILE_PREFIX+"auto.txt"
    auto_path = os.path.join(TEST_DIR,name)
    with open(auto_path, "w") as f:
        f.write("Auto content\nline2\n")

    with open(auto_path, "r") as f:
        content = f.read()

    save_file(source_path=auto_path, content=content, run_id=run_id)

    expected_backup = os.path.abspath(f"__ai_outputs__/backups/{run_id}/{name}")
    expected_diff = os.path.abspath(f"__ai_outputs__/diffs/{run_id}/{name}")

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
        save_file(file_name=name, run_id=run_id)
    except ValueError as e:
        assert "must be provided" in str(e)
    else:
        assert False, "Expected error was not raised"


# Test 5: Raise FileNotFoundError if source file doesn't exist
def test_5_fail_if_source_not_found():
    name = TEST_FILE_PREFIX+"ghost.txt"
    try:
        save_file(file_name=name, source_path="ghost_path.txt", content="placeholder", run_id=run_id)
    except ValueError as e:
        assert "Invalid usage" in str(e)
    else:
        assert False, "Expected ValueError was not raised"

# Test 6: Try exit the working directory
def test_6_escape_attempt_fails():
    try:
        save_file(file_name="../escape.txt", content="Malicious attempt", run_id=run_id)
    except PermissionError as e:
        assert "Invalid filename" in str(e)
    else:
        assert False, "Expected PermissionError was not raised"

# Test 7: Disable logging
def test_7_disable_logging():
    content = "Content with no logging"
    name = TEST_FILE_PREFIX + "no_log.txt"

    save_file(file_name=name, content=content, run_id=run_id, log_changes=False)

    try:
        log_path = os.path.abspath(f"__ai_outputs__/logs/{run_id}/actions.log")
        with open(log_path) as f:
            log = f.read()
            assert name not in log, f"Log entry found for {name} even though log_changes=False"
    except FileNotFoundError:
        # OK: log was not created
        pass

# Test 8: Disable backup
def test_8_disable_backup():
    reset_test_env(TEST_DIR)
    name = TEST_FILE_PREFIX + "no_backup.txt"
    original_path = os.path.join(TEST_DIR, name)
    with open(original_path, "w") as f:
        f.write("original content\n")

    modified_content = "new content\n"

    save_file(file_name=name, source_path=original_path, content=modified_content, run_id=run_id, backup=False)

    backup_path = os.path.abspath(f"__ai_outputs__/backups/{run_id}/{name}")
    assert not os.path.exists(backup_path)

# Test 9: Overwrite same file multiple times, versioning check
def test_9_multiple_overwrites():
    reset_test_env(TEST_DIR)
    name = TEST_FILE_PREFIX + "versioned.txt"
    path = os.path.join(TEST_DIR, name)

    # Primo contenuto
    with open(path, "w") as f:
        f.write("v1\n")
    save_file(file_name=name, source_path=path, content="v2\n", run_id=run_id)
    save_file(file_name=name, source_path=path, content="v3\n", run_id=run_id)

    # Ci devono essere almeno 2 versioni nella cartella diff (es: file.txt, file_1.txt)
    diff_dir = os.path.abspath(f"__ai_outputs__/diffs/{run_id}")
    base = os.path.splitext(name)[0]  # "test_file_versioned"
    matches = [f for f in os.listdir(diff_dir) if f.startswith(base)]
    assert len(matches) >= 2, f"Expected at least 2 diff versions, got {matches}"

# === ORDERED TEST EXECUTION ===
if __name__ == "__main__":
    log_test(1, "create file from content", test_1_create_file_from_content)
    log_test(2, "copy existing file", test_2_copy_file)
    log_test(3, "source path only, name inferred", test_3_source_path_only_uses_basename)
    log_test(4, "fail if content and source are both None", test_4_fail_if_source_and_content_missing)
    log_test(5, "fail if source file doesn't exist", test_5_fail_if_source_not_found)
    log_test(6, "prevent directory escape with ../ in filename", test_6_escape_attempt_fails)
    log_test(7, "disable logging", test_7_disable_logging)
    log_test(8, "disable backup", test_8_disable_backup)
    log_test(9, "multiple overwrites trigger versioning", test_9_multiple_overwrites)
    print("\n✅ All tests completed successfully!\n", flush=True)

    # Clear ai_ouputs sub directories if clear specified
    if "--clear" in sys.argv:
        clear_output_dirs()
