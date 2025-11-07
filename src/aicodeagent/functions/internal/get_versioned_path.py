import os


def get_versioned_path(base_path):
    """
    Returns a non-conflicting path by appending _1, _2, etc. if needed.
    Input: base_path = full secure absolute path (e.g., from get_secure_path)
    """
    if not os.path.exists(base_path):
        return base_path

    base, ext = os.path.splitext(base_path)
    i = 1
    while True:
        candidate = f"{base}_{i}{ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1
