import os
import shutil
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.save_file import save_file
from functions.internal.get_secure_path import get_secure_path

def write_file(working_directory, file_path, content, run_id, dry_run=True, log_changes=True):
    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)

        if os.path.exists(full_path):
            if dry_run:
                save_file(source_path=full_path, content=content, log_changes=log_changes, backup=False, run_id=run_id)
                return ("dry run is set to true, no changes applied to the file, "
                        "see proposed changes in __ai_outputs__/diffs")
            
            save_file(source_path=full_path, content=content, log_changes=log_changes, run_id=run_id)
            with open(full_path, "w") as f:
                f.write(content)
            return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
        else:
            file_name = os.path.basename(full_path)
            save_file(file_name=file_name, content=content, log_changes=log_changes, run_id=run_id)
            with open(full_path, "w") as f:
                f.write(content)
            return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'

    except Exception as e:
        return "Error: " + str(e)
    