# main.py - PitchIQ root launcher
# Usage: streamlit run main.py
import os
import sys

# Add repo root to path so the 'pitchiq' package is importable as a module.
# This lets app.py be loaded via a clean import instead of exec(), which
# preserves IDE static analysis, correct __file__ resolution, and the normal
# Python module system.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from pitchiq.app import main  # noqa: E402

main()
