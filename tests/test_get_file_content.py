import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.functions.llm_calls.get_file_content import get_file_content
from src.functions.internal.reset_test_env import reset_test_env
from src.functions.internal.init_run_session import init_run_session
from src.functions.internal.clear_output_dirs import clear_output_dirs

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
run_id = init_run_session()

# Paths ai_outputs
RUN_DIR = os.path.join("__ai_outputs__", run_id)

# === SETUP: create sample file ===
os.makedirs(TEST_DIR, exist_ok=True)
file_path = os.path.join(TEST_DIR, "hello.txt")
with open(file_path, "w", encoding="utf-8") as f:
    f.write("Hello, world!\nThis is a test file.")

# === HELPERS ===
def print_test_result(n, description, result):
    print(f"\n▶️ Test {n}: {description}")
    print(result)

def read_tail(path, n=20):
    if not os.path.isfile(path):
        return "<missing>"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:]).rstrip()

# === TESTS ===
print("\n==== get_file_content TESTS ====\n")

# 1) Read valid file (summary and logs generated)
res1 = get_file_content(
    working_directory=TEST_DIR,
    file_path="hello.txt",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "hello.txt"},
)
print_test_result(1, "read valid file (should log and summarize)", res1)

# 2) Read nonexistent file, error is expected
res2 = get_file_content(
    working_directory=TEST_DIR,
    file_path="nonexistent.txt",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "nonexistent.txt"},
)
print_test_result(2, "read nonexistent file (should return error)", res2)

# 3) Path traversal, error is expected
res3 = get_file_content(
    working_directory=TEST_DIR,
    file_path="../secrets.py",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "../secrets.py"},
)
print_test_result(3, "path escape attempt (should return error)", res3)

# Clear ai_outputs subdirectories if requested
if "--clear" in sys.argv:
    clear_output_dirs()