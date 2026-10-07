"""Base de conocimientos preliminar: Asesor ciberseguridad para pequeñas empresas.

Contiene 48 comprobaciones de prácticas, 48 reglas de recomendación y 9 reglas
de síntesis/verificación (105 reglas en total): R001–R096 por práctica,
R097–R101 de riesgo global por conteo de áreas con riesgo alto y R102–R105 de
verificación de respuestas «no sé». No contiene motor de inferencia.

Todas las reglas operativas son adaptaciones del equipo basadas en antecedentes;
ninguna se atribuye literalmente a sus autores. La aplicación de niveles de
riesgo, la pertinencia de cada control y las reglas globales deben ser validadas
por el especialista antes de presentar diagnósticos.
"""

from __future__ import annotations

from collections import Counter


RESPUESTAS = ("si", "no", "parcialmente", "no_se")

# Las páginas son las páginas impresas en cada artículo, salvo que se indique
# expresamente «página PDF». Conservamos títulos completos para trazabilidad.
FUENTES = {
    "FAEHNRICH_2022": {
        "autores": "Nicolas Fähnrich y Heiko Roßnagel",
        "anio": 2022,
        "titulo": "Online tool for matching company demands with IT-security offerings",
        "archivo": "proceedings-12.pdf",
    },
    "SOLIC_2015": {
        "autores": "Kresimir Solic, Hrvoje Ocevcic y Marin Golub",
        "anio": 2015,
        "titulo": "The information systems' security level assessment model based on an ontology and evidential reasoning approach",
        "archivo": "1-s2.0-S0167404815001212-main.pdf",
    },
    "PAWAR_2022": {
        "autores": "Shekhar Pawar y Hemant Palivela",
        "anio": 2022,
        "titulo": "LCCI: A framework for least cybersecurity controls to be implemented for small and medium enterprises (SMEs)",
        "archivo": "LCCI A framework for least cybersecurity controls to be implemented for SMEs.pdf",
    },
    "SIHWI_2016": {
        "autores": "Sari Widya Sihwi, Ferry Andriyanto y Rini Anggrainingsih",
        "anio": 2016,
        "titulo": "An expert system for risk assessment of information system security based on ISO 27002",
        "archivo": "2016-sari-rini-ickea-expertsystem-iso27001.pdf",
    },
    "VITKUS_2019": {
        "autores": "Donatas Vitkus, Zilvinas Steckevicius, Nikolaj Goranin, Diana Kalibatiene y Antanas Cenys",
        "anio": 2019,
        "titulo": "Automated Expert System Knowledge Base Development Method for Information Security Risk Analysis",
        "archivo": "idzitac,+Journal+manager,+08.pdf",
    },
    "KLIMES_2015": {
        "autores": "Cyril Klimeš y Jiří Bartoš",
        "anio": 2015,
        "titulo": "IT/IS security management with uncertain information",
        "archivo": "paper.pdf",
    },
    "HIBSHI_2016": {
        "autores": "Hanan Hibshi, Travis D. Breaux y Christian Wagner",
        "anio": 2016,
        "titulo": "Improving Security Requirements Adequacy: An Interval Type 2 Fuzzy Logic Security Assessment System",
        "archivo": "HBW16.pdf",
    },
    "KOEZE_2017": {
        "autores": "Ruben Koeze",
        "anio": 2017,
        "titulo": "Designing a cyber risk assessment tool for small to medium enterprises",
        "archivo": "Thesis_Final_Ruben_Koeze_4107810.pdf",
    },
    "GHANEM_2023": {
        "autores": "Mohamed Chahine Ghanem, Thomas M. Chen, Mohamed Amine Ferrag y Mohyi E. Kettouche",
        "anio": 2023,
        "titulo": "ESASCF: Expertise Extraction, Generalization and Reply Framework for Optimized Automation of Network Security Compliance",
        "archivo": "2307.10967v2.pdf",
    },
    "CHIDUKWANI_2026": {
        "autores": "Alladean Chidukwani, Sebastian Zander y Polychronis Koutsakis",
        "anio": 2026,
        "titulo": "Beyond self-reporting: Uncovering the operational realities of SME cybersecurity through expert assessment",
        "archivo": "Beyond self reporting Uncovering the operational realities of SME cybersecurity through expert assessment.pdf",
    },
}

