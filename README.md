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
| Full traceability | Each run creates a structured directory `ai_outputs/run_xxx/` containing logs, summaries, backups, and diffs for full auditability. |
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
    You can generate an API key directly here:
    https://aistudio.google.com/app/apikey

3. **Install dependencies using uv**

    ```bash
    uv sync
    ```
    
3. **Run the test suite (optional)**

    You can run the full e2e test suite to verify that the agent works correctly.  
    Note: this step is optional and may take a few minutes to complete.  
    Install development dependencies first:

    ```bash
    uv sync --group dev
    uv run pytest -s
    ```

4. **Run a quick test**

    ```bash
    uv run aicodeagent "Hello"
    ```

---  

### Testing the agent on a sample buggy project

If you want to test the agent on an example codebase, copy the sample project:

```bash
cp -r examples/minirepo/code_to_fix/calculator_bugged ./code_to_fix/
```

---  

## Quick Demo

A ready-to-run demo is included to showcase the agent’s workflow.

```bash
bash demo_quickstart.sh
```

For full documentation (architecture, safety mechanisms, extended demo), see `docs/full.md`.

## License

Open-source project released under the MIT License.  
Created by Riccardo Caporali – Aerospace Engineer & AI Developer.
