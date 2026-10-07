"""Pruebas de la memoria de trabajo y del motor de inferencia.

Los resultados esperados se escribieron a mano a partir de la base de
conocimientos (R001–R096 por práctica, R097–R101 riesgo global por conteo de
áreas, R102–R105 verificación de cuentas, respaldos, correo y redes).
"""

import unittest

from asesor.base_conocimientos import VARIABLES
from asesor.explicacion import formatear_regla
from asesor.memoria import MemoriaTrabajo
from asesor.motor import inferir


def caso(**cambios):
    """Respuestas «si» en las 48 preguntas, con los cambios indicados."""
    respuestas = {clave: "si" for clave in VARIABLES}
    respuestas.update(cambios)
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    return memoria


class PruebasMemoria(unittest.TestCase):

    def test_variable_desconocida(self):
        with self.assertRaises(ValueError):
            MemoriaTrabajo().cargar_respuestas({"no_existe": "si"})

    def test_respuesta_no_permitida(self):
        memoria = MemoriaTrabajo()
        with self.assertRaises(ValueError):
            memoria.cargar_respuestas({"cuentas_individuales": "tal_vez"})
        self.assertFalse(memoria.tiene("cuentas_individuales"))


class PruebasMotor(unittest.TestCase):

    def test_todo_si_sin_hallazgos(self):
        resultado = inferir(caso())
        self.assertEqual(resultado.hallazgos, [])
        self.assertEqual(resultado.recomendaciones, {})
        self.assertEqual(resultado.clasificacion_provisional, "sin_hallazgos_en_este_cuestionario")
        self.assertEqual([d.id for d in resultado.disparos], ["R097"])

    def test_un_solo_no(self):
        resultado = inferir(caso(cuentas_individuales="no"))
        self.assertEqual(resultado.hallazgos,
                         [{"id": "hallazgo_cuentas_individuales", "area": "cuentas"}])
        self.assertEqual(resultado.recomendaciones,
                         {"cuentas": ["Asignar una cuenta individual a cada empleado."]})
        self.assertEqual(resultado.hechos["areas_con_hallazgos"], 1)
        self.assertEqual(resultado.clasificacion_provisional, "atencion")
        self.assertEqual([d.id for d in resultado.disparos], ["R001", "R002", "R098"])

    def test_respuestas_incompletas(self):
        memoria = MemoriaTrabajo()
        memoria.cargar_respuestas({"cuentas_individuales": "si"})
        with self.assertRaises(ValueError) as contexto:
            inferir(memoria)
        self.assertIn("admin_restringido", str(contexto.exception))

    def test_no_se_pide_verificacion_sin_clasificacion(self):
        resultado = inferir(caso(cuentas_individuales="no_se"))
        self.assertEqual(resultado.verificaciones_solicitadas, ["cuentas"])
        self.assertIsNone(resultado.clasificacion_provisional)
        self.assertEqual([d.id for d in resultado.disparos], ["R102"])

    def test_todo_no_genera_47_hallazgos(self):
        # mfa_cobertura solo genera hallazgo con «parcialmente» (base del 01/10),
        # así que con las 48 respuestas en «no» hay 47 hallazgos y 47 recomendaciones.
        resultado = inferir(caso(**{clave: "no" for clave in VARIABLES}))
        self.assertEqual(len(resultado.hallazgos), 47)
        self.assertNotIn("hallazgo_mfa_cobertura", [h["id"] for h in resultado.hallazgos])
        self.assertEqual(sum(len(v) for v in resultado.recomendaciones.values()), 47)
        self.assertEqual(resultado.hechos["areas_con_hallazgos"], 4)
        self.assertEqual(resultado.clasificacion_provisional, "elevado")

    def test_mfa_cobertura_parcialmente_genera_hallazgo(self):
        resultado = inferir(caso(mfa_cobertura="parcialmente"))
        self.assertEqual(resultado.hallazgos,
                         [{"id": "hallazgo_mfa_cobertura", "area": "cuentas"}])
        self.assertEqual([d.id for d in resultado.disparos], ["R009", "R010", "R098"])

    def test_cada_regla_a_lo_sumo_una_vez(self):
        resultado = inferir(caso(
            cuentas_individuales="no", admin_restringido="no",
            copia_fuera_sede="no", filtro_spam="no_se", cortafuegos="no",
        ))
        ids = [d.id for d in resultado.disparos]
        self.assertEqual(len(ids), len(set(ids)))

    def test_operador_no_soportado(self):
        regla = {
            "id": "R999", "area": "cuentas", "etapa": "riesgo_parcial",
            "si": [{"hecho": "cuentas_individuales", "operador": "distinto", "valor": "si"}],
            "entonces": {"tipo": "hallazgo", "id": "hallazgo_x", "area": "cuentas"},
            "explicacion": "", "fuentes": [],
        }
        with self.assertRaises(ValueError):
            inferir(caso(), reglas=[regla])


class PruebasExplicacion(unittest.TestCase):

    def test_formato_regla(self):
        regla = {
            "si": [{"hecho": "cuentas_individuales", "operador": "igual", "valor": "no"}],
            "entonces": {"tipo": "hallazgo", "id": "hallazgo_cuentas_individuales", "area": "cuentas"},
            "fuentes": [{"id": "CHIDUKWANI_2026", "localizacion": "§4.3.2, p. 11"}],
        }
        self.assertEqual(
            formatear_regla(regla),
            "SI cuentas_individuales = «no» ENTONCES hallazgo_cuentas_individuales "
            "(área: cuentas) [Fuente: CHIDUKWANI_2026, §4.3.2, p. 11]",
        )


if __name__ == "__main__":
    unittest.main()
