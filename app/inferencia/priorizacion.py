# Lista priorizada de recomendaciones.

from __future__ import annotations

from app.conocimiento import mantenimiento
from app.conocimiento.base_conocimientos import VARIABLES

_RANGO = {"alta": 0, "media": 1, "baja": 2}


def _recomendaciones(reglas=None):
    reglas = mantenimiento.reglas_vigentes() if reglas is None else reglas
    textos = {}
    for regla in reglas:
        if regla["etapa"] == "recomendacion":
            textos[regla["si"][0]["hecho"]] = regla["entonces"]["texto"]
    return textos


def lista_priorizada(resultado):
    textos = _recomendaciones(resultado.reglas or None)
    orden_control = {c: i for i, c in enumerate(VARIABLES)}
    items = []
    for p in resultado.prioridades:
        c = p["control"]
        texto = textos.get(f"hallazgo_{c}", "")
        if not texto:
            continue
        items.append({
            "control": c,
            "area": p["area"],
            "prioridad": p["prioridad"],
            "pregunta": VARIABLES[c]["pregunta"],
            "recomendacion": texto,
            "p_area": resultado.hechos[f"p_{p['area']}"],
            "adicional": False,
        })
    for extra in resultado.recomendaciones_adicionales:
        items.append({
            "control": extra["id"],
            "area": extra["area"],
            "prioridad": extra["prioridad"],
            "pregunta": f"Regla adicional {extra['id']} (agregada por el administrador)",
            "recomendacion": extra["texto"],
            "p_area": resultado.hechos[f"p_{extra['area']}"],
            "adicional": True,
        })
    items.sort(key=lambda x: (_RANGO[x["prioridad"]], -x["p_area"],
                              orden_control.get(x["control"], len(orden_control)), x["control"]))
    for n, item in enumerate(items, start=1):
        item["orden"] = n
    return items
