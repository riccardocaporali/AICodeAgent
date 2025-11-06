import os

def get_project_root(start: str | None = None) -> str:
    """
    Locate the absolute path of the project root.

    Search upward from `start` (or this file) until a directory
    containing either `pyproject.toml` or `.git` is found.
    Falls back four levels up from src/functions/internal if none found.

    Returns:
        str: Absolute path to the project root directory.
    """
    cur = os.path.abspath(start or __file__)
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)

    while True:
        if (
            os.path.exists(os.path.join(cur, "pyproject.toml"))
            or os.path.exists(os.path.join(cur, ".git"))
        ):
            return cur

        parent = os.path.dirname(cur)
        if parent == cur:
            # Fallback path from src/functions/internal/
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
        cur = parent


if __name__ == "__main__":
    print(get_project_root())