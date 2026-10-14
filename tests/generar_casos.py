# Genera tests/casos/casos_prueba.csv: 50 casos con su resultado esperado (oráculo).

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from tests.oraculo import AREAS, AREA_DE, ORDEN, esperado

RUTA = Path(__file__).parent / "casos" / "casos_prueba.csv"
COLUMNAS = ["caso_id", "grupo", "origen", "descripcion", "respuestas_json", "impactos_json",
            "niveles_esperados", "global_esperado", "hallazgos_esperados", "priorizadas_esperadas",
            "verificaciones_esperadas", "zona_esperada", "banda_global_esperada",
            "verificado_por", "revisado_a_mano"]


def base(valor):
    return {c: valor for c in ORDEN}


def con(valor_base, **cambios):
    r = base(valor_base)
    r.update(cambios)
    return r


def area_con(r, area, valor, cuantos=12):
    for c in [c for c in ORDEN if AREA_DE[c] == area][:cuantos]:
        r[c] = valor
    return r


CASOS = []   # (grupo, origen, descripcion, respuestas, impactos)


def agregar(grupo, origen, descripcion, respuestas, impactos=None):
    CASOS.append((grupo, origen, descripcion, respuestas, impactos))


# ---------------------------------------------------------------- G1: fuentes y enunciado
# Ocho pymes de Chidukwani et al. (2026): cada «no» corresponde a una carencia citada en sección 4.3 y sección 4.4.
CHID = {
    "SME1": ("parcialmente", dict(cortafuegos_verificado="no", wifi_invitados_separado="no",
             filtro_correo_verificado="no", parches_equipos="no", diagrama_red="no"),
             "tecnología; defecto «parcialmente» (38 % de controles implementados)"),
    "SME2": ("no_se", dict(cuentas_individuales="no", admin_restringido="no", mfa_contacto_individual="no",
             politica_claves_aplicada="no", formacion_phishing="no", evidencia_capacitacion="no",
             cortafuegos_verificado="no", monitoreo_red="no", plan_recuperacion="no",
             parches_integrados="no", inventario_dispositivos="no", diagrama_red="no"),
             "ONG con proveedor gestionado; defecto «no sé»"),
    "SME3": ("no_se", dict(filtro_correo_verificado="no", parches_equipos="no_se", mfa_publico="no",
             inventario_dispositivos="no", accesos_proveedor="no", diagrama_red="no"),
             "salud; la gerencia desconocía que el proveedor aplicaba parches; defecto «no sé»"),
    "SME4": ("no", dict(inventario_dispositivos="no", mfa_publico="no", politica_claves_aplicada="no",
             filtro_correo_verificado="no", plan_recuperacion="no", diagrama_red="no"),
             "servicios administrativos; 86 % de brechas; defecto «no»"),
    "SME5": ("no", dict(politica_claves_aplicada="no", plan_recuperacion="no", diagrama_red="no"),
             "salud, administración propia; 90 % de brechas; defecto «no»"),
    "SME6": ("parcialmente", dict(formacion_general="no", formacion_phishing="no", parches_integrados="no",
             filtro_correo_verificado="no", plan_recuperacion="no", accesos_proveedor="no", diagrama_red="no"),
             "agricultura; depende por completo del proveedor; defecto «parcialmente» (38 %)"),
    "SME7": ("si", dict(formacion_phishing="no", evidencia_capacitacion="no", sistema_soportado="no",
             parches_equipos="no", dispositivos_personales="no", diagrama_red="no"),
             "medios y telecomunicaciones; mayor implementación (60 %); defecto «sí»"),
    "SME8": ("no", dict(inventario_dispositivos="no", wifi_invitados_separado="no", cortafuegos_verificado="no",
             plan_recuperacion="no", diagrama_red="no"),
             "otra ONG; 98 % de brechas; defecto «no»"),
}
for nombre, (defecto, cambios, nota) in CHID.items():
    agregar("G1", "Chidukwani et al. (2026), sección 4.3-4.4",
            f"Pyme simulada inspirada en {nombre}: {nota}. Respuestas no descritas en el artículo: valor por defecto.",
            con(defecto, **cambios))

# Ejemplos del enunciado de P5 (contraseñas repetidas y sin verificación en dos pasos; sin respaldos).
r = con("si", claves_diferentes="no", mfa_publico="no", mfa_cobertura="no", mfa_contacto_individual="no",
        politica_claves_aplicada="no", cuentas_individuales="no", responsable_accesos="no",
        acceso_datos_criticos="no")
agregar("G1", "Enunciado de P5, regla ilustrativa 1",
        "Contraseñas repetidas y sin verificación en dos pasos: cuentas con riesgo alto; el resto bien.", r)
r = area_con(base("si"), "respaldos", "no", 8)
agregar("G1", "Enunciado de P5, regla ilustrativa 2",
        "Sin copias periódicas ni pruebas de restauración: respaldos con riesgo alto; el resto bien.", r)
r = area_con(area_con(base("si"), "cuentas", "no"), "respaldos", "no")
agregar("G1", "Enunciado de P5, regla ilustrativa 3",
        "Cuentas y respaldos en riesgo alto: dos áreas altas dan riesgo global alto.", r)
r = area_con(base("si"), "redes", "no", 11)
agregar("G1", "Enunciado de P5 (caso de una sola área)",
        "Solo la red tiene carencias: una área alta da riesgo global medio.", r)

