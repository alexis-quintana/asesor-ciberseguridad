# Asesor de ciberseguridad para pequeñas empresas

Trabajo de Aplicación 2 (TA2) de Inteligencia Artificial, USAT. Sistema experto
basado en reglas (proyecto P5) para las áreas de cuentas, respaldos, correo y redes.

**Estado:** esqueleto del proyecto. Solo la base de conocimientos preliminar
(`src/asesor/base_conocimientos.py`, avance del 01/10/2026) tiene contenido; los demás
módulos contienen únicamente su docstring.

## Requisitos
Python 3.9 o superior. Solo biblioteca estándar (`requirements.txt` está vacío).

## Ejecutar
Desde la raíz del repositorio:

```
PYTHONPATH=src python -m asesor.interfaz_consola
```

(Alternativa: `cd src && python -m asesor.interfaz_consola`.) La interfaz aún no está implementada.

## Pruebas
```
PYTHONPATH=src python -m unittest
```

## Estructura
- `src/asesor/`: módulos del sistema (base de conocimientos, memoria, motor, explicación, interfaz, reporte).
- `tests/`: pruebas automatizadas.
- `docs/matriz_trazabilidad.csv`: matriz regla–fuente–página.
- `casos/casos_prueba.csv`: casos de prueba.

## Autores
Quintana Luis, Alexis Abel · Montenegro Urrutia, Juan Diego
