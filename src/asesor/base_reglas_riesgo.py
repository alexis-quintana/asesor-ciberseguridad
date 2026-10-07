"""Reglas SI-ENTONCES del modelo de riesgo (niveles, bandas y zona).

Convierte en reglas de la base de conocimientos los cortes que antes vivían
solo como funciones de riesgo.py: nivel de probabilidad e impacto (Sihwi et al.,
2016), banda de riesgo (Koeze, 2017) y zona de la matriz 3×3 (Sihwi et al.,
2016). No modifica base_conocimientos.py.

Las reglas son GENÉRICAS: una misma regla se aplica a cada ámbito (las cuatro
áreas y «global») y se expande con expandir(). Se cuentan como 20 reglas
distintas (R106–R125), no como las 20 × ámbitos instancias.

Hechos numéricos de entrada (los calcula el motor a partir de las respuestas
y los impactos): p_<ámbito> (0–100), i100_<ámbito> (0–100), r_<ámbito> (0–1).
"""

from __future__ import annotations

from .base_conocimientos import FUENTES
from .riesgo import AREAS, CORTE_ALTO, CORTE_MEDIO

AMBITOS = AREAS + ("global",)

_SIHWI_NIVELES = [{"id": "SIHWI_2016", "localizacion": "§II.D, p. 3 (rangos bajo/medio/alto)"}]
_SIHWI_ZONA = [{"id": "SIHWI_2016", "localizacion": "§II.D, pp. 3-4 (matriz probabilidad–impacto 3×3)"}]
_KOEZE_BANDAS = [{"id": "KOEZE_2017", "localizacion": "Tabla 8, p. 42 impresa (bandas de riesgo)"}]

_ADAPTACION_NIVELES = ("Sihwi da rangos enteros (0–33, 34–66, 67–100); el corte continuo "
                       "(<34, <67) es una adaptación del equipo.")


def _cond(hecho, operador, valor):
    return {"hecho": hecho, "operador": operador, "valor": valor}


def _generica(numero, etapa, ambitos, si, hecho, valor, explicacion, fuentes, nota):
    return {
        "id": f"R{numero}",
        "area": "riesgo",
        "etapa": etapa,
        "ambitos": ambitos,
        "si": si,
        "entonces": {"tipo": "nivel", "hecho": hecho, "valor": valor},
        "explicacion": explicacion,
        "fuentes": fuentes,
        "tipo_respaldo": "fuente_con_adaptacion",
        "evidencia_del_articulo": nota,
        "validacion_experto": "pendiente",
    }


