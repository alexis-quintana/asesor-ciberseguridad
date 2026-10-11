"""Verificación de la base de conocimientos (sección 4.3 del informe).

Busca cuatro problemas en las reglas, además de la comprobación estructural de
verificar_base() (identificadores, fuentes, hechos definidos):

1. Redundancia: reglas con las mismas condiciones y la misma conclusión (duplicadas) o cuyas
   condiciones contienen las de otra con la misma conclusión (subsunción).
2. Conflicto: dos reglas que pueden cumplirse a la vez y asignan valores distintos al mismo
   hecho. Si están en etapas distintas, la posterior sustituye al valor anterior (se informa como
   «resuelto por etapa»); si están en la misma etapa, es un conflicto sin resolver.
3. Circularidad: ciclos entre reglas, donde la conclusión de una alimenta, directa o
   indirectamente, sus propias condiciones. Una regla que corrige un hecho con otro valor y se
   dispara una sola vez se informa como autorreferencia benigna.
4. Reglas sin salida: reglas cuya conclusión produce un hecho que ninguna otra regla usa y que
   la interfaz tampoco muestra; y reglas inalcanzables, cuyas condiciones usan hechos que nadie
   produce.

Uso: python main.py --verificar
"""

from __future__ import annotations

from itertools import combinations

from app.conocimiento.base_conocimientos import REGLAS, VARIABLES
from app.conocimiento.base_reglas_criticidad import REGLAS_CRITICIDAD
from app.conocimiento.base_reglas_prioridad import REGLAS_PRIORIDAD
from app.conocimiento.base_reglas_riesgo import REGLAS_RIESGO
from app.inferencia.motor import AREAS, ETAPAS, OPERADORES

# Hechos que el motor calcula antes de cada etapa o a partir de las respuestas (no los produce una regla).
HECHOS_DEL_MOTOR = (
    set(VARIABLES)
    | {f"p_{a}" for a in AREAS + ("global",)} | {f"i100_{a}" for a in AREAS + ("global",)}
    | {f"r_{a}" for a in AREAS + ("global",)} | {f"nivel_r_{c}" for c in VARIABLES}
    | {"areas_riesgo_alto", "areas_riesgo_medio", "respuestas_desconocidas"}
    | {f"desconocidas_{a}" for a in AREAS}
)
# Hechos que la interfaz y el reporte leen: son salidas del sistema aunque ninguna regla los use.
PREFIJOS_DE_SALIDA = ("riesgo_global", "prioridad_", "zona_global", "banda_", "nivel_p_", "nivel_i_")
SALIDAS_DIRECTAS = ("recomendacion", "solicitud_verificacion", "recomendacion_adicional")


def reglas_base():
    """Todas las reglas de la base original, con las genéricas ya expandidas."""
    return list(REGLAS) + list(REGLAS_RIESGO) + list(REGLAS_PRIORIDAD) + list(REGLAS_CRITICIDAD)


def _clave(r):
    return r.get("clave", r["id"])


def _hecho_producido(r):
    e = r["entonces"]
    if e["tipo"] == "hallazgo":
        return e["id"]
    if e["tipo"] in ("nivel", "prioridad"):
        return e["hecho"]
    return None


def _valor_producido(r):
    e = r["entonces"]
    return True if e["tipo"] == "hallazgo" else e.get("valor")


def _firma_condiciones(r):
    return frozenset((c["hecho"], c["operador"], repr(c["valor"])) for c in r["si"])


def _firma_conclusion(r):
    e = r["entonces"]
    return (e["tipo"], e.get("id"), e.get("hecho"), repr(e.get("valor")), e.get("texto"), e.get("area"))


def _candidatos(condiciones):
    """Valores de prueba para decidir si un conjunto de condiciones sobre un hecho es satisfacible."""
    valores = []
    for c in condiciones:
        v = c["valor"]
        for x in (v if c["operador"] == "en" else [v]):
            valores.append(x)
            if isinstance(x, (int, float)) and not isinstance(x, bool):
                valores += [x - 1, x + 1, x - 0.001, x + 0.001]
    return valores


