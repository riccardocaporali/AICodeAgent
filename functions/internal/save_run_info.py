import os, json, time, re

def save_run_info(messages, run_id):
    """
    Build a compact, structured ledger of the last run from `messages`
    and save two files under __ai_outputs__/run_<id>/:
      - run_summary.json  (structured: header, calls, assistant.last_text)
      - llm_message       (plain last assistant text)
    """
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    os.makedirs(base_dir, exist_ok=True)

    def brief_text(s, n=160):
        s = (s or "").strip().replace("\r", "")
        return s[:n] + ("…" if len(s) > n else "")

    def parse_status(res):
        if not isinstance(res, str):
            return "OK"
        if res.startswith("Error:"):
            return "ERROR"
        if "TIMEOUT" in res or "timed out" in res:
            return "TIMEOUT"
        return "OK"

    calls = []
    pending = []
    last_text = ""

    # Extract the first user prompt of the run ---
    user_prompt = ""
    for msg in (messages or []):
        if getattr(msg, "role", None) == "user":
            for p in (getattr(msg, "parts", []) or []):
                t = getattr(p, "text", None)
                if t and t.strip():
                    user_prompt = t.strip()
                    break
            if user_prompt:
                break

    for msg in (messages or []):
        role = getattr(msg, "role", None)
        parts = getattr(msg, "parts", []) or []

        if role in ("model", "assistant"):
            for p in parts:
                t = getattr(p, "text", None)
                if t and t.strip():
                    last_text = t  # keep last assistant text

                fc = getattr(p, "function_call", None)
                if fc:
                    name = getattr(fc, "name", None)
                    args = getattr(fc, "args", {}) or {}
                    rec = {
                        "t": name,
                        "args": {
                            "wd": args.get("working_directory"),
                            "file_path": args.get("file_path"),
                            "directory": args.get("directory"),
                        },
                    }
                    if isinstance(args.get("content"), str):
                        rec["args"]["content_len"] = len(args["content"])
                    pending.append(rec)

        elif role == "tool":
            for p in parts:
                fr = getattr(p, "function_response", None)
                if not fr:
                    continue

                name = getattr(fr, "name", None)
                resp = getattr(fr, "response", None)
                result = resp.get("result") if isinstance(resp, dict) else resp

                rec = pending.pop(0) if pending else {"t": name, "args": {}}
                rec["t"] = name
                rec["status"] = parse_status(result if isinstance(result, str) else "")

                extras = {}
                if name == "get_files_info" and isinstance(result, str):
                    lines = [ln for ln in result.splitlines() if ln.startswith("- ")]
                    extras["count"] = len(lines)
                    extras["sample"] = lines[:5]
                elif name == "get_file_content" and isinstance(result, str):
                    extras["content_len"] = len(result)
                    extras["content_head"] = brief_text(result, 120)
                elif name == "run_python_file" and isinstance(result, str):
                    m = re.search(r"Exit code:([^\n]+)", result)
                    extras["exit"] = m.group(1).strip() if m else None
                    ms = re.search(r"STDOUT:(.*)\nSTDERR:", result, re.S)
                    me = re.search(r"STDERR:(.*)\nExit code:", result, re.S)
                    stdout = (ms.group(1) if ms else "").strip()
                    stderr = (me.group(1) if me else "").strip()
                    extras["stdout_len"] = len(stdout)
                    extras["stderr_len"] = len(stderr)
                elif name in ("write_file_preview", "write_file_confirmed"):
                    a = rec.get("args", {})
                    extras["target"] = a.get("file_path")
                    if "content_len" in a:
                        extras["content_len"] = a["content_len"]

                rec["brief"] = brief_text(str(result), 160) if isinstance(result, str) else None
                rec["extras"] = extras
                calls.append(rec)

    summary = {
        "header": {
            "run_id": run_id,
            "ts": time.time(),
            "phase": "NONE",
            "user_prompt": user_prompt,
            "user_prompt_len": len(user_prompt),
            "user_prompt_brief": brief_text(user_prompt, 160),
        },
        "calls": calls[-10:],  # keep last N calls
        "assistant": {
            "last_text": brief_text(last_text, 2000),
        },
    }

    json_path = os.path.join(base_dir, "run_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    txt_path = os.path.join(base_dir, "llm_message")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(last_text or "")

    return json_path