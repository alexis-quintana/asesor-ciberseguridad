"""Pruebas de la memoria de trabajo y del motor de inferencia.

Los resultados esperados se escribieron a mano a partir de la base de
conocimientos (R001–R096 por práctica, R097–R101 riesgo global por conteo de
áreas con riesgo alto y medio, R102–R105 verificación de cuentas, respaldos,
correo y redes, R106–R108 nivel de riesgo de cada área). Nivel de un área: bajo
si P < 34, medio si P < 67, alto si P ≥ 67; «si» = 16,5, «parcialmente» = 50,
«no» = «no_se» = 83,5 y P es el promedio de los 12 puntajes.
"""

import unittest

from asesor.base_conocimientos import VARIABLES
from asesor.explicacion import formatear_regla
from asesor.interfaz_consola import CASO_DEMO, IMPACTOS_DEMO
from asesor.memoria import MemoriaTrabajo
from asesor.motor import inferir
from asesor.riesgo import AREAS


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


def area_con(area, respuesta, cantidad=12):
    """Cambia a «respuesta» las primeras «cantidad» preguntas del área."""
    claves = [c for c, v in VARIABLES.items() if v["area"] == area][:cantidad]
    return {c: respuesta for c in claves}


class PruebasMotor(unittest.TestCase):

    def test_todo_si_sin_hallazgos(self):
        resultado = inferir(caso())
        self.assertEqual(resultado.hallazgos, [])
        self.assertEqual(resultado.recomendaciones, {})
        self.assertEqual(resultado.riesgo_global, "bajo")
        # Cuatro niveles de área (R106, P = 16,5) y R101 (todas las áreas bajas).
        self.assertEqual([d.id for d in resultado.disparos], ["R106"] * 4 + ["R101"])

    def test_un_solo_no(self):
        resultado = inferir(caso(cuentas_individuales="no"))
        self.assertEqual(resultado.hallazgos,
                         [{"id": "hallazgo_cuentas_individuales", "area": "cuentas"}])
        self.assertEqual(resultado.recomendaciones,
                         {"cuentas": ["Asignar una cuenta individual a cada empleado."]})
        # P(cuentas) = (11 × 16,5 + 83,5) / 12 = 22,083…: sigue en «bajo».
        self.assertEqual(resultado.hechos["nivel_p_cuentas"], "bajo")
        self.assertEqual(resultado.riesgo_global, "bajo")
        self.assertEqual([d.id for d in resultado.disparos],
                         ["R001", "R002"] + ["R106"] * 4 + ["R101", "R128"])

    def test_respuestas_incompletas(self):
        memoria = MemoriaTrabajo()
        memoria.cargar_respuestas({"cuentas_individuales": "si"})
        with self.assertRaises(ValueError) as contexto:
            inferir(memoria)
        self.assertIn("admin_restringido", str(contexto.exception))

    def test_no_se_pide_verificacion_y_cuenta_como_no(self):
        resultado = inferir(caso(cuentas_individuales="no_se"))
        self.assertEqual(resultado.verificaciones_solicitadas, ["cuentas"])
        self.assertEqual(resultado.hallazgos, [])
        self.assertEqual(resultado.riesgo_global, "bajo")
        self.assertEqual([d.id for d in resultado.disparos],
                         ["R102"] + ["R106"] * 4 + ["R101"])

    def test_todo_no_genera_48_hallazgos(self):
        # mfa_cobertura genera hallazgo con «no» y con «parcialmente» (operador «en»),
        # así que con las 48 respuestas en «no» hay 48 hallazgos y 48 recomendaciones.
        resultado = inferir(caso(**{clave: "no" for clave in VARIABLES}))
        self.assertEqual(len(resultado.hallazgos), 48)
        self.assertIn("hallazgo_mfa_cobertura", [h["id"] for h in resultado.hallazgos])
        self.assertEqual(sum(len(v) for v in resultado.recomendaciones.values()), 48)
        self.assertEqual(resultado.hechos["areas_riesgo_alto"], 4)
        self.assertEqual(resultado.riesgo_global, "alto")

    def test_mfa_cobertura_no_genera_hallazgo(self):
        resultado = inferir(caso(mfa_cobertura="no"))
        self.assertEqual(resultado.hallazgos,
                         [{"id": "hallazgo_mfa_cobertura", "area": "cuentas"}])
        # P = (83,5 + 11 × 16,5) / 12 = 22,1 (bajo): R009, R010, cuatro R106, R101 y R128 (baja).
        self.assertEqual([d.id for d in resultado.disparos],
                         ["R009", "R010"] + ["R106"] * 4 + ["R101", "R128"])

    def test_mfa_cobertura_no_se_y_si_no_generan_hallazgo(self):
        self.assertEqual(inferir(caso(mfa_cobertura="no_se")).hallazgos, [])
        self.assertEqual(inferir(caso(mfa_cobertura="si")).hallazgos, [])

    def test_mfa_cobertura_parcialmente_genera_hallazgo(self):
        resultado = inferir(caso(mfa_cobertura="parcialmente"))
        self.assertEqual(resultado.hallazgos,
                         [{"id": "hallazgo_mfa_cobertura", "area": "cuentas"}])
        # P(cuentas) = (11 × 16,5 + 50) / 12 = 19,6…: bajo.
        self.assertEqual([d.id for d in resultado.disparos],
                         ["R009", "R010"] + ["R106"] * 4 + ["R101", "R131"])

    def test_cada_regla_a_lo_sumo_una_vez(self):
        resultado = inferir(caso(
            cuentas_individuales="no", admin_restringido="no",
            copia_fuera_sede="no", filtro_spam="no_se", cortafuegos="no",
        ))
        # Las reglas genéricas (R106) se instancian por área: se distinguen por clave.
        claves = [d.regla.get("clave", d.id) for d in resultado.disparos]
        self.assertEqual(len(claves), len(set(claves)))

    def test_operador_no_soportado(self):
        regla = {
            "id": "R999", "area": "cuentas", "etapa": "riesgo_parcial",
            "si": [{"hecho": "cuentas_individuales", "operador": "distinto", "valor": "si"}],
            "entonces": {"tipo": "hallazgo", "id": "hallazgo_x", "area": "cuentas"},
            "explicacion": "", "fuentes": [],
        }
        with self.assertRaises(ValueError):
            inferir(caso(), reglas=[regla])


