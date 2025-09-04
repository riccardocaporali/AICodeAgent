import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.save_file import save_file
from functions.internal.get_secure_path import get_secure_path
from functions.internal.save_summary_entry import save_summary_entry
from functions.internal.save_logs import save_logs

def write_file_confirmed(working_directory, file_path, content, run_id, function_args=None, dry_run=False):
    # Function name
    function_name = "write_file_confirmed"
    # Define summary directory
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    # Get the file name 
    file_name = "unknown"

    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)

        # Stop the function and save changes if dry run. Save file update the logs and summary
        if os.path.exists(full_path):
            save_file(run_id, function_name, function_args, dry_run=dry_run, source_path=full_path, content=content)
            if dry_run:
                return ("dry run is set to true, no changes applied to the file, "
                    "see proposed changes in __ai_outputs__")
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
        else:
            file_name = os.path.basename(full_path)
            save_file(run_id, function_name, function_args, dry_run=dry_run, file_name=file_name, content=content)
            if dry_run:
                return ("dry run is set to true, new file not created, "
                        "see proposed changes in __ai_outputs__")
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f'Successfully wrote to "{file_path}" ({len(content)} characters written)' 

    except Exception as e:
        details = str(e)
        # Save logs
        log_line = save_logs(file_name, base_dir, function_name,result="ERROR",details=details)
        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)
        return "Error: " + str(e)
    