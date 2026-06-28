"""
Test bootstrap — runs before any test module is imported.

Sets the required environment variables and pre-creates the directory
that instrument.py expects at `logs/system/instrument.log` (relative
to cwd, which is `src/` when pytest is invoked from there).
"""
import os
import pathlib
import sys

# ── paths ──────────────────────────────────────────────────────────────────
src_dir = pathlib.Path(__file__).parent.parent          # …/src
log_dir = src_dir / "logs"
(log_dir / "system").mkdir(parents=True, exist_ok=True)
(log_dir / "samples").mkdir(parents=True, exist_ok=True)

# ── env vars (must be set before instrument.py is imported) ────────────────
os.environ.setdefault("LOGS_ROOT_DIR", str(log_dir))
os.environ.setdefault("OPENAI_API_KEY", "test-sk-not-real")

# ── make src/ importable ───────────────────────────────────────────────────
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