def _construir():
    reglas = []
    n = 106
    # Nivel de probabilidad (R106–R108): p_<ámbito> -> nivel_p_<ámbito>.
    for nivel, si in (
        ("bajo", [_cond("p_{ambito}", "menor_que", CORTE_MEDIO)]),
        ("medio", [_cond("p_{ambito}", "mayor_o_igual", CORTE_MEDIO),
                   _cond("p_{ambito}", "menor_que", CORTE_ALTO)]),
        ("alto", [_cond("p_{ambito}", "mayor_o_igual", CORTE_ALTO)]),
    ):
        reglas.append(_generica(
            n, "nivel_probabilidad", AMBITOS, si, "nivel_p_{ambito}", nivel,
            f"La probabilidad de {{ambito}} cae en el rango «{nivel}» de Sihwi.",
            _SIHWI_NIVELES, _ADAPTACION_NIVELES))
        n += 1
    # Nivel de impacto (R109–R111): i100_<ámbito> -> nivel_i_<ámbito>.
    for nivel, si in (
        ("bajo", [_cond("i100_{ambito}", "menor_que", CORTE_MEDIO)]),
        ("medio", [_cond("i100_{ambito}", "mayor_o_igual", CORTE_MEDIO),
                   _cond("i100_{ambito}", "menor_que", CORTE_ALTO)]),
        ("alto", [_cond("i100_{ambito}", "mayor_o_igual", CORTE_ALTO)]),
    ):
        reglas.append(_generica(
            n, "nivel_impacto", AMBITOS, si, "nivel_i_{ambito}", nivel,
            f"El impacto de {{ambito}} cae en el rango «{nivel}» de Sihwi.",
            _SIHWI_NIVELES, _ADAPTACION_NIVELES))
        n += 1
    # Banda de riesgo (R112–R116): r_<ámbito> -> banda_<ámbito>.
    for banda, si in (
        ("muy_bajo", [_cond("r_{ambito}", "menor_o_igual", 0.20)]),
        ("bajo", [_cond("r_{ambito}", "mayor_que", 0.20), _cond("r_{ambito}", "menor_o_igual", 0.40)]),
        ("medio", [_cond("r_{ambito}", "mayor_que", 0.40), _cond("r_{ambito}", "menor_o_igual", 0.60)]),
        ("alto", [_cond("r_{ambito}", "mayor_que", 0.60), _cond("r_{ambito}", "menor_o_igual", 0.80)]),
        ("muy_alto", [_cond("r_{ambito}", "mayor_que", 0.80)]),
    ):
        reglas.append(_generica(
            n, "banda_riesgo", AMBITOS, si, "banda_{ambito}", banda,
            f"El riesgo de {{ambito}} cae en la banda «{banda}» de Koeze.",
            _KOEZE_BANDAS, "Las bandas son las de la Tabla 8; los bordes se tratan como límite superior inclusivo."))
        n += 1
    # Zona global (R117–R125): las 9 celdas de la matriz 3×3 de Sihwi.
    zonas = {
        ("alto", "alto"): "roja",
        ("medio", "medio"): "amarilla", ("alto", "medio"): "amarilla", ("medio", "alto"): "amarilla",
    }
    for p in ("bajo", "medio", "alto"):
        for i in ("bajo", "medio", "alto"):
            zona = zonas.get((p, i), "verde")
            reglas.append(_generica(
                n, "zona", ("global",),
                [_cond("nivel_p_global", "igual", p), _cond("nivel_i_global", "igual", i)],
                "zona_global", zona,
                f"Probabilidad «{p}» e impacto «{i}» corresponden a la zona {zona} de la matriz.",
                _SIHWI_ZONA,
                "El mapeo de las 9 celdas a verde/amarilla/roja se lee de la figura de la matriz (pp. 3-4)."))
            n += 1
    return reglas


REGLAS_RIESGO_GENERICAS = _construir()


def expandir(genericas=None):
    """Instancia cada regla genérica en cada uno de sus ámbitos.

    Devuelve reglas concretas con «ambito» y una «clave» única (R106:cuentas).
    """
    genericas = REGLAS_RIESGO_GENERICAS if genericas is None else genericas
    concretas = []
    for g in genericas:
        for ambito in g["ambitos"]:
            sustituir = lambda texto: texto.replace("{ambito}", ambito) if isinstance(texto, str) else texto
            concretas.append({
                **g,
                "ambito": ambito,
                "clave": f"{g['id']}:{ambito}",
                "area": ambito,
                "si": [{**c, "hecho": sustituir(c["hecho"])} for c in g["si"]],
                "entonces": {**g["entonces"], "hecho": sustituir(g["entonces"]["hecho"])},
                "explicacion": sustituir(g["explicacion"]),
            })
    return concretas


REGLAS_RIESGO = expandir()


def verificar_reglas_riesgo():
    """Comprobación estructural de las reglas genéricas (lista de errores)."""
    errores = []
    ids = [r["id"] for r in REGLAS_RIESGO_GENERICAS]
    if len(ids) != len(set(ids)):
        errores.append("Hay identificadores duplicados")
    for r in REGLAS_RIESGO_GENERICAS:
        if not all(f["id"] in FUENTES and f["localizacion"] for f in r["fuentes"]):
            errores.append(f"{r['id']}: fuente o localización inválida")
    return errores
