# Reglas del proyecto «Asesor de ciberseguridad para pymes»

- La lógica del sistema (base, memoria, motor, explicación, reporte) usa solo biblioteca estándar y NO importa Flask. Flask se usará solo en la interfaz web (`src/asesor/web/`, más adelante) como herramienta de implementación, no como método del sistema experto.
- Toda clase, fórmula, regla o algoritmo cita fuente (autor, año, sección/página). Si no hay fuente, no implementarlo y avisar.
- No hacer commits ni push.
- Docstrings, comentarios y mensajes en español. Pruebas con `unittest` en `tests/`.
- No modificar `src/asesor/base_conocimientos.py` sin avisar.
- Decisiones congeladas: `no_se` se tratará como «no» en la puntuación (criterio conservador, Hibshi 2016); el riesgo global final usará el modelo de Sihwi 2016 y Koeze 2017 (las reglas R097–R101 por conteo de áreas son provisionales y serán reemplazadas).
