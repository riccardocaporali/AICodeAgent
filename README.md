# AiCodeAgent – AI-Driven Code Refactoring Agent

AiCodeAgent is an AI-driven code refactoring agent designed for autonomous debugging, analysis, and self-contained code repair.  
It uses Google Gemini with function-calling to read, analyze, propose, and safely apply code edits inside a sandboxed environment.

Each session generates:
- detailed logs and statistics  
- diff and backup files  
- structured run summaries (`run_summary.json`) ensuring full continuity between runs  

---

## Main Features

| Category | Description |
|-----------|-------------|
| Code analysis | The agent can explore and inspect any file inside `code_to_fix/` using its built-in tools: `get_files_info`, `get_file_content`, and `run_python_file`. These allow it to list files, read source code, and execute scripts to observe runtime behavior. |
| Change proposals (preview) | Generates non-destructive previews via `propose_changes`, where the LLM suggests code modifications without altering files. |
| Controlled application (apply) | Applies only previously proposed edits, verified through `(file_path, content_len)` or digest checks for safety and consistency. |
| Full traceability | Each run creates a structured directory `__ai_outputs__/run_xxx/` containing logs, summaries, backups, and diffs for full auditability. |
| Sandbox safety | All operations are confined to the `code_to_fix/` folder, ensuring the LLM cannot access or modify files outside the sandbox. |

---

## Setup

1. **Clone the repository**

```bash
git clone https://github.com/riccardocaporali/AiCodeAgent.git
cd AiCodeAgent
```

2. **Create a `.env` file with your Gemini API key**

```bash
GEMINI_API_KEY=your_api_key_here
```   
Get your API key at:  
https://aistudio.google.com/app/apikey

3. **Install dependencies using uv**

```bash
uv sync
```

4. **Run the test suite (optional)**

Install development dependencies:

```bash
uv sync --group dev
uv run pytest -s
```

5. **Run a quick test**

```bash
uv run aicodeagent "Hello"
```

---

### Testing the agent on a sample buggy project

Copy the included buggy calculator:

```bash
cp -r examples/minirepo/code_to_fix/calculator_bugged ./code_to_fix/
```

---

## Quick Demo

A ready-to-run demo script is provided:

```bash
bash demo_quickstart.sh
```

---

## Full Documentation

The complete technical documentation (architecture, internals, gating, snapshot system, error handling, CLI, testing, development workflow) is available here:

### [docs/full.md](docs/full.md)

---

## GitHub link
https://github.com/riccardocaporali/AiCodeAgent

---

## License

Open-source project released under the MIT License.  
Created by Riccardo Caporali – Aerospace Engineer & AI Developer.