class PruebasRiesgoGlobal(unittest.TestCase):
    """Esperados calculados a mano con las fórmulas del docstring del módulo."""

    def test_dos_areas_altas_dan_riesgo_global_alto(self):
        # P(cuentas) = P(respaldos) = 83,5 (alto); correo y redes = 16,5 (bajo).
        resultado = inferir(caso(**area_con("cuentas", "no"), **area_con("respaldos", "no")))
        self.assertEqual(resultado.hechos["areas_riesgo_alto"], 2)
        self.assertEqual(resultado.riesgo_global, "alto")
        self.assertIn("R097", [d.id for d in resultado.disparos])

    def test_una_area_alta_da_riesgo_global_medio(self):
        resultado = inferir(caso(**area_con("redes", "no")))
        self.assertEqual(resultado.hechos["nivel_p_redes"], "alto")
        self.assertEqual(resultado.riesgo_global, "medio")
        self.assertIn("R098", [d.id for d in resultado.disparos])

    def test_dos_areas_medias_dan_riesgo_global_medio(self):
        # 4 «no» y 8 «si»: P = (4 × 83,5 + 8 × 16,5) / 12 = 38,83… (medio).
        resultado = inferir(caso(**area_con("cuentas", "no", 4), **area_con("correo", "no", 4)))
        self.assertEqual(resultado.hechos["areas_riesgo_alto"], 0)
        self.assertEqual(resultado.hechos["areas_riesgo_medio"], 2)
        self.assertEqual(resultado.riesgo_global, "medio")
        self.assertIn("R099", [d.id for d in resultado.disparos])

    def test_una_area_media_da_riesgo_global_bajo(self):
        resultado = inferir(caso(**area_con("cuentas", "no", 4)))
        self.assertEqual(resultado.hechos["nivel_p_cuentas"], "medio")
        self.assertEqual(resultado.riesgo_global, "bajo")
        self.assertIn("R100", [d.id for d in resultado.disparos])

    def test_no_se_cuenta_como_no(self):
        resultado = inferir(caso(**area_con("cuentas", "no_se"), **area_con("redes", "no_se")))
        self.assertEqual(resultado.riesgo_global, "alto")
        self.assertEqual(resultado.verificaciones_solicitadas, ["cuentas", "redes"])

    def test_una_sola_regla_global_por_caso(self):
        for cambios in ({}, area_con("cuentas", "no"), area_con("cuentas", "no", 4),
                        {**area_con("cuentas", "no"), **area_con("redes", "no")}):
            resultado = inferir(caso(**cambios))
            globales = [d.id for d in resultado.disparos if d.etapa == "riesgo_global"]
            self.assertEqual(len(globales), 1, cambios)

    def test_niveles_por_area_en_los_hechos(self):
        resultado = inferir(caso(**area_con("respaldos", "parcialmente")))
        self.assertEqual(resultado.hechos["p_respaldos"], 50.0)
        self.assertEqual({a: resultado.hechos[f"nivel_p_{a}"] for a in AREAS},
                         {"cuentas": "bajo", "respaldos": "medio", "correo": "bajo", "redes": "bajo"})


