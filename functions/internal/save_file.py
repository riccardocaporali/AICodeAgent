import os 

def save_file(destination_directory, file_name=None, source_path=None, content=None):
    """
    Saves a file to a specified directory.

    - If `content` is provided, it writes that content directly.
    - If `source_path` is provided and `content` is None, it copies the content from the source file.
    - `file_name` is required if `source_path` is None.
    """

    # If no file name is specified, it is automatically extracted from the file path otherwise --> error
    if file_name is None:
        if source_path:
            file_name = os.path.basename(source_path)
        else:
            raise ValueError("file_name must be specified if source_path is None")
    
    # Check if destination directory is set
    if destination_directory is None:
        raise ValueError("destination_directory must be provided")
    
    # Generate the target path for the saving, if the directory does not exist it is created
    destination_path = os.path.join(destination_directory, file_name)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    # Create special cases for saving an existing file or save a new file with a specified content
    if content:
        with open(destination_path, "w", encoding="utf-8") as f:
            f.write(content)

    elif source_path:
        # Copy target file
        with open(source_path, "r", encoding="utf-8") as f_in:
            content = f_in.read()

        # Salva il file nella cartella selezionata
        with open(destination_path, "w", encoding="utf-8") as f_out:
            f_out.write(content)
    
    else:
        raise ValueError("Either content or source_path must be provided")
    