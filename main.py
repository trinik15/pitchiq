# main.py - PitchIQ root launcher
# Usage: streamlit run main.py
import os
import sys

# Resolve path to the actual app so Path(__file__).parent works correctly inside app.py
_here = os.path.dirname(os.path.abspath(__file__))
_app = os.path.join(_here, "pitchiq", "app.py")

with open(_app, "r", encoding="utf-8") as _f:
    _src = _f.read()

exec(compile(_src, _app, "exec"), {"__file__": _app, "__name__": "__main__"})
