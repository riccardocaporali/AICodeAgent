import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.run_python import run_python_file
from functions.internal.reset_test_env import reset_test_env
from functions.internal.init_run_session import init_run_session
from functions.internal.clear_output_dirs import clear_output_dirs

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
run_id = init_run_session()

# Paths for ai_outputs
RUN_DIR = os.path.join("__ai_outputs__", run_id)
LOG_PATH = os.path.join(RUN_DIR, "actions.log")
SUMMARY_PATH = os.path.join(RUN_DIR, "summary.txt")

# === SETUP: create scripts to be executed ===
# 1) Script that creates a file
code_create = """\
import os
TEST_DIR = "."
os.makedirs(TEST_DIR, exist_ok=True)
file_path = os.path.join(TEST_DIR, "hello_created.txt")
with open(file_path, "w", encoding="utf-8") as f:
    f.write("Hello, world!\\nThis is a test file.")
"""
os.makedirs(TEST_DIR, exist_ok=True)
with open(os.path.join(TEST_DIR, "create_hello.py"), "w", encoding="utf-8") as f:
    f.write(code_create)

# 2) Script that sleeps for 40 seconds (to trigger timeout)
code_sleep = """\
import time
time.sleep(40)
"""
with open(os.path.join(TEST_DIR, "sleep_long.py"), "w", encoding="utf-8") as f:
    f.write(code_sleep)

# === HELPERS ===
def print_test_result(n, description, result):
    print(f"\n▶️ Test {n}: {description}")
    print(result)

def read_all(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def read_tail(path, n=20):
    if not os.path.isfile(path):
        return "<missing>"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:]).rstrip()

print("\n==== run_python_file TESTS ====\n")

# Snapshot before
before_log = read_all(LOG_PATH)
before_summary = read_all(SUMMARY_PATH)

# 1) SUCCESS: run valid file
res1 = run_python_file(
    working_directory=TEST_DIR,
    file_path="create_hello.py",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "create_hello.py"},
    log_changes=True
)
print_test_result(1, "run valid file (should log and summary)", res1)

# Snapshot after test 1
after1_log = read_all(LOG_PATH)
after1_summary = read_all(SUMMARY_PATH)

# Verify created file
created_file = os.path.join(TEST_DIR, "hello_created.txt")
print("\n— File creation check —")
if os.path.isfile(created_file):
    with open(created_file, "r", encoding="utf-8") as f:
        content = f.read().strip()
    print(f"hello_created.txt found with content:\n{content}")
else:
    print("hello_created.txt was NOT created ❌")

# 2) ERROR: run nonexistent file
res2 = run_python_file(TEST_DIR, "nonexistent.txt", run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "nonexistent.txt"},
    log_changes=True
)
print_test_result(2, "nonexistent file (should return error)", res2)

# 3) ERROR: path traversal
res3 = run_python_file(TEST_DIR, "../secrets.py", run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "../secrets.py"},
    log_changes=True
)
print_test_result(3, "path traversal (should return error)", res3)

# 4) TIMEOUT: run script that sleeps 40s
print("....wait 30s for time out")
res4 = run_python_file(
    working_directory=TEST_DIR,
    file_path="sleep_long.py",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "sleep_long.py"},
    log_changes=True
)
print_test_result(4, "long sleep (should timeout)", res4)

# Snapshot after test 4
after4_log = read_all(LOG_PATH)
after4_summary = read_all(SUMMARY_PATH)

# === CHECKS ===
print("\n— CHECK 1: Did Test 1 write something new? —")
print("Logs written:", "YES" if after1_log != before_log else "NO ❌")
print("Summary written:", "YES" if after1_summary != before_summary else "NO ❌")

print("\n— CHECK 2: Timeout recorded in logs and summary —")
print("Timeout in logs:", "YES" if "TIMEOUT" in after4_log or "timed out" in after4_log else "NO ❌")
print("Timeout in summary:", "YES" if "TIMEOUT" in after4_summary or "timed out" in after4_summary else "NO ❌")

# Optional clear
if "--clear" in sys.argv:
    clear_output_dirs()