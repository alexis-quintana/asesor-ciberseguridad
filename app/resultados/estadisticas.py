# Estadísticas del resultado: fuente única para el reporte HTML y el PDF.

from __future__ import annotations

from collections import Counter

from app.conocimiento.base_conocimientos import VARIABLES
from app.inferencia.priorizacion import lista_priorizada
from app.inferencia.riesgo import AREAS, CORTE_ALTO, CORTE_MEDIO

RESPUESTAS_ORDEN = ("si", "parcialmente", "no", "no_se")
NOMBRE_RESPUESTA = {"si": "Sí", "parcialmente": "Parcialmente", "no": "No", "no_se": "No sé"}
PRIORIDADES_ORDEN = ("alta", "media", "baja")


def calcular_estadisticas(resultado):
    h = resultado.hechos
    lista = lista_priorizada(resultado)
    por_area_prioridad = Counter((i["area"], i["prioridad"]) for i in lista)
    areas = []
    total = Counter()
    for area in AREAS:
        claves = [c for c, v in VARIABLES.items() if v["area"] == area]
        conteo = Counter(h[c] for c in claves)
        total.update(conteo)
        areas.append({
            "area": area,
            "p": h[f"p_{area}"],
            "nivel": h[f"nivel_p_{area}"],
            "conteo": {r: conteo.get(r, 0) for r in RESPUESTAS_ORDEN},
            "total": len(claves),
            "recomendaciones": {p: por_area_prioridad.get((area, p), 0) for p in PRIORIDADES_ORDEN},
        })
    prioridades = Counter(i["prioridad"] for i in lista)
    return {
        "global_nivel": resultado.riesgo_global,
        "areas_alto": sum(1 for a in areas if a["nivel"] == "alto"),
        "areas_medio": sum(1 for a in areas if a["nivel"] == "medio"),
        "cortes": {"medio": CORTE_MEDIO, "alto": CORTE_ALTO},
        "areas": areas,
        "respuestas_total": {r: total.get(r, 0) for r in RESPUESTAS_ORDEN},
        "prioridades": {p: prioridades.get(p, 0) for p in PRIORIDADES_ORDEN},
        "n_recomendaciones": len(lista),
        "n_verificar": total.get("no_se", 0),
        "recomendaciones": lista,
    }
