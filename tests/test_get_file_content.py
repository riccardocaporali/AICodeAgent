import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.get_file_content import get_file_content
from functions.internal.reset_test_env import reset_test_env
from functions.internal.init_run_session import init_run_session
from functions.internal.clear_output_dirs import clear_output_dirs

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
# Get the run_ids to create the backup/diffs/logs directory 
run_id = init_run_session()

# === SETUP: crea file di esempio ===
file_path = os.path.join(TEST_DIR, "hello.txt")
with open(file_path, "w") as f:
    f.write("Hello, world!\nThis is a test file.")

# === HELPER ===
def print_test_result(n, description, result):
    print(f"\n▶️ Test {n}: {description}")
    print(result)

# === TESTS ===

print("\n==== get_file_content TESTS ====\n")

# 1. Lettura file valido
res1 = get_file_content(
    working_directory=TEST_DIR,
    file_path="hello.txt",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "hello.txt"},
    log_changes=True
)
print_test_result(1, "read valid file (should log and summary)", res1)

# 2. File non esistente
res2 = get_file_content(
    working_directory=TEST_DIR,
    file_path="nonexistent.txt",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "nonexistent.txt"},
    log_changes=True
)
print_test_result(2, "read nonexistent file (should return error)", res2)

# 3. Tentativo di path traversal
res3 = get_file_content(
    working_directory=TEST_DIR,
    file_path="../secrets.py",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "../secrets.py"},
    log_changes=True
)
print_test_result(3, "path escape attempt", res3)

# Clear ai_ouputs sub directories if clear specified
if "--clear" in sys.argv:
    clear_output_dirs()