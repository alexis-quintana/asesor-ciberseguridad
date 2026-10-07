"""Memoria de trabajo del sistema experto.

Almacena los hechos del caso en curso (respuestas del usuario y hechos
derivados por las reglas), separados de la base de conocimientos.

Fuente: Ghanem et al. (2023), ESASCF, representación de hechos.
"""

from __future__ import annotations

from .base_conocimientos import RESPUESTAS, VARIABLES


class MemoriaTrabajo:
    """Conjunto de hechos «nombre -> valor» del caso evaluado.

    Fuente: Ghanem et al. (2023), ESASCF, representación de hechos.
    """

    def __init__(self):
        self._hechos = {}

    def asignar(self, hecho, valor):
        """Registra o reemplaza el valor de un hecho."""
        self._hechos[hecho] = valor

    def obtener(self, hecho, defecto=None):
        """Devuelve el valor del hecho, o «defecto» si no existe."""
        return self._hechos.get(hecho, defecto)

    def tiene(self, hecho):
        """Indica si el hecho está registrado."""
        return hecho in self._hechos

    @property
    def hechos(self):
        """Copia de todos los hechos (modificarla no altera la memoria)."""
        return dict(self._hechos)

    def cargar_respuestas(self, respuestas):
        """Carga respuestas del cuestionario tras validarlas todas.

        Lanza ValueError si alguna clave no está en VARIABLES o algún valor no
        está en RESPUESTAS; en ese caso no se carga ninguna respuesta.
        """
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

    def respuestas_faltantes(self):
        """Claves de VARIABLES que aún no tienen respuesta, en orden del cuestionario."""
        return [clave for clave in VARIABLES if clave not in self._hechos]
