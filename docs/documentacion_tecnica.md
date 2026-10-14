# Documentación técnica

Cómo está construido el asesor, cómo se representa el conocimiento, cómo razona el motor y cómo se prueba. Para usarlo, vea [manual_usuario.md](manual_usuario.md).

## 1. Arquitectura

Componentes clásicos de un sistema experto (Sihwi et al., 2016; Ghanem et al., 2023):

```
Usuario → Interfaz (web / consola) → Memoria de trabajo ⇄ Motor de inferencia ⇄ Base de conocimientos
                                              ↓
                              Explicación · Reporte · Lista priorizada
```

| Componente | Archivos | Función |
|---|---|---|
| Base de conocimientos | `app/conocimiento/base_conocimientos.py`, `base_reglas_riesgo.py`, `base_reglas_prioridad.py`, `base_reglas_criticidad.py` | 48 controles, 10 fuentes y las reglas R001–R132 |
| Ayudas | `app/conocimiento/ayudas.py` | Significado, ejemplo y cómo comprobar cada pregunta |
| Mantenimiento | `app/conocimiento/mantenimiento.py` | Cambios del administrador, historial y clave |
| Memoria de trabajo | `app/inferencia/memoria.py` | Hechos del caso; valida respuestas e impactos |
| Motor | `app/inferencia/motor.py` | Encadenamiento hacia adelante por etapas |
| Modelo de riesgo | `app/inferencia/riesgo.py` | Puntajes, probabilidad P, nivel de cada respuesta e impacto |
| Priorización | `app/inferencia/priorizacion.py` | Ordena las recomendaciones |
| Caso completo | `app/inferencia/caso.py` | Carga respuestas e impactos y llama al motor |
| Explicación y reporte | `app/resultados/explicacion.py`, `reporte.py`, `estadisticas.py` | Reglas disparadas, cadena de cada recomendación, reporte HTML |
| Interfaz | `app/consola.py`, `app/web/` | Consola y web (Flask) |
| Calidad | `app/validacion.py`, `app/verificacion.py`, `tests/` | Casos de prueba, oráculo, verificación de la base y pruebas unitarias |

## 2. Representación del conocimiento

### 2.1 Hechos

La memoria de trabajo guarda pares `nombre → valor`:

| Hecho | Valores | Quién lo produce |
|---|---|---|
| `<control>` (48) | `si`, `parcialmente`, `no`, `no_se` | Usuario |
| `impacto_<area>` (4) | 1 a 5 | Usuario (extensión) |
| `p_<area>`, `nivel_r_<control>` | 0–100; bajo/medio/alto | `riesgo.py` |
| `i100_<area>`, `r_<area>`, `p_global`, `r_global` | números | `riesgo.py` (extensión) |
| `areas_riesgo_alto`, `areas_riesgo_medio`, `desconocidas_<area>` | enteros | Motor, antes de cada etapa |
| `hallazgo_<control>` | verdadero | Reglas R001–R095 |
| `nivel_p_<area>` | bajo/medio/alto | Reglas R106–R108 |
| `riesgo_global` | bajo/medio/alto | Reglas R097–R101 |
| `prioridad_<control>` | alta/media/baja | Reglas R126–R132 |

### 2.2 Formato de una regla

```python
{
    "id": "R017",
    "area": "cuentas",
    "etapa": "riesgo_parcial",
    "si": [{"hecho": "responsable_accesos", "operador": "en", "valor": ["no", "parcialmente"]}],
    "entonces": {"tipo": "hallazgo", "id": "hallazgo_responsable_accesos", "area": "cuentas"},
    "explicacion": "Varias pymes carecían de una persona designada como responsable...",
    "fuentes": [{"id": "CHIDUKWANI_2026", "localizacion": "sección 4.4.4.3, p. 18"}],
    "tipo_respaldo": "regla_adaptada_a_P5",
    "validacion_experto": "pendiente",
}
```

- Las condiciones de `si` se unen con Y.
- Operadores: `igual`, `mayor_que`, `menor_que`, `mayor_o_igual`, `menor_o_igual`, `en`.
- Tipos de conclusión: `hallazgo`, `recomendacion`, `solicitud_verificacion`, `nivel`, `prioridad`, `recomendacion_adicional`.

