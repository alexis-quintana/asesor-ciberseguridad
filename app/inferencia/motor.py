# Motor de inferencia.

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.conocimiento import mantenimiento
from app.conocimiento.base_conocimientos import REGLAS, VARIABLES
from app.conocimiento.base_reglas_criticidad import REGLAS_CRITICIDAD
from app.conocimiento.base_reglas_riesgo import REGLAS_RIESGO
from app.conocimiento.base_reglas_prioridad import REGLAS_PRIORIDAD
from app.inferencia.riesgo import hechos_nivel_respuesta, hechos_numericos, hechos_probabilidad

# Etapas del flujo principal, en orden.
ETAPAS_BASE = ("riesgo_parcial", "recomendacion", "verificacion",
               "nivel_probabilidad", "riesgo_global", "prioridad", "criticidad",
               "recomendacion_adicional")
# Etapas de la extensión: solo con los cuatro impactos.
ETAPAS_EXTENSION = ("nivel_impacto", "banda_riesgo", "zona")
ETAPAS = ETAPAS_BASE + ETAPAS_EXTENSION

# Operadores de condición que usa la base de conocimientos.
OPERADORES = {
    "igual": lambda actual, esperado: actual == esperado,
    "mayor_que": lambda actual, esperado: actual > esperado,
    "menor_que": lambda actual, esperado: actual < esperado,
    "mayor_o_igual": lambda actual, esperado: actual >= esperado,
    "menor_o_igual": lambda actual, esperado: actual <= esperado,
    "en": lambda actual, esperado: actual in esperado,
}

TIPOS_CONCLUSION = (
    "hallazgo", "recomendacion", "solicitud_verificacion", "nivel", "prioridad",
    "recomendacion_adicional",
)

# Áreas en el orden del cuestionario.
AREAS = tuple(dict.fromkeys(v["area"] for v in VARIABLES.values()))


@dataclass
class Disparo:

    id: str
    etapa: str
    area: str
    explicacion: str
    fuentes: list
    regla: dict = field(repr=False)
    # clave: instancia de la regla; observados: valores al disparar.
    clave: str = ""
    observados: dict = field(default_factory=dict)


@dataclass
class ResultadoInferencia:

    disparos: list = field(default_factory=list)
    hallazgos: list = field(default_factory=list)
    recomendaciones: dict = field(default_factory=dict)
    riesgo_global: str | None = None
    verificaciones_solicitadas: list = field(default_factory=list)
    prioridades: list = field(default_factory=list)
    recomendaciones_adicionales: list = field(default_factory=list)
    hechos: dict = field(default_factory=dict)
    # Estadísticas por etapa y reglas usadas.
    estadisticas: dict = field(default_factory=dict)
    reglas: list = field(default_factory=list, repr=False)


def _numero(regla):
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
    niveles = [memoria.obtener(f"nivel_p_{area}") for area in AREAS]
    memoria.asignar("areas_riesgo_alto", niveles.count("alto"))
    memoria.asignar("areas_riesgo_medio", niveles.count("medio"))
    desconocidas = [c for c in VARIABLES if memoria.obtener(c) == "no_se"]
    memoria.asignar("respuestas_desconocidas", len(desconocidas))
    for area in AREAS:
        memoria.asignar(
            f"desconocidas_{area}",
            sum(VARIABLES[c]["area"] == area for c in desconocidas),
        )


def _cumple(regla, memoria):
    for condicion in regla["si"]:
        if not memoria.tiene(condicion["hecho"]):
            return False
        actual = memoria.obtener(condicion["hecho"])
        if not OPERADORES[condicion["operador"]](actual, condicion["valor"]):
            return False
    return True


