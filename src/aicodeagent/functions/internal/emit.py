from google.genai import types


def emit(_name, kind, reason, steps, I_O, function_response_list):
    payload = {
        "ok": False,
        "type": kind,
        "reason": reason,
        "next_steps": steps,
    }

    if I_O:
        print(f"-> {_name} denied: {payload['reason']}")

    function_response_list.append(
        types.Part.from_function_response(name=_name, response=payload)
    )
