import os
import shutil
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.save_file import save_file

def write_file(working_directory, file_path, content, run_id, dry_run=True, log_changes=True):
    try:
        # Define the selecte file and directory full path
        full_path = os.path.abspath(os.path.join(working_directory, file_path))
        directory_path = os.path.abspath(working_directory)

        # Check if the selected file is outside of the working directory --> Error
        if not full_path.startswith(os.path.abspath(directory_path)):
            return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'
        
        # Check if the workind directory exist
        if not os.path.isdir(os.path.dirname(full_path)):
            return f'Error: directory \"{os.path.dirname(full_path)}\" does not exist.'
        
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
    