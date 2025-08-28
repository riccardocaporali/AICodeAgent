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
run_id = init_run_session()

# Paths ai_outputs
RUN_DIR = os.path.join("__ai_outputs__", run_id)
LOG_PATH = os.path.join(RUN_DIR, "actions.log")
SUMMARY_PATH = os.path.join(RUN_DIR, "summary.txt")

# === SETUP: crea file di esempio ===
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

def print_logs_and_summary_tail(label):
    print(f"\n— {label} | actions.log (tail) —")
    print(read_tail(LOG_PATH, n=20))
    print(f"\n— {label} | summary.txt (tail) —")
    print(read_tail(SUMMARY_PATH, n=40))

# === TESTS ===
print("\n==== get_file_content TESTS ====\n")

# Snapshot iniziale per confrontare poi se errori hanno scritto (non dovrebbero)
before_log = read_tail(LOG_PATH, n=1000)
before_summary = read_tail(SUMMARY_PATH, n=2000)

# 1) Read valid file (summary and logs generated)
res1 = get_file_content(
    working_directory=TEST_DIR,
    file_path="hello.txt",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "hello.txt"},
    log_changes=True
)
print_test_result(1, "read valid file (should log and summary)", res1)
print_logs_and_summary_tail("AFTER TEST 1")
# Snapshot after test 1
after1_log = read_tail(LOG_PATH, n=1000)
after1_summary = read_tail(SUMMARY_PATH, n=2000)

# 2) Read not existent file, error is expected (no summary and logs present)
res2 = get_file_content(
    working_directory=TEST_DIR,
    file_path="nonexistent.txt",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "nonexistent.txt"},
    log_changes=True
)
print_test_result(2, "read nonexistent file (should return error)", res2)

# 3) Path trasversal, error is expected (no summary and logs present)
res3 = get_file_content(
    working_directory=TEST_DIR,
    file_path="../secrets.py",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "../secrets.py"},
    log_changes=True
)
print_test_result(3, "path escape attempt (should return error)", res3)
after3_log = read_tail(LOG_PATH, n=1000)
after3_summary = read_tail(SUMMARY_PATH, n=2000)

# Check the files tail, only first test should write in logs and summary
after_log = read_tail(LOG_PATH, n=1000)
after_summary = read_tail(SUMMARY_PATH, n=2000)

print("\n— Check no new log lines after errors —")
print("Logs changed after errors:",
      "YES" if after3_log != after1_log else "NO (as expected)")

print("\n— Check no new summary lines after errors —")
print("Summary changed after errors:",
      "YES" if after3_summary != after1_summary else "NO (as expected)")
# Clear ai_outputs sub directories if requested
if "--clear" in sys.argv:
    clear_output_dirs()