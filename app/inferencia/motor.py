"""Motor de inferencia.

Aplica las reglas de la base de conocimientos sobre la memoria de trabajo
mediante encadenamiento hacia adelante: se evalúan las reglas SI-ENTONCES y se
repite el ciclo hasta que ninguna regla nueva se dispare.

Fuente: Sihwi et al. (2016), §II.D, encadenamiento hacia adelante.

Cómo se seleccionan, evalúan y aplican las reglas (para explicarlo y demostrarlo):

1. SELECCIÓN: las reglas se agrupan por ETAPA y las etapas se procesan en un orden
   fijo (ETAPAS). Una etapa solo corre cuando la anterior terminó; así los hechos que
   una regla produce (p. ej. «hallazgo_x») ya existen cuando otra regla los necesita.
   El encadenamiento entre reglas ocurre ENTRE etapas: respuesta → hallazgo →
   recomendación → prioridad → criticidad; y respuestas → P del área → nivel del área
   → riesgo global.
2. EVALUACIÓN: dentro de la etapa se recorren sus reglas en orden de número. _cumple()
   exige que existan todos los hechos de las condiciones y que todas se cumplan
   (conjunción). Una regla cuyo hecho no existe o no coincide simplemente no se aplica.
3. APLICACIÓN: _aplicar() ejecuta el ENTONCES (asigna un hecho o registra una
   conclusión) y guarda un «Disparo» con los valores observados de las condiciones.
4. REPETICIÓN: el recorrido se repite hasta que ninguna regla nueva se dispare; cada
   instancia de regla se dispara una sola vez. En este modelo ninguna regla de una
   etapa consume lo que produce otra de la misma etapa, así que la segunda pasada
   solo confirma que no queda nada por disparar.
5. CONFLICTOS: el orden por número hace el resultado determinista, pero el motor NO
   detecta conclusiones contradictorias sobre un mismo hecho. Las reglas nuevas del
   mantenimiento solo concluyen recomendaciones, por lo que no pueden producirlos.

Flujo principal: las respuestas producen hallazgos y recomendaciones; la
probabilidad de cada área (Sihwi et al., 2016) da su nivel de riesgo (R106–R108)
y el conteo de áreas con riesgo alto da el riesgo global (R097–R101). La prioridad
de cada hallazgo (R126–R131) combina el nivel de su respuesta y el de su área,
como la matriz de Sihwi et al. (2016); la criticidad (R132) sube a «media» la prioridad
de los controles esenciales (Pawar y Palivela, 2022). Extensión
opcional de investigación: con los cuatro impactos cargados se ejecutan además
las etapas de impacto, banda de riesgo y zona (R109–R125; Sihwi et al., 2016 y
Koeze, 2017).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.conocimiento import mantenimiento
from app.conocimiento.base_conocimientos import REGLAS, VARIABLES
from app.conocimiento.base_reglas_criticidad import REGLAS_CRITICIDAD
from app.conocimiento.base_reglas_riesgo import REGLAS_RIESGO
from app.conocimiento.base_reglas_prioridad import REGLAS_PRIORIDAD
from app.inferencia.riesgo import hechos_nivel_respuesta, hechos_numericos, hechos_probabilidad

# Flujo principal, en orden: hallazgos, recomendaciones, verificación de «no sé»,
# nivel de riesgo de cada área, riesgo global, prioridad de cada hallazgo, criticidad
# de los controles esenciales y recomendaciones adicionales del mantenimiento.
ETAPAS_BASE = ("riesgo_parcial", "recomendacion", "verificacion",
               "nivel_probabilidad", "riesgo_global", "prioridad", "criticidad",
               "recomendacion_adicional")
# Extensión opcional (base_reglas_riesgo.py): solo corre si se cargaron los
# cuatro impactos.
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
    """Registro de una regla disparada, para la explicación."""

    id: str
    etapa: str
    area: str
    explicacion: str
    fuentes: list
    regla: dict = field(repr=False)
    # «clave» distingue las instancias de una regla genérica (R106:cuentas) y
    # «observados» guarda el valor que tenía cada hecho de las condiciones al disparar.
    clave: str = ""
    observados: dict = field(default_factory=dict)


@dataclass
class ResultadoInferencia:
    """Conclusiones de una ejecución del motor.

    «riesgo_global» es el nivel (bajo, medio o alto) que concluyen las reglas
    R097–R101; «hechos» es la memoria de trabajo al terminar (incluye
    nivel_p_<área> con el nivel de riesgo de cada área).
    """

    disparos: list = field(default_factory=list)
    hallazgos: list = field(default_factory=list)
    recomendaciones: dict = field(default_factory=dict)
    riesgo_global: str | None = None
    verificaciones_solicitadas: list = field(default_factory=list)
    prioridades: list = field(default_factory=list)
    recomendaciones_adicionales: list = field(default_factory=list)
    hechos: dict = field(default_factory=dict)
    # Por etapa: reglas, evaluaciones de condiciones, disparos y pasadas (para mostrar
    # cómo trabajó el motor) y las reglas usadas, para explicar las que no se aplicaron.
    estadisticas: dict = field(default_factory=dict)
    reglas: list = field(default_factory=list, repr=False)


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
    """Ejecuta el encadenamiento hacia adelante sobre la memoria de trabajo.

    Fuente: Sihwi et al. (2016), §II.D.

    - Exige las 48 respuestas; si faltan, lanza ValueError con la lista.
    - Calcula la probabilidad de cada área (p_<área>) y procesa las etapas en el
      orden de ETAPAS. Antes de cada etapa recalcula los hechos derivados
      (areas_riesgo_alto, areas_riesgo_medio, respuestas_desconocidas y
      desconocidas_<área>). Dentro de la etapa repite el ciclo «evaluar reglas,
      disparar las aplicables» en orden de número hasta que ninguna regla nueva
      se dispare; cada regla se dispara una sola vez.
    - Si la memoria tiene los cuatro impactos, calcula además los hechos
      numéricos de la extensión (i100_, r_ y los globales) y ejecuta sus etapas.
    - Modifica la memoria recibida (agrega hallazgos y hechos derivados).
    - Sin argumentos de reglas usa la versión vigente de la base: la original con los
      cambios del mantenimiento (reglas desactivadas, editadas y nuevas). Si se pasan
      reglas explícitas (pruebas), se usan tal cual.
    """
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
