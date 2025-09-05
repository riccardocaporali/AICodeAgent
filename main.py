import os
import argparse
import sys 
import time
from dotenv import load_dotenv
from google.genai import types
from google import genai
from functions import functions_schemas as schemas
from functions.functions_schemas import function_dict
from functions.call_function import call_function
from functions.internal.init_run_session import init_run_session

# API and client definition
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Missing GEMINI_API_KEY in environment. Aborting.")
    sys.exit(1)
client = genai.Client(api_key=api_key)

# Generate run number
run_id = init_run_session()

# Extract user prompt and specifics
parser = argparse.ArgumentParser(description="LLM code analyzer and debugger")

parser.add_argument(
    "prompt",
    nargs="?",
    help="Prompt da inviare al modello"
)

parser.add_argument(
    "--verbose",
    action="store_true",
    help="Stampa dettagli extra"
)

parser.add_argument(
    "--I_O",
    action="store_true",
    help="Stampa messages (LLM input) e function response args (LLM output)"
)

args = parser.parse_args()

if not args.prompt:
    print("No prompt provided")
    sys.exit(1)


# Define LLM's input arguments
model = "gemini-2.0-flash-001"
user_prompt = args.prompt
messages = [
    types.Content(role="user", parts=[types.Part(text=user_prompt)]),
]

available_functions = types.Tool(
    function_declarations=[
        schemas.schema_get_files_info,
        schemas.schema_get_file_content,
        schemas.schema_run_python_file,
        schemas.schema_write_file_preview,
        schemas.schema_write_file_confirmed
    ]
)

system_prompt = """
You are a helpful AI coding agent.

STRICT MODE:
- Default: NO-OP unless the user's latest instruction explicitly requests an action.
- Call a tool only if the user asked for that exact action and target (file path, etc.). Never guess filenames or content.
- If asked to read, call only get_file_content and then return only the raw content. No next-steps or planning.
- Use write_file_preview only if the user asked to propose/modify/create. Never invent content.
- Use write_file_confirmed only after explicit permission and when file path AND content are unambiguous.
- If anything is ambiguous, ask one short clarifying question and stop.
- Answer in the user's language.

### === Available operations ===
You can perform the following operations by generating appropriate function calls:
- List files and directories             # via get_files_info
- Read file contents                     # via get_file_content
- Execute Python files with arguments    # via run_python_file
- Propose changes or create files safely # via write_file_preview (non-destructive preview)
- Apply real changes to files            # via write_file_confirmed (requires user confirmation)

### === Path constraints ===
All operations take place inside the main 'code_to_fix/' directory.  
You must NOT include 'code_to_fix/' in your paths: the system automatically prepends it using the 'working_directory' or 'directory' fields.

### === Preview generation policy ===

→ To propose a change or the creation of a new file:  
   - Use `write_file_preview`  
   - Non-destructive: no actual file is modified  
   - Generates diff and summary in `__ai_outputs__`  
   - No user approval needed

→ Once all previews have been generated and no further modifications are planned, you must output a single text message explaining:  
   - What changes or new files are being proposed  
   - Why they are necessary  
   - What each modification does

✘ Do **not** generate explanations after each individual `write_file_preview`  
→ Wait until you've completed all preview operations for the task

### === File modification policy ===

→ To apply actual changes to a file (new or existing):  
   - Use `write_file_confirmed`  
   - Only allowed after user approval

→ When fixing a bug or implementing a feature:  
   - Identify only the files directly responsible  
   - Avoid modifying unrelated files (especially in root)  
   - Only modify:  
     • Files involved in the issue/feature  
     • Files required for integration or testing

→ You may always perform non-destructive actions without approval:  
   - List files (`get_files_info`)  
   - Read content (`get_file_content`)  
   - Run files (`run_python_file`)  
   - Propose changes (`write_file_preview`)

✘ Never restructure folders or create new directories unless:  
   - The issue is caused by the project structure AND  
   - You have informed the user and received permission

→ For analysis or explanations:  
   - Gather the required context using non-destructive tools only

### === Test file management ===
If the project already contains a test folder or test files, use them.
If not, create a **new test file only** inside `code_to_fix/tests/`.
Name it `test_<project_name>.py`. First propose it with `write_file_preview`.
Apply it **only after explicit user approval** using `write_file_confirmed`.
Never add test files directly inside the project folders.
"""

