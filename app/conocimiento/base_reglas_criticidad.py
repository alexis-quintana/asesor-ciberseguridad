# Regla de criticidad de los controles esenciales (R132).

from __future__ import annotations

from app.conocimiento.base_conocimientos import FUENTES, VARIABLES

# Control -> capa de Pawar y Palivela (2022) a la que corresponde.
CONTROLES_ESENCIALES = {
    # Capa humana (sección 5.5-5.6, p. 11): formación contra phishing.
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
    # Activo crítico (sección 4.2, p. 7): datos esenciales y su protección.
    "copia_datos_criticos": "activo crítico",
    "copia_aplicacion_critica": "activo crítico",
    "acceso_datos_criticos": "activo crítico",
}

_FUENTES = [{"id": "PAWAR_2022",
             "localizacion": "sección 4.2, p. 7 (priorizar el nivel inicial de capas y los activos críticos); "
                             "sección 5.5-5.6, p. 11 (MOCCI nivel 1)"}]

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
    errores = []
    for control in CONTROLES_ESENCIALES:
        if control not in VARIABLES:
            errores.append(f"Control esencial desconocido: {control}")
    if not all(f["id"] in FUENTES and f["localizacion"] for f in _FUENTES):
        errores.append("R132: fuente o localización inválida")
    return errores
