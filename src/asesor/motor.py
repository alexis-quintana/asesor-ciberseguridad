"""Motor de inferencia.

Aplica las reglas de la base de conocimientos sobre la memoria de trabajo
mediante encadenamiento hacia adelante: se evalúan las reglas SI-ENTONCES y se
repite el ciclo hasta que ninguna regla nueva se dispare.

Fuente: Sihwi et al. (2016), §II.D, encadenamiento hacia adelante.

La clasificación por conteo de áreas (R097–R101) es PROVISIONAL: proviene de las
reglas R097–R101 (conteo de áreas con hallazgos, criterio propuesto por el
equipo) y será reemplazada por el modelo de riesgo de Sihwi et al. (2016) y
Koeze (2017) en un paso posterior. Este módulo no calcula puntajes ni fórmulas
de riesgo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .base_conocimientos import REGLAS, VARIABLES
from .base_reglas_riesgo import REGLAS_RIESGO
from .riesgo import hechos_numericos

# Orden de procesamiento de las etapas de la base de conocimientos.
ETAPAS_BASE = ("riesgo_parcial", "recomendacion", "riesgo_global", "verificacion")
# Etapas del modelo de riesgo (base_reglas_riesgo.py); solo corren si se cargaron
# los cuatro impactos.
ETAPAS_RIESGO = ("nivel_probabilidad", "nivel_impacto", "banda_riesgo", "zona")
ETAPAS = ETAPAS_BASE + ETAPAS_RIESGO

# Operadores de condición que usa la base de conocimientos.
OPERADORES = {
    "igual": lambda actual, esperado: actual == esperado,
    "mayor_que": lambda actual, esperado: actual > esperado,
    "menor_que": lambda actual, esperado: actual < esperado,
    "mayor_o_igual": lambda actual, esperado: actual >= esperado,
    "menor_o_igual": lambda actual, esperado: actual <= esperado,
}

TIPOS_CONCLUSION = (
    "hallazgo", "recomendacion", "clasificacion_provisional", "solicitud_verificacion",
    "nivel",
)

# Áreas en el orden del cuestionario.
AREAS = tuple(dict.fromkeys(v["area"] for v in VARIABLES.values()))


@dataclass
class Disparo:
    """Registro de una regla disparada, para la explicación."""

    id: str
    etapa: str
    area: str
    explicacion: str
    fuentes: list
    regla: dict = field(repr=False)


@dataclass
class ResultadoInferencia:
    """Conclusiones de una ejecución del motor.

    La clasificación provisional se reemplazará por el modelo de Sihwi et al.
    (2016) y Koeze (2017); es None si ninguna regla de riesgo global se disparó
    (por ejemplo, cuando hay respuestas «no_se»).
    """

    disparos: list = field(default_factory=list)
    hallazgos: list = field(default_factory=list)
    recomendaciones: dict = field(default_factory=dict)
    clasificacion_provisional: str | None = None
    verificaciones_solicitadas: list = field(default_factory=list)
    hechos: dict = field(default_factory=dict)


def _numero(regla):
    """Número de la regla a partir de su id (R001 -> 1)."""
    return int(re.sub(r"\D", "", regla["id"]))


def _validar_reglas(reglas):
    for regla in reglas:
        if regla["etapa"] not in ETAPAS:
            raise ValueError(f"{regla['id']}: etapa no soportada: {regla['etapa']!r}")
        for condicion in regla["si"]:
            if condicion["operador"] not in OPERADORES:
                raise ValueError(
                    f"{regla['id']}: operador no soportado: {condicion['operador']!r}"
                )
        if regla["entonces"]["tipo"] not in TIPOS_CONCLUSION:
            raise ValueError(
                f"{regla['id']}: conclusión no soportada: {regla['entonces']['tipo']!r}"
            )


def _actualizar_derivados(memoria, resultado):
    """Recalcula los hechos derivados que usan las reglas de síntesis."""
    areas = {h["area"] for h in resultado.hallazgos}
    memoria.asignar("areas_con_hallazgos", len(areas))
    desconocidas = [c for c in VARIABLES if memoria.obtener(c) == "no_se"]
    memoria.asignar("respuestas_desconocidas", len(desconocidas))
    for area in AREAS:
        memoria.asignar(
            f"desconocidas_{area}",
            sum(VARIABLES[c]["area"] == area for c in desconocidas),
        )


def _cumple(regla, memoria):
    """Una regla es aplicable si todas sus condiciones se cumplen (conjunción)."""
    for condicion in regla["si"]:
        if not memoria.tiene(condicion["hecho"]):
            return False
        actual = memoria.obtener(condicion["hecho"])
        if not OPERADORES[condicion["operador"]](actual, condicion["valor"]):
            return False
    return True


def _aplicar(regla, memoria, resultado):
    """Ejecuta la parte ENTONCES de la regla y registra el disparo."""
    entonces = regla["entonces"]
    tipo = entonces["tipo"]
    if tipo == "hallazgo":
        memoria.asignar(entonces["id"], True)
        resultado.hallazgos.append({"id": entonces["id"], "area": entonces["area"]})
    elif tipo == "recomendacion":
        resultado.recomendaciones.setdefault(entonces["area"], []).append(entonces["texto"])
    elif tipo == "clasificacion_provisional":
        resultado.clasificacion_provisional = entonces["nivel"]
    elif tipo == "solicitud_verificacion":
        resultado.verificaciones_solicitadas.append(entonces["area"])
    elif tipo == "nivel":
        memoria.asignar(entonces["hecho"], entonces["valor"])
    resultado.disparos.append(Disparo(
        id=regla["id"],
        etapa=regla["etapa"],
        area=regla["area"],
        explicacion=regla["explicacion"],
        fuentes=list(regla["fuentes"]),
        regla=regla,
    ))


def inferir(memoria, reglas=None, reglas_riesgo=None):
    """Ejecuta el encadenamiento hacia adelante sobre la memoria de trabajo.

    Fuente: Sihwi et al. (2016), §II.D.

    - Exige las 48 respuestas; si faltan, lanza ValueError con la lista.
    - Procesa las etapas en el orden de ETAPAS. Antes de cada etapa recalcula
      los hechos derivados (areas_con_hallazgos, respuestas_desconocidas y
      desconocidas_<area>). Dentro de la etapa repite el ciclo «evaluar reglas,
      disparar las aplicables» en orden de número hasta que ninguna regla nueva
      se dispare; cada regla se dispara una sola vez.
    - Si la memoria tiene los cuatro impactos, calcula los hechos numéricos
      (p_, i100_, r_) y ejecuta además las etapas del modelo de riesgo
      (niveles, bandas y zona; reglas R106–R125 de base_reglas_riesgo.py).
    - Modifica la memoria recibida (agrega hallazgos y hechos derivados).

    La clasificación global resultante es provisional (reglas R097–R101) y será
    reemplazada por el modelo de Sihwi et al. (2016) y Koeze (2017).
    """
    reglas = REGLAS if reglas is None else reglas
    reglas_riesgo = REGLAS_RIESGO if reglas_riesgo is None else reglas_riesgo
    reglas = list(reglas) + list(reglas_riesgo)
    faltantes = memoria.respuestas_faltantes()
    if faltantes:
        raise ValueError(f"Faltan respuestas: {', '.join(faltantes)}")
    _validar_reglas(reglas)

    resultado = ResultadoInferencia()
    disparadas = set()
    con_riesgo = memoria.impactos_cargados()
    if con_riesgo:
        respuestas = {c: memoria.obtener(c) for c in VARIABLES}
        impactos = {a: memoria.obtener(f"impacto_{a}") for a in AREAS}
        for hecho, valor in hechos_numericos(respuestas, impactos).items():
            memoria.asignar(hecho, valor)
    for etapa in ETAPAS:
        if etapa in ETAPAS_RIESGO and not con_riesgo:
            continue
        _actualizar_derivados(memoria, resultado)
        reglas_etapa = sorted((r for r in reglas if r["etapa"] == etapa), key=_numero)
        hubo_disparo = True
        while hubo_disparo:
            hubo_disparo = False
            for regla in reglas_etapa:
                clave = regla.get("clave", regla["id"])
                if clave in disparadas or not _cumple(regla, memoria):
                    continue
                disparadas.add(clave)
                _aplicar(regla, memoria, resultado)
                hubo_disparo = True
    resultado.hechos = memoria.hechos
    return resultado