# ---------------------------------------------------------------- G2: casos límite
agregar("G2", "Límite", "Todas las respuestas «sí».", base("si"), {a: 1 for a in AREAS})
agregar("G2", "Límite", "Todas las respuestas «no».", base("no"), {a: 5 for a in AREAS})
agregar("G2", "Límite", "Todas las respuestas «parcialmente».", base("parcialmente"))
agregar("G2", "Límite", "Todas las respuestas «no sé».", base("no_se"))
agregar("G2", "Límite (R097-R101)", "Una sola área alta (cuentas), el resto «sí».", area_con(base("si"), "cuentas", "no"))
agregar("G2", "Límite (R097-R101)", "Dos áreas altas (correo y redes), el resto «sí».",
        area_con(area_con(base("si"), "correo", "no"), "redes", "no"))
agregar("G2", "Límite (R097-R101)", "Tres áreas altas, redes «sí».",
        area_con(area_con(area_con(base("si"), "cuentas", "no"), "respaldos", "no"), "correo", "no"))
# Cortes de nivel: P = (198 + 33,5·p + 67·n) / 12 (n=3 bajo, n=9 medio, n=9 y p=1 alto).
def area_np(area, n, p):
    r = base("si")
    claves = [c for c in ORDEN if AREA_DE[c] == area]
    for c in claves[:n]:
        r[c] = "no"
    for c in claves[n:n + p]:
        r[c] = "parcialmente"
    return r
agregar("G2", "Límite de nivel", "Cuentas con 6 puntos de carencia (P = 33,25): justo debajo del corte medio.", area_np("cuentas", 3, 0))
agregar("G2", "Límite de nivel", "Cuentas con 7 puntos de carencia (P = 36,04): justo sobre el corte medio.", area_np("cuentas", 3, 1))
agregar("G2", "Límite de nivel", "Respaldos con 18 puntos de carencia (P = 66,75): justo debajo del corte alto.", area_np("respaldos", 9, 0))
agregar("G2", "Límite de nivel", "Respaldos con 19 puntos de carencia (P = 69,54): justo sobre el corte alto.",
        area_np("respaldos", 9, 1), {"cuentas": 3, "respaldos": 3, "correo": 3, "redes": 3})
# Esquinas de la matriz de zona (extensión): cada una dispara una celda distinta.
agregar("G2", "Límite de zona", "Todo «sí» con impacto máximo: probabilidad baja e impacto alto (zona verde).",
        base("si"), {a: 5 for a in AREAS})
agregar("G2", "Límite de zona", "Todo «parcialmente» con impacto mínimo: probabilidad media e impacto bajo (zona verde).",
        base("parcialmente"), {a: 1 for a in AREAS})
agregar("G2", "Límite de zona", "Todo «no» con impacto mínimo: probabilidad alta e impacto bajo (zona verde).",
        base("no"), {a: 1 for a in AREAS})
agregar("G2", "Límite de zona", "Todo «no» con impacto medio (3): probabilidad alta e impacto medio (zona amarilla).",
        base("no"), {a: 3 for a in AREAS})
agregar("G2", "Límite (R102-R105)", "Todo «sí» salvo una respuesta «no sé» en correo: sin hallazgos, pero se pide verificar el área.",
        con("si", filtro_spam="no_se"))
# R132: un control esencial no baja de prioridad media aunque su área tenga riesgo bajo.
agregar("G2", "Límite (R132)", "Solo falla el cortafuegos (control esencial) en un área de riesgo bajo: prioridad media por R132.",
        con("si", cortafuegos="no"))
agregar("G2", "Límite (R132)", "Solo falla el inventario de dispositivos (no esencial) en un área de riesgo bajo: prioridad baja.",
        con("si", inventario_dispositivos="no"))

# ---------------------------------------------------------------- G3: mixtos (semilla fija)
azar = random.Random(2026)
PERFILES = [  # pesos de («si», «parcialmente», «no», «no_se»)
    (0.60, 0.15, 0.20, 0.05), (0.30, 0.20, 0.40, 0.10), (0.15, 0.15, 0.60, 0.10),
    (0.80, 0.10, 0.08, 0.02), (0.45, 0.25, 0.25, 0.05), (0.25, 0.10, 0.50, 0.15),
]
for k in range(20):
    r = {}
    for area in AREAS:
        pesos = PERFILES[azar.randrange(len(PERFILES))]
        for c in [c for c in ORDEN if AREA_DE[c] == area]:
            r[c] = azar.choices(["si", "parcialmente", "no", "no_se"], weights=pesos)[0]
    r = {c: r[c] for c in ORDEN}
    imp = {a: azar.randint(1, 5) for a in AREAS} if k % 3 == 0 else None
    agregar("G3", "Mixto con semilla fija 2026",
            f"Empresa simulada de prácticas mixtas (caso {k + 1} de 20)"
            + ("; con impacto para la extensión." if imp else "."), r, imp)


def escribir():
    filas = []
    for n, (grupo, origen, descripcion, resp, imp) in enumerate(CASOS, start=1):
        e = esperado(resp, imp)
        filas.append({
            "caso_id": f"C{n:02d}", "grupo": grupo, "origen": origen, "descripcion": descripcion,
            "respuestas_json": json.dumps(resp, ensure_ascii=False),
            "impactos_json": json.dumps(imp) if imp else "",
            "niveles_esperados": json.dumps(e["niveles"]), "global_esperado": e["global"],
            "hallazgos_esperados": e["hallazgos"],
            "priorizadas_esperadas": ";".join(f"{c}:{p}" for c, p in e["priorizadas"]),
            "verificaciones_esperadas": ";".join(e["verificaciones"]),
            "zona_esperada": e["zona"], "banda_global_esperada": e["banda_global"],
            "verificado_por": "oráculo independiente (tests/oraculo.py)", "revisado_a_mano": "",
        })
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    with open(RUTA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    return filas


if __name__ == "__main__":
    filas = escribir()
    print(f"{len(filas)} casos escritos en {RUTA}")
