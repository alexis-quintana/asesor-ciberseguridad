"""Mantenimiento de la base de conocimientos (módulo de actualización de conocimientos).

Permite que una persona autorizada actualice las reglas sin editar el código
cuando cambie un criterio o aparezca conocimiento nuevo:

- editar el texto de una recomendación, la explicación, la evidencia, la fuente y
  el estado de validación de una regla existente;
- desactivar (y volver a activar) reglas de las etapas «riesgo_parcial»,
  «recomendacion» y «verificacion»;
- agregar reglas nuevas de recomendación sobre hechos ya definidos
  (etapa «recomendacion_adicional»);
- consultar el historial de cambios.

La base original (base_conocimientos.py y compañía) NO se modifica: los cambios se
guardan aparte, en un archivo JSON, y se aplican sobre ella cada vez que el motor
infiere (reglas_vigentes). Así el motor, la lista priorizada, la explicación y el
reporte usan siempre la misma versión de las reglas.

Reglas del módulo:
- Toda regla nueva debe citar una de las fuentes registradas con su localización
  (regla del proyecto: «toda regla cita fuente»).
- Las reglas del núcleo del modelo (niveles de riesgo, riesgo global, prioridad,
  criticidad y la extensión de impacto) no se pueden desactivar ni cambiar de
  condición, porque el resultado depende de ellas; solo se puede ajustar su
  evidencia, fuente y estado de validación.
- Las reglas nuevas solo concluyen recomendaciones: no producen hechos que otras
  reglas consuman, de modo que no pueden crear conflictos ni ciclos.

Fuente: componentes de un sistema experto, entre ellos la actualización del
conocimiento — Sesión 12 del curso (Representación del Conocimiento) y Sihwi et al.
(2016), §II.A–C (adquisición, representación y validación del conocimiento).
Los controles de validación (identificadores, fuentes, hechos y operadores) siguen
a verificar_base() de base_conocimientos.py. Solo biblioteca estándar.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from datetime import datetime
from pathlib import Path

from app.conocimiento.base_conocimientos import FUENTES, REGLAS, RESPUESTAS, VARIABLES

RUTA_DEFECTO = Path(__file__).resolve().parents[2] / "datos" / "mantenimiento.json"

ETAPAS_DESACTIVABLES = ("riesgo_parcial", "recomendacion", "verificacion")
ETAPA_NUEVAS = "recomendacion_adicional"
PRIORIDADES = ("alta", "media", "baja")
ESTADOS_VALIDACION = ("pendiente", "validada_por_fuente", "validada_por_experto")
AREAS = tuple(dict.fromkeys(v["area"] for v in VARIABLES.values()))
PRIMER_ID_NUEVO = 133          # R001–R132 son de la base
MAX_REGLAS_NUEVAS = 100
MAX_CONDICIONES = 5
MAX_HISTORIAL = 500
CAMPOS_EDITABLES = ("texto", "explicacion", "evidencia_del_articulo", "validacion_experto", "fuentes")


class ErrorMantenimiento(ValueError):
    """Dato inválido o cambio no permitido en el mantenimiento de reglas."""


# --------------------------------------------------------------------------- hechos
def hechos_permitidos():
    """Hechos que una regla nueva puede usar en sus condiciones.

    Devuelve {hecho: {"tipo", "valores" o rango, "descripcion"}}. Son las respuestas
    del cuestionario, los hallazgos y los hechos derivados que existen antes de la
    etapa «recomendacion_adicional» (no los de la extensión de impacto).
    """
    hechos = {}
    for clave, v in VARIABLES.items():
        hechos[clave] = {"tipo": "respuesta", "valores": RESPUESTAS,
                         "descripcion": v["pregunta"]}
    for clave, v in VARIABLES.items():
        hechos[f"hallazgo_{clave}"] = {"tipo": "booleano", "valores": (True, False),
                                       "descripcion": f"Hallazgo de «{v['pregunta']}»"}
    for area in AREAS:
        hechos[f"nivel_p_{area}"] = {"tipo": "nivel", "valores": ("bajo", "medio", "alto"),
                                     "descripcion": f"Nivel de riesgo del área {area}"}
    hechos["areas_riesgo_alto"] = {"tipo": "entero", "rango": (0, len(AREAS)),
                                   "descripcion": "Número de áreas con riesgo alto"}
    hechos["areas_riesgo_medio"] = {"tipo": "entero", "rango": (0, len(AREAS)),
                                    "descripcion": "Número de áreas con riesgo medio"}
    hechos["respuestas_desconocidas"] = {"tipo": "entero", "rango": (0, len(VARIABLES)),
                                         "descripcion": "Respuestas «no sé» en todo el cuestionario"}
    for area in AREAS:
        n = sum(v["area"] == area for v in VARIABLES.values())
        hechos[f"desconocidas_{area}"] = {"tipo": "entero", "rango": (0, n),
                                          "descripcion": f"Respuestas «no sé» del área {area}"}
    return hechos


def _operadores():
    from app.inferencia.motor import OPERADORES
    return OPERADORES


def _convertir_valor(hecho, operador, texto, info):
    """Convierte el texto de un formulario al valor tipado de la condición."""
    tipo = info["tipo"]
    if operador == "en":
        partes = [p.strip() for p in str(texto).split(",") if p.strip()]
        if not partes:
            raise ErrorMantenimiento(f"«{hecho}»: indique al menos un valor para «en».")
        return [_convertir_valor(hecho, "igual", p, info) for p in partes]
    if tipo == "booleano":
        valor = str(texto).strip().lower()
        if valor in ("verdadero", "true", "1", "si", "sí"):
            return True
        if valor in ("falso", "false", "0", "no"):
            return False
        raise ErrorMantenimiento(f"«{hecho}»: use verdadero o falso.")
    if tipo == "entero":
        try:
            valor = int(str(texto).strip())
        except ValueError:
            raise ErrorMantenimiento(f"«{hecho}»: el valor debe ser un número entero.") from None
        minimo, maximo = info["rango"]
        if not minimo <= valor <= maximo:
            raise ErrorMantenimiento(f"«{hecho}»: el valor debe estar entre {minimo} y {maximo}.")
        return valor
    valor = str(texto).strip()
    if valor not in info["valores"]:
        raise ErrorMantenimiento(
            f"«{hecho}»: valor «{valor}» no permitido; use {', '.join(map(str, info['valores']))}.")
    return valor


def _normalizar_condiciones(condiciones):
    """Valida y normaliza la lista de condiciones; devuelve la lista limpia."""
    permitidos = hechos_permitidos()
    operadores = _operadores()
    if not isinstance(condiciones, (list, tuple)) or not condiciones:
        raise ErrorMantenimiento("La regla necesita al menos una condición.")
    if len(condiciones) > MAX_CONDICIONES:
        raise ErrorMantenimiento(f"Máximo {MAX_CONDICIONES} condiciones por regla.")
    limpias = []
    for c in condiciones:
        hecho, operador, valor = c.get("hecho"), c.get("operador"), c.get("valor")
        if hecho not in permitidos:
            raise ErrorMantenimiento(f"Hecho no permitido en una condición: {hecho!r}.")
        if operador not in operadores:
            raise ErrorMantenimiento(f"Operador no permitido: {operador!r}.")
        info = permitidos[hecho]
        if info["tipo"] in ("respuesta", "booleano", "nivel") and operador not in ("igual", "en"):
            raise ErrorMantenimiento(f"«{hecho}» solo admite los operadores «igual» y «en».")
        if isinstance(valor, str) or not isinstance(valor, (list, bool, int)):
            valor = _convertir_valor(hecho, operador, valor, info)
        elif operador == "en" and not isinstance(valor, list):
            valor = [valor]
        limpias.append({"hecho": hecho, "operador": operador, "valor": valor})
    return limpias


def _validar_fuente(fuente_id, localizacion):
    if fuente_id not in FUENTES:
        raise ErrorMantenimiento(f"Fuente desconocida: {fuente_id!r}.")
    localizacion = (localizacion or "").strip()
    if len(localizacion) < 3:
        raise ErrorMantenimiento("Indique la sección o página de la fuente (localización).")
    if len(localizacion) > 200:
        raise ErrorMantenimiento("La localización de la fuente es demasiado larga.")
    return [{"id": fuente_id, "localizacion": localizacion}]


def _validar_texto(nombre, texto, minimo, maximo):
    texto = " ".join(str(texto or "").split())
    if not minimo <= len(texto) <= maximo:
        raise ErrorMantenimiento(f"{nombre}: debe tener entre {minimo} y {maximo} caracteres.")
    return texto


def _firma(condiciones, texto):
    return json.dumps([condiciones, texto], sort_keys=True, ensure_ascii=False)


# --------------------------------------------------------------------------- almacén
class Almacen:
    """Archivo JSON con los cambios del mantenimiento (se crea al primer cambio)."""

    def __init__(self, ruta=None):
        self.ruta = Path(ruta) if ruta else Path(os.environ.get("ASESOR_DATOS") or RUTA_DEFECTO)

    # -- lectura
    @staticmethod
    def _vacio():
        return {"version": 1, "siguiente": PRIMER_ID_NUEVO, "desactivadas": [],
                "ediciones": {}, "reglas_nuevas": [], "historial": []}

    def cargar(self):
        """Lee el archivo. Si no existe devuelve datos vacíos; si está dañado, ErrorMantenimiento."""
        datos = self._vacio()
        if not self.ruta.exists():
            return datos
        try:
            leidos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ErrorMantenimiento(f"No se pudo leer {self.ruta.name}: {error}") from None
        if not isinstance(leidos, dict):
            raise ErrorMantenimiento(f"{self.ruta.name} no tiene el formato esperado.")
        for clave in datos:
            if clave in leidos and isinstance(leidos[clave], type(datos[clave])):
                datos[clave] = leidos[clave]
        return datos

    def cargar_seguro(self):
        """Como cargar(), pero un archivo dañado se ignora; devuelve (datos, error o None)."""
        try:
            return self.cargar(), None
        except ErrorMantenimiento as error:
            return self._vacio(), str(error)

    def _guardar(self, datos):
        datos["historial"] = datos["historial"][-MAX_HISTORIAL:]
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporal = tempfile.mkstemp(dir=self.ruta.parent, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
            os.replace(temporal, self.ruta)       # escritura atómica
        except BaseException:
            if os.path.exists(temporal):
                os.unlink(temporal)
            raise

    @staticmethod
    def _anotar(datos, accion, regla, detalle=""):
        datos["historial"].append({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "accion": accion, "regla": regla, "detalle": detalle,
        })

    # -- consultas
    def historial(self):
        """Cambios registrados, el más reciente primero."""
        return list(reversed(self.cargar_seguro()[0]["historial"]))

    def hay_cambios(self):
        datos = self.cargar_seguro()[0]
        return bool(datos["desactivadas"] or datos["ediciones"] or datos["reglas_nuevas"])

    # -- cambios sobre reglas de la base
    def _regla_base(self, regla_id):
        for regla in _base_completa():
            if regla["id"] == regla_id:
                return regla
        raise ErrorMantenimiento(f"No existe la regla {regla_id}.")

    def desactivar(self, regla_id, motivo):
        """Desactiva una regla de la base (solo etapas desactivables)."""
        regla = self._regla_base(regla_id)
        if regla["etapa"] not in ETAPAS_DESACTIVABLES:
            raise ErrorMantenimiento(
                f"{regla_id} pertenece al núcleo del modelo de riesgo y no se puede desactivar.")
        motivo = _validar_texto("Motivo", motivo, 5, 300)
        datos = self.cargar()
        if regla_id not in datos["desactivadas"]:
            datos["desactivadas"].append(regla_id)
            self._anotar(datos, "desactivar", regla_id, motivo)
            self._guardar(datos)

    def activar(self, regla_id):
        datos = self.cargar()
        if regla_id in datos["desactivadas"]:
            datos["desactivadas"].remove(regla_id)
            self._anotar(datos, "activar", regla_id)
            self._guardar(datos)

    def editar(self, regla_id, cambios):
        """Edita campos permitidos de una regla de la base o de una regla nueva.

        «cambios» puede traer: texto, explicacion, evidencia_del_articulo,
        validacion_experto y fuente_id + localizacion.
        """
        datos = self.cargar()
        nueva = next((r for r in datos["reglas_nuevas"] if r["id"] == regla_id), None)
        if nueva is not None:
            return self._editar_nueva(datos, nueva, cambios)
        regla = self._regla_base(regla_id)
        edicion = dict(datos["ediciones"].get(regla_id, {}))
        vigente = _aplicar_edicion(regla, edicion)
        if "texto" in cambios:
            if regla["etapa"] != "recomendacion":
                raise ErrorMantenimiento(f"{regla_id} no es una regla de recomendación.")
            edicion["texto"] = _validar_texto("Texto de la recomendación", cambios["texto"], 5, 300)
            # Mantiene la explicación sincronizada si terminaba con el texto anterior.
            anterior = vigente["entonces"]["texto"]
            if "explicacion" not in cambios and vigente["explicacion"].endswith(anterior):
                edicion["explicacion"] = vigente["explicacion"][:-len(anterior)] + edicion["texto"]
        if "explicacion" in cambios:
            if "ambito" in regla:
                raise ErrorMantenimiento(
                    f"{regla_id} es una regla genérica: su explicación se genera por área.")
            edicion["explicacion"] = _validar_texto("Explicación", cambios["explicacion"], 5, 500)
        if "evidencia_del_articulo" in cambios:
            edicion["evidencia_del_articulo"] = _validar_texto(
                "Evidencia", cambios["evidencia_del_articulo"], 5, 500)
        if "validacion_experto" in cambios:
            if cambios["validacion_experto"] not in ESTADOS_VALIDACION:
                raise ErrorMantenimiento("Estado de validación no permitido.")
            edicion["validacion_experto"] = cambios["validacion_experto"]
        if "fuente_id" in cambios or "localizacion" in cambios:
            edicion["fuentes"] = _validar_fuente(cambios.get("fuente_id"), cambios.get("localizacion"))
        # Solo se guardan los campos que difieren de la versión original.
        original = {"texto": regla["entonces"].get("texto"), "explicacion": regla["explicacion"],
                    "evidencia_del_articulo": regla["evidencia_del_articulo"],
                    "validacion_experto": regla["validacion_experto"], "fuentes": regla["fuentes"]}
        edicion = {k: v for k, v in edicion.items() if original.get(k) != v}
        if edicion == datos["ediciones"].get(regla_id, {}):
            return
        if edicion:
            datos["ediciones"][regla_id] = edicion
        else:
            datos["ediciones"].pop(regla_id, None)
        self._anotar(datos, "editar", regla_id, ", ".join(sorted(k for k in cambios)))
        self._guardar(datos)

    def restablecer(self, regla_id):
        """Quita las ediciones de una regla de la base y la vuelve a su versión original."""
        self._regla_base(regla_id)
        datos = self.cargar()
        if regla_id in datos["ediciones"]:
            del datos["ediciones"][regla_id]
            self._anotar(datos, "restablecer", regla_id)
            self._guardar(datos)

    # -- reglas nuevas
    def agregar(self, area, condiciones, texto, prioridad, fuente_id, localizacion,
                evidencia, validacion_experto="pendiente", explicacion=""):
        """Agrega una regla nueva de recomendación. Devuelve su identificador (R133, …)."""
        datos = self.cargar()
        if len(datos["reglas_nuevas"]) >= MAX_REGLAS_NUEVAS:
            raise ErrorMantenimiento(f"Se alcanzó el máximo de {MAX_REGLAS_NUEVAS} reglas nuevas.")
        regla = _construir_nueva(
            f"R{datos['siguiente']}", area, condiciones, texto, prioridad,
            fuente_id, localizacion, evidencia, validacion_experto, explicacion)
        firma = _firma(regla["si"], regla["entonces"]["texto"])
        if any(_firma(r["si"], r["entonces"]["texto"]) == firma for r in datos["reglas_nuevas"]):
            raise ErrorMantenimiento("Ya existe una regla nueva idéntica (mismas condiciones y texto).")
        datos["reglas_nuevas"].append(regla)
        datos["siguiente"] += 1
        self._anotar(datos, "agregar", regla["id"], regla["entonces"]["texto"])
        self._guardar(datos)
        return regla["id"]

    def _editar_nueva(self, datos, nueva, cambios):
        area = cambios.get("area", nueva["area"])
        fuente = nueva["fuentes"][0]
        reconstruida = _construir_nueva(
            nueva["id"], area,
            cambios.get("condiciones", nueva["si"]),
            cambios.get("texto", nueva["entonces"]["texto"]),
            cambios.get("prioridad", nueva["entonces"]["prioridad"]),
            cambios.get("fuente_id", fuente["id"]),
            cambios.get("localizacion", fuente["localizacion"]),
            cambios.get("evidencia_del_articulo", nueva["evidencia_del_articulo"]),
            cambios.get("validacion_experto", nueva["validacion_experto"]),
            cambios.get("explicacion", nueva["explicacion"]))
        indice = datos["reglas_nuevas"].index(nueva)
        datos["reglas_nuevas"][indice] = reconstruida
        self._anotar(datos, "editar", nueva["id"], ", ".join(sorted(cambios)))
        self._guardar(datos)

    def eliminar_nueva(self, regla_id):
        datos = self.cargar()
        antes = len(datos["reglas_nuevas"])
        datos["reglas_nuevas"] = [r for r in datos["reglas_nuevas"] if r["id"] != regla_id]
        if len(datos["reglas_nuevas"]) == antes:
            raise ErrorMantenimiento(
                f"{regla_id} no es una regla nueva: las reglas de la base solo se desactivan.")
        self._anotar(datos, "eliminar", regla_id)
        self._guardar(datos)


# --------------------------------------------------------------------------- reglas
def _construir_nueva(regla_id, area, condiciones, texto, prioridad, fuente_id,
                     localizacion, evidencia, validacion_experto, explicacion):
    if area not in AREAS:
        raise ErrorMantenimiento(f"Área no válida: {area!r}.")
    if prioridad not in PRIORIDADES:
        raise ErrorMantenimiento("La prioridad debe ser alta, media o baja.")
    if validacion_experto not in ESTADOS_VALIDACION:
        raise ErrorMantenimiento("Estado de validación no permitido.")
    condiciones = _normalizar_condiciones(condiciones)
    texto = _validar_texto("Texto de la recomendación", texto, 5, 300)
    evidencia = _validar_texto("Evidencia", evidencia, 5, 500)
    fuentes = _validar_fuente(fuente_id, localizacion)
    explicacion = " ".join(str(explicacion or "").split()) or (
        f"Se cumplen las condiciones de la regla {regla_id}: {texto}")
    if len(explicacion) > 500:
        raise ErrorMantenimiento("La explicación es demasiado larga.")
    return {
        "id": regla_id,
        "area": area,
        "etapa": ETAPA_NUEVAS,
        "si": condiciones,
        "entonces": {"tipo": "recomendacion_adicional", "texto": texto,
                     "area": area, "prioridad": prioridad},
        "explicacion": explicacion,
        "fuentes": fuentes,
        "tipo_respaldo": "agregada_por_administrador",
        "evidencia_del_articulo": evidencia,
        "validacion_experto": validacion_experto,
        "origen": "administrador",
    }


def _aplicar_edicion(regla, edicion):
    """Devuelve una copia de la regla con las ediciones permitidas aplicadas."""
    copia = {**regla, "entonces": dict(regla["entonces"]), "fuentes": [dict(f) for f in regla["fuentes"]]}
    if not edicion:
        return copia
    if "texto" in edicion and regla["etapa"] == "recomendacion":
        copia["entonces"]["texto"] = edicion["texto"]
    if "explicacion" in edicion and "ambito" not in regla:
        copia["explicacion"] = edicion["explicacion"]
    if "evidencia_del_articulo" in edicion:
        copia["evidencia_del_articulo"] = edicion["evidencia_del_articulo"]
    if edicion.get("validacion_experto") in ESTADOS_VALIDACION:
        copia["validacion_experto"] = edicion["validacion_experto"]
    if "fuentes" in edicion:
        copia["fuentes"] = [dict(f) for f in edicion["fuentes"]]
    copia["editada"] = True
    return copia


def _base_completa():
    from app.conocimiento.base_reglas_criticidad import REGLAS_CRITICIDAD
    from app.conocimiento.base_reglas_prioridad import REGLAS_PRIORIDAD
    from app.conocimiento.base_reglas_riesgo import REGLAS_RIESGO
    return list(REGLAS) + list(REGLAS_RIESGO) + list(REGLAS_PRIORIDAD) + list(REGLAS_CRITICIDAD)


def reglas_vigentes(reglas_base=None, almacen=None):
    """Reglas que usa el motor: la base, con los cambios del mantenimiento aplicados.

    Quita las reglas desactivadas, aplica las ediciones y agrega las reglas nuevas.
    Sin archivo de mantenimiento devuelve la base tal cual. Un archivo dañado se
    ignora (se usa la base original) para no impedir el funcionamiento del asesor.
    """
    base = _base_completa() if reglas_base is None else list(reglas_base)
    datos, _error = (almacen or Almacen()).cargar_seguro()
    desactivadas = set(datos["desactivadas"])
    resultado = []
    for regla in base:
        if regla["id"] in desactivadas and regla["etapa"] in ETAPAS_DESACTIVABLES:
            continue
        edicion = datos["ediciones"].get(regla["id"])
        resultado.append(_aplicar_edicion(regla, edicion) if edicion else regla)
    resultado.extend(datos["reglas_nuevas"])
    return resultado


def listar_reglas(almacen=None):
    """Filas para el panel: una por identificador de regla (las genéricas una sola vez)."""
    almacen = almacen or Almacen()
    datos, _ = almacen.cargar_seguro()
    desactivadas = set(datos["desactivadas"])
    nuevas = {r["id"] for r in datos["reglas_nuevas"]}
    filas, vistos = [], set()
    for regla in reglas_vigentes(_base_completa(), almacen=_SinCambios()) + datos["reglas_nuevas"]:
        if regla["id"] in vistos:
            continue
        vistos.add(regla["id"])
        filas.append({
            "id": regla["id"], "etapa": regla["etapa"], "area": regla["area"],
            "regla": regla,
            "es_nueva": regla["id"] in nuevas,
            "desactivada": False,
            "desactivable": regla["etapa"] in ETAPAS_DESACTIVABLES,
            "editada": regla["id"] in datos["ediciones"],
        })
    por_id = {f["id"]: f for f in filas}
    for regla_id in desactivadas:
        if regla_id in por_id:
            por_id[regla_id]["desactivada"] = True
    for fila in filas:
        edit = datos["ediciones"].get(fila["id"])
        if edit and not fila["es_nueva"]:
            fila["regla"] = _aplicar_edicion(fila["regla"], edit)
    return filas


class _SinCambios(Almacen):
    """Almacén vacío: sirve para listar la base original sin aplicar cambios."""

    def __init__(self):
        super().__init__(ruta=Path(os.devnull))

    def cargar_seguro(self):
        return self._vacio(), None


def siguiente_id_nuevo(almacen=None):
    return f"R{(almacen or Almacen()).cargar_seguro()[0]['siguiente']}"


def numero_de_regla(regla_id):
    return int(re.sub(r"\D", "", regla_id))


class ClaveAdmin:
    """Clave del administrador, guardada como resumen PBKDF2 (nunca en texto plano).

    Se crea desde la propia página la primera vez que se entra a «Administrar
    reglas» y se guarda junto al archivo de cambios (admin_clave.json). Fuente:
    OWASP, Password Storage Cheat Sheet (PBKDF2-HMAC-SHA256 con sal aleatoria y
    muchas iteraciones); implementación con la biblioteca estándar (hashlib).
    """

    ITERACIONES = 310_000
    LARGO_MINIMO = 8

    def __init__(self, ruta=None):
        base = Path(ruta) if ruta else Path(os.environ.get("ASESOR_DATOS") or RUTA_DEFECTO)
        self.ruta = base.parent / "admin_clave.json"

    @staticmethod
    def _resumen(clave, sal, iteraciones):
        return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, iteraciones)

    def existe(self):
        return self.ruta.exists()

    def establecer(self, clave, confirmacion):
        if self.existe():
            raise ErrorMantenimiento("Ya existe una clave de administrador.")
        if len(clave) < self.LARGO_MINIMO:
            raise ErrorMantenimiento(f"La clave debe tener al menos {self.LARGO_MINIMO} caracteres.")
        if clave != confirmacion:
            raise ErrorMantenimiento("La clave y su confirmación no coinciden.")
        sal = secrets.token_bytes(16)
        datos = {"algoritmo": "pbkdf2_sha256", "iteraciones": self.ITERACIONES,
                 "sal": sal.hex(), "resumen": self._resumen(clave, sal, self.ITERACIONES).hex()}
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporal = tempfile.mkstemp(dir=self.ruta.parent, suffix=".tmp")
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo)
        os.replace(temporal, self.ruta)

    def verificar(self, clave):
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            esperado = bytes.fromhex(datos["resumen"])
            calculado = self._resumen(clave, bytes.fromhex(datos["sal"]), int(datos["iteraciones"]))
        except (OSError, ValueError, KeyError, TypeError):
            return False
        return hmac.compare_digest(esperado, calculado)
