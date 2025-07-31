import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.save_file import save_file
from functions.internal.get_secure_path import get_secure_path

def write_file_preview(working_directory, file_path, content, run_id, function_args=None, log_changes=True):
    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)

        # Additional variables
        function_name = "write_file_preview"
        if os.path.exists(full_path):
            save_file(run_id, function_name, function_args, source_path=full_path, content=content, log_changes=log_changes)
            return f'Save proposed changes to "{file_path}" in __ai_outputs__ ({len(content)} characters to be written)'
        
        else:
            file_name = os.path.basename(full_path)
            save_file(run_id, function_name, function_args, file_name=file_name, content=content, log_changes=log_changes)
            return f'Save proposed creation of "{file_path}" in __ai_outputs__ ({len(content)} characters to be written)'

    except Exception as e:
        return "Error: " + str(e)
    