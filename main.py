"""Punto de entrada: ejecuta la interfaz de consola del asesor.

Uso: python main.py [--demo] [--explicar]
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from asesor.interfaz_consola import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
