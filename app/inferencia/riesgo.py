# Cálculo de riesgo: probabilidad por área (flujo principal) y extensión de impacto.

from __future__ import annotations

from dataclasses import dataclass, field

from app.conocimiento.base_conocimientos import RESPUESTAS, VARIABLES

# Punto medio de cada rango de Sihwi (2016, II.D); «no_se» = «no».
PUNTAJE = {"si": 16.5, "parcialmente": 50.0, "no": 83.5, "no_se": 83.5}

# Corte continuo de los niveles de Sihwi (adaptación del equipo).
CORTE_MEDIO = 34
CORTE_ALTO = 67

# Koeze (2017), p. 42 impresa, Tabla 8: límite superior de cada banda.
BANDAS_KOEZE = (
    (0.20, "muy_bajo"),
    (0.40, "bajo"),
    (0.60, "medio"),
    (0.80, "alto"),
)

AREAS = tuple(dict.fromkeys(v["area"] for v in VARIABLES.values()))

# Redacción del equipo; concepto de impacto: Sihwi (2016) y Koeze (2017).
PREGUNTAS_IMPACTO = {
    "cuentas": ("Si un tercero accediera a las cuentas de la empresa, ¿qué tan grave "
                "sería para el negocio?"),
    "respaldos": ("Si se perdieran los datos del negocio, ¿qué tan grave sería?"),
    "correo": ("Si el correo corporativo fuera comprometido, ¿qué tan grave sería?"),
    "redes": ("Si la red fuera intrusada o dejara de funcionar, ¿qué tan grave sería?"),
}


@dataclass
class ResultadoRiesgo:

    probabilidad: dict = field(default_factory=dict)      # área -> 0–100
    nivel_probabilidad: dict = field(default_factory=dict)  # área -> bajo|medio|alto
    impacto: dict = field(default_factory=dict)           # área -> 0.2–1.0
    riesgo_area: dict = field(default_factory=dict)       # área -> 0–1
    banda_area: dict = field(default_factory=dict)        # área -> banda de Koeze
    probabilidad_media: float = 0.0
    impacto_medio: float = 0.0                            # 0–100
    nivel_probabilidad_media: str = ""
    nivel_impacto_medio: str = ""
    zona: str = ""                                        # verde|amarilla|roja
    riesgo_global: float = 0.0
    banda_global: str = ""
    trazabilidad: list = field(default_factory=list)


def nivel_sihwi(valor):
    valor = round(valor, 9)  # evita errores de coma flotante en los cortes
    if valor < CORTE_MEDIO:
        return "bajo"
    if valor < CORTE_ALTO:
        return "medio"
    return "alto"


def banda_koeze(riesgo):
    riesgo = round(riesgo, 9)  # evita errores de coma flotante en los bordes
    for limite, nombre in BANDAS_KOEZE:
        if riesgo <= limite:
            return nombre
    return "muy_alto"


def zona_sihwi(nivel_probabilidad, nivel_impacto):
    if nivel_probabilidad == "alto" and nivel_impacto == "alto":
        return "roja"
    if (nivel_probabilidad, nivel_impacto) in {
        ("medio", "medio"), ("alto", "medio"), ("medio", "alto"),
    }:
        return "amarilla"
    return "verde"


def validar_impactos(impactos):
    desconocidas = [a for a in impactos if a not in AREAS]
    if desconocidas:
        raise ValueError(f"Área desconocida en los impactos: {', '.join(map(str, desconocidas))}")
    faltantes = [a for a in AREAS if a not in impactos]
    if faltantes:
        raise ValueError(f"Faltan impactos de las áreas: {', '.join(faltantes)}")
    for area, valor in impactos.items():
        if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 5:
            raise ValueError(
                f"Impacto de {area!r} debe ser un entero de 1 a 5; recibido: {valor!r}"
            )


def _validar_respuestas(respuestas):
    for clave, valor in respuestas.items():
        if clave not in VARIABLES:
            raise ValueError(f"Variable desconocida: {clave!r}")
        if valor not in RESPUESTAS:
            raise ValueError(f"Respuesta no permitida para {clave!r}: {valor!r}")
    faltantes = [c for c in VARIABLES if c not in respuestas]
    if faltantes:
        raise ValueError(f"Faltan respuestas: {', '.join(faltantes)}")