### 2.3 Familias de reglas (132)

| Reglas | Etapa | Qué concluyen | Cómo se definen |
|---|---|---|---|
| R001–R095 impares | riesgo_parcial | Hallazgo si la respuesta es «no» o «parcialmente» | Plantilla: `_construir_reglas()` recorre `CONTROLES` |
| R002–R096 pares | recomendacion | Una medida por hallazgo | Misma plantilla |
| R097–R101 | riesgo_global | Riesgo global según áreas altas y medias | `_RIESGO_GLOBAL` |
| R102–R105 | verificacion | Pide verificar un área con «no sé» | Una por área |
| R106–R108 | nivel_probabilidad | Nivel de cada área a partir de P | Genéricas; se instancian por ámbito |
| R109–R125 | nivel_impacto, banda_riesgo, zona | Extensión de impacto | `base_reglas_riesgo.py` |
| R126–R131 | prioridad | Matriz respuesta × área (6 celdas) | `expandir()`: 6 × 48 = 288 instancias |
| R132 | criticidad | Piso «media» para 12 controles esenciales | `expandir()`: 12 instancias |

En total son 469 instancias: 96 de plantilla y 36 reglas propias. Al expandirse las genéricas, esas 36 suman 373 instancias.

### 2.4 Controles

`CONTROLES` en `base_conocimientos.py` es un diccionario `área → lista de tuplas`:

```
(clave, pregunta, respuesta, evidencia, recomendación, fuente, localización)
```

Cada tupla genera dos reglas, la de hallazgo y la de recomendación. `FUENTES` registra las 10 fuentes con su referencia completa.

## 3. Modelo de riesgo

| Elemento | Valor | Fuente |
|---|---|---|
| Puntaje | sí 16,5 · parcialmente 50 · no 83,5 · no sé 83,5 | Rangos de Sihwi (2016, II.D); punto medio y «no sé» = «no»: equipo |
| Probabilidad | P = promedio de los 12 puntajes del área | Sihwi (2016) |
| Nivel | bajo < 34 ≤ medio < 67 ≤ alto | Sihwi (2016); cortes continuos: equipo |
| Riesgo global | alto: ≥ 2 áreas altas; medio: 1 alta, o 0 altas y ≥ 2 medias; bajo: resto | Umbral 2: enunciado P5; resto: equipo |
| Prioridad | (alto, alto) alta; (alto, medio), (medio, alto), (medio, medio) media; área baja: baja | Celdas de Sihwi (2016, Tabla III); ejes: equipo |
| Criticidad | 12 controles esenciales no bajan de media | Pawar y Palivela (2022, 4.2 y 5.5–5.6); selección: equipo |
| Impacto (ext.) | I = impacto / 5; R = (P / 100) × I | Koeze (2017) |
| Banda (ext.) | ≤ 0,2 muy bajo; ≤ 0,4 bajo; ≤ 0,6 medio; ≤ 0,8 alto; > 0,8 muy alto | Koeze (2017) |
| Zona (ext.) | roja (alto, alto); amarilla (medio, medio), (alto, medio), (medio, alto); verde resto | Sihwi (2016) |

`nivel_sihwi()` redondea a 9 decimales antes de comparar para evitar errores de coma flotante en 34 y 67.

## 4. Motor de inferencia

`inferir()` en `motor.py` aplica encadenamiento hacia adelante por etapas:

```
ETAPAS_BASE = riesgo_parcial, recomendacion, verificacion, nivel_probabilidad,
              riesgo_global, prioridad, criticidad, recomendacion_adicional
ETAPAS_EXTENSION = nivel_impacto, banda_riesgo, zona     (solo con los 4 impactos)
```

```
si faltan respuestas: error
calcular P y el nivel de cada respuesta (y, con impactos, I y R)
para cada etapa:
    recalcular hechos derivados (áreas altas y medias, «no sé» por área)
    repetir
        para cada regla de la etapa, en orden de número:
            si no disparó antes y se cumplen sus condiciones:
                aplicar la conclusión y registrar el disparo
    hasta que una pasada no dispare nada
```

