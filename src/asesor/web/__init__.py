"""Interfaz web con Flask.

Flask es solo una herramienta de implementación de la interfaz: la lógica del
sistema experto (base, motor, explicación, reporte) no lo importa. La web no
guarda nada: cada petición recibe las respuestas, las evalúa y devuelve la página.

Rutas: «/» (cuestionario), «/resultado» (evaluación) y «/reporte» (reporte imprimible).
"""

from __future__ import annotations

from flask import Flask, render_template, request

from ..base_conocimientos import RESPUESTAS, VARIABLES
from ..caso import evaluar
from ..explicacion import explicar
from ..interfaz_consola import CASO_DEMO, IMPACTOS_DEMO
from ..priorizacion import lista_priorizada
from ..reporte import AVISO_LIMITES, NOMBRE_NIVEL, generar_reporte_html
from ..riesgo import AREAS, PREGUNTAS_IMPACTO, riesgo_desde_hechos, validar_impactos

OPCIONES = (("si", "Sí"), ("parcialmente", "Parcialmente"), ("no", "No"), ("no_se", "No sé"))


def _preguntas_por_area():
    """[(área, [(número, clave, pregunta), ...]), ...] en el orden del cuestionario."""
    grupos, numero = [], 0
    for area in AREAS:
        items = []
        for clave, v in VARIABLES.items():
            if v["area"] == area:
                numero += 1
                items.append((numero, clave, v["pregunta"]))
        grupos.append((area, items))
    return grupos


def leer_formulario(form):
    """Lee el formulario. Devuelve (respuestas, impactos o None, empresa, errores)."""
    errores = []
    respuestas = {c: form.get(f"r_{c}", "") for c in VARIABLES}
    faltan = [c for c, v in respuestas.items() if not v]
    if faltan:
        errores.append(f"Faltan {len(faltan)} respuestas por contestar.")
    if any(v and v not in RESPUESTAS for v in respuestas.values()):
        errores.append("Hay respuestas con un valor no permitido.")
    valores = {a: form.get(f"i_{a}", "") for a in AREAS}
    impactos = None
    if any(valores.values()):
        if all(valores.values()):
            try:
                impactos = {a: int(v) for a, v in valores.items()}
                validar_impactos(impactos)
            except ValueError:
                impactos = None
                errores.append("Los impactos deben ser números del 1 al 5.")
        else:
            errores.append("Para usar la extensión de impacto se deben valorar las cuatro áreas.")
    return respuestas, impactos, form.get("empresa", "").strip()[:80], errores


def create_app():
    app = Flask(__name__)

    def pagina_formulario(respuestas=None, impactos=None, empresa="", errores=()):
        return render_template(
            "formulario.html", grupos=_preguntas_por_area(), opciones=OPCIONES,
            respuestas=respuestas or {}, impactos=impactos or {}, empresa=empresa,
            errores=errores, preguntas_impacto=PREGUNTAS_IMPACTO, areas=AREAS)

    @app.get("/")
    def inicio():
        if request.args.get("demo"):
            return pagina_formulario(CASO_DEMO, IMPACTOS_DEMO if request.args.get("demo") == "2" else {},
                                     "Tienda de ejemplo (simulada)")
        return pagina_formulario()

    @app.post("/resultado")
    def resultado():
        respuestas, impactos, empresa, errores = leer_formulario(request.form)
        if errores:
            return pagina_formulario(respuestas, {a: request.form.get(f"i_{a}", "") for a in AREAS},
                                     empresa, errores), 400
        res = evaluar(respuestas, impactos)
        return render_template(
            "resultado.html", r=res, h=res.hechos, areas=AREAS, nombres=NOMBRE_NIVEL,
            lista=lista_priorizada(res), riesgo=riesgo_desde_hechos(res.hechos),
            explicacion=explicar(res), aviso=AVISO_LIMITES, empresa=empresa,
            respuestas=respuestas, impactos=impactos or {})

    @app.post("/reporte")
    def reporte():
        respuestas, impactos, empresa, errores = leer_formulario(request.form)
        if errores:
            return pagina_formulario(respuestas, {a: request.form.get(f"i_{a}", "") for a in AREAS},
                                     empresa, errores), 400
        return generar_reporte_html(evaluar(respuestas, impactos), empresa)

    return app
