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

OPCIONES = {"1": "si", "2": "no", "3": "parcialmente", "4": "no_se"}

# Caso fijo de demostración: todo «si» salvo algunos «no».
CASO_DEMO = {clave: "si" for clave in VARIABLES}
CASO_DEMO.update({
    "mfa_publico": "no",
    "restauracion_probada": "no",
    "formacion_phishing": "no",
})


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

    print("\nClasificación global provisional (pendiente de validación; será reemplazada"
          " por el modelo de Sihwi 2016 y Koeze 2017):")
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
        respuestas = CASO_DEMO
    else:
        try:
            respuestas = preguntar()
        except (EOFError, KeyboardInterrupt):
            print("\nCuestionario interrumpido.")
            return 1

    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    resultado = inferir(memoria)
    mostrar_resultado(resultado)
    if args.explicar:
        print("\n=== Explicación (reglas disparadas) ===")
        print(explicar(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
