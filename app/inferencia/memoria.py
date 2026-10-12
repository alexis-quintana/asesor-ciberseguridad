# Memoria de trabajo del sistema experto.

from __future__ import annotations

from app.conocimiento.base_conocimientos import RESPUESTAS, VARIABLES
from app.inferencia.riesgo import AREAS, validar_impactos


class MemoriaTrabajo:

    def __init__(self):
        self._hechos = {}

    def asignar(self, hecho, valor):
        self._hechos[hecho] = valor

    def obtener(self, hecho, defecto=None):
        return self._hechos.get(hecho, defecto)

    def tiene(self, hecho):
        return hecho in self._hechos

    @property
    def hechos(self):
        return dict(self._hechos)

    def cargar_respuestas(self, respuestas):
        for clave, valor in respuestas.items():
            if clave not in VARIABLES:
                raise ValueError(f"Variable desconocida: {clave!r}")
            if valor not in RESPUESTAS:
                raise ValueError(
                    f"Respuesta no permitida para {clave!r}: {valor!r}; "
                    f"valores válidos: {', '.join(RESPUESTAS)}"
                )
        for clave, valor in respuestas.items():
            self.asignar(clave, valor)

    def cargar_impactos(self, impactos):
        validar_impactos(impactos)
        for area in AREAS:
            self.asignar(f"impacto_{area}", impactos[area])

    def impactos_cargados(self):
        return all(self.tiene(f"impacto_{a}") for a in AREAS)

    def respuestas_faltantes(self):
        return [clave for clave in VARIABLES if clave not in self._hechos]
