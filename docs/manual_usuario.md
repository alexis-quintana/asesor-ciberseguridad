# Manual de usuario

Asesor de ciberseguridad para pequeñas empresas: sistema experto basado en reglas que evalúa 48 prácticas en cuatro áreas (cuentas, respaldos, correo y redes) y entrega un nivel de riesgo con recomendaciones priorizadas.

> El resultado orienta y no reemplaza a un especialista ni a una auditoría. Un riesgo bajo no garantiza que la empresa esté protegida.

## 1. Requisitos e instalación

- Python 3.9 o superior.
- Flask, solo para la interfaz web (`requirements.txt`).

**Windows (recomendado):** doble clic en `ejecutar.bat`, o desde la terminal:

```
ejecutar.bat --web
```

El archivo crea el entorno `.venv` la primera vez, instala las dependencias y abre el asesor.

**Manual (cualquier sistema):**

```
python -m venv .venv
.venv\Scripts\activate            (Windows)
source .venv/bin/activate         (Linux/macOS)
pip install -r requirements.txt
```

## 2. Interfaz web

1. Ejecute `python main.py --web` y abra http://127.0.0.1:5000. Para otro puerto: `--puerto 8080`.
2. **Presentación** (`/`): explica qué evalúa el asesor y en qué fuentes se basa. Pulse «Evaluar mi empresa», o «Probar demostración» para cargar un caso de ejemplo.
3. **Evaluación** (`/evaluar`): el cuestionario avanza un área por paso.
   - Nombre de la empresa: opcional; solo aparece en el reporte.
   - Cada pregunta tiene cuatro opciones (ver sección 4) y un enlace «¿Qué significa?» con un ejemplo y cómo comprobarla.
   - Paso final opcional, **Impacto para el negocio**: valore de 1 (mínimo) a 5 (crítico) cada área. Si no lo necesita, deje las filas sin marcar; «Limpiar» quita una selección. Para usar esta extensión hay que valorar las cuatro áreas.
   - Pulse «Ver resultado». Si falta alguna respuesta, la página indica cuáles.
4. **Resultados** (`/resultado`): riesgo global, nivel de cada área, recomendaciones ordenadas por prioridad, áreas por verificar y la explicación (sección 5).
5. **Reporte imprimible**: «Ver reporte imprimible» y luego «Imprimir o guardar como PDF».
6. «Nueva evaluación» vuelve al cuestionario vacío.

Las respuestas no se guardan: se usan solo para calcular el resultado de esa petición.

## 3. Consola

```
python main.py                    cuestionario interactivo (48 preguntas)
python main.py --demo             caso de demostración, sin preguntas
python main.py --explicar         añade las reglas SI–ENTONCES disparadas
python main.py --con-impacto      pide además el impacto (1 a 5) de cada área
```

Las opciones se combinan, por ejemplo `python main.py --demo --explicar`. En el cuestionario se responde con un número: 1 = sí, 2 = no, 3 = parcialmente, 4 = no sé.

## 4. Cómo responder

| Opción | Cuándo marcarla | Efecto |
|---|---|---|
| Sí | La práctica existe y se aplica. | Riesgo bajo para esa pregunta; sin hallazgo. |
| Parcialmente | Existe, pero incompleta o sin aplicar siempre. | Riesgo medio; genera hallazgo y recomendación. |
| No | La práctica no existe. | Riesgo alto; genera hallazgo y recomendación. |
| No sé | No conoce la respuesta. | Se cuenta como «no» para calcular el riesgo, pero no genera hallazgo: el sistema pide verificar esa área. |

Responda lo que realmente ocurre, no lo que debería ocurrir: el sistema no comprueba lo declarado.

## 5. Cómo leer el resultado

- **Nivel de cada área.** Cada respuesta vale puntos (sí 16,5; parcialmente 50; no y no sé 83,5). El promedio P de las 12 respuestas da el nivel: bajo si P < 34, medio si 34 ≤ P < 67, alto si P ≥ 67.
- **Riesgo global.** Alto con dos o más áreas altas; medio con una área alta, o con ninguna alta y dos o más medias; bajo en los demás casos.
- **Prioridad de cada recomendación.** Combina el nivel de la respuesta con el de su área:

| Respuesta \ Área | Alto | Medio | Bajo |
|---|---|---|---|
| No (alto) | alta | media | baja |
| Parcialmente (medio) | media | media | baja |

  Doce controles esenciales (por ejemplo cortafuegos, formación contra phishing, MFA en aplicaciones expuestas) nunca bajan de prioridad media.
- **Por verificar.** Áreas con respuestas «no sé», con una sugerencia de cómo comprobar cada una.
- **Explicación.** Para cada recomendación: la respuesta, el hallazgo, la regla aplicada y su fuente. También muestra cómo se calculó cada área, cuántas reglas evaluó y disparó el motor en cada etapa, y las reglas que no se aplicaron con su motivo.
- **Extensión de impacto** (opcional). Con los cuatro impactos se calcula R = (P / 100) × (impacto / 5), su banda (muy bajo a muy alto) y una zona global verde, amarilla o roja.

## 6. Panel del administrador

Permite ajustar las reglas sin tocar el código. Los cambios se guardan en `datos/mantenimiento.json`, con historial; la base original no se modifica.

1. Pulse «Administrar reglas» en la cabecera.
2. **Primera vez:** cree la clave (mínimo 8 caracteres). Solo puede crearse desde el mismo equipo (127.0.0.1). Se guarda como resumen PBKDF2, nunca en texto plano, en `datos/admin_clave.json`; no hay clave por defecto.
3. Acciones disponibles:
   - Desactivar o reactivar reglas de riesgo parcial, recomendación y verificación, indicando un motivo. Las reglas del núcleo (niveles, riesgo global, prioridad y criticidad) no se pueden desactivar.
   - Editar el texto de una regla, o restablecerla a su versión original.
   - Agregar reglas nuevas de recomendación (R133 en adelante, máximo 100): área, condiciones, texto, prioridad, fuente de la base y localización (sección o página).
4. «Cerrar sesión» sale del panel.

Variables de entorno opcionales: `ASESOR_ADMIN_CLAVE` (fija la clave y tiene prioridad), `ASESOR_SECRETO` (clave de las sesiones) y `ASESOR_DATOS` (ruta del archivo de cambios).

## 7. Problemas frecuentes

| Problema | Solución |
|---|---|
| `ejecutar.bat` no crea el entorno | Instale Python 3 desde python.org y marque «Add Python to PATH». |
| `ModuleNotFoundError: flask` | Active `.venv` y ejecute `pip install -r requirements.txt`. |
| El puerto 5000 está ocupado | `python main.py --web --puerto 8080`. |
| No aparece «crear clave» en el panel | Abra la web desde el mismo equipo (http://127.0.0.1:5000). |
| Olvidó la clave | Borre `datos/admin_clave.json` y créela de nuevo, o defina `ASESOR_ADMIN_CLAVE`. |
