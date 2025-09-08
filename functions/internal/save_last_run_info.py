import os

def save_last_run_info(message, run_id):

    # Define the current run directory
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))

    # Create directory
    os.makedirs(base_dir, exist_ok=True)

    # Define the llm_message file path
    message_path = os.path.join(base_dir, "llm_message")

    with open(message_path, "a", encoding="utf-8") as f:
    # Header
        f.write(f"\n### Last llm message\n\n")
        f.write(message)

   
