# Pruebas del reporte (HTML y PDF): deben coincidir con el resultado del motor.

import unittest
from datetime import datetime

from app.inferencia.caso import evaluar
from app.consola import CASO_DEMO, IMPACTOS_DEMO
from app.resultados.estadisticas import calcular_estadisticas
from app.resultados.reporte import AVISO_LIMITES, generar_reporte_html
from app.resultados.reporte_pdf import generar_reporte_pdf


FECHA = datetime(2026, 10, 7)


class PruebasReporte(unittest.TestCase):

    def test_contenido_del_caso_demo(self):
        html = generar_reporte_html(evaluar(CASO_DEMO), "Tienda <demo>", fecha=FECHA)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("Empresa: Tienda &lt;demo&gt;", html)
        self.assertIn("07/10/2026", html)
        self.assertIn("<div class='c t-alto'>Alto</div>", html)
        # Cuatro áreas con sus niveles calculados a mano (69,5; 69,5; 44,4; 27,7).
        for fragmento in ("<td>69.5</td><td class='alto nivel'>Alto</td>",
                          "<td>44.4</td><td class='medio nivel'>Medio</td>",
                          "<td>27.7</td><td class='bajo nivel'>Bajo</td>"):
            self.assertIn(fragmento, html)
        # 26 filas de recomendaciones: 18 altas, 6 medias y 2 bajas.
        self.assertEqual(html.count("<td class='alta nivel'>Alta</td>"), 18)
        self.assertEqual(html.count("<td class='media nivel'>Media</td>"), 6)
        self.assertEqual(html.count("<td class='baja nivel'>Baja</td>"), 2)
        self.assertIn("<svg", html)
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
        self.assertIn("<div class='c t-bajo'>Bajo</div>", html)

    def test_no_se_no_afirma_que_todo_esta_implementado(self):
        resultado = evaluar({c: "no_se" for c in CASO_DEMO})
        html = generar_reporte_html(resultado, fecha=FECHA)
        self.assertNotIn("están implementadas", html)
        self.assertIn("48 respuesta(s) «No sé»", html)
        self.assertIn("<div class='c t-alto'>Alto</div>", html)
        self.assertIn("solo para calcular el riesgo", html)

    def test_evaluar_exige_las_48_respuestas(self):
        with self.assertRaises(ValueError):
            evaluar({"cuentas_individuales": "si"})


def _texto_pdf(contenido):
    from io import BytesIO
    from pypdf import PdfReader
    lector = PdfReader(BytesIO(contenido))
    return len(lector.pages), "\n".join(p.extract_text() for p in lector.pages)


class PruebasEstadisticas(unittest.TestCase):

    def test_cifras_del_caso_demo(self):
        est = calcular_estadisticas(evaluar(CASO_DEMO))
        self.assertEqual(est["global_nivel"], "alto")
        self.assertEqual((est["areas_alto"], est["areas_medio"]), (2, 1))
        self.assertEqual(est["n_recomendaciones"], 26)
        self.assertEqual(est["prioridades"], {"alta": 18, "media": 6, "baja": 2})
        self.assertEqual(est["n_verificar"], 1)
        self.assertEqual([round(a["p"], 1) for a in est["areas"]], [69.5, 69.5, 44.4, 27.7])
        self.assertEqual(sum(est["respuestas_total"].values()), 48)
        # Las recomendaciones por área suman las de la lista.
        self.assertEqual(sum(sum(a["recomendaciones"].values()) for a in est["areas"]), 26)


class PruebasPdf(unittest.TestCase):

    def test_es_un_pdf_con_las_cifras_del_motor(self):
        res = evaluar(CASO_DEMO, IMPACTOS_DEMO)
        contenido = generar_reporte_pdf(res, "Tienda <demo> & Cía", fecha=FECHA)
        self.assertTrue(contenido.startswith(b"%PDF-"))
        paginas, texto = _texto_pdf(contenido)
        self.assertGreaterEqual(paginas, 3)
        self.assertIn("Informe de evaluación de riesgo de ciberseguridad", texto)
        self.assertIn("Tienda <demo> & Cía", texto)
        self.assertIn("07/10/2026", texto)
        est = calcular_estadisticas(res)
        for a in est["areas"]:
            self.assertIn(f"{a['p']:.1f}", texto)
        self.assertIn("Alto", texto)
        # Las 26 recomendaciones aparecen completas (se normalizan los saltos de línea).
        plano = " ".join(texto.split())
        for item in est["recomendaciones"]:
            self.assertIn(item["recomendacion"], plano)
        self.assertIn("Zona global: amarilla", texto)
        self.assertIn("Anexo A. Reglas aplicadas", texto)
        self.assertIn("R097", texto)
        self.assertIn(f"Página 1 de {paginas}", texto)
        self.assertIn("Resumen ejecutivo", texto)
        self.assertIn("Riesgo alto (regla R097)", texto)

    def test_sin_anexo_y_sin_recomendaciones(self):
        res = evaluar({c: "si" for c in CASO_DEMO})
        contenido = generar_reporte_pdf(res, incluir_explicacion=False, fecha=FECHA)
        _, texto = _texto_pdf(contenido)
        self.assertNotIn("Anexo A. Reglas aplicadas", texto)
        self.assertIn("todas las prácticas evaluadas están implementadas", texto)
        self.assertIn("Bajo", texto)

    def test_todo_no_se_no_afirma_que_esta_implementado(self):
        res = evaluar({c: "no_se" for c in CASO_DEMO})
        _, texto = _texto_pdf(generar_reporte_pdf(res, fecha=FECHA))
        self.assertNotIn("están implementadas", texto)
        self.assertIn("48 respuesta(s)", texto)

    def test_el_caracter_no_soportado_se_reemplaza(self):
        res = evaluar(CASO_DEMO)
        _, texto = _texto_pdf(generar_reporte_pdf(res, fecha=FECHA))
        self.assertNotIn("\u2265", texto)


if __name__ == "__main__":
    unittest.main()
