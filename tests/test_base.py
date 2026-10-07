"""Pruebas de la base de conocimientos."""

import unittest

from asesor.base_conocimientos import REGLAS, VARIABLES, verificar_base


class PruebasBase(unittest.TestCase):

    def test_verificar_base_sin_errores(self):
        self.assertEqual(verificar_base(), [])

    def test_cantidades(self):
        self.assertEqual(len(VARIABLES), 48)
        self.assertEqual(len(REGLAS), 105)


if __name__ == "__main__":
    unittest.main()
