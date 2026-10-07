# Asesor de ciberseguridad para pequeñas empresas

Trabajo de Aplicación 2 (TA2) de Inteligencia Artificial, USAT. Sistema experto
basado en reglas (proyecto P5) para las áreas de cuentas, respaldos, correo y redes.

**Estado:** base de conocimientos de 131 reglas (`src/asesor/base_conocimientos.py`,
`base_reglas_riesgo.py`, `base_reglas_prioridad.py`), memoria de trabajo, motor de
encadenamiento hacia adelante, explicación SI-ENTONCES, lista priorizada de
recomendaciones, reporte imprimible, interfaz de consola e interfaz web (Flask).
Flujo principal: probabilidad por área (Sihwi, 2016), riesgo global por conteo de áreas
con riesgo alto (R097–R101) y prioridad de cada hallazgo (R126–R131). El impacto, las
bandas de Koeze (2017) y la zona de Sihwi (2016) son una extensión opcional (`--con-impacto`).

## Requisitos
Python 3.9 o superior. La lógica del sistema (base, memoria, motor, explicación,
reporte) usa solo biblioteca estándar; Flask (`requirements.txt`) se usa únicamente en la
interfaz web.

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
python main.py --con-impacto  # extensión: pide el impacto por área y muestra bandas y zona
python main.py --web        # interfaz web en http://127.0.0.1:5000 (opción --puerto N)
```

En la web, el enlace «Cargar el caso de demostración» rellena el cuestionario y el botón
«Ver reporte imprimible» abre el reporte para imprimir o guardar como PDF. La web no
guarda ninguna respuesta.

## Pruebas
```
python -m unittest
```

## Estructura
- `src/asesor/`: módulos del sistema (base de conocimientos, memoria, motor, explicación, priorización, reporte, consola y `web/`).
- `tests/`: pruebas automatizadas.
- `docs/matriz_trazabilidad.csv`: matriz regla–fuente–página.
- `casos/casos_prueba.csv`: casos de prueba.

## Autores
Quintana Luis, Alexis Abel · Montenegro Urrutia, Juan Diego
