import os
from aicodeagent.functions.internal.save_file import save_file
from aicodeagent.functions.internal.get_secure_path import get_secure_path
from aicodeagent.functions.internal.save_summary_entry import save_summary_entry
from aicodeagent.functions.internal.save_logs import save_logs


def propose_changes(working_directory, file_path, content, run_id, function_args=None):
    # Function name
    function_name = "propose_changes"
    # Define summary directory
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    # Get the file name 
    file_name = "unknown"

    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)

        if os.path.exists(full_path):
            save_file(run_id, function_name, function_args, source_path=full_path, content=content)
            return f'Save proposed changes to "{file_path}" in __ai_outputs__ ({len(content)} characters to be written)'
        
        else:
            file_name = os.path.basename(full_path)
            save_file(run_id, function_name, function_args, file_name=file_name, content=content)
            return f'Save proposed creation of "{file_path}" in __ai_outputs__ ({len(content)} characters to be written)'

    except Exception as e:
        details = str(e)
        # Save logs
        log_line = save_logs(file_name, base_dir, function_name,result="ERROR",details=details)
        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)
        return "Error: " + str(e)
    