- **Resolución de conflictos:** orden de etapas, orden numérico dentro de la etapa y una sola ejecución por regla. Solo R132 corrige un valor de una etapa anterior (la prioridad).
- **Terminación:** el conjunto `disparadas` impide repetir reglas, y `verificacion.py` comprueba que no haya ciclos.
- **Trazabilidad:** cada disparo guarda la regla, sus fuentes y los valores observados. Con eso, `explicacion.py` arma la cadena respuesta → hallazgo → recomendación → prioridad → criticidad.
- **Orden de la lista final** (`lista_priorizada()`): primero por prioridad, luego por P del área (de mayor a menor) y luego por el orden del cuestionario.

## 5. Calidad

### 5.1 Comandos

```
python -m unittest                      160 pruebas unitarias
python main.py --verificar              verificación de la base
python main.py --validar                50 casos frente al oráculo y análisis de sensibilidad
python -m tests.generar_casos           regenera tests/casos/casos_prueba.csv
python -m tests.sensibilidad_puntajes   sensibilidad de los puntajes
python -m tests.trazabilidad_casos      llena casos_prueba en la matriz
```

### 5.2 Verificación (`app/verificacion.py`)

Revisa las 469 instancias en busca de reglas redundantes (duplicadas o subsumidas), conflictivas (misma etapa), circulares (búsqueda en profundidad sobre el grafo «regla produce un hecho que lee otra regla»), sin salida e inalcanzables. Resultado actual: 0 problemas sin explicar. Las 24 correcciones R128/R131 → R132 y las 12 autorreferencias de R132 son intencionales.

### 5.3 Validación (`app/validacion.py`, `tests/oraculo.py`)

- **Casos:** 50 en total. G1 tiene 12 casos tomados de las fuentes, G2 tiene 18 casos límite y G3 tiene 20 mixtos generados con la semilla 2026.
- **Oráculo:** `tests/oraculo.py` calcula el resultado esperado con fórmulas directas, sin usar el motor; de la base solo toma la lista de preguntas (`VARIABLES`).
- **Métricas:** exactitud, cobertura de reglas y consistencia (repetir el caso y reordenar las respuestas). Resultado: 50 de 50, cobertura de 132 de 132 y consistencia de 50 de 50.
- **Análisis de sensibilidad:** se altera la base y se cuenta cuántos casos fallan. Corte 34 → 40: 11; celda alto/alto: 27; sin R132: 8; sin R097: 15.
- **Salidas:** los resultados se guardan en `docs/validacion/`.

Sin un experto, la coincidencia con el oráculo mide la fidelidad a la especificación, no la corrección del conocimiento.

### 5.4 Trazabilidad

`docs/matriz_trazabilidad.csv` enlaza cada regla con su fuente, la página comprobada en el PDF, la evidencia, el tipo de respaldo, quién la verificó y los casos que la disparan. El formato está explicado en [guia_matriz_trazabilidad.md](guia_matriz_trazabilidad.md).

## 6. Cómo extender la base

**Agregar un control:**

1. Añada una tupla en `CONTROLES[área]` con su pregunta, respuesta, evidencia, recomendación, fuente de `FUENTES` y localización.
2. Añada su ayuda en `ayudas.py`.
3. Agregue la fila en la matriz de trazabilidad y regenere los casos con `python -m tests.generar_casos`.
4. Ejecute `python -m unittest`, `--verificar` y `--validar`.

Si cambia el número de controles por área, cambian P y los resultados esperados, y hay que actualizar el oráculo.

**Agregar una recomendación sin tocar el código:** use el panel del administrador (manual de usuario, sección 6). Las reglas nuevas se guardan en `datos/mantenimiento.json` y entran al motor en la etapa `recomendacion_adicional`.

## 7. Seguridad y datos

- Las respuestas se procesan en memoria y no se guardan.
- El panel exige una clave guardada como PBKDF2, que solo puede crearse desde el mismo equipo. Las acciones llevan un token CSRF y las respuestas del panel no se guardan en caché.
- `datos/` no se sube al repositorio (`.gitignore`).
