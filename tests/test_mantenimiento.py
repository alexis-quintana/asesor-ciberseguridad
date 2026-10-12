# Pruebas del mantenimiento de reglas (lógica, sin Flask).

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.conocimiento import mantenimiento
from app.conocimiento.base_conocimientos import VARIABLES
from app.conocimiento.mantenimiento import Almacen, ErrorMantenimiento
from app.inferencia.memoria import MemoriaTrabajo
from app.inferencia.motor import inferir
from app.inferencia.priorizacion import lista_priorizada

FUENTE = {"fuente_id": "PAWAR_2022", "localizacion": "sección 4.2, p. 7"}


def respuestas(**cambios):
    datos = {c: "si" for c in VARIABLES}
    datos.update(cambios)
    return datos


def ejecutar(**cambios):
    memoria = MemoriaTrabajo()
    memoria.cargar_respuestas(respuestas(**cambios))
    return inferir(memoria)


class Base(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)
        self.ruta = Path(self.carpeta.name) / "mantenimiento.json"
        parche = mock.patch.dict(os.environ, {"ASESOR_DATOS": str(self.ruta)})
        parche.start()
        self.addCleanup(parche.stop)
        self.almacen = Almacen()

    def nueva_regla(self, **cambios):
        datos = dict(
            area="respaldos",
            condiciones=[{"hecho": "copia_fuera_sede", "operador": "igual", "valor": "no"},
                         {"hecho": "hallazgo_cuentas_individuales", "operador": "igual", "valor": "verdadero"}],
            texto="Revisar juntas las copias fuera de la sede y las cuentas compartidas.",
            prioridad="alta", evidencia="Prioriza los activos críticos de la empresa.", **FUENTE)
        datos.update(cambios)
        return self.almacen.agregar(**datos)


class PruebasSinCambios(Base):

    def test_sin_archivo_la_base_queda_igual(self):
        base = mantenimiento._base_completa()
        self.assertEqual([r["id"] for r in mantenimiento.reglas_vigentes()], [r["id"] for r in base])
        self.assertFalse(self.almacen.hay_cambios())
        self.assertFalse(self.ruta.exists())

    def test_la_base_tiene_132_reglas_distintas(self):
        ids = {r["id"] for r in mantenimiento._base_completa()}
        self.assertEqual(len(ids), 132)           # R001–R132
        self.assertEqual(mantenimiento.PRIMER_ID_NUEVO, 133)


class PruebasReglasExistentes(Base):

    def test_desactivar_quita_la_regla_del_motor(self):
        self.assertEqual(len(ejecutar(cuentas_individuales="no").hallazgos), 1)
        self.almacen.desactivar("R001", "Ya no se evalúa esta práctica")
        r = ejecutar(cuentas_individuales="no")
        self.assertEqual(r.hallazgos, [])
        self.assertNotIn("R001", [d.id for d in r.disparos])
        self.assertIn("R001", self.almacen.cargar()["desactivadas"])
        self.almacen.activar("R001")
        self.assertEqual(len(ejecutar(cuentas_individuales="no").hallazgos), 1)

    def test_desactivar_la_recomendacion_deja_el_hallazgo_sin_texto(self):
        self.almacen.desactivar("R002", "Texto en revisión")
        r = ejecutar(cuentas_individuales="no")
        self.assertEqual(len(r.hallazgos), 1)
        self.assertEqual(r.recomendaciones, {})
        self.assertEqual(lista_priorizada(r), [])          # sin texto no hay recomendación que mostrar

    def test_el_nucleo_no_se_puede_desactivar(self):
        for regla_id in ("R097", "R106", "R126", "R132", "R110"):
            with self.subTest(regla=regla_id), self.assertRaises(ErrorMantenimiento):
                self.almacen.desactivar(regla_id, "No debería permitirse")
        self.assertFalse(self.ruta.exists())

    def test_regla_inexistente(self):
        with self.assertRaises(ErrorMantenimiento):
            self.almacen.desactivar("R999", "No existe esa regla")

    def test_editar_el_texto_cambia_motor_lista_y_explicacion(self):
        self.almacen.editar("R002", {"texto": "Dar una cuenta propia a cada persona."})
        r = ejecutar(cuentas_individuales="no")
        self.assertEqual(r.recomendaciones, {"cuentas": ["Dar una cuenta propia a cada persona."]})
        self.assertEqual(lista_priorizada(r)[0]["recomendacion"], "Dar una cuenta propia a cada persona.")
        disparo = next(d for d in r.disparos if d.id == "R002")
        self.assertTrue(disparo.explicacion.endswith("Dar una cuenta propia a cada persona."))
        self.almacen.restablecer("R002")
        r = ejecutar(cuentas_individuales="no")
        self.assertEqual(r.recomendaciones, {"cuentas": ["Asignar una cuenta individual a cada empleado."]})

    def test_editar_fuente_y_estado_de_validacion(self):
        self.almacen.editar("R001", {"fuente_id": "PAWAR_2022", "localizacion": "sección 4.2, p. 7",
                                     "validacion_experto": "validada_por_fuente"})
        regla = next(r for r in mantenimiento.reglas_vigentes() if r["id"] == "R001")
        self.assertEqual(regla["fuentes"], [{"id": "PAWAR_2022", "localizacion": "sección 4.2, p. 7"}])
        self.assertEqual(regla["validacion_experto"], "validada_por_fuente")

    def test_ediciones_invalidas(self):
        for cambios in ({"texto": "no"}, {"fuente_id": "INVENTADA_2020", "localizacion": "p. 1"},
                        {"fuente_id": "PAWAR_2022", "localizacion": ""},
                        {"validacion_experto": "aprobada"}):
            with self.subTest(cambios=cambios), self.assertRaises(ErrorMantenimiento):
                self.almacen.editar("R002", cambios)
        with self.assertRaises(ErrorMantenimiento):
            self.almacen.editar("R001", {"texto": "Una regla de hallazgo no tiene texto"})
        with self.assertRaises(ErrorMantenimiento):
            self.almacen.editar("R106", {"explicacion": "Explicación nueva para la regla"})

    def test_no_guarda_ediciones_que_no_cambian_nada(self):
        original = next(r for r in mantenimiento._base_completa() if r["id"] == "R002")
        self.almacen.editar("R002", {"texto": original["entonces"]["texto"],
                                     "fuente_id": original["fuentes"][0]["id"],
                                     "localizacion": original["fuentes"][0]["localizacion"]})
        self.assertFalse(self.almacen.hay_cambios())


