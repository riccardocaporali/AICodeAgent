import os

from aicodeagent.functions.core.get_secure_path import get_secure_path
from aicodeagent.functions.core.save_file import save_file
from aicodeagent.functions.core.save_logs import save_logs
from aicodeagent.functions.core.save_summary_entry import save_summary_entry
from aicodeagent.functions.fs.get_project_root import get_project_root


def propose_changes(
    working_directory, file_path, content, run_id, function_args=None, output_root=None
):
    # Function name
    function_name = "propose_changes"
    # Define summary directory
    project_root = (
        str(output_root) if output_root is not None else get_project_root(__file__)
    )
    base_dir = os.path.join(project_root, "__ai_outputs__", run_id)
    # Get the file name
    file_name = "unknown"

    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)

        if os.path.exists(full_path):
            save_file(
                run_id,
                function_name,
                function_args,
                source_path=full_path,
                content=content,
                output_root=output_root,
            )
            return f'Save proposed changes to "{file_path}" in __ai_outputs__ ({len(content)} characters to be written)'

        else:
            file_name = os.path.basename(full_path)
            save_file(
                run_id,
                function_name,
                function_args,
                file_name=file_name,
                content=content,
                output_root=output_root,
            )
            return f'Save proposed creation of "{file_path}" in __ai_outputs__ ({len(content)} characters to be written)'

    except Exception as e:
        details = str(e)
        # Save logs
        log_line = save_logs(
            file_name, base_dir, function_name, result="ERROR", details=details
        )
        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)
        return "Error: " + str(e)