def pueden_cumplirse_a_la_vez(a, b):
    """True si existe un conjunto de hechos que cumple todas las condiciones de ambas reglas."""
    por_hecho = {}
    for c in a["si"] + b["si"]:
        por_hecho.setdefault(c["hecho"], []).append(c)
    for condiciones in por_hecho.values():
        if len(condiciones) < 2:
            continue
        if not any(all(OPERADORES[c["operador"]](v, c["valor"]) for c in condiciones)
                   for v in _candidatos(condiciones)):
            return False
    return True


def redundancias(reglas):
    """Pares (regla, otra, tipo) con la misma conclusión y condiciones iguales o contenidas."""
    por_conclusion = {}
    for r in reglas:
        por_conclusion.setdefault(_firma_conclusion(r), []).append(r)
    hallados = []
    for grupo in por_conclusion.values():
        for a, b in combinations(grupo, 2):
            fa, fb = _firma_condiciones(a), _firma_condiciones(b)
            if fa == fb:
                hallados.append((_clave(a), _clave(b), "duplicada"))
            elif fa < fb:
                hallados.append((_clave(b), _clave(a), "subsumida"))
            elif fb < fa:
                hallados.append((_clave(a), _clave(b), "subsumida"))
    return hallados


def _lee_resultado(a, b):
    """Si la regla b tiene una condición sobre el hecho que produce a: «encadenada» o «incompatible»."""
    h = _hecho_producido(a)
    for c in b["si"]:
        if c["hecho"] == h:
            return "encadenada" if OPERADORES[c["operador"]](_valor_producido(a), c["valor"]) else "incompatible"
    return None


def conflictos(reglas):
    """Pares que asignan valores distintos al mismo hecho y pueden cumplirse a la vez."""
    por_hecho = {}
    for r in reglas:
        h = _hecho_producido(r)
        if h is not None:
            por_hecho.setdefault(h, []).append(r)
    resueltos, sin_resolver = [], []
    for h, grupo in por_hecho.items():
        for a, b in combinations(grupo, 2):
            if _valor_producido(a) == _valor_producido(b):
                continue
            lee = _lee_resultado(a, b) or _lee_resultado(b, a)
            if lee == "incompatible":
                continue                 # una lee el hecho de la otra con otro valor: nunca se dan juntas
            if lee is None and not pueden_cumplirse_a_la_vez(a, b):
                continue
            par = (_clave(a), _clave(b), h)
            (sin_resolver if a["etapa"] == b["etapa"] else resueltos).append(par)
    return resueltos, sin_resolver


def circularidad(reglas):
    """Ciclos entre reglas: (ciclos de varias reglas, autorreferencias benignas, autorreferencias dudosas)."""
    productoras = {}
    for r in reglas:
        h = _hecho_producido(r)
        if h is not None:
            productoras.setdefault(h, []).append(r)
    orden = {e: i for i, e in enumerate(ETAPAS)}
    grafo = {_clave(r): set() for r in reglas}
    benignas, dudosas = [], []
    for r in reglas:
        for c in r["si"]:
            for p in productoras.get(c["hecho"], []):
                if orden.get(p["etapa"], 0) > orden.get(r["etapa"], 0):
                    continue            # el motor procesa las etapas en orden: no puede alimentar hacia atrás
                if _clave(p) == _clave(r):
                    mismo = repr(c["valor"]) == repr(_valor_producido(r))
                    (dudosas if mismo else benignas).append(_clave(r))
                else:
                    grafo[_clave(p)].add(_clave(r))
    ciclos, estado = [], {}

    def visitar(n, camino):
        estado[n] = 1
        for m in grafo[n]:
            if estado.get(m) == 1:
                ciclos.append(camino[camino.index(m):] + [m] if m in camino else [n, m])
            elif m not in estado:
                visitar(m, camino + [m])
        estado[n] = 2

    for n in grafo:
        if n not in estado:
            visitar(n, [n])
    return ciclos, sorted(set(benignas)), sorted(set(dudosas))


