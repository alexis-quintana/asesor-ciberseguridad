"""Pruebas del asesor. Agrega «src» a sys.path para que «python -m unittest» funcione desde la raíz."""

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
