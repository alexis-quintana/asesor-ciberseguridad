"""Reglas de prioridad de las recomendaciones (R126–R131).

Cada hallazgo recibe una prioridad (alta, media o baja) combinando dos niveles:
el de su respuesta (nivel_r_<control>, con los puntajes y cortes de Sihwi) y el
de riesgo de su área (nivel_p_<área>, R106–R108). Las celdas son las de la
matriz de 3×3 de Sihwi et al. (2016, Tabla III, p. 3), con los mismos colores
que usa la zona (R117–R125): roja = alta, amarilla = media, verde = baja.

ADAPTACIÓN DEL EQUIPO: en Sihwi los ejes son probabilidad × impacto; aquí son
respuesta × nivel del área, porque en el flujo principal no hay impacto. Los
nombres «alta, media, baja» y su correspondencia con los colores son del equipo.

Solo hay 6 reglas: la fila de respuesta «bajo» («sí») no genera hallazgo, así
que su regla nunca se dispararía. Las reglas son genéricas: se escriben una vez
y se expanden a los 48 controles (R126:<control>).
"""

from __future__ import annotations

from .base_conocimientos import FUENTES, VARIABLES

_FUENTES = [{"id": "SIHWI_2016",
             "localizacion": "Tabla III, p. 3 (matriz de 9 categorías); §II.D, p. 4 (interpretación)"}]

# (nivel de la respuesta, nivel del área) -> prioridad.
_CELDAS = (
    ("alto", "alto", "alta"),
    ("alto", "medio", "media"),
    ("alto", "bajo", "baja"),
    ("medio", "alto", "media"),
    ("medio", "medio", "media"),
    ("medio", "bajo", "baja"),
)

REGLAS_PRIORIDAD_GENERICAS = []
for _n, (_r, _a, _prio) in enumerate(_CELDAS, start=126):
    REGLAS_PRIORIDAD_GENERICAS.append({
        "id": f"R{_n}",
        "etapa": "prioridad",
        "nivel_respuesta": _r,
        "nivel_area": _a,
        "prioridad": _prio,
        "fuentes": _FUENTES,
        "tipo_respaldo": "fuente_con_adaptacion",
        "evidencia_del_articulo": (
            "Sihwi clasifica las 9 celdas de la Tabla III (p. 3); aquí los ejes son "
            "respuesta × nivel del área y el nombre de la prioridad es del equipo."),
        "validacion_experto": "pendiente",
    })


def expandir(genericas=None):
    """Instancia cada regla en los 48 controles (clave R126:<control>)."""
    genericas = REGLAS_PRIORIDAD_GENERICAS if genericas is None else genericas
    concretas = []
    for g in genericas:
        for control, datos in VARIABLES.items():
            area = datos["area"]
            concretas.append({
                **g,
                "ambito": control,
                "clave": f"{g['id']}:{control}",
                "area": area,
                "si": [
                    {"hecho": f"hallazgo_{control}", "operador": "igual", "valor": True},
                    {"hecho": f"nivel_r_{control}", "operador": "igual", "valor": g["nivel_respuesta"]},
                    {"hecho": f"nivel_p_{area}", "operador": "igual", "valor": g["nivel_area"]},
                ],
                "entonces": {"tipo": "prioridad", "hecho": f"prioridad_{control}",
                             "valor": g["prioridad"], "control": control, "area": area},
                "explicacion": (
                    f"La respuesta a «{datos['pregunta']}» está en nivel «{g['nivel_respuesta']}» "
                    f"y el área {area} tiene riesgo «{g['nivel_area']}»: prioridad {g['prioridad']}."),
            })
    return concretas


REGLAS_PRIORIDAD = expandir()


def verificar_reglas_prioridad():
    """Comprobación estructural de las reglas genéricas (lista de errores)."""
    errores = []
    ids = [r["id"] for r in REGLAS_PRIORIDAD_GENERICAS]
    if len(ids) != len(set(ids)):
        errores.append("Hay identificadores duplicados")
    for r in REGLAS_PRIORIDAD_GENERICAS:
        if not all(f["id"] in FUENTES and f["localizacion"] for f in r["fuentes"]):
            errores.append(f"{r['id']}: fuente o localización inválida")
    return errores