def sin_salida(reglas):
    """(reglas cuyo hecho producido nadie usa ni muestra, reglas con condiciones sobre hechos que nadie produce)."""
    usados = {c["hecho"] for r in reglas for c in r["si"]}
    producidos = {h for r in reglas if (h := _hecho_producido(r)) is not None}
    muertas, inalcanzables = [], []
    for r in reglas:
        h = _hecho_producido(r)
        if h is not None and h not in usados and not h.startswith(PREFIJOS_DE_SALIDA):
            muertas.append(_clave(r))
        faltan = [c["hecho"] for c in r["si"] if c["hecho"] not in HECHOS_DEL_MOTOR | producidos]
        if faltan:
            inalcanzables.append((_clave(r), faltan))
    return muertas, inalcanzables


def verificar(reglas=None):
    """Ejecuta las cuatro comprobaciones y devuelve un dict con los hallazgos."""
    reglas = reglas_base() if reglas is None else reglas
    resueltos, sin_resolver = conflictos(reglas)
    ciclos, benignas, dudosas = circularidad(reglas)
    muertas, inalcanzables = sin_salida(reglas)
    return {
        "reglas": len(reglas), "redundancias": redundancias(reglas),
        "conflictos_resueltos_por_etapa": resueltos, "conflictos_sin_resolver": sin_resolver,
        "ciclos": ciclos, "autorreferencias_benignas": benignas, "autorreferencias_dudosas": dudosas,
        "reglas_sin_salida": muertas, "reglas_inalcanzables": inalcanzables,
    }


def hay_problemas(r):
    return bool(r["redundancias"] or r["conflictos_sin_resolver"] or r["ciclos"]
                or r["autorreferencias_dudosas"] or r["reglas_sin_salida"] or r["reglas_inalcanzables"])


def informe_texto(r):
    def pares(lista, n=6):
        texto = [x if isinstance(x, str) else "/".join(map(str, x)) for x in lista[:n]]
        return ", ".join(texto) + (" …" if len(lista) > n else "")
    resumen_resueltos = sorted({f"{a.split(':')[0]}→{b.split(':')[0]}" for a, b, h in
                                r["conflictos_resueltos_por_etapa"]})
    lineas = [
        "Verificación de la base de conocimientos", "=" * 40,
        f"Reglas revisadas (instancias): {r['reglas']}",
        f"Redundancias (duplicadas o subsumidas): {len(r['redundancias'])}"
        + (f" → {pares(r['redundancias'])}" if r["redundancias"] else ""),
        f"Conflictos sin resolver (misma etapa): {len(r['conflictos_sin_resolver'])}"
        + (f" → {pares(r['conflictos_sin_resolver'])}" if r["conflictos_sin_resolver"] else ""),
        f"Correcciones entre etapas (una regla posterior sustituye el valor): {len(r['conflictos_resueltos_por_etapa'])} pares de instancias"
        + (f" (reglas {', '.join(resumen_resueltos)})" if resumen_resueltos else ""),
        f"Ciclos entre reglas: {len(r['ciclos'])}"
        + (f" → {pares(r['ciclos'])}" if r["ciclos"] else ""),
        f"Autorreferencias benignas: {len(r['autorreferencias_benignas'])}"
        + (f" ({pares(r['autorreferencias_benignas'], 3)})" if r["autorreferencias_benignas"] else ""),
        f"Autorreferencias dudosas: {len(r['autorreferencias_dudosas'])}",
        f"Reglas sin salida: {len(r['reglas_sin_salida'])}"
        + (f" → {pares(r['reglas_sin_salida'])}" if r["reglas_sin_salida"] else ""),
        f"Reglas inalcanzables: {len(r['reglas_inalcanzables'])}"
        + (f" → {pares(r['reglas_inalcanzables'])}" if r["reglas_inalcanzables"] else ""),
        "Resultado: " + ("hay problemas por revisar." if hay_problemas(r) else "sin problemas sin explicar."),
    ]
    return "\n".join(lineas)


def main():
    r = verificar()
    print(informe_texto(r))
    return 1 if hay_problemas(r) else 0
