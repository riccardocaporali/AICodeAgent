import os, json, time, re, hashlib

def save_run_info(messages, run_id, proposed_content=None, extra_data=None):
    """
    Build a compact, structured ledger of the last run from `messages`
    and save two files under __ai_outputs__/run_<id>/:
      - run_summary.json  (structured: header, calls, proposals, assistant.last_text)
      - llm_message       (plain last assistant text)
    """
    # Compat: se il terzo argomento è in realtà extra_data (dict con wd/fp/ct), riallinea
    if extra_data is None and isinstance(proposed_content, dict) and (
        {"wd", "fp", "ct"} & set(proposed_content.keys())
    ):
        extra_data, proposed_content = proposed_content, None

    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    os.makedirs(base_dir, exist_ok=True)

    def brief_text(s, n=160):
        s = (s or "").strip().replace("\r", "")
        return s[:n] + ("…" if len(s) > n else "")

    def parse_status(res):
        # dict payloads from tools/deny
        if isinstance(res, dict):
            if res.get("ok") is False:
                return "ERROR"
            return "OK"
        if not isinstance(res, str):
            return "OK"
        if res.startswith("Error:"):
            return "ERROR"
        if "TIMEOUT" in res or "timed out" in res:
            return "TIMEOUT"
        return "OK"

    calls, pending = [], []
    last_text = ""

    # --- extract last non-PREV_RUN_JSON user prompt ---
    user_prompt, _last_any_user = "", ""
    for msg in (messages or []):
        if getattr(msg, "role", None) == "user":
            for p in (getattr(msg, "parts", []) or []):
                t = getattr(p, "text", None)
                if not t or not t.strip():
                    continue
                t = t.strip()
                _last_any_user = t
                if not t.startswith("PREV_RUN_JSON"):
                    user_prompt = t
    if not user_prompt:
        user_prompt = _last_any_user

    # --- walk message stream ---
    for msg in (messages or []):
        role = getattr(msg, "role", None)
        parts = getattr(msg, "parts", []) or []

        if role in ("model", "assistant"):
            for p in parts:
                t = getattr(p, "text", None)
                if t and t.strip():
                    last_text = t
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
                rec["status"] = parse_status(resp if isinstance(resp, dict) else result)

                a = rec.setdefault("args", {})

                # ---- extras summary (minimale) ----
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

                # --- conclude_edit: registra i feed dai dati iniettati (extra_data) ---
                if name == "conclude_edit" and isinstance(extra_data, dict):
                    feed_wd = extra_data.get("wd")
                    feed_fp = extra_data.get("fp")
                    feed_ct = extra_data.get("ct")

                    # Oggetto compatto nel record
                    feed = {}
                    if feed_wd is not None:
                        feed["wd"] = feed_wd
                    if feed_fp is not None:
                        feed["file_path"] = feed_fp
                    if feed_ct is not None:
                        try:
                            feed["content_len"] = len(feed_ct)
                        except Exception:
                            pass
                    if feed:
                        rec["feed"] = feed

                    # Aiuta il riepilogo veloce
                    if feed_fp and "target" not in extras:
                        extras["target"] = feed_fp
                    if "content_len" not in extras and "content_len" in feed:
                        extras["content_len"] = feed["content_len"]

                if isinstance(resp, dict) and resp.get("ok") is False:
                    err = resp.get("error") or {}
                    extras["error"] = {
                        "type": err.get("type"),
                        "reason": err.get("reason"),
                        "message": err.get("message"),
                    }

                rec["brief"] = brief_text(str(result), 160) if isinstance(result, str) else None
                rec["extras"] = extras
                calls.append(rec)

    # --- proposals for next run ---
    proposals, pid = [], 1
    for rec in calls:
        if rec.get("t") == "propose_changes" and rec.get("status") == "OK":
            args = rec.get("args", {}) or {}
            brief = rec.get("brief", "") or ""

            # file_path: prima dagli args, poi fallback dal brief
            fp = args.get("file_path")
            if not fp:
                m = re.search(r'Save proposed changes to "([^"]+)"', brief)
                fp = m.group(1) if m else None

            # content_len: da proposed_content, altrimenti dagli args/extras
            if isinstance(proposed_content, str):
                clen = len(proposed_content)
            else:
                clen = args.get("content_len")
                if clen is None:
                    clen = (rec.get("extras") or {}).get("content_len")

            proposal = {
                "id": pid,
                "wd": args.get("wd"),
                "file_path": fp,
                "content_len": clen,
                "brief": rec.get("brief"),
            }
            if isinstance(proposed_content, str):
                proposal["content"] = proposed_content
                proposal["digest"] = hashlib.sha256(proposed_content.encode("utf-8")).hexdigest()
            proposals.append(proposal)
            pid += 1

    summary = {
        "header": {
            "run_id": run_id,
            "ts": time.time(),
            "user_prompt": user_prompt,
            "user_prompt_len": len(user_prompt),
            "user_prompt_brief": brief_text(user_prompt, 160),
        },
        "calls": calls[-10:],
        "proposals": proposals,
        "assistant": {"last_text": brief_text(last_text, 2000)},
    }

    json_path = os.path.join(base_dir, "run_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    txt_path = os.path.join(base_dir, "llm_message")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(last_text or "")

    return json_path