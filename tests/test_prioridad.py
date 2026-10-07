"""Pruebas de la prioridad de las recomendaciones (R126–R131).

Resultados esperados calculados a mano. Nivel de la respuesta: «no» = 83,5 (alto),
«parcialmente» = 50 (medio). Nivel del área: P < 34 bajo, P < 67 medio, P ≥ 67 alto.
Celdas: R126 (alto, alto) alta; R127 (alto, medio) media; R128 (alto, bajo) baja;
R129 (medio, alto) media; R130 (medio, medio) media; R131 (medio, bajo) baja.
"""

import unittest

from asesor.base_conocimientos import VARIABLES
from asesor.base_reglas_prioridad import (
    REGLAS_PRIORIDAD, REGLAS_PRIORIDAD_GENERICAS, verificar_reglas_prioridad,
)
from asesor.explicacion import formatear_regla
from asesor.interfaz_consola import CASO_DEMO
from asesor.memoria import MemoriaTrabajo
from asesor.motor import inferir
from asesor.priorizacion import lista_priorizada

CUENTAS = [c for c, v in VARIABLES.items() if v["area"] == "cuentas"]
MFA = "mfa_cobertura"  # su hallazgo se dispara con «no» y con «parcialmente»
SIN_MFA = [c for c in CUENTAS if c != MFA]  # los otros 11 controles de cuentas


def ejecutar(**cambios):
    respuestas = {c: "si" for c in VARIABLES}
    respuestas.update(cambios)
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    return inferir(memoria)


def prioridades(resultado):
    return {p["control"]: p["prioridad"] for p in resultado.prioridades}


def ids_prioridad(resultado):
    return [d.id for d in resultado.disparos if d.etapa == "prioridad"]


class PruebasReglasPrioridad(unittest.TestCase):

    def test_estructura(self):
        self.assertEqual([r["id"] for r in REGLAS_PRIORIDAD_GENERICAS],
                         [f"R{n}" for n in range(126, 132)])
        self.assertEqual(len(REGLAS_PRIORIDAD), 6 * len(VARIABLES))
        self.assertEqual(len({r["clave"] for r in REGLAS_PRIORIDAD}), len(REGLAS_PRIORIDAD))
        self.assertEqual(verificar_reglas_prioridad(), [])

    def test_formato(self):
        regla = next(r for r in REGLAS_PRIORIDAD if r["clave"] == "R126:cuentas_individuales")
        texto = formatear_regla(regla)
        self.assertIn("hallazgo_cuentas_individuales = verdadero", texto)
        self.assertIn("nivel_p_cuentas = «alto»", texto)
        self.assertIn("prioridad_cuentas_individuales = «alta»", texto)
        self.assertIn("SIHWI_2016", texto)


class PruebasCeldas(unittest.TestCase):

    def test_alto_alto_es_alta(self):
        # cuentas: 12 «no», P = 83,5 (alto) → los 12 hallazgos reciben R126.
        r = ejecutar(**{c: "no" for c in CUENTAS})
        self.assertEqual(set(prioridades(r).values()), {"alta"})
        self.assertEqual(ids_prioridad(r), ["R126"] * 12)

    def test_alto_medio_es_media(self):
        # 6 «no» y 6 «si»: P = (6 × 83,5 + 6 × 16,5) / 12 = 50 (medio).
        r = ejecutar(**{c: "no" for c in CUENTAS[:6]})
        self.assertEqual(set(prioridades(r).values()), {"media"})
        self.assertEqual(ids_prioridad(r), ["R127"] * 6)

    def test_alto_bajo_es_baja(self):
        # Un solo «no»: P = (83,5 + 11 × 16,5) / 12 = 22,1 (bajo).
        r = ejecutar(**{CUENTAS[0]: "no"})
        self.assertEqual(ids_prioridad(r), ["R128"])
        self.assertEqual(prioridades(r), {CUENTAS[0]: "baja"})

    def test_medio_alto_es_media(self):
        # 11 «no» y mfa «parcialmente»: P = (11 × 83,5 + 50) / 12 = 72,3 (alto).
        cambios = {c: "no" for c in SIN_MFA}
        cambios[MFA] = "parcialmente"
        r = ejecutar(**cambios)
        self.assertEqual(prioridades(r)[MFA], "media")
        self.assertIn("R129", ids_prioridad(r))
        self.assertEqual(ids_prioridad(r).count("R126"), 11)

    def test_medio_medio_es_media(self):
        # 5 «no», mfa «parcialmente» y 6 «si»: P = (5 × 83,5 + 50 + 6 × 16,5) / 12 = 47,2 (medio).
        otros = SIN_MFA[:5]
        cambios = {c: "no" for c in otros}
        cambios[MFA] = "parcialmente"
        r = ejecutar(**cambios)
        self.assertEqual(sorted(ids_prioridad(r)), ["R127"] * 5 + ["R130"])

    def test_medio_bajo_es_baja(self):
        # Solo mfa «parcialmente»: P = (50 + 11 × 16,5) / 12 = 19,8 (bajo).
        r = ejecutar(**{MFA: "parcialmente"})
        self.assertEqual(ids_prioridad(r), ["R131"])
        self.assertEqual(prioridades(r), {MFA: "baja"})

    def test_sin_hallazgos_no_hay_prioridades(self):
        r = ejecutar()
        self.assertEqual(r.prioridades, [])
        self.assertEqual(lista_priorizada(r), [])

    def test_no_se_no_genera_prioridad(self):
        # «no sé» cuenta como «no» en P pero no genera hallazgo; no hay prioridad.
        r = ejecutar(**{CUENTAS[0]: "no_se"})
        self.assertEqual(r.prioridades, [])


class PruebasListaPriorizada(unittest.TestCase):

    def test_orden_del_caso_demo(self):
        memoria = MemoriaTrabajo()
        memoria.cargar_respuestas(CASO_DEMO)
        lista = lista_priorizada(inferir(memoria))
        self.assertEqual([i["orden"] for i in lista], list(range(1, 26)))
        self.assertEqual([i["prioridad"] for i in lista],
                         ["alta"] * 18 + ["media"] * 5 + ["baja"] * 2)
        # Altas: cuentas (P = 69,5) y respaldos (P = 69,5) empatan; desempata el orden del cuestionario.
        self.assertEqual([i["area"] for i in lista[:18]], ["cuentas"] * 9 + ["respaldos"] * 9)
        # Medias: primero mfa_cobertura (cuentas, P = 69,5) y luego correo (P = 44,4).
        self.assertEqual(lista[18]["control"], MFA)
        self.assertEqual({i["area"] for i in lista[19:23]}, {"correo"})
        self.assertEqual({i["area"] for i in lista[23:]}, {"redes"})
        self.assertTrue(all(i["recomendacion"] for i in lista))

    def test_ordena_por_probabilidad_del_area(self):
        # cuentas: 12 «no» (P = 83,5); respaldos: 11 «no» y 1 «si» (P = 77,0). Ambas altas.
        respaldos = [c for c, v in VARIABLES.items() if v["area"] == "respaldos"]
        cambios = {c: "no" for c in CUENTAS}
        cambios.update({c: "no" for c in respaldos[:11]})
        lista = lista_priorizada(ejecutar(**cambios))
        self.assertEqual([i["area"] for i in lista], ["cuentas"] * 12 + ["respaldos"] * 11)


if __name__ == "__main__":
    unittest.main()

