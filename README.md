# Asesor de ciberseguridad para pequeñas empresas

Trabajo de Aplicación 2 (TA2) de Inteligencia Artificial, USAT. Sistema experto
basado en reglas (proyecto P5) para las áreas de cuentas, respaldos, correo y redes.

**Estado:** base de conocimientos preliminar (`src/asesor/base_conocimientos.py`, avance
del 01/10/2026), memoria de trabajo, motor de encadenamiento hacia adelante, explicación
SI-ENTONCES e interfaz de consola. La clasificación global es provisional (reglas
R097–R101) y será reemplazada por el modelo de Sihwi (2016) y Koeze (2017).

## Requisitos
Python 3.9 o superior. La lógica del sistema usa solo biblioteca estándar; Flask
(`requirements.txt`) se usará únicamente en la futura interfaz web.

## Instalación
Desde la raíz del repositorio, crear y activar un entorno virtual e instalar dependencias:

```
python -m venv .venv
.venv\Scripts\activate        (Windows)
source .venv/bin/activate        (Linux/macOS)
pip install -r requirements.txt
```

En Windows también puede usarse `ejecutar.bat`, que crea `.venv` si no existe,
instala las dependencias y ejecuta el asesor.

## Ejecutar
```
python main.py              # cuestionario interactivo (48 preguntas)
python main.py --demo       # caso fijo de ejemplo, sin pedir respuestas
python main.py --explicar   # muestra además las reglas SI-ENTONCES disparadas
```

## Pruebas
```
python -m unittest
```

## Estructura
- `src/asesor/`: módulos del sistema (base de conocimientos, memoria, motor, explicación, interfaz, reporte).
- `tests/`: pruebas automatizadas.
- `docs/matriz_trazabilidad.csv`: matriz regla–fuente–página.
- `casos/casos_prueba.csv`: casos de prueba.

## Autores
Quintana Luis, Alexis Abel · Montenegro Urrutia, Juan Diego
