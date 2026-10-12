# Asesor de ciberseguridad para pequeñas empresas

Trabajo de Aplicación 2 (TA2) de Inteligencia Artificial, USAT. Sistema experto
basado en reglas (proyecto P5) para las áreas de cuentas, respaldos, correo y redes.

**Estado:** base de conocimientos de 132 reglas (`app/conocimiento/`: `base_conocimientos.py`,
`base_reglas_riesgo.py`, `base_reglas_prioridad.py`, `base_reglas_criticidad.py`), memoria de trabajo, motor de
encadenamiento hacia adelante, explicación SI-ENTONCES, lista priorizada de
recomendaciones, reporte imprimible, interfaz de consola e interfaz web (Flask).
Flujo principal: probabilidad por área (Sihwi, 2016), riesgo global por conteo de áreas
con riesgo alto (R097–R101) y prioridad de cada hallazgo (R126–R131, con piso «media» para los controles esenciales, R132). «Parcialmente» y «No» generan hallazgo; «No sé» se trata como «No» en la puntuación y se pide verificarlo. El impacto, las
bandas de Koeze (2017) y la zona de Sihwi (2016) son una extensión opcional (`--con-impacto`).

## Requisitos
Python 3.9 o superior. La lógica del sistema (base, memoria, motor, explicación,
reporte HTML) usa solo biblioteca estándar; Flask (interfaz web) está en `requirements.txt`.

## Instalación
Desde la raíz del repositorio, crear y activar un entorno virtual e instalar dependencias:

```
python -m venv .venv
.venv\Scripts\activate        (Windows)
source .venv/bin/activate        (Linux/macOS)
pip install -r requirements.txt
```

En Windows también puede usarse `ejecutar.bat` (por ejemplo, `ejecutar.bat --web` para abrir la web), que crea `.venv` si no existe,
instala las dependencias y ejecuta el asesor.

## Ejecutar
```
python main.py              # cuestionario interactivo (48 preguntas)
python main.py --demo       # caso fijo de ejemplo, sin pedir respuestas
python main.py --explicar   # muestra además las reglas SI-ENTONCES disparadas
python main.py --con-impacto  # extensión: pide el impacto por área y muestra bandas y zona
python main.py --web        # interfaz web en http://127.0.0.1:5000 (opción --puerto N)
python main.py --validar    # ejecuta los 50 casos de prueba: exactitud, cobertura y consistencia
python main.py --verificar  # busca reglas redundantes, conflictivas, circulares y sin salida
```

La web sigue el flujo Presentación → Evaluación → Resultados: `/` es una landing opcional (contexto, uso, fundamento y antecedentes), `/evaluar` el cuestionario y `/resultado` el diagnóstico. Los estilos están en `app/web/static/css/style.css`.

En la web, el enlace «Cargar el caso de demostración» rellena el cuestionario y el botón
«Ver reporte imprimible» abre el reporte de recomendaciones en HTML, listo para imprimir o guardar como PDF desde el navegador, con las cifras de `app/resultados/estadisticas.py`. El formulario web va por pasos (una área por paso) con ayuda por pregunta. La web no
guarda ninguna respuesta del cuestionario; el resultado muestra la explicación detallada (valores, umbrales, cadena de reglas, reglas no aplicadas y estadísticas del motor).

## Mantenimiento de reglas (administrador)
En `/admin` se pueden desactivar o reactivar reglas de recomendación, riesgo parcial y verificación, editar su texto, restablecer la base y agregar reglas nuevas de recomendación (R133 en adelante, con fuente registrada). Las reglas del núcleo (hallazgos, niveles, riesgo global, prioridad y criticidad) no se pueden desactivar. Los cambios se guardan en `datos/mantenimiento.json`, con historial; la base de código no se modifica.

Se entra con el botón «⚙ Administrar reglas» de la cabecera de la web. La primera vez la página pide crear la clave del administrador (mínimo 8 caracteres, solo desde el mismo equipo); se guarda como resumen PBKDF2 en `datos/admin_clave.json`, nunca en texto plano. No hay clave por defecto. Variables opcionales: `ASESOR_ADMIN_CLAVE` (fija la clave y tiene prioridad), `ASESOR_SECRETO` (clave de las sesiones) y `ASESOR_DATOS` (ruta del archivo de cambios).

## Pruebas
```
python -m unittest        # desde la raíz del proyecto (157 pruebas)
```

## Validación
`python main.py --validar` compara el sistema con los resultados esperados de `tests/casos/casos_prueba.csv` (50 casos: 12 de las fuentes, 18 límite y 20 mixtos). Los esperados los calcula `tests/oraculo.py`, que no usa el motor; `python -m tests.generar_casos` regenera el archivo. El detalle queda en `docs/validacion/` (resultados por caso, resumen y verificación de la base).

## Estructura
```
asesor-ciberseguridad/
├── app/                         código del sistema experto
│   ├── conocimiento/            BASE DE CONOCIMIENTOS: preguntas, reglas, fuentes, ayudas y mantenimiento
│   ├── inferencia/              MOTOR: memoria de trabajo, encadenamiento hacia adelante, riesgo y priorización
│   ├── resultados/              EXPLICACIÓN, estadísticas y reporte imprimible (HTML)
│   ├── web/                     interfaz web (Flask)
│   │   ├── static/{css,js,img}/ estilos (css/style.css), scripts e imágenes
│   │   ├── templates/           base, landing, evaluación, resultados y panel de reglas
│   │   ├── rutas.py             rutas públicas y de administración
│   │   └── __init__.py          creación y configuración de la aplicación
│   ├── validacion.py            validación con los 50 casos (--validar)
│   ├── verificacion.py          redundancias, conflictos, ciclos y reglas sin salida (--verificar)
│   └── consola.py               interfaz de consola
├── datos/                       cambios del administrador (se generan al usar el panel; no se suben a git)
├── docs/                        trazabilidad regla–fuente, guía de la exposición y resultados de la validación
├── tests/
│   ├── casos/                   50 casos de prueba con resultado esperado (casos_prueba.csv)
│   ├── oraculo.py               cálculo independiente de los resultados esperados
│   └── generar_casos.py         genera casos_prueba.csv
├── main.py                      punto de entrada (consola y --web)
├── ejecutar.bat                 prepara el entorno y ejecuta el asesor (Windows)
├── requirements.txt
└── README.md
```

Guion de la demostración y qué mostrar de cada carpeta: `docs/exposicion/GUIA_EXPOSICION.md`.
Matriz regla–fuente–página: `docs/matriz_trazabilidad.csv`.

## Autores
Quintana Luis, Alexis Abel · Montenegro Urrutia, Juan Diego
