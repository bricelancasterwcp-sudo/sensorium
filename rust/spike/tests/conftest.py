"""Makes `rust/spike/convert.py` importable as `import convert` from this
directory's tests, without touching `pyproject.toml` (the plan's Global
Constraints forbid referencing spike code from it). `pyproject.toml`'s
`testpaths = ["tests"]` already keeps the main suite from collecting
anything under `rust/`; this file only affects a run that explicitly
targets `rust/spike/tests/`."""
import sys
from pathlib import Path

SPIKE_ROOT = Path(__file__).resolve().parents[1]
if str(SPIKE_ROOT) not in sys.path:
    sys.path.insert(0, str(SPIKE_ROOT))