class PruebasCasoDemostracion(unittest.TestCase):
    """Valores del caso de demostración calculados a mano (ver interfaz_consola.py)."""

    def test_niveles_y_riesgo_global(self):
        memoria = MemoriaTrabajo()
        memoria.cargar_respuestas(CASO_DEMO)
        resultado = inferir(memoria)
        h = resultado.hechos
        # P = (9 × 83,5 + 50 + 2 × 16,5) / 12 = 834,5 / 12 en cuentas y respaldos;
        # correo: (5 × 83,5 + 7 × 16,5) / 12; redes: (2 × 83,5 + 10 × 16,5) / 12.
        self.assertAlmostEqual(h["p_cuentas"], 834.5 / 12, places=6)
        self.assertAlmostEqual(h["p_respaldos"], 834.5 / 12, places=6)
        self.assertAlmostEqual(h["p_correo"], 533 / 12, places=6)
        self.assertAlmostEqual(h["p_redes"], 332 / 12, places=6)
        self.assertEqual([h[f"nivel_p_{a}"] for a in AREAS], ["alto", "alto", "medio", "bajo"])
        self.assertEqual(resultado.riesgo_global, "alto")
        self.assertEqual(len(resultado.hallazgos), 25)
        self.assertEqual(resultado.verificaciones_solicitadas, ["correo"])

    def test_extension_con_impactos(self):
        memoria = MemoriaTrabajo()
        memoria.cargar_respuestas(CASO_DEMO)
        memoria.cargar_impactos(IMPACTOS_DEMO)
        h = inferir(memoria).hechos
        # P media = 211,1667 / 4 = 52,8 (medio); I media = 100 × (0,8 + 1 + 0,6 + 0,6) / 4
        # = 75 (alto); riesgo = P/100 × I por área, promediado = 0,421 (medio).
        self.assertEqual((h["nivel_p_global"], h["nivel_i_global"]), ("medio", "alto"))
        self.assertEqual(h["zona_global"], "amarilla")
        self.assertEqual(h["banda_global"], "medio")
        self.assertEqual([h[f"banda_{a}"] for a in AREAS], ["medio", "alto", "bajo", "muy_bajo"])


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
