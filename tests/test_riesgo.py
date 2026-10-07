"""Pruebas del cálculo de riesgo (motor v1).

Los valores esperados se calcularon a mano con las fórmulas de Sihwi et al.
(2016) y Koeze (2017); no se obtuvieron ejecutando el código.
"""

import unittest

from asesor.base_conocimientos import VARIABLES
from asesor.riesgo import (
    AREAS, banda_koeze, evaluar_riesgo, nivel_sihwi, zona_sihwi,
)


def respuestas(valor="si", **cambios):
    """Las 48 preguntas con la misma respuesta, con los cambios indicados."""
    datos = {clave: valor for clave in VARIABLES}
    datos.update(cambios)
    return datos


def impactos(valor):
    return {area: valor for area in AREAS}


class PruebasCasosCompletos(unittest.TestCase):

    def test_todo_si_impacto_minimo(self):
        r = evaluar_riesgo(respuestas("si"), impactos(1))
        for area in AREAS:
            self.assertAlmostEqual(r.probabilidad[area], 16.5)
            self.assertEqual(r.nivel_probabilidad[area], "bajo")
            self.assertAlmostEqual(r.impacto[area], 0.2)
            self.assertAlmostEqual(r.riesgo_area[area], 0.033)
            self.assertEqual(r.banda_area[area], "muy_bajo")
        self.assertAlmostEqual(r.impacto_medio, 20.0)
        self.assertEqual(r.zona, "verde")
        self.assertEqual(r.banda_global, "muy_bajo")

    def test_todo_no_impacto_critico(self):
        r = evaluar_riesgo(respuestas("no"), impactos(5))
        for area in AREAS:
            self.assertAlmostEqual(r.probabilidad[area], 83.5)
            self.assertEqual(r.nivel_probabilidad[area], "alto")
            self.assertAlmostEqual(r.impacto[area], 1.0)
            self.assertAlmostEqual(r.riesgo_area[area], 0.835)
            self.assertEqual(r.banda_area[area], "muy_alto")
        self.assertAlmostEqual(r.impacto_medio, 100.0)
        self.assertEqual(r.zona, "roja")
        self.assertAlmostEqual(r.riesgo_global, 0.835)
        self.assertEqual(r.banda_global, "muy_alto")

    def test_no_se_puntua_como_no(self):
        igual_no = evaluar_riesgo(respuestas("no"), impactos(5))
        con_no_se = evaluar_riesgo(respuestas("no_se"), impactos(5))
        self.assertEqual(con_no_se.probabilidad, igual_no.probabilidad)
        self.assertEqual(con_no_se.zona, igual_no.zona)
        self.assertEqual(con_no_se.banda_global, igual_no.banda_global)

    def test_todo_parcialmente_impacto_medio(self):
        r = evaluar_riesgo(respuestas("parcialmente"), impactos(3))
        for area in AREAS:
            self.assertAlmostEqual(r.probabilidad[area], 50.0)
            self.assertEqual(r.nivel_probabilidad[area], "medio")
            self.assertAlmostEqual(r.impacto[area], 0.6)
            self.assertAlmostEqual(r.riesgo_area[area], 0.30)
            self.assertEqual(r.banda_area[area], "bajo")
        self.assertAlmostEqual(r.impacto_medio, 60.0)
        self.assertEqual(r.zona, "amarilla")

    def test_un_area_critica_y_las_demas_sanas(self):
        # cuentas: todo «no» con impacto 5; el resto «si» con impacto 1.
        datos = respuestas("si")
        datos.update({c: "no" for c, v in VARIABLES.items() if v["area"] == "cuentas"})
        r = evaluar_riesgo(datos, {"cuentas": 5, "respaldos": 1, "correo": 1, "redes": 1})
        self.assertAlmostEqual(r.riesgo_area["cuentas"], 0.835)
        self.assertEqual(r.banda_area["cuentas"], "muy_alto")
        self.assertAlmostEqual(r.riesgo_area["redes"], 0.033)
        # P media = (83.5 + 3 × 16.5) / 4 = 33.25 -> bajo; I media = 25 × 1.6 = 40 -> medio.
        self.assertAlmostEqual(r.probabilidad_media, 33.25)
        self.assertAlmostEqual(r.impacto_medio, 40.0)
        self.assertEqual(r.zona, "verde")
        # Riesgo global = (0.835 + 3 × 0.033) / 4 = 0.2335 -> bajo.
        self.assertAlmostEqual(r.riesgo_global, 0.2335)
        self.assertEqual(r.banda_global, "bajo")


class PruebasUmbrales(unittest.TestCase):

    def test_niveles_de_sihwi(self):
        self.assertEqual(nivel_sihwi(0), "bajo")
        self.assertEqual(nivel_sihwi(33.9), "bajo")
        self.assertEqual(nivel_sihwi(34), "medio")
        self.assertEqual(nivel_sihwi(66.9), "medio")
        self.assertEqual(nivel_sihwi(67), "alto")
        self.assertEqual(nivel_sihwi(100), "alto")

    def test_bandas_de_koeze(self):
        esperadas = [
            (0.0, "muy_bajo"), (0.20, "muy_bajo"), (0.21, "bajo"), (0.40, "bajo"),
            (0.41, "medio"), (0.60, "medio"), (0.61, "alto"), (0.80, "alto"),
            (0.81, "muy_alto"), (1.0, "muy_alto"),
        ]
        for valor, banda in esperadas:
            with self.subTest(valor=valor):
                self.assertEqual(banda_koeze(valor), banda)

    def test_matriz_de_zonas(self):
        esperadas = {
            ("alto", "alto"): "roja",
            ("medio", "medio"): "amarilla", ("alto", "medio"): "amarilla",
            ("medio", "alto"): "amarilla",
            ("bajo", "bajo"): "verde", ("bajo", "medio"): "verde",
            ("bajo", "alto"): "verde", ("medio", "bajo"): "verde",
            ("alto", "bajo"): "verde",
        }
        for (p, i), zona in esperadas.items():
            with self.subTest(p=p, i=i):
                self.assertEqual(zona_sihwi(p, i), zona)


class PruebasValidacion(unittest.TestCase):

    def test_impacto_fuera_de_rango_o_de_tipo(self):
        for invalido in (0, 6, -1, "x", "3", 2.5, True, None):
            with self.subTest(valor=invalido):
                datos = impactos(3)
                datos["redes"] = invalido
                with self.assertRaises(ValueError):
                    evaluar_riesgo(respuestas("si"), datos)

    def test_impacto_de_area_faltante_o_desconocida(self):
        faltante = impactos(3)
        del faltante["correo"]
        with self.assertRaises(ValueError):
            evaluar_riesgo(respuestas("si"), faltante)
        sobrante = impactos(3)
        sobrante["fisica"] = 3
        with self.assertRaises(ValueError):
            evaluar_riesgo(respuestas("si"), sobrante)

    def test_respuestas_incompletas_o_invalidas(self):
        incompletas = respuestas("si")
        del incompletas["cortafuegos"]
        with self.assertRaises(ValueError):
            evaluar_riesgo(incompletas, impactos(3))
        with self.assertRaises(ValueError):
            evaluar_riesgo(respuestas("tal_vez"), impactos(3))
        with self.assertRaises(ValueError):
            evaluar_riesgo({**respuestas("si"), "no_existe": "si"}, impactos(3))


if __name__ == "__main__":
    unittest.main()
