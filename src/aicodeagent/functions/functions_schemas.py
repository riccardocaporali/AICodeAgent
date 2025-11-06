import os
from google import genai
from google.genai import types
from aicodeagent.functions.llm_calls.get_files_info import get_files_info
from aicodeagent.functions.llm_calls.get_file_content import get_file_content
from aicodeagent.functions.llm_calls.run_python import run_python_file
from aicodeagent.functions.llm_calls.propose_changes import propose_changes
from aicodeagent.functions.llm_calls.conclude_edit import conclude_edit

# Define the dictionary of functions
function_dict = {
    "get_files_info" : get_files_info,
    "get_file_content" : get_file_content,
    "run_python_file" : run_python_file,
    "propose_changes" : propose_changes,
    "conclude_edit" : conclude_edit,
}

schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="Lists files in the specified directory along with their sizes, constrained to the working directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "directory": types.Schema(
                type=types.Type.STRING,
                description= "The directory to list files from, relative to the 'code_to_fix' directory. Use None or omit the field to list the root of 'code_to_fix'."
            ),
        },
    ),
)

schema_get_file_content = types.FunctionDeclaration(
    name="get_file_content",
    description="Return a string representing the content of the input file.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Path relative to the 'code_to_fix' directory. Use this to specify the subfolder containing the project to analyze (e.g., 'calculator' or 'project_01/module'). If not provided, 'file_path' is considered relative to 'code_to_fix'."
            ),
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the target file, starting from the working directory.",
            ),
        },
        required=["file_path"]
    ),
)

schema_run_python_file = types.FunctionDeclaration(
    name="run_python_file",
    description="Run a Python file and return its output, errors, and exit code.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Path relative to the 'code_to_fix' directory. Use this to specify the subfolder containing the project to analyze (e.g., 'calculator' or 'project_01/module'). If not provided, 'file_path' is considered relative to 'code_to_fix'."
            ),
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the target file, starting from the working directory.",
            ),
        },
        required=["file_path"]
    ),
)

schema_propose_changes = types.FunctionDeclaration(
    name="propose_changes",
    description="Generate a preview of the proposed changes to a file. No actual file is modified. The diff and summary are saved in the __ai_outputs__ directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Path relative to the 'code_to_fix' directory. Use this to specify the subfolder containing the project to analyze (e.g., 'calculator' or 'project_01/module'). If not provided, 'file_path' is considered relative to 'code_to_fix'"
            ),
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the target file, starting from the working directory."
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="The proposed content to preview in the target file."
            ),
        },
        required=["file_path", "content"]
    )
)

schema_conclude_edit = types.FunctionDeclaration(
    name="conclude_edit",
    description=(
        "Apply the last approved proposal saved in the previous run summary. "
        "It requires no input parameters; the tool automatically loads file and content from the previous summary."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={},
        required=[]
    )
)