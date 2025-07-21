import os
import shutil

def write_file(working_directory, file_path, content, dry_run=True, log_changes=False):
    try:
        # Define the selecte file and directory full path
        full_path = os.path.abspath(os.path.join(working_directory, file_path))
        directory_path = os.path.abspath(working_directory)

        # Check if the selected file is outside of the working directory --> Error
        if not full_path.startswith(os.path.abspath(directory_path)):
            return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'
        
        # Write/create content on a file
        with open(full_path, "w") as f:
            f.write(content)
        return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'

    except Exception as e:
        return "Error: " + str(e)
    