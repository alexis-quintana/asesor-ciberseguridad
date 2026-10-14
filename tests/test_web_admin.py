# Pruebas del panel de mantenimiento de reglas (Flask).

import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from app.web import create_app
except ImportError:  # Flask no instalado
    create_app = None

from app.consola import CASO_DEMO
from app.conocimiento.mantenimiento import Almacen

CLAVE = "clave-de-prueba-123"


def formulario(**cambios):
    datos = {f"r_{c}": v for c, v in CASO_DEMO.items()}
    datos.update(cambios)
    return datos


@unittest.skipIf(create_app is None, "Flask no está instalado")
class PruebasAdmin(unittest.TestCase):

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / "mantenimiento.json"
        entorno = mock.patch.dict(os.environ, {"ASESOR_DATOS": str(self.ruta),
                                               "ASESOR_ADMIN_CLAVE": CLAVE})
        entorno.start()
        self.addCleanup(entorno.stop)
        self.cliente = create_app().test_client()

    def entrar(self):
        r = self.cliente.post("/admin/entrar", data={"clave": CLAVE})
        self.assertEqual(r.status_code, 302)
        html = self.cliente.get("/admin").data.decode()
        return re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1)

    def test_hay_que_iniciar_sesion(self):
        r = self.cliente.get("/admin")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Clave de acceso", r.data.decode())
        self.assertNotIn("Historial de cambios", r.data.decode())
        for ruta in ("/admin/regla/R002", ):
            self.assertEqual(self.cliente.get(ruta).status_code, 302)
        self.assertEqual(self.cliente.post("/admin/nueva", data={}).status_code, 302)
        self.assertEqual(self.cliente.post("/admin/regla/R001/desactivar", data={}).status_code, 302)
        self.assertFalse(self.ruta.exists())

    def test_clave_incorrecta_y_bloqueo(self):
        r = self.cliente.post("/admin/entrar", data={"clave": "mala"})
        self.assertEqual(r.status_code, 401)
        for _ in range(4):
            self.cliente.post("/admin/entrar", data={"clave": "mala"})
        # Tras 5 fallos seguidos se bloquea, incluso con la clave correcta.
        r = self.cliente.post("/admin/entrar", data={"clave": CLAVE})
        self.assertEqual(r.status_code, 429)

    def test_pantalla_de_acceso_y_mensajes(self):
        html = self.cliente.get("/admin").data.decode()
        for texto in ("Acceso de administrador", "Introduce tu clave para gestionar las reglas del sistema",
                      "Clave de acceso", "Acceder", "Mostrar clave", "Volver al inicio"):
            self.assertIn(texto, html)
        self.assertNotIn(CLAVE, html)
        vacio = self.cliente.post("/admin/entrar", data={"clave": "  "})
        self.assertEqual(vacio.status_code, 400)
        self.assertIn("Introduce tu clave de acceso", vacio.data.decode())
        mala = self.cliente.post("/admin/entrar", data={"clave": "mala"})
        self.assertEqual(mala.status_code, 401)
        self.assertIn("La clave ingresada no es correcta", mala.data.decode())
        self.assertEqual(self.cliente.get("/admin/regla/R002").status_code, 302)

    def test_cerrar_sesion_protege_de_nuevo(self):
        csrf = self.entrar()
        self.assertIn("Cerrar sesión", self.cliente.get("/admin").data.decode())
        self.assertEqual(self.cliente.get("/admin/regla/R002").status_code, 200)
        self.assertEqual(self.cliente.post("/admin/salir", data={"csrf": csrf}).status_code, 302)
        self.assertEqual(self.cliente.get("/admin/regla/R002").status_code, 302)
        self.assertIn("Clave de acceso", self.cliente.get("/admin").data.decode())

    def test_panel_lista_reglas_y_cabeceras(self):
        self.entrar()
        r = self.cliente.get("/admin")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        texto = r.data.decode()
        self.assertIn("Reglas (132)", texto)
        self.assertIn("R132", texto)
        r = self.cliente.get("/admin?etapa=criticidad")
        self.assertIn("Reglas (1)", r.data.decode())

    def test_exige_token_csrf(self):
        self.entrar()
        r = self.cliente.post("/admin/regla/R001/desactivar", data={"motivo": "Motivo de prueba"})
        self.assertEqual(r.status_code, 400)
        r = self.cliente.post("/admin/regla/R001/desactivar",
                              data={"motivo": "Motivo de prueba", "csrf": "otro"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.ruta.exists())

    def test_desactivar_y_activar(self):
        csrf = self.entrar()
        r = self.cliente.post("/admin/regla/R001/desactivar", data={"csrf": csrf, "motivo": "Motivo de prueba"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("R001", Almacen().cargar()["desactivadas"])
        self.assertIn("desactivada", self.cliente.get("/admin").data.decode())
        self.cliente.post("/admin/regla/R001/activar", data={"csrf": csrf})
        self.assertEqual(Almacen().cargar()["desactivadas"], [])

    def test_el_nucleo_no_se_desactiva(self):
        csrf = self.entrar()
        r = self.cliente.post("/admin/regla/R097/desactivar", data={"csrf": csrf, "motivo": "Motivo de prueba"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("núcleo del modelo", r.data.decode())

    def test_editar_texto_se_refleja_en_el_resultado(self):
        csrf = self.entrar()
        r = self.cliente.post("/admin/regla/R002", data={
            "csrf": csrf, "texto": "Dar una cuenta propia a cada persona.",
            "explicacion": "Se identificó un hallazgo de cuentas compartidas.",
            "evidencia_del_articulo": "El estudio observó cuentas compartidas.",
            "fuente_id": "CHIDUKWANI_2026", "localizacion": "sección 4.3.2, p. 11",
            "validacion_experto": "pendiente"})
        self.assertEqual(r.status_code, 302)
        resultado = self.cliente.post("/resultado", data=formulario())
        self.assertIn("Dar una cuenta propia a cada persona.", resultado.data.decode())
        formulario_edicion = self.cliente.get("/admin/regla/R002")
        self.assertEqual(formulario_edicion.status_code, 200)
        self.assertIn("Dar una cuenta propia", formulario_edicion.data.decode())

    def test_agregar_regla_nueva_y_verla_en_el_resultado(self):
        csrf = self.entrar()
        datos = {"csrf": csrf, "hecho_0": "copia_fuera_sede", "operador_0": "igual", "valor_0": "no",
                 "hecho_1": "hallazgo_cuentas_individuales", "operador_1": "igual", "valor_1": "verdadero",
                 "texto": "Revisar juntas las copias externas y las cuentas compartidas.",
                 "area": "respaldos", "prioridad": "alta", "fuente_id": "PAWAR_2022",
                 "localizacion": "sección 4.2, p. 7", "evidencia": "Prioriza los activos críticos.",
                 "validacion_experto": "pendiente"}
        r = self.cliente.post("/admin/nueva", data=datos)
        self.assertEqual(r.status_code, 302)
        resultado = self.cliente.post("/resultado", data=formulario())
        texto = resultado.data.decode()
        self.assertIn("Revisar juntas las copias externas y las cuentas compartidas.", texto)
        self.assertIn("Recomendaciones priorizadas (27)", texto)
        reporte = self.cliente.post("/reporte", data=formulario())
        self.assertIn("Revisar juntas las copias externas", reporte.data.decode())
        # Eliminarla la quita del resultado.
        self.cliente.post("/admin/regla/R133/eliminar", data={"csrf": csrf})
        self.assertIn("Recomendaciones priorizadas (26)",
                      self.cliente.post("/resultado", data=formulario()).data.decode())

    def test_regla_nueva_invalida_muestra_el_error(self):
        csrf = self.entrar()
        r = self.cliente.post("/admin/nueva", data={
            "csrf": csrf, "hecho_0": "copia_fuera_sede", "operador_0": "igual", "valor_0": "quizas",
            "texto": "Texto de la recomendación nueva.", "area": "respaldos", "prioridad": "alta",
            "fuente_id": "PAWAR_2022", "localizacion": "p. 7", "evidencia": "Evidencia de prueba."})
        self.assertEqual(r.status_code, 400)
        self.assertIn("no permitido", r.data.decode())
        self.assertFalse(self.ruta.exists())

    def test_el_texto_del_administrador_se_escapa(self):
        csrf = self.entrar()
        self.cliente.post("/admin/regla/R002", data={
            "csrf": csrf, "texto": "<script>alert(1)</script> Cuenta propia.",
            "fuente_id": "CHIDUKWANI_2026", "localizacion": "sección 4.3.2, p. 11"})
        resultado = self.cliente.post("/resultado", data=formulario()).data.decode()
        self.assertNotIn("<script>alert(1)</script>", resultado)
        self.assertIn("&lt;script&gt;", resultado)

    def test_cerrar_sesion(self):
        self.entrar()
        self.cliente.post("/admin/salir", data={})
        self.assertIn("Clave de acceso", self.cliente.get("/admin").data.decode())

    def test_el_resultado_publico_no_requiere_clave(self):
        r = self.cliente.post("/resultado", data=formulario())
        self.assertEqual(r.status_code, 200)

    def test_formulario_con_ayudas_y_pasos(self):
        texto = self.cliente.get("/evaluar").data.decode()
        self.assertEqual(texto.count("<summary>¿Qué significa?</summary>"), 48)
        self.assertIn("¿Cuándo marcar cada opción?", texto)
        self.assertIn('id="progreso"', texto)

    def test_error_de_respuestas_faltantes_indica_las_preguntas(self):
        datos = formulario()
        del datos["r_cuentas_individuales"], datos["r_admin_restringido"]
        r = self.cliente.post("/resultado", data=datos)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Faltan 2 respuestas por contestar (preguntas 1, 2)", r.data.decode())



@unittest.skipIf(create_app is None, "Flask no está instalado")
class PruebasCrearClave(unittest.TestCase):

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta = Path(carpeta.name) / "mantenimiento.json"
        entorno = mock.patch.dict(os.environ, {"ASESOR_DATOS": str(self.ruta)})
        entorno.start()
        self.addCleanup(entorno.stop)
        os.environ.pop("ASESOR_ADMIN_CLAVE", None)
        self.cliente = create_app().test_client()

    def csrf(self):
        html = self.cliente.get("/admin").data.decode()
        return re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1), html

    def test_boton_visible_en_la_pagina_principal(self):
        html = self.cliente.get("/").data.decode()
        self.assertIn('href="/admin"', html)
        self.assertIn("Administrar reglas", html)

    def test_primer_uso_pide_crear_la_clave(self):
        _, html = self.csrf()
        self.assertIn("Cree la clave del administrador", html)
        self.assertIn("/admin/crear-clave", html)

    def test_crear_clave_entra_y_guarda_solo_el_resumen(self):
        token, _ = self.csrf()
        r = self.cliente.post("/admin/crear-clave", data={
            "csrf": token, "clave": "mi-clave-segura", "confirmacion": "mi-clave-segura"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("Historial de cambios", self.cliente.get("/admin").data.decode())
        guardado = (self.ruta.parent / "admin_clave.json").read_text(encoding="utf-8")
        self.assertNotIn("mi-clave-segura", guardado)
        # una sesión nueva debe iniciar con esa clave
        otro = create_app().test_client()
        html = otro.get("/admin").data.decode()
        self.assertIn("Clave de acceso", html)
        t2 = re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1)
        self.assertEqual(otro.post("/admin/entrar", data={"csrf": t2, "clave": "otra"}).status_code, 401)
        self.assertEqual(otro.post("/admin/entrar", data={"csrf": t2, "clave": "mi-clave-segura"}).status_code, 302)

    def test_clave_corta_o_distinta_se_rechaza(self):
        token, _ = self.csrf()
        corta = self.cliente.post("/admin/crear-clave", data={"csrf": token, "clave": "abc", "confirmacion": "abc"})
        self.assertEqual(corta.status_code, 400)
        distinta = self.cliente.post("/admin/crear-clave", data={
            "csrf": token, "clave": "clave-larga-1", "confirmacion": "clave-larga-2"})
        self.assertEqual(distinta.status_code, 400)
        self.assertFalse((self.ruta.parent / "admin_clave.json").exists())

    def test_no_se_puede_crear_sin_token_ni_desde_otro_equipo(self):
        self.csrf()
        sin_token = self.cliente.post("/admin/crear-clave", data={
            "clave": "mi-clave-segura", "confirmacion": "mi-clave-segura"})
        self.assertEqual(sin_token.status_code, 400)
        remoto = create_app().test_client()
        remoto.get("/admin", environ_overrides={"REMOTE_ADDR": "10.0.0.5"})
        r = remoto.post("/admin/crear-clave", data={"clave": "mi-clave-segura", "confirmacion": "mi-clave-segura"},
                        environ_overrides={"REMOTE_ADDR": "10.0.0.5"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse((self.ruta.parent / "admin_clave.json").exists())

    def test_no_se_puede_recrear_si_ya_existe(self):
        token, _ = self.csrf()
        self.cliente.post("/admin/crear-clave", data={
            "csrf": token, "clave": "mi-clave-segura", "confirmacion": "mi-clave-segura"})
        otro = create_app().test_client()
        r = otro.post("/admin/crear-clave", data={"clave": "intruso-123", "confirmacion": "intruso-123"})
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
