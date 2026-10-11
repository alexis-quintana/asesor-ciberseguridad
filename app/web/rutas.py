"""Interfaz web con Flask.

Flask es solo una herramienta de implementación de la interfaz: la lógica del
sistema experto (base, motor, explicación, reporte, mantenimiento) no lo importa.
La parte pública no guarda nada: cada petición recibe las respuestas, las evalúa y
devuelve la página.

Rutas públicas, en el orden del flujo Presentación → Evaluación → Resultados: «/» (landing
de presentación, opcional), «/evaluar» (cuestionario), «/resultado» (evaluación) y
«/reporte» (reporte imprimible). Los estilos están en static/css/style.css.

Rutas de administración («/admin…»): mantenimiento de reglas, a las que se llega con
el botón «Administrar reglas» de la cabecera. No hay clave por defecto: la primera
vez la página pide crear una (solo desde el mismo equipo) y la guarda como resumen
PBKDF2. Opcionalmente, la variable de entorno ASESOR_ADMIN_CLAVE fija la clave y
tiene prioridad. Las acciones usan un token anti-CSRF por sesión, y se bloquean los
intentos tras varios fallos seguidos.

Fuente: requisito del proyecto P5 (prototipo con interfaz simple y explicación);
componente de actualización de conocimientos (Sesión 12; Sihwi et al., 2016, §II.A–C).
"""

from __future__ import annotations

import hmac
import os
import secrets
import time

from flask import abort, redirect, render_template, request, session, url_for

from app.conocimiento import mantenimiento
from app.conocimiento.ayudas import AYUDAS, GUIA_RESPUESTAS, ayuda
from app.conocimiento.base_conocimientos import FUENTES, RESPUESTAS, VARIABLES
from app.inferencia.caso import evaluar
from app.resultados.explicacion import armar_detalle, explicar, formatear_regla
from app.consola import CASO_DEMO, IMPACTOS_DEMO
from app.inferencia.priorizacion import lista_priorizada
from app.resultados.reporte import (AVISO_LIMITES, NOMBRE_NIVEL, generar_reporte_html,
                       mensaje_sin_recomendaciones, verificaciones_concretas)
from app.inferencia.riesgo import AREAS, PREGUNTAS_IMPACTO, riesgo_desde_hechos, validar_impactos

OPCIONES = (("si", "Sí"), ("parcialmente", "Parcialmente"), ("no", "No"), ("no_se", "No sé"))
MAX_FALLOS = 5            # intentos de clave fallidos antes de bloquear
BLOQUEO_SEGUNDOS = 60
OPERADORES_FORMULARIO = (("igual", "es igual a"), ("en", "es alguno de (separar con comas)"),
                         ("mayor_que", "es mayor que"), ("menor_que", "es menor que"),
                         ("mayor_o_igual", "es mayor o igual a"), ("menor_o_igual", "es menor o igual a"))
FILAS_CONDICIONES = 3


def _preguntas_por_area():
    """[(área, [(número, clave, pregunta, ayuda), ...]), ...] en el orden del cuestionario."""
    grupos, numero = [], 0
    for area in AREAS:
        items = []
        for clave, v in VARIABLES.items():
            if v["area"] == area:
                numero += 1
                items.append((numero, clave, v["pregunta"], ayuda(clave)))
        grupos.append((area, items))
    return grupos


def _numeros():
    return {clave: n for _, items in _preguntas_por_area() for n, clave, *_ in items}


def leer_formulario(form):
    """Lee el formulario. Devuelve (respuestas, impactos o None, empresa, errores)."""
    errores = []
    respuestas = {c: form.get(f"r_{c}", "") for c in VARIABLES}
    faltan = [c for c, v in respuestas.items() if not v]
    if faltan:
        numeros = _numeros()
        lista = ", ".join(str(numeros[c]) for c in faltan[:12]) + (" …" if len(faltan) > 12 else "")
        errores.append(f"Faltan {len(faltan)} respuestas por contestar (preguntas {lista}).")
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



