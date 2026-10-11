# Guía para la exposición

Asesor de ciberseguridad para pequeñas empresas · sistema experto basado en reglas (P5).

## 1. Qué mostrar de cada carpeta
Las carpetas del código siguen los componentes de un sistema experto (Sesión 12; Sihwi et al., 2016), así que cada diapositiva puede apuntar a una carpeta.

| Componente | Carpeta (`app/…`) | Qué enseñar |
|---|---|---|
| Base de conocimientos | `conocimiento/` | `base_conocimientos.py`: 48 controles y 96 reglas de plantilla; `base_reglas_*.py`: riesgo, prioridad y criticidad (R132); cada regla con fuente y página |
| Adquisición y actualización del conocimiento | `conocimiento/mantenimiento.py` | Panel «Administrar reglas»: desactivar, editar y agregar reglas con fuente e historial |
| Memoria de trabajo | `inferencia/memoria.py` | Hechos del caso: 48 respuestas y los hechos que se derivan |
| Motor de inferencia | `inferencia/motor.py` | Encadenamiento hacia adelante por etapas |
| Modelo de riesgo y prioridad | `inferencia/riesgo.py`, `priorizacion.py` | Puntajes 16.5 / 50 / 83.5, umbrales 34 y 67, matriz de prioridad |
| Explicación | `resultados/explicacion.py` | Reglas SI–ENTONCES disparadas, valores observados y reglas no aplicadas |
| Interfaz | `consola.py`, `web/` | Landing, evaluación por pasos, resultados y reporte imprimible; rutas en `web/rutas.py`, plantillas en `web/templates/`, estilos en `web/static/css/style.css` |

## 2. Demostración sugerida (7 minutos)
1. **Arranque y contexto** (1 min): doble clic en `ejecutar.bat` con el argumento `--web` (o `ejecutar.bat --web` en la consola); se abre la landing en `http://127.0.0.1:5000`. Recorrerla de arriba abajo: por qué importa (datos de los antecedentes), cómo funciona, qué se recibe, fundamento y límites. El botón «Ver demostración» pasa al paso siguiente.
2. **Cuestionario** (1 min): mostrar la guía de respuestas, la ayuda «¿Qué significa?» de una pregunta y el avance por áreas.
3. **Caso de demostración** (1 min): enlace «Cargar el caso de demostración» y «Ver resultado».
4. **Resultado** (2 min): riesgo global *alto*; niveles por área; recomendaciones ordenadas (18 alta, 6 media, 2 baja); verificaciones pendientes por respuestas «No sé».
5. **Explicación** (1 min): abrir la cadena de una recomendación (respuesta → hallazgo → recomendación → prioridad → criticidad) y las reglas que no se aplicaron.
6. **Mantenimiento de reglas** (1 min): «Administrar reglas», desactivar una recomendación, volver a evaluar y ver el cambio; restablecerla.
7. **Reporte** (opcional): «Ver reporte imprimible».

Si falla la web: `python main.py --demo --explicar` muestra lo mismo por consola.

## 3. Cifras para tener a mano
- 4 áreas, 48 controles, **132 reglas** (96 de plantilla y 36 de lógica propia), 10 fuentes.
- Caso de demostración: 26 hallazgos; riesgo global alto (cuentas 69.5 y respaldos 69.5 altos, correo 44.4 medio, redes 27.7 bajo).
- 140 pruebas automatizadas (`python -m unittest`).
- Decisiones del equipo (decirlas con franqueza): «No sé» cuenta como «No»; la lista de 12 controles esenciales y el piso «media» de R132 son criterio del equipo; no hay validación por un experto, la validación se apoya en las fuentes.

## 4. Preguntas probables
- *¿Por qué reglas y no aprendizaje automático?* Porque el sistema debe explicar cada conclusión y citar su fuente.
- *¿Qué pasa si una regla no aplica?* No se dispara y no produce nada; la pantalla de resultado lista cuáles y por qué.
- *¿Cómo se mantiene el conocimiento?* Con el panel de administración; la base original no se modifica y cada cambio queda en el historial.
- *¿Qué limita al sistema?* Depende de lo que el usuario declara y cubre cuatro áreas.
