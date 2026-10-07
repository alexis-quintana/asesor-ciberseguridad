# Guía de la matriz de trazabilidad

Este documento explica el formato de `docs/matriz_trazabilidad.csv`. Su finalidad es que cada regla de la base de conocimientos pueda rastrearse hasta la fuente que la respalda, y que cada regla pueda rastrearse hasta los casos de prueba que la ejercitan.

## Base del formato

El formato aplica las prácticas habituales de las matrices de trazabilidad de requisitos a las reglas de un sistema experto:

- La norma ISO/IEC/IEEE 29148:2018 define la trazabilidad de requisitos como la identificación y documentación de la ruta de derivación (hacia arriba) y de la ruta de asignación (hacia abajo), y la matriz de trazabilidad como un artefacto estructurado que vincula los requisitos con sus necesidades de nivel superior o con la implementación de nivel inferior (§3.1.23 y §3.1.24, p. 5). Define además la verificación de requisitos como la confirmación, por examen, de que están bien formados (§3.1.26, p. 5).
- Identificador único y jerárquico de cada elemento, con su fuente y su texto en la propia matriz, y mantenida como documento electrónico fácil de ordenar en ambos sentidos (guía de ingeniería de software de la NASA, SWE-052).
- Columnas típicas de una matriz: identificador, descripción, fuente, prioridad, estado, método de verificación, responsable y notas (project-management.com).
- Trazabilidad bidireccional: hacia adelante (regla → caso de prueba) y hacia atrás (caso de prueba → regla). Así se detectan reglas que ningún caso ejercita y casos que no disparan nada.
- Comprobaciones de consistencia y completitud de la base: reglas redundantes, en conflicto, subsumidas, circulares, sin salida o inalcanzables (Nguyen et al., 1985). Son las mismas que pide la guía del informe.

Estas referencias respaldan la **práctica de documentación**, no el método del sistema experto. Los métodos del sistema se justifican únicamente con las 10 fuentes del proyecto.

## Columnas de `matriz_trazabilidad.csv`

| Columna | Contenido |
|---|---|
| `regla_id` | Identificador único de la regla en `base_conocimientos.py` (R001, R002…). |
| `area` | cuentas, respaldos, correo, redes o global. |
| `control` | Clave del control evaluado. |
| `tipo_regla` | hallazgo, recomendacion, clasificacion, verificacion. |
| `regla_si_entonces` | La regla en forma SI–ENTONCES, generada desde la base para evitar discrepancias. |
| `fuente` | Clave de la fuente en `FUENTES`. |
| `localizacion_declarada` | Sección y página que cita hoy la base. |
| `localizacion_verificada` | Sección y página comprobadas en el PDF (página impresa; en Koeze se indica también la del PDF). |
| `evidencia_en_la_fuente` | Qué dice la fuente en esa localización, en paráfrasis. |
| `tipo_respaldo` | `directo`: la fuente describe la práctica o la recomienda. `parcial`: la fuente respalda la práctica, pero la medida es adaptación del equipo. `criterio_equipo`: sin respaldo en las fuentes (debe justificarse o retirarse). |
| `ajuste_propuesto` | Corrección a la cita o a la redacción del control. |
| `estado` | `pendiente` (sin revisar), `con_observacion` (hay un ajuste propuesto), `confirmada` (revisada y sin cambios) o `corregida` (ajuste aplicado en la base). |
| `verificado_por` | Persona del equipo que contrastó la fila con el PDF. Se rellena solo tras revisar. |
| `fecha_verificacion` | AAAA-MM-DD de esa revisión. |
| `casos_prueba` | Casos que disparan la regla. Se genera con el script de métricas; no se edita a mano. |

## Matriz de cobertura (hacia atrás)

La matriz inversa (caso de prueba → reglas disparadas) la produce el script de métricas al ejecutar los casos. Con ella se calculan la cobertura (porcentaje de reglas disparadas por al menos un caso) y las reglas que ningún caso ejercita.

## Referencias de este formato

- ISO/IEC/IEEE. (2018). *ISO/IEC/IEEE 29148:2018. Systems and software engineering — Life cycle processes — Requirements engineering* (2.ª ed.). Solo se consultó la vista previa de 14 páginas (índice y definiciones); no se verificó el texto completo de la norma.
- NASA. *SWE-052 — Bidirectional Traceability*. Software Engineering Handbook. https://swehb.nasa.gov/x/7QL7
- project-management.com. *Requirements Traceability Matrix (RTM)*. https://project-management.com/requirements-traceability-matrix-rtm/
- Nguyen, T. A., Perkins, W. A., Laffey, T. J. y Pecora, D. (1985). Checking an expert systems knowledge base for consistency and completeness. *IJCAI-85*. https://mlanthology.org/ijcai/1985/nguyen1985ijcai-checking
