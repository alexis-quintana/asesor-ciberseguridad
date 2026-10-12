# Pruebas de la traza del motor y de la explicación detallada.

import unittest

from app.conocimiento.ayudas import AYUDAS, GUIA_RESPUESTAS, ayuda
from app.conocimiento.base_conocimientos import VARIABLES
from app.resultados.explicacion import armar_detalle, explicar, reglas_no_aplicadas
from app.consola import CASO_DEMO
from app.inferencia.memoria import MemoriaTrabajo
from app.inferencia.motor import ETAPAS_BASE, inferir


def ejecutar(base=None, **cambios):
    respuestas = {c: "si" for c in VARIABLES} if base is None else dict(base)
    respuestas.update(cambios)
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    return inferir(memoria)


class PruebasTraza(unittest.TestCase):

    def setUp(self):
        self.r = ejecutar(copia_datos_criticos="no")

    def test_el_disparo_guarda_clave_y_valores_observados(self):
        por_clave = {d.clave: d for d in self.r.disparos}
        self.assertEqual(por_clave["R025"].observados, {"copia_datos_criticos": "no"})
        self.assertEqual(por_clave["R026"].observados, {"hallazgo_copia_datos_criticos": True})
        nivel = por_clave["R106:respaldos"]
        self.assertAlmostEqual(nivel.observados["p_respaldos"], 265 / 12, places=6)
        prioridad = por_clave["R128:copia_datos_criticos"]
        self.assertEqual(prioridad.observados, {"hallazgo_copia_datos_criticos": True,
                                                "nivel_r_copia_datos_criticos": "alto",
                                                "nivel_p_respaldos": "bajo"})
        self.assertEqual(por_clave["R132:copia_datos_criticos"].observados["prioridad_copia_datos_criticos"], "baja")

    def test_estadisticas_por_etapa(self):
        e = self.r.estadisticas
        self.assertEqual(list(e), list(ETAPAS_BASE))
        self.assertEqual(e["riesgo_parcial"]["reglas"], 48)
        self.assertEqual(e["riesgo_parcial"]["disparadas"], 1)
        self.assertEqual(e["recomendacion"]["disparadas"], 1)
        self.assertEqual(e["nivel_probabilidad"]["disparadas"], 4)
        self.assertEqual(e["prioridad"]["reglas"], 6 * 48)
        self.assertEqual(e["criticidad"]["disparadas"], 1)
        # La segunda pasada solo confirma que no queda nada por disparar.
        self.assertEqual(e["riesgo_parcial"]["pasadas"], 2)
        # Cada instancia se evalúa mientras no haya disparado: nunca más de 2 veces cada una.
        for estadistica in e.values():
            self.assertLessEqual(estadistica["evaluaciones"], 2 * estadistica["reglas"])

    def test_explicar_muestra_instancia_y_valores(self):
        texto = explicar(self.r)
        self.assertIn("R106:respaldos [nivel_probabilidad]", texto)
        self.assertIn("Valores observados: p_respaldos = 22.1", texto)
        self.assertIn("R132:copia_datos_criticos [criticidad]", texto)


class PruebasDetalle(unittest.TestCase):

    def test_cadena_de_una_recomendacion(self):
        detalle = armar_detalle(ejecutar(copia_datos_criticos="no"))
        (item,) = detalle["recomendaciones"]
        self.assertEqual(item["prioridad"], "media")
        self.assertEqual(item["respuesta"], "No")
        self.assertEqual([p["regla"] for p in item["cadena"]],
                         ["R025", "R026", "R128:copia_datos_criticos", "R132:copia_datos_criticos"])
        self.assertIn("«No»", item["cadena"][0]["texto"])
        self.assertIn("«alto»", item["cadena"][2]["texto"])
        self.assertIn("control esencial", item["cadena"][3]["texto"])

    def test_resumen_de_areas_y_global(self):
        detalle = armar_detalle(ejecutar(CASO_DEMO))
        cuentas = detalle["areas"][0]
        self.assertEqual(cuentas["area"], "cuentas")
        self.assertEqual(cuentas["conteo"], {"si": 2, "parcialmente": 1, "no": 9, "no_se": 0})
        self.assertAlmostEqual(cuentas["p"], 834.5 / 12, places=6)
        self.assertEqual((cuentas["nivel"], cuentas["regla"]), ("alto", "R108:cuentas"))
        self.assertEqual(detalle["global"]["nivel"], "alto")
        self.assertEqual(detalle["global"]["regla"], "R097")
        self.assertEqual(detalle["global"]["areas_alto"], 2)
        self.assertEqual(detalle["umbrales"], {"medio": 34, "alto": 67})

    def test_reglas_que_no_se_aplicaron(self):
        # Todo «si»: no hay hallazgos, así que ninguna regla de prioridad ni de criticidad se aplica.
        r = ejecutar()
        filas = reglas_no_aplicadas(r)
        r126 = next(f for f in filas if f["id"] == "R126")
        self.assertEqual(r126["n"], 48)
        self.assertIn("no existe el hecho «hallazgo_", r126["motivo"])
        r097 = next(f for f in filas if f["id"] == "R097")
        self.assertIn("areas_riesgo_alto vale 0", r097["motivo"])
        self.assertNotIn("R101", [f["id"] for f in filas])

    def test_sin_hallazgos_no_hay_recomendaciones_detalladas(self):
        self.assertEqual(armar_detalle(ejecutar())["recomendaciones"], [])


class PruebasAyudas(unittest.TestCase):

    def test_hay_ayuda_para_las_48_preguntas(self):
        self.assertEqual(set(AYUDAS), set(VARIABLES))
        for clave in VARIABLES:
            self.assertGreater(len(ayuda(clave)["ejemplo"]), 20, clave)
            self.assertGreater(len(ayuda(clave)["verificar"]), 20, clave)

    def test_guia_de_respuestas(self):
        self.assertEqual([n for n, _ in GUIA_RESPUESTAS], ["Sí", "Parcialmente", "No", "No sé"])


if __name__ == "__main__":
    unittest.main()
