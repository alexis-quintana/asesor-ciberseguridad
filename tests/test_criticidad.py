"""Pruebas de la regla de criticidad R132 (controles esenciales).

Esperados calculados a mano. Un solo «no» en un área: P = (11 × 16,5 + 83,5) / 12 =
22,1 (bajo); la respuesta es de nivel «alto» y la celda (alto, bajo) da «baja» (R128).
Si el control es esencial, R132 la sube a «media».
"""

import unittest

from app.conocimiento.base_conocimientos import VARIABLES
from app.conocimiento.base_reglas_criticidad import (
    CONTROLES_ESENCIALES, REGLAS_CRITICIDAD, verificar_reglas_criticidad,
)
from app.resultados.explicacion import formatear_regla
from app.inferencia.memoria import MemoriaTrabajo
from app.inferencia.motor import inferir

RESPALDOS = [c for c, v in VARIABLES.items() if v["area"] == "respaldos"]


def ejecutar(**cambios):
    respuestas = {c: "si" for c in VARIABLES}
    respuestas.update(cambios)
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas)
    return inferir(memoria)


class PruebasCriticidad(unittest.TestCase):

    def test_estructura(self):
        self.assertEqual(len(CONTROLES_ESENCIALES), 12)
        self.assertEqual(len(REGLAS_CRITICIDAD), 12)
        self.assertEqual(verificar_reglas_criticidad(), [])
        self.assertTrue(all(c in VARIABLES for c in CONTROLES_ESENCIALES))
        self.assertEqual({r["id"] for r in REGLAS_CRITICIDAD}, {"R132"})
        self.assertEqual(len({r["clave"] for r in REGLAS_CRITICIDAD}), 12)

    def test_formato_de_la_regla(self):
        regla = next(r for r in REGLAS_CRITICIDAD if r["clave"] == "R132:copia_datos_criticos")
        texto = formatear_regla(regla)
        self.assertIn("prioridad_copia_datos_criticos = «baja»", texto)
        self.assertIn("ENTONCES prioridad_copia_datos_criticos = «media»", texto)
        self.assertIn("PAWAR_2022", texto)

    def test_control_esencial_con_un_solo_no_sube_a_media(self):
        r = ejecutar(copia_datos_criticos="no")
        self.assertEqual(r.hechos["nivel_p_respaldos"], "bajo")
        self.assertEqual(r.prioridades, [{"control": "copia_datos_criticos", "area": "respaldos",
                                          "prioridad": "media"}])
        ids = [d.clave for d in r.disparos if d.etapa in ("prioridad", "criticidad")]
        self.assertEqual(ids, ["R128:copia_datos_criticos", "R132:copia_datos_criticos"])
        self.assertEqual(r.hechos["prioridad_copia_datos_criticos"], "media")

    def test_control_no_esencial_se_queda_en_baja(self):
        r = ejecutar(copia_bases_datos="no")
        self.assertEqual(r.prioridades[0]["prioridad"], "baja")
        self.assertNotIn("criticidad", [d.etapa for d in r.disparos])

    def test_no_baja_prioridades_que_ya_eran_altas_o_medias(self):
        # 12 «no» en respaldos: P = 83,5 (alto) → (alto, alto) = alta; R132 no se dispara.
        r = ejecutar(**{c: "no" for c in RESPALDOS})
        self.assertEqual({p["prioridad"] for p in r.prioridades}, {"alta"})
        self.assertNotIn("criticidad", [d.etapa for d in r.disparos])

    def test_no_duplica_la_entrada_de_prioridad(self):
        r = ejecutar(cortafuegos="no", copia_datos_criticos="no")
        controles = [p["control"] for p in r.prioridades]
        self.assertEqual(sorted(controles), ["copia_datos_criticos", "cortafuegos"])
        self.assertEqual({p["prioridad"] for p in r.prioridades}, {"media"})


if __name__ == "__main__":
    unittest.main()
