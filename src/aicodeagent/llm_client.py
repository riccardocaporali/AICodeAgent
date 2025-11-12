import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


class LLMClient:
    """Base interface for any LLM backend."""

    def complete(self, model: str, messages, config) -> object:
        raise NotImplementedError


class RealLLMClient(LLMClient):
    """Uses the real Gemini API."""

    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

        # Fail fast if API key is missing
        if not api_key:
            print("Missing GEMINI_API_KEY in environment. Aborting.", file=sys.stderr)
            sys.exit(1)

        # Initialize the official Google GenAI client
        self.client = genai.Client(api_key=api_key)

    def complete(self, model: str, messages, config) -> object:
        """Perform a real API call and return the raw response object."""
        return self.client.models.generate_content(
            model=model, contents=messages, config=config
        )


class FileLLMClient(LLMClient):
    """Mock LLM backend that simulates responses from local JSON files."""

    def __init__(self, canned_dir: Path):
        # Directory where canned responses are stored
        self.canned_dir = Path(canned_dir)

    def _hash_prompt(self, messages) -> str:
        """Compute SHA1 hash exactly like save_canned.py."""
        concat = ""
        for m in messages:
            if hasattr(m, "role") and m.role:
                concat += m.role
            if hasattr(m, "parts"):
                for p in m.parts:
                    t = getattr(p, "text", None)
                    if t:
                        concat += t
        return hashlib.sha1(concat.encode("utf-8")).hexdigest()

    def complete(self, model: str, messages, config) -> object:

        h = self._hash_prompt(messages)
        path = (self.canned_dir / f"response_{h}.json").resolve()
        print(f"[FileLLMClient] loading {path}")
        if not path.exists():
            print("not exist")
            raise FileNotFoundError(f"Canned response not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        resp = types.GenerateContentResponse.model_validate(data)
        return resp
