import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.get_secure_path import get_secure_path
from functions.internal.save_summary_entry import save_summary_entry
from functions.internal.save_logs import save_logs

def get_file_content(working_directory, file_path, run_id, function_args=None):  
    # Function name
    function_name = "get_file_content"
    # Define summary directory
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    # Get the file name 
    file_name = "unknown"

    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)
        # Get the file name 
        file_name = os.path.basename(full_path)
        # File content extraction
        MAX_CHARS = 10000
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            file_content_string = f.read(MAX_CHARS+1)
            if len(file_content_string) > MAX_CHARS:
                file_content_string = file_content_string[:-1] + f'\n\n[...File "{file_path}" truncated at 10000 characters]'
 
        # Save logs
        log_line = save_logs(file_name, base_dir, function_name,result="OK")

        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)

        return file_content_string 
    
    except Exception as e:
        details = str(e)
        # Save logs
        log_line = save_logs(file_name, base_dir, function_name,result="ERROR",details=details)
        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)

        return "Error: " + str(e)