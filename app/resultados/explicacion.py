"""Módulo de explicación.

Muestra qué reglas se dispararon y por qué, de dos maneras:

- explicar(): lista técnica de las reglas SI-ENTONCES disparadas, con los valores
  que tenían los hechos al dispararse y la fuente de cada regla.
- armar_detalle(): explicación pensada para el usuario y para la demostración del
  motor: cómo se calculó cada área (puntajes, umbrales y regla de nivel), cómo se
  llegó al riesgo global, la cadena de reglas de cada recomendación (respuesta →
  hallazgo → recomendación → prioridad), las reglas que NO se aplicaron y por qué,
  y cuántas reglas evaluó el motor en cada etapa.

Fuente: Sesión 12, Representación del Conocimiento (reglas SI-ENTONCES); la
pregunta «¿cómo se llegó a este resultado?» y la lista de reglas disparadas con sus
condiciones siguen la explicación de Sihwi et al. (2016), §II.D.
"""

from __future__ import annotations

from collections import Counter

from app.inferencia.priorizacion import lista_priorizada
from app.inferencia.riesgo import AREAS, CORTE_ALTO, CORTE_MEDIO, PUNTAJE

_SIMBOLOS = {"igual": "=", "mayor_que": ">", "menor_que": "<",
             "mayor_o_igual": "≥", "menor_o_igual": "≤", "en": "="}

_NOMBRE_RESPUESTA = {"si": "Sí", "no": "No", "parcialmente": "Parcialmente", "no_se": "No sé"}

# Etapas cuyas reglas conviene explicar cuando no se aplican (las de las 96 reglas
# por práctica se resumen: una regla no se aplica porque la práctica está en «sí»).
_ETAPAS_CON_MOTIVO = ("verificacion", "nivel_probabilidad", "riesgo_global", "prioridad", "criticidad")


def _valor(valor):
    if isinstance(valor, (list, tuple)):
        return " o ".join(_valor(v) for v in valor)
    if isinstance(valor, bool):
        return "verdadero" if valor else "falso"
    if isinstance(valor, str):
        return f"«{valor}»"
    if isinstance(valor, float):
        return f"{valor:.1f}"
    return str(valor)


def _condicion(condicion):
    simbolo = _SIMBOLOS.get(condicion["operador"], condicion["operador"])
    return f"{condicion['hecho']} {simbolo} {_valor(condicion['valor'])}"


def _conclusion(entonces):
    tipo = entonces["tipo"]
    if tipo == "hallazgo":
        return f"{entonces['id']} (área: {entonces['area']})"
    if tipo == "recomendacion":
        return f"recomendar «{entonces['texto']}» (área: {entonces['area']})"
    if tipo == "recomendacion_adicional":
        return (f"recomendar «{entonces['texto']}» con prioridad {entonces['prioridad']} "
                f"(área: {entonces['area']})")
    if tipo == "solicitud_verificacion":
        return f"solicitar verificación del área «{entonces['area']}»"
    if tipo in ("nivel", "prioridad"):
        return f"{entonces['hecho']} = {_valor(entonces['valor'])}"
    return repr(entonces)


def formatear_regla(regla):
    """Devuelve «SI <condiciones> ENTONCES <conclusión> [Fuente: id, localización]»."""
    condiciones = " Y ".join(_condicion(c) for c in regla["si"])
    fuentes = "; ".join(f"{f['id']}, {f['localizacion']}" for f in regla["fuentes"])
    return f"SI {condiciones} ENTONCES {_conclusion(regla['entonces'])} [Fuente: {fuentes}]"


def _observados(observados):
    return ", ".join(f"{hecho} = {_valor(valor)}" for hecho, valor in observados.items())


def explicar(resultado):
    """Lista los disparos del resultado, en orden, como reglas SI-ENTONCES.

    Cada disparo muestra la regla (con la clave de su instancia, p. ej. R106:cuentas),
    su motivo y los valores que tenían los hechos cuando se cumplió.
    """
    if not resultado.disparos:
        return "No se disparó ninguna regla."
    lineas = []
    for numero, disparo in enumerate(resultado.disparos, start=1):
        clave = disparo.clave or disparo.id
        lineas.append(f"{numero}. {clave} [{disparo.etapa}] {formatear_regla(disparo.regla)}")
        lineas.append(f"   Motivo: {disparo.explicacion}")
        if disparo.observados:
            lineas.append(f"   Valores observados: {_observados(disparo.observados)}")
    return "\n".join(lineas)


# --------------------------------------------------------------------------- detalle
def _texto_natural(disparo, hechos):
    """Frase en lenguaje natural para un disparo de la cadena de una recomendación."""
    regla, obs = disparo.regla, disparo.observados
    tipo = regla["entonces"]["tipo"]
    clave = disparo.clave or disparo.id
    if tipo == "hallazgo":
        control = regla["si"][0]["hecho"]
        respuesta = _NOMBRE_RESPUESTA.get(hechos.get(control), str(hechos.get(control)))
        return f"{clave}: la respuesta «{respuesta}» a esta pregunta se considera un hallazgo."
    if tipo == "recomendacion":
        return f"{clave}: para ese hallazgo se recomienda «{regla['entonces']['texto'].rstrip('.')}»."
    if tipo == "prioridad" and regla["etapa"] == "prioridad":
        control = regla["entonces"]["control"]
        area = regla["entonces"]["area"]
        nivel_r, nivel_p = obs.get(f"nivel_r_{control}"), obs.get(f"nivel_p_{area}")
        return (f"{clave}: la respuesta equivale a un nivel «{nivel_r}» y el área {area} tiene "
                f"riesgo «{nivel_p}» (P = {hechos.get(f'p_{area}', 0):.1f}); la matriz de "
                f"prioridad da «{regla['entonces']['valor']}».")
    if tipo == "prioridad":                       # criticidad (R132)
        return (f"{clave}: es un control esencial (Pawar y Palivela, 2022); su prioridad "
                f"sube de «baja» a «{regla['entonces']['valor']}».")
    if tipo == "recomendacion_adicional":
        return (f"{clave}: se cumplieron las condiciones de esta regla del administrador "
                f"({_observados(obs)}).")
    return f"{clave}: {disparo.explicacion}"