# (clave, pregunta positiva sobre un control, respuesta que activa hallazgo,
#  evidencia resumida, recomendación adaptada, fuente, sección/página impresa)
CONTROLES = {
    "cuentas": [
        ("cuentas_individuales", "¿Cada empleado utiliza una cuenta individual?", "no", "El estudio observó cuentas compartidas en una pyme.", "Asignar una cuenta individual a cada empleado.", "CHIDUKWANI_2026", "§4.3.2, pp. 11-12"),
        ("admin_restringido", "¿Los privilegios de administrador local están restringidos a quien los necesita?", "no", "Se observaron usuarios locales con privilegios administrativos amplios.", "Revisar y limitar los permisos de administrador local.", "CHIDUKWANI_2026", "§4.3.2, pp. 11-12"),
        ("carpetas_restringidas", "¿Los permisos de las carpetas de red limitan el acceso a quienes lo necesitan?", "no", "Se detectaron permisos de unidades de red definidos de forma laxa.", "Revisar los permisos de las carpetas y unidades de red.", "CHIDUKWANI_2026", "§4.3.2, p. 11"),
        ("mfa_publico", "¿Las aplicaciones expuestas a Internet exigen autenticación multifactor?", "no", "Se identificaron portales externos sin MFA pese a declaraciones de implementación.", "Activar MFA en las aplicaciones expuestas, cuando sea compatible.", "CHIDUKWANI_2026", "§4.3.2 y §4.4.2.7, pp. 12 y 17"),
        ("mfa_cobertura", "¿La política de MFA cubre todas las cuentas y servicios críticos definidos?", ("no", "parcialmente"), "La adopción selectiva de MFA dejó sistemas críticos sin protección.", "Completar y comprobar la cobertura de MFA en servicios críticos.", "CHIDUKWANI_2026", "§4.4.2.7, p. 17"),
        ("mfa_contacto_individual", "¿Cada usuario dispone de un factor de MFA bajo su propio control?", "no", "Una pyme utilizaba un solo teléfono para recibir códigos SMS de varios usuarios.", "Evitar que varias cuentas dependan de un mismo número para MFA.", "CHIDUKWANI_2026", "§4.3.2 y §4.4.2.7, pp. 12 y 17"),
        ("politica_claves_aplicada", "¿La política de contraseñas se aplica mediante controles comprobables?", "no", "Varias organizaciones declararon una política que no se aplicaba técnicamente.", "Comprobar que los requisitos de acceso se aplican en las cuentas pertinentes.", "CHIDUKWANI_2026", "§4.3.2, p. 12"),
        ("claves_diferentes", "¿Se utilizan contraseñas diferentes en las aplicaciones de la empresa?", "no", "Se aconseja utilizar contraseñas diferentes para las aplicaciones en línea.", "Evitar la reutilización de contraseñas entre aplicaciones.", "PAWAR_2022", "§4.1, p. 6"),
        ("responsable_accesos", "¿Hay una persona responsable de gestionar los accesos a los activos?", "no", "La evaluación basada en ISO pregunta quién es responsable de cada activo.", "Asignar la responsabilidad de gestionar y revisar los accesos.", "SIHWI_2016", "§II.A, p. 2"),
        ("acceso_datos_criticos", "¿Solo los grupos autorizados acceden a los datos críticos del negocio?", "no", "El modelo para pymes relaciona actores, dispositivos, activos y políticas de acceso.", "Identificar los datos críticos y restringir sus rutas de acceso.", "KOEZE_2017", "Modeling and calculating the risk; apartados Actors, Assets y Policies, pp. 29 y 36-38 impresas"),
        ("permisos_roles", "¿Los permisos cambian según el rol de los empleados?", "no", "El modelo distingue grupos como administración, RR. HH. y administradores por sus distintos permisos.", "Definir permisos por funciones y revisar los excesivos.", "KOEZE_2017", "Modeling and calculating the risk; apartado Actors, p. 37 impresa (PDF 38)"),
        ("accesos_proveedor", "¿Están definidos los accesos y responsabilidades del proveedor de TI?", "no", "La falta de claridad en los contratos dejó tareas de seguridad sin responsable.", "Acordar por escrito qué accesos y tareas de seguridad gestiona el proveedor.", "CHIDUKWANI_2026", "§4.4.4.1 a §4.4.4.3, p. 18"),
    ],
    "respaldos": [
        ("copia_datos_criticos", "¿Se realizan copias de los datos más críticos del negocio?", "no", "La protección del activo crítico incluye respaldos periódicos de información esencial.", "Incluir los datos críticos en el plan de copias de seguridad.", "PAWAR_2022", "§4.2, p. 7"),
        ("copia_bases_datos", "¿Las bases de datos cruciales están incluidas en los respaldos?", "no", "El modelo de defensa por capas contempla copias de bases de datos cruciales.", "Incluir las bases de datos cruciales en las copias.", "PAWAR_2022", "§4.2, p. 7"),
        ("copia_actualizaciones", "¿Las copias abarcan las actualizaciones importantes de los datos?", "no", "La lista de riesgos identifica respaldos que no cubren actualizaciones importantes.", "Revisar el alcance de las copias para incluir los cambios importantes.", "SIHWI_2016", "§II.A, p. 2"),
        ("copia_aplicacion_critica", "¿Están incluidos los datos de cada aplicación crítica?", "no", "Se detectó un sistema de reservas crítico que carecía de copias declaradas.", "Verificar las aplicaciones críticas una por una y respaldar sus datos.", "CHIDUKWANI_2026", "§4.3.5, p. 12"),
        ("programacion_documentada", "¿Existe un calendario documentado de copias?", "no", "Una pyme declaró copias rutinarias sin calendario documentado.", "Documentar cuándo se realizan las copias y quién comprueba su ejecución.", "CHIDUKWANI_2026", "§4.3.5, p. 12"),
        ("frecuencia_conocida", "¿El responsable conoce la frecuencia real de las copias?", "no", "Varias pymes asumían la suficiencia de sus copias sin conocer su frecuencia.", "Comprobar y registrar la frecuencia real de los respaldos.", "CHIDUKWANI_2026", "§4.3.5, p. 12; §4.4.2.4, p. 17"),
        ("restauracion_probada", "¿Se han realizado pruebas de restauración de los datos?", "no", "Se encontraron respaldos sin procedimientos de verificación y restauración probada.", "Probar la restauración y registrar el resultado.", "CHIDUKWANI_2026", "§4.3.5 y §4.4.2.4, pp. 12 y 16-17"),
        ("copia_fuera_sede", "¿Existe una copia fuera de la ubicación principal?", "no", "La evaluación desmintió afirmaciones de copias guardadas fuera de la sede.", "Mantener y comprobar una copia fuera de la ubicación principal.", "CHIDUKWANI_2026", "§4.3.5, p. 12; §4.4.2.4, p. 17"),
        ("copia_separada", "¿Las copias dependen de un medio distinto al dispositivo de producción?", "no", "El análisis contrapone una copia externa declarada con un disco local susceptible a riesgos físicos.", "Revisar la dependencia de un único medio y diversificar el almacenamiento.", "CHIDUKWANI_2026", "§4.3.5, p. 12"),
        ("copia_cifrada", "¿Los respaldos externos con datos sensibles están cifrados?", "no", "Se documentan respaldos externos cifrados como práctica de protección.", "Evaluar el cifrado de las copias que contienen datos sensibles.", "CHIDUKWANI_2026", "§4.3.5, p. 12"),
        ("alcance_proveedor_copias", "¿Está documentado qué sistemas respalda el proveedor de TI?", "no", "La ambigüedad contractual provocó suposiciones incorrectas sobre la cobertura.", "Pedir al proveedor la lista de sistemas respaldados y responsabilidades.", "CHIDUKWANI_2026", "§4.4.4.1 y §4.4.4.3, p. 18"),
        ("plan_recuperacion", "¿Existe un plan de recuperación ante incidentes que afecten los datos?", "no", "Se observaron organizaciones sin un plan formal de recuperación para incidentes.", "Documentar el procedimiento de recuperación de los servicios y datos esenciales.", "CHIDUKWANI_2026", "§4.4.2.4, pp. 16-17"),
    ],
    "correo": [
        ("formacion_general", "¿El personal ha recibido formación en seguridad del correo?", "no", "La formación del personal se identifica como defensa necesaria ante phishing.", "Capacitar al personal para reconocer mensajes sospechosos.", "PAWAR_2022", "§4.1, p. 5"),
        ("formacion_periodica", "¿La formación sobre correo y phishing se repite periódicamente?", "no", "El estudio pregunta la frecuencia de formación y destaca su continuidad.", "Planificar sesiones periódicas de sensibilización sobre phishing.", "PAWAR_2022", "§4.1, p. 5; Fig. 14 en p. 6"),
        ("formacion_ingreso", "¿Los nuevos empleados reciben formación antes de utilizar el correo corporativo?", "no", "El trabajo recomienda formar a los nuevos empleados antes de acceder a los activos.", "Incluir seguridad del correo en la incorporación de personal.", "PAWAR_2022", "§4.1, p. 5"),
        ("formacion_phishing", "¿La capacitación incluye la identificación de correos de phishing?", "no", "Una pyme decía formar al personal sin evidencias de formación específica en phishing.", "Incorporar casos de phishing en la capacitación.", "CHIDUKWANI_2026", "§4.3.2 y §4.4.3.1, pp. 12 y 18"),
        ("evidencia_capacitacion", "¿Se conserva evidencia de la formación del personal en phishing?", "no", "Los investigadores no pudieron verificar capacitaciones declaradas.", "Guardar constancia de sesiones y participantes para permitir verificación.", "CHIDUKWANI_2026", "§4.3.2, p. 12"),
        ("filtro_spam", "¿Existe un filtro de mensajes no deseados?", "no", "El artículo relaciona filtros antispam con la reducción de correo malicioso.", "Habilitar y revisar el filtrado de correo no deseado.", "PAWAR_2022", "§4.1, p. 6"),
        ("filtro_correo_verificado", "¿Se ha comprobado que el filtro de correo declarado realmente funciona?", "no", "Varias pymes creían disponer de filtrado web o de correo sin evidencia operativa.", "Comprobar la configuración y funcionamiento del filtro de correo.", "CHIDUKWANI_2026", "§4.3.2, p. 12"),
        ("adjuntos_desconocidos", "¿El personal verifica los adjuntos de remitentes inesperados?", "no", "Los mensajes de phishing suelen incluir archivos adjuntos maliciosos.", "Establecer un procedimiento de verificación de adjuntos inesperados.", "PAWAR_2022", "§4.1, p. 6"),
        ("enlaces_inesperados", "¿El personal verifica los enlaces de correos inesperados antes de abrirlos?", "no", "El artículo describe enlaces maliciosos incluidos en correos fraudulentos.", "Enseñar a verificar mensajes y destinos de enlaces inesperados.", "PAWAR_2022", "§4.1, p. 6"),
        ("urgencias_falsas", "¿El personal reconoce mensajes que presionan para actuar con urgencia?", "no", "Los ataques descritos utilizan la urgencia para inducir acciones inseguras.", "Incluir señales de urgencia artificial en la formación de phishing.", "PAWAR_2022", "§4.1, p. 6"),
        ("adjuntos_rrhh", "¿RR. HH. verifica los archivos inesperados enviados como currículos?", "no", "Se señala a los adjuntos recibidos por RR. HH. como posible vía de ataque.", "Definir un tratamiento seguro de los currículos y archivos recibidos.", "PAWAR_2022", "§4.1, p. 6"),
        ("revision_post_incidente", "¿Tras un incidente de phishing se revisan las prácticas de correo?", "no", "Se observó una reacción puntual a phishing sin formación posterior del personal.", "Revisar el incidente e incorporar el aprendizaje a la formación.", "CHIDUKWANI_2026", "§4.4.5.1, p. 19"),
    ],
    "redes": [
        ("cortafuegos", "¿La red empresarial utiliza un cortafuegos configurado?", "no", "La defensa por capas incluye controles en el perímetro digital.", "Revisar la necesidad y la configuración del cortafuegos de red.", "PAWAR_2022", "§5.5-5.6, p. 11"),
        ("cortafuegos_verificado", "¿Se ha verificado el cortafuegos que la empresa declara tener?", "no", "Se encontraron cortafuegos declarados que no pudieron verificarse.", "Confirmar que el cortafuegos está instalado, activo y administrado.", "CHIDUKWANI_2026", "§4.3.2 y §4.4.2.5, pp. 12 y 17"),
        ("wifi_invitados_separado", "¿La red Wi-Fi de invitados está separada de la red corporativa?", "no", "Se observaron redes de invitados y corporativas sin separación.", "Separar el acceso de invitados del acceso corporativo.", "CHIDUKWANI_2026", "§4.3.2, p. 12"),
        ("diagrama_red", "¿Existe un diagrama actualizado de la red?", "no", "Seis de ocho pymes examinadas carecían de diagramas de red.", "Documentar los segmentos y equipos principales de la red.", "CHIDUKWANI_2026", "§4.3.1, p. 10"),
        ("inventario_dispositivos", "¿El inventario incluye servidores, móviles e impresoras conectados?", "no", "Los inventarios omitían con frecuencia servidores, móviles y dispositivos integrados.", "Completar el inventario de dispositivos conectados.", "CHIDUKWANI_2026", "§4.3.1, p. 10"),
        ("dispositivo_publico", "¿Los dispositivos de red accesibles desde Internet tienen controles específicos?", "no", "El marco LCCI prioriza protección de dispositivos de red expuestos.", "Identificar dispositivos expuestos y aplicarles controles de red adecuados.", "PAWAR_2022", "§5.5-5.6, p. 11"),
        ("aplicacion_publica", "¿Los portales o aplicaciones públicas tienen controles de red y datos?", "no", "El marco prioriza la seguridad de aplicaciones y datos expuestos.", "Evaluar los controles de portales y aplicaciones expuestos.", "PAWAR_2022", "§5.5-5.6, p. 11"),
        ("parches_equipos", "¿Se comprueba que los equipos reciben actualizaciones de seguridad?", "no", "Se observaron fallas críticas pese a declaraciones de actualización regular.", "Verificar la instalación de actualizaciones en equipos y servicios.", "CHIDUKWANI_2026", "§4.3.2, p. 12"),
        ("sistema_soportado", "¿Los sistemas operativos conectados conservan soporte y actualizaciones?", "no", "Un sistema operativo fuera de soporte aparecía en la red examinada.", "Planificar la sustitución o aislamiento de sistemas sin soporte.", "CHIDUKWANI_2026", "§4.3.2, p. 12"),
        ("parches_integrados", "¿Se actualizan impresoras, grabadores y otros dispositivos integrados?", "no", "Se hallaron vulnerabilidades importantes en impresoras y grabadores.", "Incluir dispositivos integrados en la gestión de actualizaciones.", "CHIDUKWANI_2026", "§4.3.2 y §4.4.2.3, pp. 12 y 16"),
        ("dispositivos_personales", "¿Hay una política para dispositivos personales conectados a la red?", "no", "El estudio LCCI destaca la necesidad de reglas para dispositivos propios (BYOD).", "Definir condiciones de conexión de dispositivos personales.", "PAWAR_2022", "§4.1, p. 6"),
        ("monitoreo_red", "¿Se comprueba la existencia de monitoreo de la red?", "no", "Una pyme declaró monitoreo continuo, pero la evaluación no halló tal sistema.", "Comprobar los medios de supervisión de red y asignar un responsable.", "CHIDUKWANI_2026", "§4.3.3 y §4.4.2.6, pp. 12 y 17"),
    ],
}


