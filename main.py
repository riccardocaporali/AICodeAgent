import os
import argparse
import sys 
import time
import functions.functions_schemas as schemas
from functions.call_function import call_function
from dotenv import load_dotenv
from google.genai import types
from google import genai

# API and client definition
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

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
        schemas.schema_write_file,
    ]
)
system_prompt = """
You are a helpful AI coding agent.

When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

- List files and directories
- Read file contents
- Execute Python files with optional arguments
- Write or overwrite files

All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.

**Crucially, when fixing a bug or implementing a feature, first identify the specific file(s) causing the issue or where the feature needs to be added. Limit your modifications to only those files that *need* to be changed. Avoid making unnecessary alterations to the project's top-level structure, especially files like the root `main.py` or `tests.py`, unless explicitly instructed or the bug *directly* originates there. Focus your changes on files within the `calculator/` directory when working on the calculator project.**

Prioritize changes within the `calculator/pkg/` directory if the issue or feature relates to the calculator's core logic or rendering. Only modify `calculator/main.py` or `calculator/tests.py` if the specific task directly involves changes to the calculator's entry point or its own test suite, respectively.
"""

config=types.GenerateContentConfig(
    tools=[available_functions], system_instruction=system_prompt
)

Cycle_number = 0
while Cycle_number <= 15 :
    Cycle_number += 1
    try:
        # Generate LLM's response
        print(f"---------------Iteration number:{Cycle_number}----------------")
        response = client.models.generate_content(
            model = model,
            contents =  messages,
            config = config
        )

        # Add model response to the next message iteration
        messages.append(response.candidates[0].content)

        # Call selected function and continue the cycle
        only_text_reponse = True

        # Empty dictionary to save the functions response
        function_response_list = []

        # Loop over each llm response parts (text + function or multifunction)
        for part in response.candidates[0].content.parts:
            if part.function_call:

                # Extract the function call and arguments
                function_call_part = types.FunctionCall(
                    name=part.function_call.name,
                    args=part.function_call.args
                )

                # Call the selected function 
                function_call_result = call_function(function_call_part)

                # Extract result for printing
                function_response = function_call_result.parts[0].function_response.response
                if function_response is None:
                    raise Exception("No output from inputted function")
                if args.verbose:
                    print(f"-> {function_response}")
             
                # Save the function response


                # Add the function response to the list
                function_response_list.append(
                    types.Part.from_function_response( 
                        name=function_call_part.name,
                        response=function_response,
                    )
                )

                # Change the variable to make the while cycle go on
                only_text_reponse = False

            # Already added full response (including text), so skip
            elif part.text: 
                pass
        
        # Print specifics
        prompt_token_count = response.usage_metadata.prompt_token_count
        candidates_token_count = response.usage_metadata.candidates_token_count
        if args.verbose:
            print(f"User prompt: {user_prompt}")
            print(f"Prompt tokens: {prompt_token_count}")
            print(f"Response tokens: {candidates_token_count}")
            
        # If the llm respond with only text, stop the cycle and print reponse
        if only_text_reponse == True:
            i = 100000 
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
        if "--verbose" in args:
            print("EXCEPTION while block:", e)
