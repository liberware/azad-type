"""Launch Azad Type directly from this checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from azad_type.__main__ import main

if __name__ == "__main__":
    main()

