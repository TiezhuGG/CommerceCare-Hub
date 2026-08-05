"""Cross-platform development entrypoint for synthetic seed data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.scripts.seed import main

if __name__ == "__main__":
    main()