def _construir_reglas():
    """Expande cada práctica a dos reglas con conclusiones distintas."""
    reglas = []
    orden = 1
    for area, controles in CONTROLES.items():
        for clave, pregunta, respuesta, evidencia, medida, fuente, localizacion in controles:
            hallazgo = f"hallazgo_{clave}"
            # Una tupla de respuestas dispara el hallazgo con cualquiera de ellas.
            if isinstance(respuesta, tuple):
                condicion = {"hecho": clave, "operador": "en", "valor": list(respuesta)}
                texto_respuesta = " o ".join(f"«{r}»" for r in respuesta)
            else:
                condicion = {"hecho": clave, "operador": "igual", "valor": respuesta}
                texto_respuesta = f"«{respuesta}»"
            base = {
                "area": area,
                "fuentes": [{"id": fuente, "localizacion": localizacion}],
                "tipo_respaldo": "regla_adaptada_a_P5",
                "evidencia_del_articulo": evidencia,
                "validacion_experto": "pendiente",
            }
            reglas.append({
                **base,
                "id": f"R{orden:03d}",
                "etapa": "riesgo_parcial",
                "si": [condicion],
                "entonces": {"tipo": "hallazgo", "id": hallazgo, "area": area},
                "explicacion": f"Respuesta {texto_respuesta} en «{pregunta}»; {evidencia}",
            })
            orden += 1
            reglas.append({
                **base,
                "id": f"R{orden:03d}",
                "etapa": "recomendacion",
                "si": [{"hecho": hallazgo, "operador": "igual", "valor": True}],
                "entonces": {"tipo": "recomendacion", "texto": medida, "area": area},
                "explicacion": f"Se identificó «{hallazgo}». {medida}",
            })
            orden += 1
    return reglas


