# Evaluación de un caso completo: carga de datos, inferencia y resultado.

from __future__ import annotations

from app.inferencia.memoria import MemoriaTrabajo
from app.inferencia.motor import inferir


def evaluar(respuestas, impactos=None):
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    if impactos is not None:
        memoria.cargar_impactos(impactos)
    return inferir(memoria)
