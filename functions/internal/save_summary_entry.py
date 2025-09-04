import os
from functions.internal.make_human_readable_diff import make_human_readable_diff

def save_summary_entry(summary_dir, function_name, function_args, log_line=None, diff_lines=None):
    # Define the summary directory (with optional run_id subfolder)
    os.makedirs(summary_dir, exist_ok=True)

    # Define the summary file path
    summary_path = os.path.join(summary_dir, "summary.txt")

    # Fix indentation
    clean = log_line.lstrip("\n").rstrip("\n")
    bullet = "   - " + clean.replace("\n", "\n     ") + "\n"

    # Save summary for write file functions
    if function_name in ("write_file_preview", "write_file_confirmed"):
        if log_line is not None:
            # Convert diff lines to a human-readable format
            readable_diff = make_human_readable_diff(diff_lines) if diff_lines else ""

            with open(summary_path, "a", encoding="utf-8") as f:
                # Header
                f.write(f"\n### FUNCTION: {function_name}\n\n")

                if log_line:
                    f.write("1. **Log**\n")
                    f.write(bullet)

                # Diff section (if any)
                if readable_diff:
                    f.write("\n2. **Diff**\n")
                    for line in readable_diff.strip().splitlines():
                        f.write(f"   - {line}\n")

                # Args section (if any)
                if function_args:
                    f.write("\n3. **Arguments**\n")
                    for key, value in function_args.items():
                        f.write(f"   - {key}: {str(value).strip()}\n")

                f.write("\n---\n")
        else:
            
            with open(summary_path, "a", encoding="utf-8") as f:
                # Header
                f.write(f"\n### FUNCTION: {function_name}\n\n")
                f.write("\n---\n")


    # Save summary get_file_content function
    elif function_name == "get_file_content":
         with open(summary_path, "a", encoding="utf-8") as f:
            # Header
            f.write(f"\n### FUNCTION: {function_name}\n\n")

            # Log section
            if log_line:
                f.write("1. **Log**\n")
                f.write(bullet)
                

            # Args section (if any)
            if function_args:
                f.write("\n2. **Arguments**\n")
                for key, value in function_args.items():
                    f.write(f"   - {key}: {str(value).strip()}\n")


    # Save summary get_files_info function
    elif function_name  == "get_files_info":
        with open(summary_path, "a", encoding="utf-8") as f:
            # Header
            f.write(f"\n### FUNCTION: {function_name}\n\n")

            # Log section
            if log_line:
                f.write("1. **Log**\n")
                f.write(bullet)

            # Args section (if any)
            if function_args:
                f.write("\n2. **Arguments**\n")
                for key, value in function_args.items():
                    f.write(f"   - {key}: {str(value).strip()}\n")
    

    # Save summary run_python_file function
    elif function_name  == "run_python_file":
        with open(summary_path, "a", encoding="utf-8") as f:
            # Header
            f.write(f"\n### FUNCTION: {function_name}\n\n")

            # Log section
            if log_line:
                f.write("1. **Log**\n")
                f.write(bullet)
            
            # Args section (if any)
            if function_args:
                f.write("\n2. **Arguments**\n")
                for key, value in function_args.items():
                    f.write(f"   - {key}: {str(value).strip()}\n")


