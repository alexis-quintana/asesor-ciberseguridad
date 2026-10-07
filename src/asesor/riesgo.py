"""Cálculo de riesgo por área y zona global (motor v1).

Reemplaza, como resultado principal, la clasificación provisional por conteo de
áreas (reglas R097–R101 de la base del 01/10), que no tenía respaldo en las
fuentes. Este módulo no modifica la base de conocimientos.

Fuentes y adaptaciones:

- Puntaje por respuesta: Sihwi et al. (2016), §II.D, p. 3. Cada respuesta se
  puntúa en tres niveles (bajo 0–33, medio 34–66, alto 67–100). Sihwi asigna un
  valor aleatorio dentro del rango; aquí se usa el punto medio (16.5, 50, 83.5)
  para que el sistema dé siempre el mismo resultado (adaptación del equipo).
- «no_se» se puntúa como «no»: criterio conservador de Hibshi et al. (2016).
- Probabilidad por área: promedio de los puntajes de sus preguntas, Sihwi et al.
  (2016), §II.D, p. 4, fórmula (1).
- Impacto: respuesta entera de 1 a 5 convertida linealmente a 0.2–1.0, Koeze
  (2017), «Modeling and calculating the risk», p. 42 impresa (Tabla 7). La
  redacción de las cuatro preguntas de impacto es del equipo; el concepto de
  impacto por área proviene de Sihwi (2016) y Koeze (2017).
- Riesgo = probabilidad × impacto: Koeze (2017), p. 41 impresa. Bandas de
  riesgo (muy bajo 0–0.20, bajo 0.21–0.40, medio 0.41–0.60, alto 0.61–0.80, muy
  alto 0.81–1.00): Koeze (2017), p. 42 impresa (Tabla 8).
- Zona global (verde, amarilla, roja) por la matriz probabilidad–impacto de
  3×3: Sihwi et al. (2016), §II.D, pp. 3-4. La probabilidad media y el impacto
  medio promedian las cuatro áreas (la fórmula (2) de Sihwi, p. 4, promedia el
  impacto de sus preguntas). La zona se determina con los mismos cortes de nivel.

Adaptaciones del equipo (a declarar en el informe): puntos medios en lugar de
valores aleatorios; cortes continuos (bajo si < 34, medio si < 67) porque los
rangos de Sihwi son enteros; promedio simple de las cuatro áreas para la
probabilidad media, el impacto medio y el riesgo global (las fuentes no fijan
el peso de cada área).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base_conocimientos import RESPUESTAS, VARIABLES

# Sihwi et al. (2016), §II.D, p. 3: rangos bajo 0–33, medio 34–66, alto 67–100.
# Punto medio de cada rango (adaptación del equipo). «no_se» puntúa como «no»
# (Hibshi et al., 2016).
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
                "sería para el negocio? (1 = mínimo, 5 = crítico)"),
    "respaldos": ("Si se perdieran los datos del negocio, ¿qué tan grave sería? "
                  "(1 = mínimo, 5 = crítico)"),
    "correo": ("Si el correo corporativo fuera comprometido, ¿qué tan grave sería? "
               "(1 = mínimo, 5 = crítico)"),
    "redes": ("Si la red fuera intrusada o dejara de funcionar, ¿qué tan grave sería? "
              "(1 = mínimo, 5 = crítico)"),
}


@dataclass
class ResultadoRiesgo:
    """Resultado del cálculo de riesgo de un caso."""

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
    """Nivel bajo, medio o alto de un valor de 0 a 100 (Sihwi et al., 2016, p. 3)."""
    valor = round(valor, 9)  # evita errores de coma flotante en los cortes
    if valor < CORTE_MEDIO:
        return "bajo"
    if valor < CORTE_ALTO:
        return "medio"
    return "alto"


def banda_koeze(riesgo):
    """Banda de riesgo de un valor de 0 a 1 (Koeze, 2017, Tabla 8, p. 42 impresa)."""
    riesgo = round(riesgo, 9)  # evita errores de coma flotante en los bordes
    for limite, nombre in BANDAS_KOEZE:
        if riesgo <= limite:
            return nombre
    return "muy_alto"


def zona_sihwi(nivel_probabilidad, nivel_impacto):
    """Zona de la matriz probabilidad–impacto de 3×3 (Sihwi et al., 2016, pp. 3-4).

    Roja si ambos son altos; amarilla si (medio, medio), (alto, medio) o
    (medio, alto); verde en cualquier otro caso.
    """
    if nivel_probabilidad == "alto" and nivel_impacto == "alto":
        return "roja"
    if (nivel_probabilidad, nivel_impacto) in {
        ("medio", "medio"), ("alto", "medio"), ("medio", "alto"),
    }:
        return "amarilla"
    return "verde"


def validar_impactos(impactos):
    """Exige un entero de 1 a 5 por cada área; lanza ValueError si no se cumple."""
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
    """Calcula probabilidad, impacto y riesgo por área, la zona y el riesgo global.

    «respuestas» es un dict {clave de control: respuesta} con las 48 preguntas;
    «impactos» es un dict {área: entero de 1 a 5}. Lanza ValueError si faltan
    datos o si algún valor no es válido.
    """
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
            f"({r.nivel_probabilidad[area]}) [Sihwi 2016, §II.D, p. 4, fórmula (1)]; "
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
        f"[Sihwi 2016, §II.D, pp. 3-4, matriz 3×3]"
    )
    r.trazabilidad.append(
        f"Riesgo global = promedio de los {n} riesgos por área = "
        f"{r.riesgo_global:.3f} ({r.banda_global}) [promedio simple: criterio del equipo; "
        f"bandas: Koeze 2017, Tabla 8, p. 42]"
    )
    return r


def hechos_numericos(respuestas, impactos):
    """Hechos numéricos que consumen las reglas de nivel, banda y zona.

    p_<área> (0–100), i100_<área> (0–100), r_<área> (0–1) y los equivalentes
    «global» (promedios simples de las cuatro áreas, criterio del equipo).
    Usa las mismas fórmulas que evaluar_riesgo; los valores se redondean a 9
    decimales para que los cortes no dependan de la coma flotante.
    """
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
    """Reconstruye un ResultadoRiesgo a partir de los hechos que dejó el motor.

    Devuelve None si el motor no ejecutó las reglas de riesgo (faltan impactos).
    La trazabilidad queda vacía: la explicación sale de las reglas disparadas.
    """
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