def evaluar_riesgo(respuestas, impactos):
    _validar_respuestas(respuestas)
    validar_impactos(impactos)

    r = ResultadoRiesgo()
    for area in AREAS:
        claves = [c for c, v in VARIABLES.items() if v["area"] == area]
        puntajes = [PUNTAJE[respuestas[c]] for c in claves]
        p = sum(puntajes) / len(puntajes)
        i = impactos[area] / 5
        riesgo = (p / 100) * i
        r.probabilidad[area] = p
        r.nivel_probabilidad[area] = nivel_sihwi(p)
        r.impacto[area] = i
        r.riesgo_area[area] = riesgo
        r.banda_area[area] = banda_koeze(riesgo)
        r.trazabilidad.append(
            f"{area}: P = promedio de {len(claves)} puntajes = {p:.1f} "
            f"({r.nivel_probabilidad[area]}) [Sihwi 2016, sección II.D, p. 4, fórmula (1)]; "
            f"I = {impactos[area]}/5 = {i:.1f} [Koeze 2017, Tabla 7, p. 42]; "
            f"R = (P/100) × I = {riesgo:.3f} ({r.banda_area[area]}) "
            f"[Koeze 2017, p. 41 y Tabla 8, p. 42]"
        )

    n = len(AREAS)
    r.probabilidad_media = sum(r.probabilidad.values()) / n
    r.impacto_medio = (100 / n) * sum(r.impacto.values())
    r.nivel_probabilidad_media = nivel_sihwi(r.probabilidad_media)
    r.nivel_impacto_medio = nivel_sihwi(r.impacto_medio)
    r.zona = zona_sihwi(r.nivel_probabilidad_media, r.nivel_impacto_medio)
    r.riesgo_global = sum(r.riesgo_area.values()) / n
    r.banda_global = banda_koeze(r.riesgo_global)
    r.trazabilidad.append(
        f"Global: P media = {r.probabilidad_media:.1f} ({r.nivel_probabilidad_media}), "
        f"I media = (100/{n}) × suma de I = {r.impacto_medio:.1f} "
        f"({r.nivel_impacto_medio}); zona {r.zona} "
        f"[Sihwi 2016, Tabla III, p. 3, e interpretación en sección II.D, p. 4]"
    )
    r.trazabilidad.append(
        f"Riesgo global = promedio de los {n} riesgos por área = "
        f"{r.riesgo_global:.3f} ({r.banda_global}) [promedio simple: criterio del equipo; "
        f"bandas: Koeze 2017, Tabla 8, p. 42]"
    )
    return r


def hechos_probabilidad(respuestas):
    _validar_respuestas(respuestas)
    hechos = {}
    for area in AREAS:
        claves = [c for c, v in VARIABLES.items() if v["area"] == area]
        hechos[f"p_{area}"] = round(sum(PUNTAJE[respuestas[c]] for c in claves) / len(claves), 9)
    return hechos


def hechos_nivel_respuesta(respuestas):
    _validar_respuestas(respuestas)
    return {f"nivel_r_{c}": nivel_sihwi(PUNTAJE[respuestas[c]]) for c in VARIABLES}


def hechos_numericos(respuestas, impactos):
    _validar_respuestas(respuestas)
    validar_impactos(impactos)
    hechos = {}
    for area in AREAS:
        claves = [c for c, v in VARIABLES.items() if v["area"] == area]
        p = sum(PUNTAJE[respuestas[c]] for c in claves) / len(claves)
        i = impactos[area] / 5
        hechos[f"p_{area}"] = round(p, 9)
        hechos[f"i100_{area}"] = round(i * 100, 9)
        hechos[f"r_{area}"] = round((p / 100) * i, 9)
    n = len(AREAS)
    hechos["p_global"] = round(sum(hechos[f"p_{a}"] for a in AREAS) / n, 9)
    hechos["i100_global"] = round(sum(hechos[f"i100_{a}"] for a in AREAS) / n, 9)
    hechos["r_global"] = round(sum(hechos[f"r_{a}"] for a in AREAS) / n, 9)
    return hechos


def riesgo_desde_hechos(hechos):
    if "zona_global" not in hechos:
        return None
    r = ResultadoRiesgo()
    for area in AREAS:
        r.probabilidad[area] = hechos[f"p_{area}"]
        r.nivel_probabilidad[area] = hechos[f"nivel_p_{area}"]
        r.impacto[area] = hechos[f"i100_{area}"] / 100
        r.riesgo_area[area] = hechos[f"r_{area}"]
        r.banda_area[area] = hechos[f"banda_{area}"]
    r.probabilidad_media = hechos["p_global"]
    r.impacto_medio = hechos["i100_global"]
    r.nivel_probabilidad_media = hechos["nivel_p_global"]
    r.nivel_impacto_medio = hechos["nivel_i_global"]
    r.zona = hechos["zona_global"]
    r.riesgo_global = hechos["r_global"]
    r.banda_global = hechos["banda_global"]
    return r
