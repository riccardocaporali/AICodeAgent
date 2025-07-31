import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.write_file_preview import  write_file_preview
from functions.internal.reset_test_env import reset_test_env
from functions.internal.init_run_session import init_run_session
from functions.internal.clear_output_dirs import clear_output_dirs

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
# Get the run_ids to create the backup/diffs/logs directory 
run_id = init_run_session()

print("\n==== write_file TESTS ====\n")

# Setup
working_dir = TEST_DIR
existing_file = "test_script.py"
new_file = "new_generated.py"
outside_path = "../main.py"
content_v1 = f"# First version at {datetime.now()}\n('Test 1: propose changes to an existing file')\n"
content_v2 = f"# Modified version at {datetime.now()}\n('Test 2: propose creation of a new file')\n"
content_v3 = f"# First version at {datetime.now()}\n('Test 3: path escape attempt')\n"
content_v4 = f"# First version at {datetime.now()}\n('Test 5: write with log_changes=False')\n"
content_v5 = f"# First version at {datetime.now()}\n('Test 6: verbose mode with function_args')\n"
content_v6 = f"# Modified version at {datetime.now()}\n('Test 7: verbose mode with function_args')\n"

# Create the existing file to be modified in test 1 and 2
with open(os.path.join(working_dir, existing_file), "w") as f:
    f.write(content_v1)

# 1. Propose changes to an existing file
print("\n\u25B6\uFE0F Test 1: propose changes to an existing file")
result_1 = write_file_preview(working_dir, existing_file, content_v2, run_id=run_id )
print(result_1)

# 2. Propose creation of a new file
print("\n\u25B6\uFE0F Test 2: propose creation of a new file")
result_2 = write_file_preview(working_dir, new_file, content_v1, run_id=run_id )
print(result_2)

# 3. Attempt to write outside working directory
print("\n\u25B6\uFE0F Test 3: path escape attempt")
result_3 = write_file_preview(working_dir, outside_path, content_v1, run_id=run_id )
print(result_3)

# 4. Attempt to write into a non existing directory
print("\n\u25B6\uFE0F Test 4: Non existing directory")
result_4 = write_file_preview("Fake_directory", new_file, content_v1, run_id=run_id )
print(result_4)

# 5. Disable logging
print("\n\u25B6\uFE0F Test 5: write with log_changes=False")
result_5 = write_file_preview(working_dir, new_file, content_v4, log_changes=False, run_id=run_id )
print(result_5)

# 6. Verbose mode with function_args manually passed, propose creation of a new file
print("\n\u25B6\uFE0F Test 6: verbose mode with function_args")
manual_args = {
    "working_directory": working_dir,
    "file_path": "manual_verbose.py",
    "content": content_v5,
    "run_id": run_id,
    "log_changes": True,
}

result_6 = write_file_preview(
    working_directory=manual_args["working_directory"],
    file_path=manual_args["file_path"],
    content=manual_args["content"],
    run_id=manual_args["run_id"],
    log_changes=manual_args["log_changes"],
    function_args=manual_args
)
print(result_6)

# 7. Verbose mode with function_args, second proposal version
print("\n\u25B6\uFE0F Test 7: verbose mode with function_args")
manual_args = {
    "working_directory": working_dir,
    "file_path": "manual_verbose.py",
    "content": content_v6,
    "run_id": run_id,
    "log_changes": True,
}

result_7 = write_file_preview(
    working_directory=manual_args["working_directory"],
    file_path=manual_args["file_path"],
    content=manual_args["content"],
    run_id=manual_args["run_id"],
    log_changes=manual_args["log_changes"],
    function_args=manual_args
)
print(result_7)

# Clear ai_ouputs sub directories if clear specified
if "--clear" in sys.argv:
    clear_output_dirs()