REGLAS = _construir_reglas()

# Riesgo global (R097–R101): la regla de dos o más áreas con riesgo alto es el
# ejemplo R3 del enunciado de P5; los demás escalones (medio y bajo) son
# criterio del equipo, porque los antecedentes no fijan estos cortes. El nivel
# de cada área (nivel_p_<área>) lo concluyen las reglas R106–R108.
_FUENTES_GLOBAL = [
    {"id": "SIHWI_2016", "localizacion": "§II.D, p. 4 (conclusión: combinación de resultados parciales)"},
]
_FUENTES_VERIFICACION = [
    {"id": "SIHWI_2016", "localizacion": "§II.D, p. 3 (inferencia)"},
    {"id": "CHIDUKWANI_2026", "localizacion": "§4.3, pp. 10-12 (contraste entre lo declarado y lo verificado)"},
]


def _agregar_sintesis(etiqueta, condiciones, salida, explicacion, fuentes, evidencia=None):
    REGLAS.append({
        "id": f"R{len(REGLAS) + 1:03d}",
        "area": "global",
        "etapa": etiqueta,
        "si": condiciones,
        "entonces": salida,
        "explicacion": explicacion,
        "fuentes": fuentes,
        "tipo_respaldo": "criterio_propuesto_por_el_equipo",
        "evidencia_del_articulo": evidencia or "Los artículos justifican combinar conclusiones y contrastar declaraciones; no fijan estos umbrales.",
        "validacion_experto": "pendiente",
    })


