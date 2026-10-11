"""Pruebas de la validación con casos (50 casos, oráculo independiente) y de la verificación de la base."""

import copy
import unittest

from app import validacion, verificacion
from app.conocimiento.base_reglas_prioridad import REGLAS_PRIORIDAD
from tests import oraculo


class PruebasCasos(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.casos = validacion.cargar_casos()
        cls.filas, cls.m = validacion.validar(cls.casos)

    def test_hay_50_casos_en_tres_grupos(self):
        self.assertEqual(len(self.casos), 50)
        grupos = {g: sum(c["grupo"] == g for c in self.casos) for g in ("G1", "G2", "G3")}
        self.assertEqual(grupos, {"G1": 12, "G2": 18, "G3": 20})
        self.assertEqual(len({c["caso_id"] for c in self.casos}), 50)

    def test_el_sistema_coincide_con_el_oraculo(self):
        fallos = [f"{f['caso']}: {f['diferencias']}" for f in self.filas if not f["acierto"]]
        self.assertEqual(fallos, [])
        self.assertEqual(self.m["exactitud"], 100.0)

    def test_consistencia_y_cobertura(self):
        self.assertEqual(self.m["consistencia"], 100.0)
        self.assertEqual(self.m["reglas_definidas"], 132)
        self.assertEqual(self.m["reglas_sin_disparar"], [])

    def test_el_oraculo_no_usa_el_motor(self):
        with open(oraculo.__file__, encoding="utf-8") as f:
            fuente = f.read()
        for modulo in ("motor", "riesgo", "base_reglas", "validacion"):
            self.assertNotIn(f"import {modulo}", fuente)
            self.assertNotIn(f"inferencia.{modulo}", fuente)

    def test_comparar_detecta_diferencias(self):
        caso = self.casos[0]
        esperado = validacion._esperado(caso)
        esperado["global"] = "bajo" if esperado["global"] != "bajo" else "alto"
        import json
        obtenido = validacion.ejecutar(json.loads(caso["respuestas_json"]))
        self.assertTrue(validacion.comparar(esperado, obtenido, False))

    def test_la_validacion_detecta_alteraciones_de_la_base(self):
        for texto, fallan in validacion.mutaciones(self.casos):
            self.assertGreater(fallan, 0, texto)


class PruebasVerificacion(unittest.TestCase):

    def test_la_base_original_no_tiene_problemas(self):
        r = verificacion.verificar()
        self.assertFalse(verificacion.hay_problemas(r), verificacion.informe_texto(r))
        self.assertEqual(r["conflictos_sin_resolver"], [])
        self.assertEqual(r["ciclos"], [])

    def test_las_correcciones_entre_etapas_son_las_de_r132(self):
        r = verificacion.verificar()
        self.assertEqual({a.split(":")[0] for a, _, _ in r["conflictos_resueltos_por_etapa"]}, {"R128", "R131"})
        self.assertEqual({b.split(":")[0] for _, b, _ in r["conflictos_resueltos_por_etapa"]}, {"R132"})

    def _regla(self, **cambios):
        regla = {"id": "RX1", "etapa": "riesgo_parcial", "area": "cuentas",
                 "si": [{"hecho": "cuentas_individuales", "operador": "igual", "valor": "no"}],
                 "entonces": {"tipo": "hallazgo", "id": "hallazgo_x", "area": "cuentas"}}
        regla.update(cambios)
        return regla

    def test_detecta_duplicadas(self):
        a, b = self._regla(), self._regla(id="RX2")
        self.assertEqual(verificacion.redundancias([a, b])[0][2], "duplicada")

    def test_detecta_subsumidas(self):
        a = self._regla()
        b = self._regla(id="RX2", si=a["si"] + [{"hecho": "admin_restringido", "operador": "igual", "valor": "no"}])
        self.assertEqual(verificacion.redundancias([a, b])[0], ("RX2", "RX1", "subsumida"))

    def test_detecta_conflictos_en_la_misma_etapa(self):
        n1 = self._regla(etapa="riesgo_global", si=[{"hecho": "areas_riesgo_alto", "operador": "mayor_o_igual", "valor": 1}],
                         entonces={"tipo": "nivel", "hecho": "riesgo_global", "valor": "alto"})
        n2 = self._regla(id="RX2", etapa="riesgo_global", si=[{"hecho": "areas_riesgo_alto", "operador": "igual", "valor": 2}],
                         entonces={"tipo": "nivel", "hecho": "riesgo_global", "valor": "bajo"})
        _, sin_resolver = verificacion.conflictos([n1, n2])
        self.assertEqual(len(sin_resolver), 1)

    def test_no_marca_reglas_excluyentes(self):
        n1 = self._regla(etapa="riesgo_global", si=[{"hecho": "areas_riesgo_alto", "operador": "mayor_o_igual", "valor": 2}],
                         entonces={"tipo": "nivel", "hecho": "riesgo_global", "valor": "alto"})
        n2 = self._regla(id="RX2", etapa="riesgo_global", si=[{"hecho": "areas_riesgo_alto", "operador": "igual", "valor": 1}],
                         entonces={"tipo": "nivel", "hecho": "riesgo_global", "valor": "medio"})
        self.assertEqual(verificacion.conflictos([n1, n2]), ([], []))

    def test_detecta_ciclos(self):
        a = self._regla(etapa="riesgo_parcial", si=[{"hecho": "hallazgo_b", "operador": "igual", "valor": True}],
                        entonces={"tipo": "hallazgo", "id": "hallazgo_a", "area": "cuentas"})
        b = self._regla(id="RX2", etapa="riesgo_parcial", si=[{"hecho": "hallazgo_a", "operador": "igual", "valor": True}],
                        entonces={"tipo": "hallazgo", "id": "hallazgo_b", "area": "cuentas"})
        ciclos, _, _ = verificacion.circularidad([a, b])
        self.assertTrue(ciclos)

    def test_detecta_reglas_sin_salida_e_inalcanzables(self):
        muerta = self._regla(entonces={"tipo": "hallazgo", "id": "hallazgo_nadie_lo_usa", "area": "cuentas"})
        sin_entrada = self._regla(id="RX2", si=[{"hecho": "hecho_que_nadie_produce", "operador": "igual", "valor": 1}])
        muertas, inalcanzables = verificacion.sin_salida([muerta, sin_entrada])
        self.assertIn("RX1", muertas)
        self.assertEqual(inalcanzables[0][0], "RX2")


if __name__ == "__main__":
    unittest.main()
