import hashlib
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def hash_prompt(messages):
    concat = ""
    for m in messages:
        concat += m["role"]
        # supporta sia 'parts' che 'content'
        if "parts" in m:
            for p in m["parts"]:
                if isinstance(p, dict) and "text" in p:
                    concat += p["text"]
                elif isinstance(p, str):
                    concat += p
        elif "content" in m:
            concat += m["content"]
    return hashlib.sha1(concat.encode()).hexdigest()


def main():
    model = "gemini-2.0-flash-001"
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY")

    msgs = json.load(
        open(
            os.path.join(os.path.dirname(__file__), "messages.json"),
            "r",
            encoding="utf-8",
        )
    )
    h = hash_prompt(msgs)

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role=m["role"],
                parts=[
                    (
                        types.Part(text=p["text"])
                        if isinstance(p, dict) and "text" in p
                        else types.Part(text=p)
                    )
                    for p in m.get("parts", [])
                ],
            )
            for m in msgs
        ],
        config=types.GenerateContentConfig(),
    )
    out = f"tests/integration/data/canned_llm/response_{h}.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(
        resp.model_dump(),
        open(out, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=2,
    )
    print("Saved", out)


if __name__ == "__main__":
    main()
