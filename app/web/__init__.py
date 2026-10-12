# Interfaz web con Flask.

from __future__ import annotations

import os
import secrets
from datetime import date

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

    @app.context_processor
    def _datos_comunes():
        return {"anio": date.today().year}      # año del pie de página, siempre actual

    registrar_rutas(app)
    return app
