import os

def get_files_info(working_directory, directory=None):
    try:
        full_path = os.path.abspath(os.path.join(working_directory, directory))
        directory_path = os.path.abspath(working_directory)

        # Eedge cases handling
        if not full_path.startswith(directory_path):
            return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'
        if os.path.isdir(full_path) == False:
            return f'Error: "{directory}" is not a directory'
        
        # Directory content extraction
        directory_content = os.listdir(full_path)
        file_list = []
        for file in directory_content:
            file_path = os.path.join(full_path, file)
            file_list.append(f"- {file}: file_size={os.path.getsize(file_path)} bytes, is_dir={os.path.isdir(file_path)}")
        return "\n".join(file_list)
    
    except Exception as e:
        #print(str(e))
        return "Error: " + str(e)