class PruebasReglasNuevas(Base):

    def test_regla_nueva_se_dispara_y_aparece_en_la_lista(self):
        self.assertEqual(self.nueva_regla(), "R133")
        r = ejecutar(copia_fuera_sede="no", cuentas_individuales="no")
        self.assertEqual(r.recomendaciones_adicionales,
                         [{"id": "R133", "area": "respaldos", "prioridad": "alta",
                           "texto": "Revisar juntas las copias fuera de la sede y las cuentas compartidas."}])
        lista = lista_priorizada(r)
        adicional = next(i for i in lista if i["adicional"])
        self.assertEqual((adicional["prioridad"], adicional["control"]), ("alta", "R133"))
        # Con prioridad alta se ordena antes de las recomendaciones de prioridad baja.
        self.assertEqual(lista[0]["control"], "R133")
        disparo = next(d for d in r.disparos if d.id == "R133")
        self.assertEqual(disparo.etapa, "recomendacion_adicional")
        self.assertEqual(disparo.observados, {"copia_fuera_sede": "no",
                                              "hallazgo_cuentas_individuales": True})

    def test_no_se_dispara_si_falta_una_condicion(self):
        self.nueva_regla()
        r = ejecutar(copia_fuera_sede="no")
        self.assertEqual(r.recomendaciones_adicionales, [])

    def test_identificadores_consecutivos_y_no_reutilizados(self):
        self.assertEqual(self.nueva_regla(), "R133")
        self.assertEqual(self.nueva_regla(texto="Segunda recomendación de prueba válida."), "R134")
        self.almacen.eliminar_nueva("R134")
        self.assertEqual(self.nueva_regla(texto="Tercera recomendación de prueba válida."), "R135")

    def test_rechaza_reglas_duplicadas(self):
        self.nueva_regla()
        with self.assertRaises(ErrorMantenimiento):
            self.nueva_regla()

    def test_validaciones(self):
        casos = {
            "hecho desconocido": dict(condiciones=[{"hecho": "p_cuentas", "operador": "mayor_que", "valor": "10"}]),
            "operador inválido": dict(condiciones=[{"hecho": "copia_fuera_sede", "operador": "parecido", "valor": "no"}]),
            "valor de respuesta inválido": dict(condiciones=[{"hecho": "copia_fuera_sede", "operador": "igual", "valor": "quizas"}]),
            "operador numérico sobre respuesta": dict(condiciones=[{"hecho": "copia_fuera_sede", "operador": "mayor_que", "valor": "no"}]),
            "entero fuera de rango": dict(condiciones=[{"hecho": "areas_riesgo_alto", "operador": "igual", "valor": "9"}]),
            "sin condiciones": dict(condiciones=[]),
            "demasiadas condiciones": dict(condiciones=[{"hecho": "copia_fuera_sede", "operador": "igual", "valor": "no"}] * 6),
            "área inválida": dict(area="fisica"),
            "prioridad inválida": dict(prioridad="urgente"),
            "texto vacío": dict(texto=" "),
            "sin localización": dict(localizacion=""),
            "fuente desconocida": dict(fuente_id="NO_EXISTE"),
            "sin evidencia": dict(evidencia=""),
            "estado inválido": dict(validacion_experto="aprobada"),
        }
        for nombre, cambios in casos.items():
            with self.subTest(caso=nombre), self.assertRaises(ErrorMantenimiento):
                self.nueva_regla(**cambios)
        self.assertFalse(self.ruta.exists())

    def test_valores_de_tipos_distintos(self):
        self.nueva_regla(condiciones=[
            {"hecho": "nivel_p_cuentas", "operador": "en", "valor": "medio, alto"},
            {"hecho": "areas_riesgo_alto", "operador": "mayor_o_igual", "valor": "1"},
            {"hecho": "hallazgo_mfa_publico", "operador": "igual", "valor": "falso"}])
        regla = self.almacen.cargar()["reglas_nuevas"][0]
        self.assertEqual([c["valor"] for c in regla["si"]], [["medio", "alto"], 1, False])

    def test_editar_y_eliminar_una_regla_nueva(self):
        self.nueva_regla()
        self.almacen.editar("R133", {"texto": "Texto corregido de la recomendación.", "prioridad": "baja"})
        regla = self.almacen.cargar()["reglas_nuevas"][0]
        self.assertEqual((regla["entonces"]["texto"], regla["entonces"]["prioridad"]),
                         ("Texto corregido de la recomendación.", "baja"))
        with self.assertRaises(ErrorMantenimiento):
            self.almacen.editar("R133", {"prioridad": "urgente"})
        self.almacen.eliminar_nueva("R133")
        self.assertEqual(self.almacen.cargar()["reglas_nuevas"], [])
        with self.assertRaises(ErrorMantenimiento):                  # las de la base solo se desactivan
            self.almacen.eliminar_nueva("R001")

    def test_las_reglas_nuevas_solo_concluyen_recomendaciones(self):
        self.nueva_regla()
        (regla,) = self.almacen.cargar()["reglas_nuevas"]
        self.assertEqual(regla["entonces"]["tipo"], "recomendacion_adicional")
        self.assertEqual(regla["etapa"], "recomendacion_adicional")
        self.assertEqual(regla["tipo_respaldo"], "agregada_por_administrador")
        self.assertEqual(regla["fuentes"], [{"id": "PAWAR_2022", "localizacion": "sección 4.2, p. 7"}])


