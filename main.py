"""Punto de entrada: ejecuta el asesor (consola o web).

Uso: python main.py [--demo] [--explicar] [--con-impacto] [--web] [--validar] [--verificar]
"""

import sys

from app.consola import main

if __name__ == "__main__":
    sys.exit(main())