def _cadena(resultado, item):
    """Disparos que llevaron a una recomendación, en orden de ejecución."""
    hechos = resultado.hechos
    if item["adicional"]:
        propios = [d for d in resultado.disparos if d.id == item["control"]]
    else:
        control = item["control"]
        hallazgo = f"hallazgo_{control}"
        propios = []
        for d in resultado.disparos:
            regla = d.regla
            if regla["entonces"].get("id") == hallazgo:
                propios.append(d)
            elif regla["etapa"] == "recomendacion" and regla["si"][0]["hecho"] == hallazgo:
                propios.append(d)
            elif regla.get("ambito") == control and regla["etapa"] in ("prioridad", "criticidad"):
                propios.append(d)
    return [{"regla": d.clave or d.id, "etapa": d.etapa,
             "texto": _texto_natural(d, hechos), "formal": formatear_regla(d.regla)}
            for d in propios]


def _detalle_areas(resultado):
    h = resultado.hechos
    filas = []
    for area in AREAS:
        claves = [c for c, v in _variables().items() if v["area"] == area]
        conteo = Counter(h[c] for c in claves)
        disparo = next((d for d in resultado.disparos
                        if d.etapa == "nivel_probabilidad" and d.regla.get("ambito") == area), None)
        filas.append({
            "area": area,
            "p": h[f"p_{area}"],
            "nivel": h[f"nivel_p_{area}"],
            "regla": disparo.clave if disparo else "",
            "conteo": {r: conteo.get(r, 0) for r in ("si", "parcialmente", "no", "no_se")},
            "total": len(claves),
        })
    return filas


def _variables():
    from app.conocimiento.base_conocimientos import VARIABLES
    return VARIABLES


def _detalle_global(resultado):
    h = resultado.hechos
    disparo = next((d for d in resultado.disparos if d.etapa == "riesgo_global"), None)
    return {
        "nivel": resultado.riesgo_global,
        "regla": (disparo.clave or disparo.id) if disparo else "",
        "areas_alto": h.get("areas_riesgo_alto", 0),
        "areas_medio": h.get("areas_riesgo_medio", 0),
        "formal": formatear_regla(disparo.regla) if disparo else "",
        "motivo": disparo.explicacion if disparo else "",
    }


def _primer_fallo(regla, hechos):
    """Primera condición que impide que la regla se cumpla: (hecho, esperado, actual, falta)."""
    from app.inferencia.motor import OPERADORES
    for c in regla["si"]:
        if c["hecho"] not in hechos:
            return c["hecho"], c, None, True
        if not OPERADORES[c["operador"]](hechos[c["hecho"]], c["valor"]):
            return c["hecho"], c, hechos[c["hecho"]], False
    return None


def reglas_no_aplicadas(resultado):
    """Resume las reglas que se evaluaron y no se aplicaron, con el motivo.

    Responde «¿qué ocurre cuando una regla no aplica?»: no se dispara y no produce
    nada. Las reglas por práctica (R001–R096) se resumen aparte porque no se aplican
    simplemente cuando la respuesta es «sí».
    """
    disparadas = {d.clave or d.id for d in resultado.disparos}
    grupos = {}
    for regla in resultado.reglas:
        clave = regla.get("clave", regla["id"])
        if clave in disparadas or regla["etapa"] not in _ETAPAS_CON_MOTIVO:
            continue
        fallo = _primer_fallo(regla, resultado.hechos)
        if fallo is None:
            continue
        hecho, condicion, actual, falta = fallo
        if falta:
            motivo = f"no existe el hecho «{hecho}» (no hubo hallazgo o no se calculó)"
            tipo = "sin_hecho"
        else:
            motivo = (f"{hecho} vale {_valor(actual)} y la regla pide "
                      f"{_SIMBOLOS.get(condicion['operador'], condicion['operador'])} "
                      f"{_valor(condicion['valor'])}")
            tipo = "valor"
        grupo = grupos.setdefault((regla["id"], tipo), {
            "id": regla["id"], "etapa": regla["etapa"], "n": 0,
            "motivo": motivo, "regla": formatear_regla(regla)})
        grupo["n"] += 1
    filas = sorted(grupos.values(), key=lambda g: (g["etapa"], g["id"]))
    for fila in filas:
        fila["instancias"] = "" if fila["n"] == 1 else f" ({fila['n']} instancias; ejemplo)"
    return filas


def armar_detalle(resultado):
    """Reúne la explicación para mostrar en pantalla (ver el docstring del módulo)."""
    recomendaciones = []
    for item in lista_priorizada(resultado):
        control = item["control"]
        respuesta = None if item["adicional"] else resultado.hechos.get(control)
        recomendaciones.append({
            **item,
            "respuesta": _NOMBRE_RESPUESTA.get(respuesta, ""),
            "cadena": _cadena(resultado, item),
        })
    return {
        "areas": _detalle_areas(resultado),
        "global": _detalle_global(resultado),
        "recomendaciones": recomendaciones,
        "no_aplicadas": reglas_no_aplicadas(resultado),
        "estadisticas": resultado.estadisticas,
        "umbrales": {"medio": CORTE_MEDIO, "alto": CORTE_ALTO},
        "puntajes": {_NOMBRE_RESPUESTA[k]: v for k, v in PUNTAJE.items()},
    }
