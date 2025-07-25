import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.write_file import  write_file
from functions.internal.reset_test_env import reset_test_env
from functions.internal.init_run_session import init_run_session
from functions.internal.clear_output_dirs import clear_output_dirs

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
# Get the run_ids to create the backup/diffs/logs directory 
run_id = init_run_session()

# Manual test write_file
from datetime import datetime

print("\n==== write_file TESTS ====\n")

# Setup
working_dir = TEST_DIR
existing_file = "test_script.py"
new_file = "new_generated.py"
outside_path = "../main.py"
content_v1 = f"# First version at {datetime.now()}\nprint('Hello')\n"
content_v2 = f"# Modified version at {datetime.now()}\nprint('Modified')\n"

# Create the existing file to be modified in test 1 and 2
with open(os.path.join(working_dir, existing_file), "w") as f:
    f.write(content_v1)

# 1. Dry run on existing file
print("\u25B6\uFE0F Test 1: dry run on existing file")
result_1 = write_file(working_dir, existing_file, content_v2, dry_run=True, run_id=run_id )
print(result_1)

# 2. Actual write on existing file
print("\n\u25B6\uFE0F Test 2: actual write on existing file")
result_2 = write_file(working_dir, existing_file, content_v2, dry_run=False, run_id=run_id )
print(result_2)

# 3. Write to a new file
print("\n\u25B6\uFE0F Test 3: write to new file")
result_3 = write_file(working_dir, new_file, content_v1, dry_run=False, run_id=run_id )
print(result_3)

# 4. Attempt to write outside working directory
print("\n\u25B6\uFE0F Test 4: path escape attempt")
result_4 = write_file(working_dir, outside_path, content_v1, run_id=run_id )
print(result_4)

# 5. Attempt to write into a non exististing directory
print("\n\u25B6\uFE0F Test 5: Non existing directory")
result_5 = write_file("Fake_directory", new_file, content_v1, run_id=run_id )
print(result_5)

# 6. Disable logging
print("\n\u25B6\uFE0F Test 6: write with log_changes=False")
result_6 = write_file(working_dir, new_file, "# silent\n", log_changes=False, run_id=run_id )
print(result_6)

# Clear ai_ouputs sub directories if clear specified
if "--clear" in sys.argv:
    clear_output_dirs()