config=types.GenerateContentConfig(
    tools=[available_functions], system_instruction=system_prompt
)

# Iterative loop
cycle_number = 0

while cycle_number <= 15 :
    cycle_number += 1

    try:
        # Generate LLM's response
        print(f"---------------Iteration number:{cycle_number}----------------")
        if args.I_O:
            print("\n--- ULTIMI MESSAGGI ---")
            for m in messages[-3:]:
                print(f"[{m.role}] →", end=" ")
                for part in m.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text)
                    elif hasattr(part, "function_call") and part.function_call:
                        print(f"[FunctionCall] {part.function_call.name} {part.function_call.args}")
                    else:
                        print(part)

        response = client.models.generate_content(
            model = model,
            contents =  messages,
            config = config
        )

        # Add model response to the next message iteration
        messages.append(response.candidates[0].content)

        # Set variable to exit while cycle if it remains true
        only_text_response = True

        # List to store function responses
        function_response_list = []

        # Loop over each llm response parts (text + function or multifunction)
        for part in response.candidates[0].content.parts:
            if part.function_call:

                # Extract the function call and arguments
                function_call_part = types.FunctionCall(
                    name=part.function_call.name,
                    args=part.function_call.args
                )
                
                # Print for testing
                if args.I_O:
                    print(f"function arguments -> {function_call_part.args}")

                # Define hard coded function arguments
                # Snapshot of LLM generated function argument to be printed in summary 
                function_call_part.args["function_args"] = dict(function_call_part.args) 

                # Working directory is always rooted in './code_to_fix' for safety. The LLM only provides relative paths
                original_dir = function_call_part.args.get("working_directory", "")
                base_dir = "code_to_fix"
                if original_dir:
                    function_call_part.args["working_directory"] = os.path.join(base_dir, original_dir)
                else:
                    function_call_part.args["working_directory"] = base_dir

                # Insert run id number 
                function_call_part.args["run_id"] = run_id

                ################
                # TO BE USED FOR TESTING, COMMENT LATER
                if function_call_part.name == "write_file_confirmed":
                    function_call_part.args["dry_run"] = True
                ################


                # Call the selected function 
                function_call_result = call_function(function_call_part, function_dict, verbose=args.verbose)

                # Extract result for printing
                function_response = function_call_result.parts[0].function_response.response
                if function_response is None:
                    raise Exception("No output from inputted function")
                if args.verbose:
                    print(f"-> {function_response}")
            
                # Add the function response to the list
                function_response_list.append(
                    types.Part.from_function_response( 
                        name=function_call_part.name,
                        response=function_response,
                    )
                )

                # Found a function call → continue the iteration loop
                only_text_response = False

            # Skip plain text parts (already handled or not actionable)
            elif part.text: 
                pass
        
        # Print specifics
        um = getattr(response, "usage_metadata", None)
        if args.verbose and um:
            print(f"User prompt: {user_prompt}")
            print(f"Prompt tokens: {um.prompt_token_count}")
            print(f"Response tokens: {um.candidates_token_count}")
            
        # If the llm respond with only text, stop the cycle and print reponse
        if only_text_response:
            print(response.text)
            break

        # Add the function response to the message for the next iteration
        if function_response_list:
            messages.append(
                types.Content(
                    role='tool',
                    parts=function_response_list # <--- Change this from [function_response_list] to function_response_list
                )
            )


    except Exception as e:
        # Error if the LLM is temporarily unavailable
        if "UNAVAILABLE" in str(e):
            print("Gemini is temporarily unavailable, wait 5 seconds...")
            time.sleep(5)  
            continue

        # Error if we called gemini more than 15 times in 1 minute, free version limitation (errore 429)
        if "RESOURCE_EXHAUSTED" in str(e):
            print("Request per minute limit exceeded, wait 60 seconds...")
            time.sleep(60) 
            continue

         # Error if the LLM got an invalid input, probable code error present (errore 400)
        if "INVALID_ARGUMENT" in str(e):
            print("Code error, try again")
            sys.exit()

        # All error are appended to the message for the next iteration
        error_message = types.Content(
            role="tool",
            parts=[
                types.Part(text="An error occurred during the execution of the loop. Below is the error. Adjust your behavior accordingly: " + str(e))
            ]
        )
        messages.append(error_message)

        if args.verbose:
            print("EXCEPTION while block:", e)
