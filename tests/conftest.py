import sys
from pathlib import Path

# Tests live in tests/, the app modules (utils.py, analytics.py, db.py, config.py)
# live in the repo root. Make sure the root is importable regardless of which
# directory pytest is invoked from or which pytest version is in use.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
