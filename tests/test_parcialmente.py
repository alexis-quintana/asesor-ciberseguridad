# Pruebas del tratamiento de «Parcialmente» y «No sé».

import unittest

from app.conocimiento.base_conocimientos import REGLAS, VARIABLES
from app.conocimiento.base_reglas_criticidad import CONTROLES_ESENCIALES
from app.inferencia.memoria import MemoriaTrabajo
from app.inferencia.motor import inferir
from app.resultados.reporte import mensaje_sin_recomendaciones


def ejecutar(**cambios):
    respuestas = {c: "si" for c in VARIABLES}
    respuestas.update(cambios)
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    return inferir(memoria)


class PruebasParcialmente(unittest.TestCase):

    def test_cada_control_parcial_genera_hallazgo_y_recomendacion(self):
        for control in VARIABLES:
            with self.subTest(control=control):
                r = ejecutar(**{control: "parcialmente"})
                self.assertEqual([h["id"] for h in r.hallazgos], [f"hallazgo_{control}"])
                self.assertEqual(sum(len(v) for v in r.recomendaciones.values()), 1)

    def test_prioridad_de_un_control_parcial(self):
        for control in VARIABLES:
            with self.subTest(control=control):
                r = ejecutar(**{control: "parcialmente"})
                esperado = "media" if control in CONTROLES_ESENCIALES else "baja"
                self.assertEqual(r.prioridades,
                                 [{"control": control, "area": VARIABLES[control]["area"],
                                   "prioridad": esperado}])

    def test_todo_parcialmente(self):
        r = ejecutar(**{c: "parcialmente" for c in VARIABLES})
        self.assertEqual(len(r.hallazgos), 48)
        self.assertEqual(sum(len(v) for v in r.recomendaciones.values()), 48)
        # P = 50 en todo: R099 da global medio y prioridad media.
        self.assertEqual(r.riesgo_global, "medio")
        self.assertEqual({p["prioridad"] for p in r.prioridades}, {"media"})
        self.assertEqual(len(r.prioridades), 48)

    def test_la_explicacion_de_la_regla_menciona_parcialmente(self):
        regla = next(r for r in REGLAS if r["id"] == "R001")
        self.assertEqual(regla["si"][0]["valor"], ["no", "parcialmente"])
        self.assertIn("«no» o «parcialmente»", regla["explicacion"])


class PruebasNoSe(unittest.TestCase):

    def test_no_se_no_genera_hallazgo_pero_pide_verificacion(self):
        r = ejecutar(**{c: "no_se" for c in VARIABLES})
        self.assertEqual(r.hallazgos, [])
        self.assertEqual(r.prioridades, [])
        self.assertEqual(r.verificaciones_solicitadas, ["cuentas", "respaldos", "correo", "redes"])
        # Puntúa como «no» (83,5): cuatro áreas altas → riesgo global alto.
        self.assertEqual(r.riesgo_global, "alto")

    def test_mensaje_sin_recomendaciones(self):
        todo_no_se = ejecutar(**{c: "no_se" for c in VARIABLES})
        mensaje = mensaje_sin_recomendaciones(todo_no_se)
        self.assertIn("48 respuesta(s) «No sé»", mensaje)
        self.assertNotIn("implementadas", mensaje)
        todo_si = ejecutar()
        self.assertIn("todas las prácticas evaluadas están implementadas",
                      mensaje_sin_recomendaciones(todo_si))
        self.assertIsNone(mensaje_sin_recomendaciones(ejecutar(cuentas_individuales="no")))


if __name__ == "__main__":
    unittest.main()
