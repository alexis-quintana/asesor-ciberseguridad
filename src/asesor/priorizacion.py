"""Lista priorizada de recomendaciones.

Ordena los hallazgos por la prioridad que concluyeron las reglas R126–R131
(alta, media, baja). Criterios de desempate, del equipo: primero el área con
mayor probabilidad P y, a igual P, el orden de los controles en el cuestionario.
"""

from __future__ import annotations

from .base_conocimientos import REGLAS, VARIABLES

_RANGO = {"alta": 0, "media": 1, "baja": 2}


def _recomendaciones():
    """Texto de la recomendación de cada hallazgo (por id de hallazgo)."""
    textos = {}
    for regla in REGLAS:
        if regla["etapa"] == "recomendacion":
            textos[regla["si"][0]["hecho"]] = regla["entonces"]["texto"]
    return textos


def lista_priorizada(resultado):
    """Devuelve las recomendaciones ordenadas, cada una con su prioridad.

    Cada elemento: orden, control, area, prioridad, pregunta, recomendacion y
    p_area (probabilidad del área, 0–100).
    """
    textos = _recomendaciones()
    orden_control = {c: i for i, c in enumerate(VARIABLES)}
    items = []
    for p in resultado.prioridades:
        c = p["control"]
        items.append({
            "control": c,
            "area": p["area"],
            "prioridad": p["prioridad"],
            "pregunta": VARIABLES[c]["pregunta"],
            "recomendacion": textos.get(f"hallazgo_{c}", ""),
            "p_area": resultado.hechos[f"p_{p['area']}"],
        })
    items.sort(key=lambda x: (_RANGO[x["prioridad"]], -x["p_area"], orden_control[x["control"]]))
    for n, item in enumerate(items, start=1):
        item["orden"] = n
    return items
