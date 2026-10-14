# Oráculo: calcula el resultado ESPERADO de un caso sin usar el motor de inferencia.

from __future__ import annotations

from app.conocimiento.base_conocimientos import VARIABLES

AREAS = ("cuentas", "respaldos", "correo", "redes")
ORDEN = list(VARIABLES)                      # orden del cuestionario
AREA_DE = {c: v["area"] for c, v in VARIABLES.items()}

# Tabla 3 del informe: puntaje de cada respuesta («no sé» se puntúa como «no»).
PUNTAJE = {"si": 16.5, "parcialmente": 50.0, "no": 83.5, "no_se": 83.5}
# Hallazgo con «no» o «parcialmente»; «no sé» pide verificar.
CON_HALLAZGO = {"no", "parcialmente"}

# Los 12 controles esenciales (Pawar y Palivela, 2022; selección del equipo).
ESENCIALES = {
    "formacion_general", "formacion_phishing", "cortafuegos", "cortafuegos_verificado",
    "parches_equipos", "sistema_soportado", "dispositivo_publico", "aplicacion_publica",
    "mfa_publico", "copia_datos_criticos", "copia_aplicacion_critica", "acceso_datos_criticos",
}


def nivel(valor):
    valor = round(valor, 6)
    return "bajo" if valor < 34 else ("medio" if valor < 67 else "alto")


def banda(riesgo):
    riesgo = round(riesgo, 6)
    for limite, nombre in ((0.20, "muy_bajo"), (0.40, "bajo"), (0.60, "medio"), (0.80, "alto")):
        if riesgo <= limite:
            return nombre
    return "muy_alto"


def zona(nivel_p, nivel_i):
    if nivel_p == "alto" and nivel_i == "alto":
        return "roja"
    if (nivel_p, nivel_i) in (("medio", "medio"), ("alto", "medio"), ("medio", "alto")):
        return "amarilla"
    return "verde"


PRIORIDAD = {  # (nivel de la respuesta, nivel del área) -> prioridad
    ("alto", "alto"): "alta", ("alto", "medio"): "media", ("alto", "bajo"): "baja",
    ("medio", "alto"): "media", ("medio", "medio"): "media", ("medio", "bajo"): "baja",
}


def esperado(respuestas, impactos=None):
    p = {a: sum(PUNTAJE[respuestas[c]] for c in ORDEN if AREA_DE[c] == a) / 12 for a in AREAS}
    niv = {a: nivel(p[a]) for a in AREAS}
    altas = sum(1 for a in AREAS if niv[a] == "alto")
    medias = sum(1 for a in AREAS if niv[a] == "medio")
    if altas >= 2:
        glob = "alto"
    elif altas == 1:
        glob = "medio"
    elif medias >= 2:
        glob = "medio"
    else:
        glob = "bajo"

    items = []
    for c in ORDEN:
        if respuestas[c] not in CON_HALLAZGO:
            continue
        nr = nivel(PUNTAJE[respuestas[c]])
        prio = PRIORIDAD[(nr, niv[AREA_DE[c]])]
        if c in ESENCIALES and prio == "baja":
            prio = "media"
        items.append((c, prio))
    rango = {"alta": 0, "media": 1, "baja": 2}
    # orden: prioridad, mayor probabilidad del área, orden del cuestionario
    items.sort(key=lambda x: (rango[x[1]], -round(p[AREA_DE[x[0]]], 6), ORDEN.index(x[0])))

    verif = [a for a in AREAS if any(respuestas[c] == "no_se" for c in ORDEN if AREA_DE[c] == a)]
    res = {
        "p": {a: round(p[a], 1) for a in AREAS}, "niveles": niv, "global": glob,
        "hallazgos": len(items), "priorizadas": items, "verificaciones": verif,
        "zona": "", "banda_global": "",
    }
    if impactos:
        i100 = {a: impactos[a] / 5 * 100 for a in AREAS}
        r = {a: p[a] / 100 * impactos[a] / 5 for a in AREAS}
        pm = sum(p.values()) / 4
        im = sum(i100.values()) / 4
        res["zona"] = zona(nivel(pm), nivel(im))
        res["banda_global"] = banda(sum(r.values()) / 4)
        res["bandas"] = {a: banda(r[a]) for a in AREAS}
    return res
