"""Pruebas de las reglas SI-ENTONCES del modelo de riesgo (R106–R125).

Los esperados de los casos fijos se calcularon a mano (ver test_riesgo.py);
además se comprueba que la ruta por reglas coincide con evaluar_riesgo, que
sigue siendo el cálculo independiente de referencia.
"""

import itertools
import random
import unittest

from asesor.base_conocimientos import VARIABLES
from asesor.base_reglas_riesgo import (
    AMBITOS, REGLAS_RIESGO, REGLAS_RIESGO_GENERICAS, verificar_reglas_riesgo,
)
from asesor.explicacion import formatear_regla
from asesor.memoria import MemoriaTrabajo
from asesor.motor import inferir
from asesor.riesgo import AREAS, evaluar_riesgo, riesgo_desde_hechos


def correr(respuestas, impactos):
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    memoria.cargar_impactos(impactos)
    resultado = inferir(memoria)
    return resultado, riesgo_desde_hechos(resultado.hechos)


def todos(valor, **cambios):
    r = {c: valor for c in VARIABLES}
    r.update(cambios)
    return r


class PruebasEstructura(unittest.TestCase):

    def test_veinte_reglas_genericas_ids_unicos(self):
        ids = [r["id"] for r in REGLAS_RIESGO_GENERICAS]
        self.assertEqual(ids, [f"R{n}" for n in range(106, 126)])
        self.assertEqual(verificar_reglas_riesgo(), [])

    def test_expansion(self):
        # 3+3+5 reglas en 5 ámbitos y 9 de zona solo en global.
        self.assertEqual(len(REGLAS_RIESGO), 11 * len(AMBITOS) + 9)
        claves = [r["clave"] for r in REGLAS_RIESGO]
        self.assertEqual(len(claves), len(set(claves)))

    def test_formato_si_entonces(self):
        regla = next(r for r in REGLAS_RIESGO if r["clave"] == "R108:cuentas")
        texto = formatear_regla(regla)
        self.assertIn("SI p_cuentas ≥ 67 ENTONCES nivel_p_cuentas = «alto»", texto)
        self.assertIn("SIHWI_2016", texto)


class PruebasCasosFijos(unittest.TestCase):

    def test_todo_no_impacto_5(self):
        resultado, r = correr(todos("no"), {a: 5 for a in AREAS})
        self.assertEqual(r.zona, "roja")
        self.assertEqual(r.banda_global, "muy_alto")
        self.assertEqual(r.nivel_probabilidad_media, "alto")
        ids = {d.id for d in resultado.disparos}
        self.assertIn("R125", ids)  # (alto, alto) -> roja

    def test_todo_si_impacto_1(self):
        _, r = correr(todos("si"), {a: 1 for a in AREAS})
        self.assertEqual((r.zona, r.banda_global), ("verde", "muy_bajo"))

    def test_todo_parcialmente_impacto_3(self):
        _, r = correr(todos("parcialmente"), {a: 3 for a in AREAS})
        self.assertEqual((r.zona, r.banda_global), ("amarilla", "bajo"))

    def test_cada_ambito_dispara_una_regla_por_etapa(self):
        resultado, _ = correr(todos("si"), {a: 3 for a in AREAS})
        por_clave = [d.regla.get("clave") for d in resultado.disparos if d.regla.get("clave")]
        self.assertEqual(len(por_clave), len(set(por_clave)))
        for etapa, esperado in (("nivel_probabilidad", 5), ("nivel_impacto", 5),
                                ("banda_riesgo", 5), ("zona", 1)):
            self.assertEqual(sum(d.etapa == etapa for d in resultado.disparos), esperado)

    def test_sin_impactos_solo_corre_el_flujo_principal(self):
        memoria = MemoriaTrabajo()
        memoria.cargar_respuestas(todos("si"))
        resultado = inferir(memoria)
        etapas = {d.etapa for d in resultado.disparos}
        self.assertIn("nivel_probabilidad", etapas)  # nivel de cada área
        self.assertFalse(etapas & {"nivel_impacto", "banda_riesgo", "zona"})
        self.assertIsNone(riesgo_desde_hechos(resultado.hechos))


class PruebasZona(unittest.TestCase):
    """Las 9 celdas se verifican contra el mapeo de Sihwi, escrito a mano."""

    ESPERADO = {
        ("bajo", "bajo"): "verde", ("bajo", "medio"): "verde", ("bajo", "alto"): "verde",
        ("medio", "bajo"): "verde", ("medio", "medio"): "amarilla", ("medio", "alto"): "amarilla",
        ("alto", "bajo"): "verde", ("alto", "medio"): "amarilla", ("alto", "alto"): "roja",
    }

    def test_nueve_celdas(self):
        for (p, i), zona in self.ESPERADO.items():
            reglas = [r for r in REGLAS_RIESGO
                      if r["etapa"] == "zona"
                      and {"nivel_p_global": p, "nivel_i_global": i}
                      == {c["hecho"]: c["valor"] for c in r["si"]}]
            self.assertEqual(len(reglas), 1, (p, i))
            self.assertEqual(reglas[0]["entonces"]["valor"], zona, (p, i))


class PruebasEquivalencia(unittest.TestCase):
    """La ruta por reglas debe dar lo mismo que evaluar_riesgo."""

    def comparar(self, respuestas, impactos):
        _, r = correr(respuestas, impactos)
        o = evaluar_riesgo(respuestas, impactos)
        self.assertEqual(r.zona, o.zona)
        self.assertEqual(r.banda_global, o.banda_global)
        self.assertEqual(r.nivel_probabilidad_media, o.nivel_probabilidad_media)
        self.assertEqual(r.nivel_impacto_medio, o.nivel_impacto_medio)
        self.assertEqual(r.nivel_probabilidad, o.nivel_probabilidad)
        self.assertEqual(r.banda_area, o.banda_area)
        self.assertAlmostEqual(r.riesgo_global, o.riesgo_global, places=8)

    def test_combinaciones_por_area(self):
        for resp, imp in itertools.product(("si", "parcialmente", "no", "no_se"), range(1, 6)):
            self.comparar(todos(resp), {a: imp for a in AREAS})

    def test_casos_aleatorios(self):
        azar = random.Random(2026)
        for _ in range(300):
            respuestas = {c: azar.choice(("si", "parcialmente", "no", "no_se")) for c in VARIABLES}
            impactos = {a: azar.randint(1, 5) for a in AREAS}
            self.comparar(respuestas, impactos)


if __name__ == "__main__":
    unittest.main()
