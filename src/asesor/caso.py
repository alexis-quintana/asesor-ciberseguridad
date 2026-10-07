"""Evaluación de un caso completo: carga de datos, inferencia y resultado.

Reúne los pasos que comparten la consola y la web, para no repetirlos.
"""

from __future__ import annotations

from .memoria import MemoriaTrabajo
from .motor import inferir


def evaluar(respuestas, impactos=None):
    """Carga las 48 respuestas (y, si se dan, los 4 impactos) y ejecuta el motor.

    Lanza ValueError si faltan respuestas o si algún valor no es válido.
    Devuelve el ResultadoInferencia.
    """
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    if impactos is not None:
        memoria.cargar_impactos(impactos)
    return inferir(memoria)
