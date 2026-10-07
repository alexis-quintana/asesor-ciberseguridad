"""Interfaz de consola.

Presenta las preguntas por área, recoge las respuestas y muestra el
resultado y su explicación. Se ejecuta con: python main.py [--demo] [--explicar]

Fuente: requisito del proyecto P5 (prototipo con interfaz simple y explicación).
"""

from __future__ import annotations

import argparse

from .base_conocimientos import VARIABLES
from .explicacion import explicar
from .memoria import MemoriaTrabajo
from .motor import AREAS, inferir
from .riesgo import PREGUNTAS_IMPACTO, evaluar_riesgo, riesgo_desde_hechos

OPCIONES = {"1": "si", "2": "no", "3": "parcialmente", "4": "no_se"}

# Caso fijo de demostración: todo «si» salvo algunos «no».
CASO_DEMO = {clave: "si" for clave in VARIABLES}
CASO_DEMO.update({
    "mfa_publico": "no",
    "restauracion_probada": "no",
    "formacion_phishing": "no",
})

# Impactos fijos del caso de demostración (escala 1–5 de Koeze, 2017).
IMPACTOS_DEMO = {"cuentas": 3, "respaldos": 4, "correo": 3, "redes": 3}


def preguntar(entrada=input):
    """Hace las 48 preguntas agrupadas por área y devuelve las respuestas."""
    respuestas = {}
    numero = 0
    print("Opciones: 1 = sí, 2 = no, 3 = parcialmente, 4 = no sé")
    for area in AREAS:
        print(f"\n=== Área: {area} ===")
        for clave, variable in VARIABLES.items():
            if variable["area"] != area:
                continue
            numero += 1
            while True:
                opcion = entrada(f"{numero}. {variable['pregunta']} [1-4]: ").strip()
                if opcion in OPCIONES:
                    respuestas[clave] = OPCIONES[opcion]
                    break
                print("   Opción no válida. Escriba 1, 2, 3 o 4.")
    return respuestas


def preguntar_impactos(entrada=input):
    """Hace las 4 preguntas de impacto (una por área, escala 1–5) y las devuelve."""
    impactos = {}
    print("\n=== Impacto para el negocio (1 = mínimo, 5 = crítico) ===")
    for area in AREAS:
        while True:
            texto = entrada(f"{PREGUNTAS_IMPACTO[area]} [1-5]: ").strip()
            if texto in {"1", "2", "3", "4", "5"}:
                impactos[area] = int(texto)
                break
            print("   Opción no válida. Escriba un número del 1 al 5.")
    return impactos


def mostrar_riesgo(riesgo):
    """Imprime el riesgo por área, la zona y el riesgo global (motor v1)."""
    print("\n=== Riesgo por área ===")
    print(f"{'Área':<11}{'Prob.':>7}  {'Nivel':<6}{'Impacto':>8}{'Riesgo':>8}  Banda")
    for area in AREAS:
        print(f"{area:<11}{riesgo.probabilidad[area]:>7.1f}  "
              f"{riesgo.nivel_probabilidad[area]:<6}{riesgo.impacto[area]:>8.1f}"
              f"{riesgo.riesgo_area[area]:>8.3f}  {riesgo.banda_area[area]}")
    print(f"\nProbabilidad media: {riesgo.probabilidad_media:.1f} "
          f"({riesgo.nivel_probabilidad_media}); "
          f"impacto medio: {riesgo.impacto_medio:.1f} ({riesgo.nivel_impacto_medio})")
    print(f"Zona global: {riesgo.zona}")
    print(f"Riesgo global: {riesgo.riesgo_global:.3f} ({riesgo.banda_global})")


def mostrar_resultado(resultado):
    """Imprime hallazgos, recomendaciones, clasificación y verificaciones."""
    print("\n=== Resultado ===")
    print(f"\nHallazgos ({len(resultado.hallazgos)}):")
    for hallazgo in resultado.hallazgos:
        clave = hallazgo["id"].removeprefix("hallazgo_")
        pregunta = VARIABLES.get(clave, {}).get("pregunta", "")
        print(f"  [{hallazgo['area']}] {hallazgo['id']}: {pregunta}")
    if not resultado.hallazgos:
        print("  (ninguno)")

    print("\nRecomendaciones por área:")
    for area, textos in resultado.recomendaciones.items():
        print(f"  {area}:")
        for texto in textos:
            print(f"    - {texto}")
    if not resultado.recomendaciones:
        print("  (ninguna)")

    print("\nClasificación provisional heredada (conteo de áreas con hallazgos; criterio del"
          " equipo sin respaldo en las fuentes, solo de referencia):")
    if resultado.clasificacion_provisional is None:
        print("  No se emitió: hay respuestas «no sé» que deben verificarse primero.")
    else:
        print(f"  {resultado.clasificacion_provisional}")

    print("\nVerificaciones solicitadas:")
    for area in resultado.verificaciones_solicitadas:
        print(f"  - Verificar las respuestas «no sé» del área {area}.")
    if not resultado.verificaciones_solicitadas:
        print("  (ninguna)")


def main(argv=None):
    """Ejecuta el asesor en consola. Devuelve el código de salida."""
    parser = argparse.ArgumentParser(
        description="Asesor de ciberseguridad para pequeñas empresas (sistema experto).",
    )
    parser.add_argument("--demo", action="store_true",
                        help="usa un caso fijo de ejemplo sin pedir respuestas")
    parser.add_argument("--explicar", action="store_true",
                        help="muestra las reglas SI-ENTONCES disparadas")
    args = parser.parse_args(argv)

    if args.demo:
        print("Modo demostración: caso fijo (todo «sí» salvo mfa_publico, "
              "restauracion_probada y formacion_phishing en «no»).")
        print("Impactos del caso de demostración: "
              + ", ".join(f"{a} = {v}" for a, v in IMPACTOS_DEMO.items()) + ".")
        respuestas = CASO_DEMO
        impactos = IMPACTOS_DEMO
    else:
        try:
            respuestas = preguntar()
            impactos = preguntar_impactos()
        except (EOFError, KeyboardInterrupt):
            print("\nCuestionario interrumpido.")
            return 1

    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    memoria.cargar_impactos(impactos)
    resultado = inferir(memoria)
    # Niveles, bandas y zona salen de las reglas R106–R125 disparadas por el motor.
    riesgo = riesgo_desde_hechos(resultado.hechos)
    mostrar_riesgo(riesgo)
    mostrar_resultado(resultado)
    if args.explicar:
        print("\n=== Explicación del cálculo de riesgo ===")
        for linea in evaluar_riesgo(respuestas, impactos).trazabilidad:
            print(f"- {linea}")
        print("\n=== Explicación (reglas disparadas) ===")
        print(explicar(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
