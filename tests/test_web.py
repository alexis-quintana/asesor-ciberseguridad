"""Pruebas de la interfaz web con el cliente de pruebas de Flask."""

import unittest

try:
    from asesor.web import create_app, leer_formulario
except ImportError:  # Flask no instalado
    create_app = None

from asesor.base_conocimientos import VARIABLES
from asesor.interfaz_consola import CASO_DEMO, IMPACTOS_DEMO


def formulario(respuestas=CASO_DEMO, impactos=None, empresa=""):
    datos = {f"r_{c}": v for c, v in respuestas.items()}
    datos.update({f"i_{a}": v for a, v in (impactos or {}).items()})
    datos["empresa"] = empresa
    return datos


@unittest.skipIf(create_app is None, "Flask no está instalado")
class PruebasWeb(unittest.TestCase):

    def setUp(self):
        self.cliente = create_app().test_client()

    def test_formulario_con_las_48_preguntas(self):
        r = self.cliente.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data.count(b'type="radio"'), 48 * 4)
        for clave in VARIABLES:
            self.assertIn(f'name="r_{clave}"'.encode(), r.data)

    def test_demo_precarga_las_respuestas(self):
        r = self.cliente.get("/?demo=1")
        self.assertEqual(r.data.count(b" checked>"), 48)
        self.assertIn("Tienda de ejemplo".encode(), r.data)

    def test_resultado_del_caso_demo(self):
        r = self.cliente.post("/resultado", data=formulario(empresa="Tienda <x>"))
        self.assertEqual(r.status_code, 200)
        texto = r.data.decode()
        self.assertIn("Tienda &lt;x&gt;", texto)            # se escapa
        self.assertIn("Recomendaciones priorizadas (25)", texto)
        self.assertIn("nivel-alto", texto)
        self.assertIn("del área correo", texto)
        self.assertNotIn("Extensión", texto)

    def test_resultado_con_extension(self):
        r = self.cliente.post("/resultado", data=formulario(impactos=IMPACTOS_DEMO))
        self.assertEqual(r.status_code, 200)
        self.assertIn("amarilla", r.data.decode())

    def test_faltan_respuestas(self):
        r = self.cliente.post("/resultado", data=formulario({"cuentas_individuales": "si"}))
        self.assertEqual(r.status_code, 400)
        self.assertIn("Faltan 47 respuestas", r.data.decode())

    def test_impactos_incompletos(self):
        r = self.cliente.post("/resultado", data=formulario(impactos={"cuentas": "3"}))
        self.assertEqual(r.status_code, 400)
        self.assertIn("las cuatro áreas", r.data.decode())

    def test_valores_manipulados_dan_error_400(self):
        datos = formulario()
        datos["r_cuentas_individuales"] = "tal_vez"
        r = self.cliente.post("/resultado", data=datos)
        self.assertEqual(r.status_code, 400)
        self.assertIn("valor no permitido", r.data.decode())
        r = self.cliente.post("/resultado", data=formulario(impactos={**IMPACTOS_DEMO, "redes": "9"}))
        self.assertEqual(r.status_code, 400)
        self.assertIn("del 1 al 5", r.data.decode())

    def test_reporte_imprimible(self):
        r = self.cliente.post("/reporte", data=formulario(empresa="Mi pyme"))
        self.assertEqual(r.status_code, 200)
        texto = r.data.decode()
        self.assertTrue(texto.startswith("<!DOCTYPE html>"))
        self.assertIn("Empresa: Mi pyme", texto)
        self.assertIn("window.print()", texto)

    def test_leer_formulario(self):
        respuestas, impactos, empresa, errores = leer_formulario(
            type("F", (), {"get": lambda self, k, d="": formulario(impactos=IMPACTOS_DEMO).get(k, d)})())
        self.assertEqual(errores, [])
        self.assertEqual(impactos, IMPACTOS_DEMO)
        self.assertEqual(respuestas, CASO_DEMO)


if __name__ == "__main__":
    unittest.main()
