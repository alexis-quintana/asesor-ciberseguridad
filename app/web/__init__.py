"""Interfaz web con Flask.

Flask es solo una herramienta de implementación de la interfaz: la lógica del
sistema experto (conocimiento, inferencia, resultados) no lo importa. Aquí solo se
crea y configura la aplicación; las rutas están en rutas.py, las plantillas en
templates/ y los estilos en static/css/style.css.
"""

from __future__ import annotations

import os
import secrets

from flask import Flask

from app.web.rutas import leer_formulario, registrar_rutas  # noqa: F401


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("ASESOR_SECRETO") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=256 * 1024,
    )
    registrar_rutas(app)
    return app
