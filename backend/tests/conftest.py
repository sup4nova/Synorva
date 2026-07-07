# backend/tests/conftest.py
# Ensures the repo root is on sys.path so `import backend.xxx` works
# and relative paths used by the app (e.g. "backend/models/...") resolve
# correctly, regardless of where pytest is invoked from.

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
