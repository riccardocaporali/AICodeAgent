import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.get_files_info import get_files_info
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

# === SETUP: Create file and subfolder ===
# __test_env__/
# ├─ example.txt
# └─ pkg/
#     └─ module.py
os.makedirs(os.path.join(TEST_DIR, "pkg"), exist_ok=True)

with open(os.path.join(TEST_DIR, "example.txt"), "w", encoding="utf-8") as f:
    f.write("print('hello world')\n")

with open(os.path.join(TEST_DIR, "pkg", "module.py"), "w", encoding="utf-8") as f:
    f.write("# module file\n")

# === HELPERS ===
def print_test_result(n, description, result):
    print(f"\n▶️ Test {n}: {description}")
    print(result)

def read_tail(path, n=40):
    if not os.path.isfile(path):
        return "<missing>"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:]).rstrip()

def print_logs_and_summary_tail(label):
    print(f"\n— {label} | actions.log (tail) —")
    print(read_tail(LOG_PATH, n=40))
    print(f"\n— {label} | summary.txt (tail) —")
    print(read_tail(SUMMARY_PATH, n=80))

print("\n==== get_files_info TESTS ====\n")

# Snapshot iniziale (solo per mostrare che alla fine qualcosa è stato scritto)
before_log = read_tail(LOG_PATH, n=2000)
before_summary = read_tail(SUMMARY_PATH, n=4000)

# 1) SUCCESS: list contents of pkg/
res1 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="pkg",
    function_args={"working_directory": TEST_DIR, "directory": "pkg"},
    log_changes=True
)
print_test_result(1, "list contents of pkg/", res1)
print_logs_and_summary_tail("AFTER TEST 1")
after1_log = read_tail(LOG_PATH, n=2000)
after1_summary = read_tail(SUMMARY_PATH, n=4000)

# 2) SUCCESS: list contents of base test directory
res2 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory=".", 
    function_args={"working_directory": TEST_DIR, "directory": "."},
    log_changes=True
)
print_test_result(2, "list contents of base test directory", res2)
print_logs_and_summary_tail("AFTER TEST 2")
after2_log = read_tail(LOG_PATH, n=2000)
after2_summary = read_tail(SUMMARY_PATH, n=4000)

# 3) ERROR: attempt to access outside of test_env (no logs or summary)
res3 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="../main.py",
    function_args={"working_directory": TEST_DIR, "directory": "../main.py"},
    log_changes=True
)
print_test_result(3, "attempt to escape working directory", res3)

# 4) ERROR: non-existent subdir in test_env (no logs or summary)
res4 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="ghost_folder",
    function_args={"working_directory": TEST_DIR, "directory": "ghost_folder"},
    log_changes=True
)
print_test_result(4, "non-existent folder in test_env", res4)

# Snapshot finale
after4_log = read_tail(LOG_PATH, n=2000)
after4_summary = read_tail(SUMMARY_PATH, n=4000)

# --- Verifiche ---
print("\n— Baseline vs End | Something was written? —")
print("Logs changed since start:", "YES" if after4_log != before_log else "NO (unexpected)")
print("Summary changed since start:", "YES" if after4_summary != before_summary else "NO (unexpected)")

print("\n— Only succesfull tests wrote? —")
print("No extra logs after errors:", "YES" if after4_log == after2_log else "NO (unexpected)")
print("No extra summary after errors:", "YES" if after4_summary == after2_summary else "NO (unexpected)")

# (facoltativo) check contenuto atteso nei log
print("\n— Correct markers present? —")
print("Log contiene 'Get content of directory:' (pkg o base):", "YES" if "Get content of directory:" in after2_log else "NO")
print("Summary contiene header funzione:", "YES" if "### FUNCTION: get_files_info" in after2_summary else "NO")

# Clear ai_outputs se richiesto
if "--clear" in sys.argv:
    clear_output_dirs()