def registrar_rutas(app):
    """Registra en la aplicación Flask las rutas públicas y de administración."""
    intentos = {"fallos": 0, "hasta": 0.0}

    def pagina_formulario(respuestas=None, impactos=None, empresa="", errores=()):
        return render_template(
            "evaluacion.html", grupos=_preguntas_por_area(), opciones=OPCIONES,
            respuestas=respuestas or {}, impactos=impactos or {}, empresa=empresa,
            errores=errores, preguntas_impacto=PREGUNTAS_IMPACTO, areas=AREAS,
            guia=GUIA_RESPUESTAS)

    @app.get("/")
    def landing():
        """Presentación opcional del sistema: contexto, uso y antecedentes."""
        return render_template("landing.html")

    @app.get("/evaluar")
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
            "resultados.html", r=res, h=res.hechos, areas=AREAS, nombres=NOMBRE_NIVEL,
            lista=lista_priorizada(res), riesgo=riesgo_desde_hechos(res.hechos),
            detalle=armar_detalle(res), explicacion=explicar(res), aviso=AVISO_LIMITES,
            sin_recomendaciones=mensaje_sin_recomendaciones(res),
            verificaciones=verificaciones_concretas(res),
            empresa=empresa, respuestas=respuestas, impactos=impactos or {})

    @app.post("/reporte")
    def reporte():
        respuestas, impactos, empresa, errores = leer_formulario(request.form)
        if errores:
            return pagina_formulario(respuestas, {a: request.form.get(f"i_{a}", "") for a in AREAS},
                                     empresa, errores), 400
        return generar_reporte_html(evaluar(respuestas, impactos), empresa)

    # ------------------------------------------------------------ administración
    def clave_entorno():
        return os.environ.get("ASESOR_ADMIN_CLAVE", "")

    def clave_configurada():
        return bool(clave_entorno()) or mantenimiento.ClaveAdmin().existe()

    def clave_correcta(enviada):
        if clave_entorno():
            return hmac.compare_digest(enviada.encode(), clave_entorno().encode())
        return mantenimiento.ClaveAdmin().verificar(enviada)

    def es_local():
        return request.remote_addr in ("127.0.0.1", "::1")

    def autenticado():
        return clave_configurada() and session.get("admin") is True

    def pagina_login(error="", estado=200, crear=None):
        crear = (not clave_configurada()) if crear is None else crear
        return render_template("admin_login.html", crear=crear, local=es_local(),
                               csrf=token_csrf(), error=error,
                               minimo=mantenimiento.ClaveAdmin.LARGO_MINIMO), estado

    def token_csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    def exigir_admin():
        if not autenticado():
            abort(redirect(url_for("admin")))
        enviado = request.form.get("csrf", "")
        if request.method == "POST" and not hmac.compare_digest(
                enviado.encode(), token_csrf().encode()):
            abort(400, "Solicitud no válida (token de seguridad incorrecto).")

    @app.after_request
    def sin_cache_en_admin(respuesta):
        if request.path.startswith("/admin"):
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    def pagina_admin(mensaje="", error="", **extra):
        almacen = mantenimiento.Almacen()
        datos, error_archivo = almacen.cargar_seguro()
        filtro = request.args.get("etapa", "")
        filas = mantenimiento.listar_reglas(almacen)
        etapas = sorted({f["etapa"] for f in filas})
        if filtro:
            filas = [f for f in filas if f["etapa"] == filtro]
        return render_template(
            "admin.html", filas=filas, etapas=etapas, filtro=filtro, csrf=token_csrf(),
            historial=almacen.historial()[:30], mensaje=mensaje, error=error or error_archivo or "",
            hechos=mantenimiento.hechos_permitidos(), operadores=OPERADORES_FORMULARIO,
            areas=mantenimiento.AREAS, prioridades=mantenimiento.PRIORIDADES,
            estados=mantenimiento.ESTADOS_VALIDACION, fuentes=FUENTES,
            filas_condiciones=range(FILAS_CONDICIONES), formal=formatear_regla,
            siguiente=mantenimiento.siguiente_id_nuevo(almacen),
            nuevas=len(datos["reglas_nuevas"]), form=extra.get("form", {}))

    @app.get("/admin")
    def admin():
        if not autenticado():
            return pagina_login()
        return pagina_admin(mensaje=request.args.get("ok", ""))

    @app.post("/admin/crear-clave")
    def admin_crear_clave():
        """Primer uso: crea la clave del administrador (solo desde este equipo)."""
        if clave_configurada():
            abort(404)
        if not es_local():
            return pagina_login("La clave solo puede crearse desde el equipo donde corre el asesor.", 403)
        if not hmac.compare_digest(request.form.get("csrf", "").encode(), token_csrf().encode()):
            abort(400, "Solicitud no válida (token de seguridad incorrecto).")
        try:
            mantenimiento.ClaveAdmin().establecer(request.form.get("clave", ""),
                                                  request.form.get("confirmacion", ""))
        except mantenimiento.ErrorMantenimiento as error:
            return pagina_login(str(error), 400, crear=True)
        session.clear()
        session["admin"] = True
        token_csrf()
        return redirect(url_for("admin", ok="Clave creada. Ya puede mantener las reglas."))

    @app.post("/admin/entrar")
    def admin_entrar():
        if not clave_configurada():
            abort(404)
        if time.time() < intentos["hasta"]:
            return pagina_login("Demasiados intentos fallidos. Espere un minuto.", 429)
        if clave_correcta(request.form.get("clave", "")):
            intentos["fallos"] = 0
            session.clear()
            session["admin"] = True
            token_csrf()
            return redirect(url_for("admin"))
        intentos["fallos"] += 1
        if intentos["fallos"] >= MAX_FALLOS:
            intentos["fallos"] = 0
            intentos["hasta"] = time.time() + BLOQUEO_SEGUNDOS
        return pagina_login("Clave incorrecta.", 401)

    @app.post("/admin/salir")
    def admin_salir():
        session.clear()
        return redirect(url_for("admin"))

    def ejecutar(accion, *args, **kwargs):
        """Ejecuta una acción de mantenimiento y vuelve al panel con el resultado."""
        try:
            accion(*args, **kwargs)
        except mantenimiento.ErrorMantenimiento as error:
            return pagina_admin(error=str(error)), 400
        return None

    @app.post("/admin/regla/<regla_id>/<accion>")
    def admin_accion(regla_id, accion):
        exigir_admin()
        almacen = mantenimiento.Almacen()
        acciones = {
            "desactivar": lambda: almacen.desactivar(regla_id, request.form.get("motivo", "")),
            "activar": lambda: almacen.activar(regla_id),
            "restablecer": lambda: almacen.restablecer(regla_id),
            "eliminar": lambda: almacen.eliminar_nueva(regla_id),
        }
        if accion not in acciones:
            abort(404)
        error = ejecutar(acciones[accion])
        if error:
            return error
        return redirect(url_for("admin", ok=f"{regla_id}: {accion} realizado."))

    def _fila(regla_id):
        for fila in mantenimiento.listar_reglas():
            if fila["id"] == regla_id:
                return fila
        abort(404)

    @app.get("/admin/regla/<regla_id>")
    def admin_regla(regla_id):
        exigir_admin()
        fila = _fila(regla_id)
        return render_template("admin_regla.html", fila=fila, csrf=token_csrf(), error="",
                               formal=formatear_regla, fuentes=FUENTES,
                               estados=mantenimiento.ESTADOS_VALIDACION,
                               prioridades=mantenimiento.PRIORIDADES)

    @app.post("/admin/regla/<regla_id>")
    def admin_editar(regla_id):
        exigir_admin()
        fila = _fila(regla_id)
        campos = {"texto": "texto", "explicacion": "explicacion",
                  "evidencia_del_articulo": "evidencia_del_articulo",
                  "validacion_experto": "validacion_experto",
                  "fuente_id": "fuente_id", "localizacion": "localizacion",
                  "prioridad": "prioridad"}
        cambios = {k: request.form[f] for f, k in campos.items() if f in request.form}
        if not fila["es_nueva"]:
            cambios.pop("prioridad", None)
        try:
            mantenimiento.Almacen().editar(regla_id, cambios)
        except mantenimiento.ErrorMantenimiento as error:
            return render_template("admin_regla.html", fila=_fila(regla_id), csrf=token_csrf(),
                                   error=str(error), formal=formatear_regla, fuentes=FUENTES,
                                   estados=mantenimiento.ESTADOS_VALIDACION,
                                   prioridades=mantenimiento.PRIORIDADES), 400
        return redirect(url_for("admin", ok=f"{regla_id}: cambios guardados."))

    @app.post("/admin/nueva")
    def admin_nueva():
        exigir_admin()
        condiciones = []
        for i in range(FILAS_CONDICIONES):
            hecho = request.form.get(f"hecho_{i}", "").strip()
            valor = request.form.get(f"valor_{i}", "").strip()
            if hecho or valor:
                condiciones.append({"hecho": hecho, "operador": request.form.get(f"operador_{i}", "igual"),
                                    "valor": valor})
        try:
            nuevo = mantenimiento.Almacen().agregar(
                area=request.form.get("area", ""), condiciones=condiciones,
                texto=request.form.get("texto", ""), prioridad=request.form.get("prioridad", ""),
                fuente_id=request.form.get("fuente_id", ""),
                localizacion=request.form.get("localizacion", ""),
                evidencia=request.form.get("evidencia", ""),
                validacion_experto=request.form.get("validacion_experto", "pendiente"),
                explicacion=request.form.get("explicacion", ""))
        except mantenimiento.ErrorMantenimiento as error:
            return pagina_admin(error=str(error), form=request.form), 400
        return redirect(url_for("admin", ok=f"Regla {nuevo} agregada."))
