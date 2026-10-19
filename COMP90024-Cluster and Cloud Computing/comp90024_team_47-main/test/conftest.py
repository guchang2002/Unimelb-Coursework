import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

# Allow tests to import modules like: from shared.cities import infer_city
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))