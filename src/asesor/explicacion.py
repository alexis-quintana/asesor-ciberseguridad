"""Módulo de explicación.

Muestra qué reglas se dispararon y por qué, expresadas como reglas
SI-ENTONCES con los hechos que las activaron.

Fuente: Sesión 12, Representación del Conocimiento (reglas SI-ENTONCES).
"""

from __future__ import annotations

_SIMBOLOS = {"igual": "=", "mayor_que": ">", "menor_que": "<",
             "mayor_o_igual": "≥", "menor_o_igual": "≤", "en": "="}


def _valor(valor):
    if isinstance(valor, (list, tuple)):
        return " o ".join(_valor(v) for v in valor)
    if isinstance(valor, bool):
        return "verdadero" if valor else "falso"
    if isinstance(valor, str):
        return f"«{valor}»"
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


def explicar(resultado):
    """Lista los disparos del resultado, en orden, como reglas SI-ENTONCES."""
    if not resultado.disparos:
        return "No se disparó ninguna regla."
    lineas = []
    for numero, disparo in enumerate(resultado.disparos, start=1):
        lineas.append(f"{numero}. {disparo.id} [{disparo.etapa}] {formatear_regla(disparo.regla)}")
        lineas.append(f"   Motivo: {disparo.explicacion}")
    return "\n".join(lineas)
