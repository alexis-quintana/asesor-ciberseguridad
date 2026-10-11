"""Lista priorizada de recomendaciones.

Ordena los hallazgos por la prioridad que concluyeron las reglas R126–R131 (y R132
para los controles esenciales): alta, media o baja. Criterios de desempate, del
equipo: primero el área con mayor probabilidad P y, a igual P, el orden de los
controles en el cuestionario.

Los textos de las recomendaciones salen de las reglas vigentes (la base con los
cambios del mantenimiento), y las recomendaciones adicionales que concluyen las
reglas nuevas del administrador se ordenan junto con las demás según la prioridad
que se les asignó al crearlas.
"""

from __future__ import annotations

from app.conocimiento import mantenimiento
from app.conocimiento.base_conocimientos import VARIABLES

_RANGO = {"alta": 0, "media": 1, "baja": 2}


def _recomendaciones(reglas=None):
    """Texto de la recomendación de cada hallazgo (por id de hallazgo).

    Solo cuenta las reglas de recomendación activas: si el mantenimiento desactivó
    la regla de un hallazgo, ese hallazgo queda sin recomendación.
    """
    reglas = mantenimiento.reglas_vigentes() if reglas is None else reglas
    textos = {}
    for regla in reglas:
        if regla["etapa"] == "recomendacion":
            textos[regla["si"][0]["hecho"]] = regla["entonces"]["texto"]
    return textos


def lista_priorizada(resultado):
    """Devuelve las recomendaciones ordenadas, cada una con su prioridad.

    Cada elemento: orden, control, area, prioridad, pregunta, recomendacion y
    p_area (probabilidad del área, 0–100). Las recomendaciones adicionales traen
    «adicional» = True y como control el identificador de su regla.
    """
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
