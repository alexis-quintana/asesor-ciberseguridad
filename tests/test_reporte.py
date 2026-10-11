"""Pruebas del reporte imprimible (solo biblioteca estándar)."""

import unittest
from datetime import datetime

from app.inferencia.caso import evaluar
from app.consola import CASO_DEMO, IMPACTOS_DEMO
from app.resultados.reporte import AVISO_LIMITES, generar_reporte_html


FECHA = datetime(2026, 10, 7)


class PruebasReporte(unittest.TestCase):

    def test_contenido_del_caso_demo(self):
        html = generar_reporte_html(evaluar(CASO_DEMO), "Tienda <demo>", fecha=FECHA)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("Empresa: Tienda &lt;demo&gt;", html)   # el nombre se escapa
        self.assertIn("07/10/2026", html)
        self.assertIn("Riesgo global: <span class='nivel'>Alto</span>", html)
        # Cuatro áreas con sus niveles calculados a mano (69,5; 69,5; 44,4; 27,7).
        for fragmento in ("<td>69.5</td><td class='nivel'>Alto</td>",
                          "<td>44.4</td><td class='nivel'>Medio</td>",
                          "<td>27.7</td><td class='nivel'>Bajo</td>"):
            self.assertIn(fragmento, html)
        # 26 filas de recomendaciones: 18 altas, 6 medias y 2 bajas.
        self.assertEqual(html.count("<td class='nivel'>Alta</td>"), 18)
        self.assertEqual(html.count("<td class='nivel'>Media</td>"), 6)
        self.assertEqual(html.count("<td class='nivel'>Baja</td>"), 2)
        self.assertIn("Verifíquelas así", html)
        self.assertIn("¿Se ha comprobado que el filtro de correo declarado realmente funciona?", html)
        self.assertNotIn("Extensión", html)

    def test_incluye_aviso_y_explicacion(self):
        html = generar_reporte_html(evaluar(CASO_DEMO), fecha=FECHA)
        for texto in AVISO_LIMITES:
            self.assertIn(texto.split(";")[0].replace("«", "«"), html)
        self.assertIn("Anexo. Reglas aplicadas", html)
        self.assertIn("R097", html)
        sin = generar_reporte_html(evaluar(CASO_DEMO), incluir_explicacion=False, fecha=FECHA)
        self.assertNotIn("Anexo. Reglas aplicadas", sin)

    def test_extension_con_impactos(self):
        html = generar_reporte_html(evaluar(CASO_DEMO, IMPACTOS_DEMO), fecha=FECHA)
        self.assertIn("Extensión: impacto, bandas y zona", html)
        self.assertIn("Zona global: <b>amarilla</b>", html)
        self.assertIn("0.421", html)

    def test_sin_hallazgos(self):
        html = generar_reporte_html(evaluar({c: "si" for c in CASO_DEMO}), fecha=FECHA)
        self.assertIn("todas las prácticas evaluadas están implementadas", html)
        self.assertIn("No hay respuestas «no sé»", html)
        self.assertIn("Riesgo global: <span class='nivel'>Bajo</span>", html)

    def test_no_se_no_afirma_que_todo_esta_implementado(self):
        resultado = evaluar({c: "no_se" for c in CASO_DEMO})
        html = generar_reporte_html(resultado, fecha=FECHA)
        self.assertNotIn("están implementadas", html)
        self.assertIn("48 respuesta(s) «No sé»", html)
        self.assertIn("Riesgo global: <span class='nivel'>Alto</span>", html)
        self.assertIn("solo para calcular el riesgo", html)

    def test_evaluar_exige_las_48_respuestas(self):
        with self.assertRaises(ValueError):
            evaluar({"cuentas_individuales": "si"})


if __name__ == "__main__":
    unittest.main()