def _aplicar(regla, memoria, resultado):
    entonces = regla["entonces"]
    tipo = entonces["tipo"]
    observados = {c["hecho"]: memoria.obtener(c["hecho"]) for c in regla["si"]}
    if tipo == "hallazgo":
        memoria.asignar(entonces["id"], True)
        resultado.hallazgos.append({"id": entonces["id"], "area": entonces["area"]})
    elif tipo == "recomendacion":
        resultado.recomendaciones.setdefault(entonces["area"], []).append(entonces["texto"])
    elif tipo == "solicitud_verificacion":
        resultado.verificaciones_solicitadas.append(entonces["area"])
    elif tipo == "nivel":
        memoria.asignar(entonces["hecho"], entonces["valor"])
        if entonces["hecho"] == "riesgo_global":
            resultado.riesgo_global = entonces["valor"]
    elif tipo == "prioridad":
        memoria.asignar(entonces["hecho"], entonces["valor"])
        existente = next((p for p in resultado.prioridades
                          if p["control"] == entonces["control"]), None)
        if existente is not None:      # la criticidad (R132) corrige la prioridad ya asignada
            existente["prioridad"] = entonces["valor"]
        else:
            resultado.prioridades.append({"control": entonces["control"], "area": entonces["area"],
                                          "prioridad": entonces["valor"]})
    elif tipo == "recomendacion_adicional":
        resultado.recomendaciones_adicionales.append({
            "id": regla["id"], "area": entonces["area"], "texto": entonces["texto"],
            "prioridad": entonces["prioridad"]})
    resultado.disparos.append(Disparo(
        id=regla["id"],
        etapa=regla["etapa"],
        area=regla["area"],
        explicacion=regla["explicacion"],
        fuentes=list(regla["fuentes"]),
        regla=regla,
        clave=regla.get("clave", regla["id"]),
        observados=observados,
    ))


def inferir(memoria, reglas=None, reglas_riesgo=None, reglas_prioridad=None,
           reglas_criticidad=None):
    usar_mantenimiento = reglas is None
    reglas = REGLAS if reglas is None else reglas
    reglas_riesgo = REGLAS_RIESGO if reglas_riesgo is None else reglas_riesgo
    reglas_prioridad = REGLAS_PRIORIDAD if reglas_prioridad is None else reglas_prioridad
    reglas_criticidad = REGLAS_CRITICIDAD if reglas_criticidad is None else reglas_criticidad
    reglas = list(reglas) + list(reglas_riesgo) + list(reglas_prioridad) + list(reglas_criticidad)
    if usar_mantenimiento:
        reglas = mantenimiento.reglas_vigentes(reglas)
    faltantes = memoria.respuestas_faltantes()
    if faltantes:
        raise ValueError(f"Faltan respuestas: {', '.join(faltantes)}")
    _validar_reglas(reglas)

    resultado = ResultadoInferencia(reglas=reglas)
    disparadas = set()
    respuestas = {c: memoria.obtener(c) for c in VARIABLES}
    for hecho, valor in {**hechos_probabilidad(respuestas),
                         **hechos_nivel_respuesta(respuestas)}.items():
        memoria.asignar(hecho, valor)
    con_extension = memoria.impactos_cargados()
    if con_extension:
        impactos = {a: memoria.obtener(f"impacto_{a}") for a in AREAS}
        for hecho, valor in hechos_numericos(respuestas, impactos).items():
            memoria.asignar(hecho, valor)
    for etapa in ETAPAS:
        if etapa in ETAPAS_EXTENSION and not con_extension:
            continue
        _actualizar_derivados(memoria, resultado)
        reglas_etapa = sorted((r for r in reglas if r["etapa"] == etapa), key=_numero)
        estadistica = {"reglas": len(reglas_etapa), "evaluaciones": 0, "disparadas": 0, "pasadas": 0}
        hubo_disparo = True
        while hubo_disparo:
            hubo_disparo = False
            estadistica["pasadas"] += 1
            for regla in reglas_etapa:
                clave = regla.get("clave", regla["id"])
                if clave in disparadas:
                    continue
                estadistica["evaluaciones"] += 1
                if not _cumple(regla, memoria):
                    continue
                disparadas.add(clave)
                _aplicar(regla, memoria, resultado)
                estadistica["disparadas"] += 1
                hubo_disparo = True
        resultado.estadisticas[etapa] = estadistica
    resultado.hechos = memoria.hechos
    return resultado