_EVIDENCIA_GLOBAL = ("Los artículos justifican combinar conclusiones parciales en una global; "
                     "no fijan estos cortes. R097 sigue el ejemplo R3 del enunciado de P5; "
                     "el resto es criterio del equipo.")

# (condiciones sobre el número de áreas con riesgo alto y medio, nivel global, motivo)
_RIESGO_GLOBAL = (
    ([("areas_riesgo_alto", "mayor_o_igual", 2)], "alto",
     "Dos o más áreas tienen riesgo alto."),
    ([("areas_riesgo_alto", "igual", 1)], "medio",
     "Una área tiene riesgo alto."),
    ([("areas_riesgo_alto", "igual", 0), ("areas_riesgo_medio", "mayor_o_igual", 2)], "medio",
     "Ninguna área tiene riesgo alto y dos o más tienen riesgo medio."),
    ([("areas_riesgo_alto", "igual", 0), ("areas_riesgo_medio", "igual", 1)], "bajo",
     "Ninguna área tiene riesgo alto y solo una tiene riesgo medio."),
    ([("areas_riesgo_alto", "igual", 0), ("areas_riesgo_medio", "igual", 0)], "bajo",
     "Todas las áreas tienen riesgo bajo."),
)

for _condiciones, _nivel, _motivo in _RIESGO_GLOBAL:
    _agregar_sintesis(
        "riesgo_global",
        [{"hecho": h, "operador": op, "valor": v} for h, op, v in _condiciones],
        {"tipo": "nivel", "hecho": "riesgo_global", "valor": _nivel},
        f"Riesgo global «{_nivel}»: {_motivo[0].lower()}{_motivo[1:]}",
        _FUENTES_GLOBAL,
        _EVIDENCIA_GLOBAL,
    )

