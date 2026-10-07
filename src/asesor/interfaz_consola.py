"""Interfaz de consola.

Presenta las preguntas por área, recoge las respuestas y muestra el nivel de
riesgo de cada área, el riesgo global y las recomendaciones priorizadas, con su
explicación. Se ejecuta con: python main.py [--demo] [--explicar] [--con-impacto]
La opción --web abre en su lugar la interfaz web (Flask) en http://127.0.0.1:5000.

La opción --con-impacto activa la extensión de investigación (impacto por área,
bandas de Koeze y zona de Sihwi); sin ella se sigue el flujo del enunciado de P5.

Fuente: requisito del proyecto P5 (prototipo con interfaz simple y explicación).
"""

from __future__ import annotations

import argparse
import threading
import webbrowser

from .base_conocimientos import VARIABLES
from .explicacion import explicar
from .memoria import MemoriaTrabajo
from .motor import AREAS, inferir
from .priorizacion import lista_priorizada
from .reporte import AVISO_LIMITES
from .riesgo import PREGUNTAS_IMPACTO, evaluar_riesgo, riesgo_desde_hechos

OPCIONES = {"1": "si", "2": "no", "3": "parcialmente", "4": "no_se"}

# Caso fijo de demostración: una tienda con comercio en línea (empresa simulada).
# Todo «si» salvo lo indicado. Resultado esperado, calculado a mano:
#   cuentas   9 «no», 1 «parcialmente», 2 «si»   -> P = 69,5 (alto)
#   respaldos 9 «no», 1 «parcialmente», 2 «si»   -> P = 69,5 (alto)
#   correo    4 «no» + 1 «no sé» (cuenta como «no») -> P = 44,4 (medio)
#   redes     2 «no»                             -> P = 27,7 (bajo)
#   dos áreas con riesgo alto (R097)             -> riesgo global alto
CASO_DEMO = {clave: "si" for clave in VARIABLES}
CASO_DEMO.update({clave: "no" for clave in (
    "cuentas_individuales", "admin_restringido", "carpetas_restringidas", "mfa_publico",
    "politica_claves_aplicada", "claves_diferentes", "responsable_accesos",
    "acceso_datos_criticos", "permisos_roles",
    "copia_bases_datos", "copia_actualizaciones", "programacion_documentada",
    "frecuencia_conocida", "restauracion_probada", "copia_fuera_sede", "copia_separada",
    "copia_cifrada", "plan_recuperacion",
    "formacion_periodica", "formacion_ingreso", "formacion_phishing", "evidencia_capacitacion",
    "diagrama_red", "inventario_dispositivos",
)})
CASO_DEMO.update({
    "mfa_cobertura": "parcialmente",
    "alcance_proveedor_copias": "parcialmente",
    "filtro_correo_verificado": "no_se",
})

# Impactos fijos del caso de demostración (escala 1–5 de Koeze, 2017).
IMPACTOS_DEMO = {"cuentas": 4, "respaldos": 5, "correo": 3, "redes": 3}


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


def mostrar_niveles(resultado):
    """Imprime la probabilidad y el nivel de riesgo de cada área y el riesgo global."""
    hechos = resultado.hechos
    print("\n=== Nivel de riesgo por área ===")
    print(f"{'Área':<11}{'Prob.':>7}  Nivel")
    for area in AREAS:
        print(f"{area:<11}{hechos[f'p_{area}']:>7.1f}  {hechos[f'nivel_p_{area}']}")
    print(f"\nRiesgo global: {resultado.riesgo_global}")


