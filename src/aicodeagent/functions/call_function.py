import traceback

from google.genai import types


def call_function(function_call_part, function_dict, verbose=False):
    try:
        if verbose:
            print(
                f"Calling function: {function_call_part.name}({function_call_part.args})"
            )
        else:
            print(f" - Calling function: {function_call_part.name}")

        function_name = function_call_part.name
        if function_name not in function_dict:
            return types.Content(
                role="tool",
                parts=[
                    types.Part.from_function_response(
                        name=function_name,
                        response={"error": f"Unknown function: {function_name}"},
                    )
                ],
            )
        function_result = function_dict[function_name](**function_call_part.args)
        return types.Content(
            role="tool",
            parts=[
                types.Part.from_function_response(
                    name=function_name,
                    response={"result": function_result},
                )
            ],
        )

    except Exception as e:

        err_payload = {
            "ok": False,
            "error": {
                "type": e.__class__.__name__,
                "message": str(e),
            },
        }

        # Add traceback if verbose is on
        if verbose:
            err_payload["error"]["details"] = {"traceback": traceback.format_exc()}

        fname = getattr(function_call_part, "name", "unknown")

        return types.Content(
            role="tool",
            parts=[
                types.Part.from_function_response(
                    name=fname,
                    response=err_payload,
                )
            ],
        )
