from __future__ import annotations

import sys
from pathlib import Path


def ensure_repo_paths() -> Path:
    root = Path(__file__).resolve().parents[2]
    for candidate in (root, root / "src"):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
    return root