for _area in CONTROLES:
    _agregar_sintesis(
        "verificacion",
        [{"hecho": f"desconocidas_{_area}", "operador": "mayor_que", "valor": 0}],
        {"tipo": "solicitud_verificacion", "area": _area},
        f"Existen respuestas «no_se» en {_area}; verificar antes de una conclusión definitiva.",
        _FUENTES_VERIFICACION,
        "Chidukwani et al. (2026) respaldan contrastar lo declarado con lo verificado; pedir verificación ante «no_se» es criterio del equipo.",
    )


VARIABLES = {
    clave: {"pregunta": pregunta, "valores": RESPUESTAS, "area": area}
    for area, controles in CONTROLES.items()
    for clave, pregunta, *_ in controles
}


def resumen():
    """Devuelve cifras observables sin ejecutar el motor de inferencia."""
    return {
        "total": len(REGLAS),
        "por_area": dict(Counter(r["area"] for r in REGLAS)),
        "por_etapa": dict(Counter(r["etapa"] for r in REGLAS)),
        "controles_independientes": len(VARIABLES),
        "pendientes_de_validacion": sum(r["validacion_experto"] == "pendiente" for r in REGLAS),
    }


def verificar_base():
    """Comprueba la estructura; no sustituye revisión semántica experta."""
    errores = []
    ids = [r["id"] for r in REGLAS]
    if len(ids) != len(set(ids)):
        errores.append("Hay identificadores duplicados")
    hallazgos_producidos = {
        r["entonces"]["id"] for r in REGLAS if r["entonces"]["tipo"] == "hallazgo"
    }
    derivados = hallazgos_producidos | {
        "areas_riesgo_alto", "areas_riesgo_medio", "respuestas_desconocidas",
        *(f"desconocidas_{area}" for area in CONTROLES),
    }
    firmas = set()
    for r in REGLAS:
        if not r.get("fuentes") or not all(
            item.get("id") in FUENTES and item.get("localizacion")
            for item in r["fuentes"]
        ):
            errores.append(f"{r['id']}: fuente o localización inválida")
        for condicion in r["si"]:
            hecho = condicion["hecho"]
            if hecho not in VARIABLES and hecho not in derivados:
                errores.append(f"{r['id']}: hecho no definido: {hecho}")
            valores = condicion["valor"] if condicion["operador"] == "en" else [condicion["valor"]]
            if hecho in VARIABLES and not all(v in RESPUESTAS for v in valores):
                errores.append(f"{r['id']}: respuesta no permitida")
        firma = (r["etapa"], repr(r["si"]), repr(r["entonces"]))
        if firma in firmas:
            errores.append(f"{r['id']}: regla idéntica a otra")
        firmas.add(firma)
    return errores


if __name__ == "__main__":
    print(resumen())
    print("Errores estructurales:", verificar_base())
