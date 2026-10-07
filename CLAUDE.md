# Reglas del proyecto «Asesor de ciberseguridad para pymes»

- La lógica del sistema (base, memoria, motor, explicación, reporte) usa solo biblioteca estándar y NO importa Flask. Flask se usa solo en la interfaz web (`src/asesor/web/`) como herramienta de implementación, no como método del sistema experto.
- Toda clase, fórmula, regla o algoritmo cita fuente (autor, año, sección/página). Si no hay fuente, no implementarlo y avisar.
- No hacer commits ni push.
- Docstrings, comentarios y mensajes en español. Pruebas con `unittest` en `tests/`.
- No modificar `src/asesor/base_conocimientos.py` sin avisar.
- Decisiones congeladas: `no_se` se trata como «no» en la puntuación (criterio conservador del equipo). El flujo principal sigue el enunciado de P5: probabilidad por área (Sihwi 2016), riesgo global por conteo de áreas con riesgo alto (R097–R101) y prioridad por hallazgo (R126–R131, matriz de Sihwi adaptada). El impacto, las bandas de Koeze 2017 y la zona son una extensión opcional (`--con-impacto`).