class PruebasPersistencia(Base):

    def test_historial_en_orden_inverso(self):
        self.almacen.desactivar("R001", "Primer cambio de prueba")
        self.nueva_regla()
        self.almacen.activar("R001")
        acciones = [h["accion"] for h in self.almacen.historial()]
        self.assertEqual(acciones, ["activar", "agregar", "desactivar"])
        self.assertTrue(all(h["fecha"] for h in self.almacen.historial()))

    def test_el_archivo_es_json_valido_y_no_deja_temporales(self):
        self.nueva_regla()
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(datos["siguiente"], 134)
        self.assertEqual([p.name for p in self.ruta.parent.iterdir()], ["mantenimiento.json"])

    def test_archivo_danado_no_rompe_el_motor(self):
        self.ruta.write_text("{ esto no es json", encoding="utf-8")
        with self.assertRaises(ErrorMantenimiento):
            self.almacen.cargar()
        datos, error = self.almacen.cargar_seguro()
        self.assertIsNotNone(error)
        self.assertEqual(len(ejecutar(cuentas_individuales="no").hallazgos), 1)
        with self.assertRaises(ErrorMantenimiento):
            self.almacen.desactivar("R001", "No se debe sobrescribir un archivo dañado")

    def test_listar_reglas_marca_estados(self):
        self.almacen.desactivar("R001", "Estado de prueba válido")
        self.almacen.editar("R002", {"texto": "Texto editado de prueba válido."})
        self.nueva_regla()
        filas = {f["id"]: f for f in mantenimiento.listar_reglas()}
        self.assertEqual(len({f for f in filas}), len(filas))
        self.assertTrue(filas["R001"]["desactivada"])
        self.assertTrue(filas["R002"]["editada"])
        self.assertEqual(filas["R002"]["regla"]["entonces"]["texto"], "Texto editado de prueba válido.")
        self.assertTrue(filas["R133"]["es_nueva"])
        self.assertFalse(filas["R106"]["desactivable"])
        self.assertTrue(filas["R003"]["desactivable"])
        self.assertEqual(len(filas), 133)


class PruebasHechos(unittest.TestCase):

    def test_hechos_permitidos(self):
        hechos = mantenimiento.hechos_permitidos()
        self.assertIn("mfa_publico", hechos)
        self.assertIn("hallazgo_mfa_publico", hechos)
        self.assertIn("nivel_p_redes", hechos)
        self.assertEqual(hechos["desconocidas_cuentas"]["rango"], (0, 12))
        self.assertNotIn("i100_cuentas", hechos)             # los de la extensión no se permiten
        self.assertNotIn("riesgo_global", hechos)


if __name__ == "__main__":
    unittest.main()
