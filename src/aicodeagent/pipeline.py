# ---- IMPORTS & INTERNALS -----------------------------------------------------
import re
import sys
import time

from google.genai import types

from aicodeagent.functions import functions_schemas as schemas
from aicodeagent.functions.call_function import call_function
from aicodeagent.functions.functions_schemas import function_dict
from aicodeagent.functions.internal.emit import emit
from aicodeagent.functions.internal.init_run_session import init_run_session
from aicodeagent.functions.internal.prev_proposal import prev_proposal
from aicodeagent.functions.internal.prev_run_summary_path import prev_run_summary_path
from aicodeagent.llm_client import RealLLMClient
from aicodeagent.prompts.system_prompt import model, system_prompt


def run_pipeline(prompt, llm, options, project_root):

    # ---- RUN SESSION INIT --------------------------------------------------------
    # - Create run_id only after validating arguments (avoid empty/garbage runs)
    run_id = init_run_session()

    # ---- PREVIOUS RUN CONTEXT BOOTSTRAP -----------------------------------------
    prev_summary_path = prev_run_summary_path(run_id)
    messages = []
    last_prop = None
    # Variable to save data fed at conclude_edit
    extra_data = None

    if isinstance(llm, RealLLMClient) and prev_summary_path and not options.reset:
        prev_context, last_prop = prev_proposal(
            prev_summary_path
        )  # last_prop: file_path, content, run_id, wd

        if prev_context:
            messages.append(
                types.Content(role="user", parts=[types.Part(text=prev_context)])
            )

    messages.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

    # ---- TOOL DECLARATIONS (FUNCTION SCHEMAS) ------------------------------------
    # - Register available tools for the model: list/read/run/propose/apply
    has_prev_proposal = bool(last_prop)

    fn_decls = [
        schemas.schema_get_files_info,
        schemas.schema_get_file_content,
        schemas.schema_run_python_file,
        schemas.schema_propose_changes,
    ]
    # Register conclude_edit only if previous proposal is present
    if has_prev_proposal:
        fn_decls.append(schemas.schema_conclude_edit)

    available_functions = types.Tool(function_declarations=fn_decls)

    # ---- GUARDS & TRACKERS INIT -------------------------------
    proposed_content = None

    run_save = {
        "save_type": "Default",
    }

    run_stats = {
        "tool_calls": 0,
        "text_only": False,
        "propose_ok": 0,
        "apply_ok": 0,
        "file_info_blox": 0,
        "read_ok": 0,
        "transient_err": 0,
    }

    # ---- SYSTEM PROMPT & MODEL CONFIG -------------------------------------------

    config = types.GenerateContentConfig(
        tools=[available_functions], system_instruction=system_prompt
    )

    # ---- MAIN LOOP (ITERATIVE DRIVER) -------------------------------------------
    cycle_number = 0
    while cycle_number <= 15:  # runs up to 16 iters (0..15)
        cycle_number += 1
        try:
            # ---- MODEL CALL & OPTIONAL DEBUG DUMP --------------------------------
            print(f"--------------- Iteration #{cycle_number} ----------------")
            if options.I_O:
                print("\n--- LAST MESSAGES ---")
                for m in messages[-3:]:
                    print(f"[{m.role}] →", end=" ")
                    for part in m.parts:
                        if hasattr(part, "text") and part.text:
                            print(part.text)
                        elif hasattr(part, "function_call") and part.function_call:
                            print(
                                f"[FunctionCall] {part.function_call.name} {part.function_call.args}"
                            )
                        else:
                            print(part)
            try:
                response = llm.complete(model=model, messages=messages, config=config)
            except FileNotFoundError as e:
                print("Error llm call", e)
                break

            # ---- APPEND MODEL MESSAGE & INIT LOOP FLAGS --------------------------
            # Add model response to the message stream for the next turn
            messages.append(response.candidates[0].content)

            # Control flags for this iteration
            only_text_response = True

            # Collect tool responses (to be appended as a single 'tool' message)
            function_response_list = []
            stop_after_tool = False
            # ---- HANDLER: FUNCTION CALL PARTS THROTTLE ------------------------
            # Loop over each LLM response part (text + single/multi function calls)
            for part in response.candidates[0].content.parts:
                if stop_after_tool:
                    pass

                if part.function_call:
                    # Extract the function call and arguments
                    function_call_part = types.FunctionCall(
                        name=part.function_call.name, args=part.function_call.args
                    )
                    name = function_call_part.name

                    # ---- PRE-CHECK ------------------
                    # 1) Only text response after a proposal
                    if run_stats.get("propose_ok", 0) >= 1:
                        emit(
                            "propose_changes",
                            "throttled",
                            "duplicate_proposal_this_run",
                            [
                                "Reply with TEXT ONLY. Summarize the proposed edit in 3 bullets.",
                                "Ask: 'Approve apply in next run?'",
                            ],
                            options.I_O,
                            function_response_list,
                        )
                        only_text_response = False
                        stop_after_tool = True
                        break

                    # 2) Deny apply in same run as a proposal (enforce two-step)
                    if name == "conclude_edit" and run_stats.get("propose_ok", 0) >= 1:
                        emit(
                            "conclude_edit",
                            "apply_denied",
                            "same_run_apply_not_allowed",
                            [
                                "Summarize the proposed edits in 3 bullet points and ask for user approval.",
                                "End the run. In the next run, call conclude_edit with no arguments.",
                            ],
                            options.I_O,
                            function_response_list,
                        )
                        only_text_response = False
                        stop_after_tool = True
                        break

                    # 3) Deny repeated apply in same run
                    if name == "conclude_edit" and run_stats.get("apply_ok", 0) >= 1:
                        emit(
                            "conclude_edit",
                            "apply_denied",
                            "duplicate_apply_this_run",
                            [
                                "Do not call conclude_edit again in this run.",
                                "Ask whether further changes or a new proposal cycle are needed.",
                            ],
                            options.I_O,
                            function_response_list,
                        )
                        only_text_response = False
                        stop_after_tool = True
                        break
                    # -------------------------------------------------------

                    # ---- NORMALIZE ARGS & DISPATCH --------------------------------------
                    if options.I_O:
                        print(f"function arguments -> {function_call_part.args}")

                    # snapshot raw LLM args
                    function_call_part.args["function_args"] = dict(
                        function_call_part.args
                    )

                    # normalize working directory (force absolute project_root/code_to_fix)
                    original_dir = function_call_part.args.get("working_directory", "")
                    if options.demo:
                        base_dir = (
                            project_root
                            / "examples/minirepo/code_to_fix/calculator_bugged"
                        )
                    else:
                        base_dir = project_root / "code_to_fix"
                    function_call_part.args["working_directory"] = str(
                        base_dir / original_dir
                    )
                    # attach run_id
                    function_call_part.args["run_id"] = run_id
                    # inject deterministic inputs for conclude_edit from last_prop (no file I/O here)
                    if function_call_part.name == "conclude_edit" and not options.reset:
                        if not last_prop:
                            emit(
                                "conclude_edit",
                                "apply_denied",
                                "no_previous_proposals",
                                [
                                    "Previous proposal not existent, generate only text response for user:",
                                    "'Error: repeat the request.'",
                                ],
                                options.I_O,
                                function_response_list,
                            )
                            only_text_response = False
                            stop_after_tool = True
                            break

                        fp = last_prop.get("file_path")
                        ct = last_prop.get("content")
                        wd = (
                            last_prop.get("wd")
                            or last_prop.get("working_directory")
                            or ""
                        ).strip("/")
                        wd = base_dir / wd if wd else base_dir

                        if not fp or ct is None:
                            emit(
                                "conclude_edit",
                                "apply_denied",
                                "Previous proposal missing file_path or content.",
                                [
                                    "Previous proposal content or file path not exist, generate only text response for user:",
                                    "'Error: changes not applied, please state again the previous request.'",
                                ],
                                options.I_O,
                                function_response_list,
                            )
                            only_text_response = False
                            stop_after_tool = True
                            break

                        # override working_directory using wd from proposal; file_path stays as-is
                        function_call_part.args["working_directory"] = str(wd)
                        function_call_part.args["file_path"] = fp
                        function_call_part.args["content"] = ct
                        extra_data = {"wd": wd, "fp": fp, "ct": ct}

                        if options.verbose:
                            print(
                                f"[conclude_edit inject] wd={wd!r} file_path={fp!r}, bytes={len(ct)}"
                            )

                    # dispatch
                    function_call_result = call_function(
                        function_call_part, function_dict, verbose=options.verbose
                    )

                    # extract tool response
                    function_response = function_call_result.parts[
                        0
                    ].function_response.response
                    if function_response is None:
                        raise Exception("No output from inputted function")

                    if options.verbose:
                        print(f"-> {function_response}")

                    function_response_list.append(
                        types.Part.from_function_response(
                            name=function_call_part.name,
                            response=function_response,
                        )
                    )
                    # ---- STATS ------------------------------------------------
                    run_stats["tool_calls"] += 1

                    # Robust OK detection for dict/str payloads
                    res_dict = (
                        function_response
                        if isinstance(function_response, dict)
                        else None
                    )
                    if res_dict is not None:
                        res_text = res_dict.get("result")
                        status_ok = not (
                            res_dict.get("ok") is False
                            or (
                                isinstance(res_text, str)
                                and (
                                    res_text.startswith("Error:")
                                    or "TIMEOUT" in res_text
                                    or "timed out" in res_text
                                )
                            )
                        )
                    else:
                        res = function_response
                        status_ok = (
                            isinstance(res, str)
                            and not res.startswith("Error:")
                            and "TIMEOUT" not in res
                            and "timed out" not in res
                        ) or not isinstance(res, str)

                    name = function_call_part.name
                    if status_ok:
                        if name == "propose_changes":
                            run_stats["propose_ok"] += 1
                            emit(
                                "propose_changes",
                                "directive",
                                "proposal_recorded",
                                [
                                    "Reply with TEXT ONLY. Summarize the proposed edit in 3 bullets.",
                                    "Ask: 'Approve apply in next run?'",
                                ],
                                options.I_O,
                                function_response_list,
                            )

                            # optional: cache proposed content for save_run_info
                            if isinstance(function_response, dict):
                                proposed_content = function_response.get("content")
                            if proposed_content is None:
                                proposed_content = function_call_part.args.get(
                                    "content"
                                )
                        elif name == "conclude_edit":
                            run_stats["apply_ok"] += 1
                        elif name in (
                            "get_file_content",
                            "get_files_info",
                            "run_python_file",
                        ):
                            run_stats["read_ok"] += 1
                    else:
                        run_stats["transient_err"] += 1

                    # ---- MARK NON-TEXT RESPONSE ------------------------------------------
                    # Found a function call → this is not a pure text response
                    only_text_response = False

                # ---- IGNORE PLAIN TEXT PARTS ---------------------------------------------
                elif part.text:
                    # Plain text part: already handled (or not actionable) → ignore here
                    pass

            # ---- POST-RESPONSE ACCOUNTING & EARLY-EXIT -------------------------------------
            um = getattr(response, "usage_metadata", None)
            if options.verbose and um:
                print(f"User prompt: {prompt}")
                print(f"Prompt tokens: {um.prompt_token_count}")
                print(f"Response tokens: {um.candidates_token_count}")

            # If the llm respond with only text, stop the cycle and print reponse
            if only_text_response:
                txt = (response.text or "").lower()
                # If model is asking for target directory
                PAT_ASK_DIR = re.compile(
                    r"""
                    (specify|which|what|where|indicate|choose|select|target|root
                    |working\s*directory|project\s*root|path|folder|dir|tree|structure
                    |cartella|percorso|quale|dove)
                    .{0,60}
                    (directory|folder|path|root|cartella|percorso|dir)
                """,
                    re.I | re.X,
                )

                # Create payload with file searching instructions
                if PAT_ASK_DIR.search(txt) and run_stats["file_info_blox"] == 0:
                    messages.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    text="The project root is 'code_to_fix/'. Use get_files_info on '.' or on the mentioned subfolder."
                                )
                            ],
                        )
                    )
                    run_stats["file_info_blox"] += 1
                    continue  # Start a new cycle

                # Print llm text response
                run_stats["text_only"] = True
                print(response.text or "")

                # if llm propose changes this run append to message ai_outputs directory position
                if run_stats.get("propose_ok", 0) >= 1:
                    print(
                        "\n[INFO] Proposed changes saved under __ai_outputs__/"
                        f"{run_id}/. Check summary.txt and diff.patch for details.\n"
                    )

                break

            # Add the function response to the message for the next iteration
            if function_response_list:
                messages.append(
                    types.Content(
                        role="tool",
                        parts=function_response_list,  # <--- Change this from [function_response_list] to function_response_list
                    )
                )

        # ---- TRANSIENT EXCEPTIONS (RETRYABLE) -----------------------------------------
        except Exception as e:
            # Error if the LLM is temporarily unavailable
            if "UNAVAILABLE" in str(e):
                run_stats["transient_err"] += 1
                print("Gemini is temporarily unavailable, wait 5 seconds...")
                time.sleep(5)
                continue

            # Error if we called gemini more than 15 times in 1 minute, free version limitation (errore 429)
            if "RESOURCE_EXHAUSTED" in str(e):
                run_stats["transient_err"] += 1
                print("Request per minute limit exceeded, wait 60 seconds...")
                time.sleep(60)
                continue

            # Error if the LLM got an invalid input, probable code error present (errore 400)
            if "INVALID_ARGUMENT" in str(e):
                run_stats["transient_err"] += 1
                print("Code error, try again")
                sys.exit()

            # All error are appended to the message for the next iteration
            error_message = types.Content(
                role="tool",
                parts=[
                    types.Part(
                        text="An error occurred during the execution of the loop. Below is the error. "
                        "Adjust your behavior accordingly: " + str(e)
                    )
                ],
            )
            messages.append(error_message)

            if options.verbose:
                print("EXCEPTION while block:", e)

    # ---- SAVE-TYPE DECISION (END-OF-RUN) ---------------------------------
    if run_save["save_type"] == "Default":
        any_useful = (
            run_stats["propose_ok"] or run_stats["apply_ok"] or run_stats["read_ok"]
        )
        only_transient = (
            run_stats["transient_err"] > 0
            and not any_useful
            and run_stats["tool_calls"] == 0
            and not run_stats["text_only"]
        )

        if only_transient:
            run_save["save_type"] = "Discard_run"
        elif run_stats["text_only"] and run_stats["tool_calls"] == 0:
            run_save["save_type"] = "Additional_run"
        elif run_stats.get("propose_ok", 0) >= 1:
            run_save["save_type"] = "propose_run"
        else:
            run_save["save_type"] = "Default"

    return {
        "run_id": run_id,
        "run_stats": run_stats,
        "save_type": run_save["save_type"],
        "messages": messages,
        "prev_summary_path": prev_summary_path,
        "extra_data": extra_data,
        "proposed_content": proposed_content,
    }