def mostrar_riesgo(riesgo):
    """Extensión: imprime impacto, riesgo y banda por área, la zona y el riesgo global."""
    print("\n=== Extensión: impacto, bandas y zona ===")
    print(f"{'Área':<11}{'Prob.':>7}  {'Nivel':<6}{'Impacto':>8}{'Riesgo':>8}  Banda")
    for area in AREAS:
        print(f"{area:<11}{riesgo.probabilidad[area]:>7.1f}  "
              f"{riesgo.nivel_probabilidad[area]:<6}{riesgo.impacto[area]:>8.1f}"
              f"{riesgo.riesgo_area[area]:>8.3f}  {riesgo.banda_area[area]}")
    print(f"\nProbabilidad media: {riesgo.probabilidad_media:.1f} "
          f"({riesgo.nivel_probabilidad_media}); "
          f"impacto medio: {riesgo.impacto_medio:.1f} ({riesgo.nivel_impacto_medio})")
    print(f"Zona global: {riesgo.zona}")
    print(f"Riesgo numérico global: {riesgo.riesgo_global:.3f} ({riesgo.banda_global})")


def mostrar_resultado(resultado):
    """Imprime hallazgos, recomendaciones y verificaciones."""
    print("\n=== Resultado ===")
    print(f"\nHallazgos ({len(resultado.hallazgos)}):")
    for hallazgo in resultado.hallazgos:
        clave = hallazgo["id"].removeprefix("hallazgo_")
        pregunta = VARIABLES.get(clave, {}).get("pregunta", "")
        print(f"  [{hallazgo['area']}] {hallazgo['id']}: {pregunta}")
    if not resultado.hallazgos:
        print("  (ninguno)")

    print("\nRecomendaciones priorizadas:")
    for item in lista_priorizada(resultado):
        print(f"  {item['orden']:>2}. [{item['prioridad']}] {item['recomendacion']} "
              f"({item['area']}, riesgo {resultado.hechos['nivel_p_' + item['area']]})")
    if not resultado.prioridades:
        print("  (ninguna)")

    print("\nVerificaciones solicitadas:")
    for area in resultado.verificaciones_solicitadas:
        print(f"  - Verificar las respuestas «no sé» del área {area} "
              "(se contaron como «no» para ser conservadores).")
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
    parser.add_argument("--con-impacto", action="store_true",
                        help="extensión: pide el impacto por área y muestra bandas y zona")
    parser.add_argument("--web", action="store_true",
                        help="inicia la interfaz web (requiere Flask) en lugar de la consola")
    parser.add_argument("--puerto", type=int, default=5000,
                        help="puerto de la interfaz web (por defecto 5000)")
    args = parser.parse_args(argv)

    if args.web:
        try:
            from .web import create_app
        except ImportError:
            print("La interfaz web necesita Flask: pip install -r requirements.txt")
            return 1
        url = f"http://127.0.0.1:{args.puerto}"
        print(f"Interfaz web en {url} (Ctrl+C para detener)")
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()  # abre el navegador
        create_app().run(host="127.0.0.1", port=args.puerto)
        return 0

    if args.demo:
        print("Modo demostración: tienda con comercio en línea (empresa simulada) con "
              "debilidades marcadas en cuentas y respaldos.")
        respuestas = CASO_DEMO
        impactos = None
        if args.con_impacto:
            print("Impactos del caso de demostración: "
                  + ", ".join(f"{a} = {v}" for a, v in IMPACTOS_DEMO.items()) + ".")
            impactos = IMPACTOS_DEMO
    else:
        try:
            respuestas = preguntar()
            impactos = preguntar_impactos() if args.con_impacto else None
        except (EOFError, KeyboardInterrupt):
            print("\nCuestionario interrumpido.")
            return 1

    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    if impactos is not None:
        memoria.cargar_impactos(impactos)
    resultado = inferir(memoria)
    mostrar_niveles(resultado)
    # Extensión: impacto, bandas y zona salen de las reglas R109–R125 disparadas.
    riesgo = riesgo_desde_hechos(resultado.hechos)
    if riesgo is not None:
        mostrar_riesgo(riesgo)
    mostrar_resultado(resultado)
    print("\nLímites de este resultado:")
    for texto in AVISO_LIMITES:
        print(f"  - {texto}")
    if args.explicar:
        if impactos is not None:
            print("\n=== Explicación del cálculo de riesgo (extensión) ===")
            for linea in evaluar_riesgo(respuestas, impactos).trazabilidad:
                print(f"- {linea}")
        print("\n=== Explicación (reglas disparadas) ===")
        print(explicar(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
