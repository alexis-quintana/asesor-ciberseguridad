"""Regla de criticidad de los controles esenciales (R132).

La prioridad de un hallazgo (R126–R131) depende del promedio de su área: si casi
todas las demás prácticas del área están bien, una carencia grave puede quedar en
prioridad «baja». Esta regla corrige ese efecto: un hallazgo de un control
ESENCIAL nunca queda por debajo de la prioridad «media».

Fuente: Pawar y Palivela (2022), marco LCCI.
- §4.2, p. 7: una pyme debe priorizar primero el nivel inicial de capas de defensa
  y ampliar la cobertura con el tiempo; los activos críticos son sobre todo
  información.
- §5.5–5.6, p. 11 (MOCCI nivel 1): primero las capas humana, de perímetro y de
  equipos (host/endpoint) y, cuando existan, los dispositivos y aplicaciones
  expuestos a Internet y los datos que manejan, «on priority».

ADAPTACIÓN DEL EQUIPO: la correspondencia entre esas capas y los controles del
cuestionario (CONTROLES_ESENCIALES) y el piso «media» son criterio del equipo;
Pawar y Palivela no definen una prioridad alta/media/baja ni este piso.

La regla es genérica: se escribe una vez y se expande a los controles esenciales
(R132:<control>). Se ejecuta en la etapa «criticidad», después de «prioridad».
"""

from __future__ import annotations

from app.conocimiento.base_conocimientos import FUENTES, VARIABLES

# Control -> capa de Pawar y Palivela (2022) a la que corresponde.
CONTROLES_ESENCIALES = {
    # Capa humana (§5.5-5.6, p. 11): formación contra phishing.
    "formacion_general": "capa humana",
    "formacion_phishing": "capa humana",
    # Perímetro físico y digital.
    "cortafuegos": "perímetro",
    "cortafuegos_verificado": "perímetro",
    # Equipos (host/endpoint).
    "parches_equipos": "equipos (endpoint)",
    "sistema_soportado": "equipos (endpoint)",
    # Dispositivos y aplicaciones expuestos a Internet, con prioridad.
    "dispositivo_publico": "expuestos a Internet",
    "aplicacion_publica": "expuestos a Internet",
    "mfa_publico": "expuestos a Internet",
    # Activo crítico (§4.2, p. 7): datos esenciales y su protección.
    "copia_datos_criticos": "activo crítico",
    "copia_aplicacion_critica": "activo crítico",
    "acceso_datos_criticos": "activo crítico",
}

_FUENTES = [{"id": "PAWAR_2022",
             "localizacion": "§4.2, p. 7 (priorizar el nivel inicial de capas y los activos críticos); "
                             "§5.5-5.6, p. 11 (MOCCI nivel 1)"}]

REGLA_CRITICIDAD_GENERICA = {
    "id": "R132",
    "etapa": "criticidad",
    "fuentes": _FUENTES,
    "tipo_respaldo": "fuente_con_adaptacion",
    "evidencia_del_articulo": (
        "Pawar y Palivela priorizan primero las capas humana, de perímetro y de equipos, "
        "lo expuesto a Internet y el activo crítico; la lista de controles y el piso "
        "«media» son criterio del equipo."),
    "validacion_experto": "pendiente",
}


def expandir():
    """Instancia R132 en cada control esencial (clave R132:<control>)."""
    concretas = []
    for control, capa in CONTROLES_ESENCIALES.items():
        area = VARIABLES[control]["area"]
        concretas.append({
            **REGLA_CRITICIDAD_GENERICA,
            "ambito": control,
            "clave": f"R132:{control}",
            "area": area,
            "si": [
                {"hecho": f"hallazgo_{control}", "operador": "igual", "valor": True},
                {"hecho": f"prioridad_{control}", "operador": "igual", "valor": "baja"},
            ],
            "entonces": {"tipo": "prioridad", "hecho": f"prioridad_{control}",
                         "valor": "media", "control": control, "area": area},
            "explicacion": (
                f"«{VARIABLES[control]['pregunta']}» es un control esencial ({capa}; "
                "Pawar y Palivela, 2022): su prioridad no baja de «media» aunque el "
                "promedio del área sea favorable."),
        })
    return concretas


REGLAS_CRITICIDAD = expandir()


def verificar_reglas_criticidad():
    """Comprobación estructural de la regla de criticidad (lista de errores)."""
    errores = []
    for control in CONTROLES_ESENCIALES:
        if control not in VARIABLES:
            errores.append(f"Control esencial desconocido: {control}")
    if not all(f["id"] in FUENTES and f["localizacion"] for f in _FUENTES):
        errores.append("R132: fuente o localización inválida")
    return errores
