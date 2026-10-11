"""Validación del sistema con casos de prueba (sección 4 del informe).

Lee tests/casos/casos_prueba.csv (50 casos con su resultado esperado, calculado por el oráculo
independiente tests/oraculo.py), ejecuta el motor sobre la base original (sin los cambios del
mantenimiento) y calcula las métricas del informe:

- Exactitud: casos en que coinciden el nivel de cada área, el riesgo global, la lista de
  hallazgos con su prioridad y su orden, las verificaciones y, si el caso trae impactos,
  la zona y la banda global (fórmula 4).
- Cobertura: reglas definidas (R001–R132) que se disparan al menos una vez en el conjunto (fórmula 5).
- Consistencia: casos con resultado idéntico al ejecutarlos de nuevo y al cargar las respuestas
  en otro orden (fórmula 6).
- Reglas disparadas por caso (promedio, mínimo y máximo).

Uso: python main.py --validar   (genera además docs/validacion/resultados_casos.csv y .md)
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from app.conocimiento.base_conocimientos import REGLAS, VARIABLES
from app.conocimiento.base_reglas_criticidad import REGLAS_CRITICIDAD
from app.conocimiento.base_reglas_prioridad import REGLAS_PRIORIDAD
from app.conocimiento.base_reglas_riesgo import REGLAS_RIESGO
from app.inferencia.memoria import MemoriaTrabajo
from app.inferencia.motor import AREAS, inferir
from app.inferencia.priorizacion import lista_priorizada

RAIZ = Path(__file__).resolve().parent.parent
CASOS = RAIZ / "tests" / "casos" / "casos_prueba.csv"
SALIDA = RAIZ / "docs" / "validacion"

# Reglas de plantilla: dos por control (hallazgo y recomendación), R001–R096.
IDS_PLANTILLA = {r["id"] for r in REGLAS if r["etapa"] in ("riesgo_parcial", "recomendacion")}


def cargar_casos(ruta=CASOS):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ejecutar(respuestas, impactos=None, orden=None, reglas=None):
    """Corre el motor y devuelve el resultado normalizado.

    Sin «reglas» usa la base original; «reglas» es una tupla (base, riesgo, prioridad, criticidad)
    y sirve para probar variantes alteradas (análisis de sensibilidad de la validación).
    """
    juego = reglas or (REGLAS, REGLAS_RIESGO, REGLAS_PRIORIDAD, REGLAS_CRITICIDAD)
    claves = list(orden) if orden else list(respuestas)
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas({c: respuestas[c] for c in claves})
    if impactos:
        memoria.cargar_impactos(impactos)
    res = inferir(memoria, *juego)
    lista = lista_priorizada(res)
    return {
        "niveles": {a: res.hechos[f"nivel_p_{a}"] for a in AREAS},
        "global": res.riesgo_global,
        "hallazgos": len(res.hallazgos),
        "priorizadas": [(i["control"], i["prioridad"]) for i in lista if not i["adicional"]],
        "verificaciones": sorted(set(res.verificaciones_solicitadas), key=AREAS.index),
        "zona": res.hechos.get("zona_global", ""),
        "banda_global": res.hechos.get("banda_global", ""),
        "disparadas": sorted({d.id for d in res.disparos}),
        "n_disparos": len(res.disparos),
    }


def _esperado(fila):
    return {
        "niveles": json.loads(fila["niveles_esperados"]),
        "global": fila["global_esperado"],
        "hallazgos": int(fila["hallazgos_esperados"]),
        "priorizadas": [tuple(x.split(":")) for x in fila["priorizadas_esperadas"].split(";") if x],
        "verificaciones": [x for x in fila["verificaciones_esperadas"].split(";") if x],
        "zona": fila["zona_esperada"],
        "banda_global": fila["banda_global_esperada"],
    }


def comparar(esperado, obtenido, con_impacto):
    """Lista de diferencias entre lo esperado y lo obtenido (vacía si coincide)."""
    dif = []
    for a in AREAS:
        if esperado["niveles"][a] != obtenido["niveles"][a]:
            dif.append(f"nivel de {a}: esperado {esperado['niveles'][a]}, obtenido {obtenido['niveles'][a]}")
    if esperado["global"] != obtenido["global"]:
        dif.append(f"riesgo global: esperado {esperado['global']}, obtenido {obtenido['global']}")
    if esperado["hallazgos"] != obtenido["hallazgos"]:
        dif.append(f"hallazgos: esperados {esperado['hallazgos']}, obtenidos {obtenido['hallazgos']}")
    if esperado["priorizadas"] != obtenido["priorizadas"]:
        dif.append("lista priorizada distinta (prioridad u orden)")
    if esperado["verificaciones"] != obtenido["verificaciones"]:
        dif.append(f"verificaciones: esperadas {esperado['verificaciones']}, obtenidas {obtenido['verificaciones']}")
    if con_impacto:
        if esperado["zona"] != obtenido["zona"]:
            dif.append(f"zona: esperada {esperado['zona']}, obtenida {obtenido['zona']}")
        if esperado["banda_global"] != obtenido["banda_global"]:
            dif.append(f"banda global: esperada {esperado['banda_global']}, obtenida {obtenido['banda_global']}")
    return dif


def validar(casos=None, reglas=None):
    """Ejecuta todos los casos y devuelve (filas por caso, métricas)."""
    casos = cargar_casos() if casos is None else casos
    filas, disparadas_total = [], set()
    consistentes = 0
    azar = random.Random(7)
    for fila in casos:
        resp = json.loads(fila["respuestas_json"])
        imp = json.loads(fila["impactos_json"]) if fila["impactos_json"] else None
        obt = ejecutar(resp, imp, reglas=reglas)
        # Consistencia: segunda ejecución y orden de carga distinto.
        orden = list(resp)
        azar.shuffle(orden)
        igual = all(ejecutar(resp, imp, o, reglas)[k] == obt[k]
                    for o in (None, orden)
                    for k in ("niveles", "global", "priorizadas", "verificaciones", "zona", "banda_global"))
        consistentes += igual
        dif = comparar(_esperado(fila), obt, bool(imp))
        disparadas_total |= set(obt["disparadas"])
        filas.append({"caso": fila["caso_id"], "grupo": fila["grupo"], "descripcion": fila["descripcion"],
                      "con_impacto": bool(imp), "acierto": not dif, "diferencias": "; ".join(dif),
                      "consistente": igual, "n_disparos": obt["n_disparos"], "global": obt["global"],
                      "hallazgos": obt["hallazgos"], "niveles": obt["niveles"]})
    ids_definidos = ({r["id"] for r in REGLAS} | {r["id"] for r in REGLAS_RIESGO}
                     | {r["id"] for r in REGLAS_PRIORIDAD} | {r["id"] for r in REGLAS_CRITICIDAD})
    propias = ids_definidos - IDS_PLANTILLA
    n = len(filas)
    disparos = [f["n_disparos"] for f in filas]
    sin_disparar = sorted(ids_definidos - disparadas_total)
    metricas = {
        "casos": n,
        "aciertos": sum(f["acierto"] for f in filas),
        "exactitud": 100 * sum(f["acierto"] for f in filas) / n,
        "reglas_definidas": len(ids_definidos),
        "reglas_disparadas": len(ids_definidos & disparadas_total),
        "cobertura": 100 * len(ids_definidos & disparadas_total) / len(ids_definidos),
        "reglas_propias": len(propias),
        "propias_disparadas": len(propias & disparadas_total),
        "cobertura_propias": 100 * len(propias & disparadas_total) / len(propias),
        "reglas_sin_disparar": sin_disparar,
        "consistentes": consistentes,
        "consistencia": 100 * consistentes / n,
        "disparos_promedio": sum(disparos) / n, "disparos_min": min(disparos), "disparos_max": max(disparos),
        "por_grupo": {g: (sum(f["acierto"] for f in filas if f["grupo"] == g),
                          sum(1 for f in filas if f["grupo"] == g)) for g in ("G1", "G2", "G3")},
    }
    return filas, metricas


def mutaciones(casos=None):
    """Sensibilidad de la validación: altera la base de cuatro formas y cuenta los casos que lo detectan.

    Devuelve [(descripción, casos que fallan)]. Una validación que no detectara estas alteraciones
    no serviría para encontrar errores reales de la base.
    """
    import copy
    casos = cargar_casos() if casos is None else casos

    def variante(cambiar):
        base, riesgo, prioridad, criticidad = (copy.deepcopy(x) for x in
                                               (REGLAS, REGLAS_RIESGO, REGLAS_PRIORIDAD, REGLAS_CRITICIDAD))
        cambiar(base, riesgo, prioridad, criticidad)
        return base, riesgo, prioridad, criticidad

    def corte(base, riesgo, prioridad, criticidad):          # corte medio 34 -> 40
        for r in riesgo:
            if r["id"] in ("R106", "R107"):
                for c in r["si"]:
                    if c["valor"] == 34:
                        c["valor"] = 40

    def celda(base, riesgo, prioridad, criticidad):          # (alto, alto) pasa de «alta» a «media»
        for r in prioridad:
            if r["id"] == "R126":
                r["entonces"]["valor"] = "media"

    def sin_r132(base, riesgo, prioridad, criticidad):       # se elimina la regla de criticidad
        criticidad.clear()

    def sin_r097(base, riesgo, prioridad, criticidad):       # se elimina «dos áreas altas → global alto»
        base[:] = [r for r in base if r["id"] != "R097"]

    resultado = []
    for texto, cambio in (("corte medio 34 → 40 (R106–R107)", corte),
                          ("celda alto/alto: prioridad alta → media (R126)", celda),
                          ("se elimina R132 (controles esenciales)", sin_r132),
                          ("se elimina R097 (dos áreas altas)", sin_r097)):
        filas, m = validar(casos, variante(cambio))
        resultado.append((texto, m["casos"] - m["aciertos"]))
    return resultado


def informe_texto(filas, m):
    lineas = ["Validación con casos de prueba", "=" * 31,
              f"Casos: {m['casos']}  |  Aciertos: {m['aciertos']}  |  Exactitud: {m['exactitud']:.1f} %",
              "Aciertos por grupo: " + ", ".join(f"{g} {a}/{t}" for g, (a, t) in m["por_grupo"].items()),
              f"Cobertura de reglas: {m['reglas_disparadas']}/{m['reglas_definidas']} = {m['cobertura']:.1f} %",
              f"Cobertura de reglas de lógica propia: {m['propias_disparadas']}/{m['reglas_propias']} = "
              f"{m['cobertura_propias']:.1f} %",
              f"Consistencia: {m['consistentes']}/{m['casos']} = {m['consistencia']:.1f} %",
              f"Reglas disparadas por caso: promedio {m['disparos_promedio']:.1f}, mínimo {m['disparos_min']}, "
              f"máximo {m['disparos_max']}"]
    if m["reglas_sin_disparar"]:
        lineas.append("Reglas que ningún caso dispara: " + ", ".join(m["reglas_sin_disparar"]))
    fallos = [f for f in filas if not f["acierto"]]
    if fallos:
        lineas.append("\nCasos con diferencias:")
        lineas += [f"  {f['caso']}: {f['diferencias']}" for f in fallos]
    return "\n".join(lineas)


def guardar(filas, m, carpeta=SALIDA):
    """Escribe el detalle por caso (CSV) y el resumen (Markdown) para el Anexo C."""
    carpeta.mkdir(parents=True, exist_ok=True)
    with open(carpeta / "resultados_casos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["caso", "grupo", "descripcion", "con_impacto", "riesgo_global", "hallazgos",
                    "reglas_disparadas", "coincide", "consistente", "diferencias"])
        for x in filas:
            w.writerow([x["caso"], x["grupo"], x["descripcion"], "sí" if x["con_impacto"] else "no", x["global"],
                        x["hallazgos"], x["n_disparos"], "sí" if x["acierto"] else "no",
                        "sí" if x["consistente"] else "no", x["diferencias"]])
    texto = informe_texto(filas, m) + "\n\nSensibilidad de la validación (base alterada → casos que fallan):\n" + "\n".join(
        f"  {n:>2} de {m['casos']}: {t}" for t, n in mutaciones())
    (carpeta / "resumen_validacion.md").write_text("```\n" + texto + "\n```\n", encoding="utf-8")


def main():
    filas, m = validar()
    print(informe_texto(filas, m))
    print("\nSensibilidad de la validación (base alterada → casos que fallan):")
    for texto, n in mutaciones():
        print(f"  {n:>2} de {m['casos']}: {texto}")
    guardar(filas, m)
    print(f"\nDetalle guardado en {SALIDA}")
    return 0 if m["aciertos"] == m["casos"] else 1
