"""Reporte imprimible del asesor.

Genera una página HTML autónoma (sin dependencias) con el nivel de riesgo de cada
área, el riesgo global, la lista priorizada de recomendaciones, las verificaciones
solicitadas, la explicación de las reglas aplicadas y el aviso de límites. Se
imprime o se guarda como PDF desde el navegador (Ctrl+P).

Fuente: requisito del proyecto P5 (reporte imprimible); recomendaciones
priorizadas en el estilo de Fähnrich y Roßnagel (2022).
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from .explicacion import formatear_regla
from .priorizacion import lista_priorizada
from .riesgo import AREAS, riesgo_desde_hechos

# Límites del sistema (sección 3.8 del informe). Se muestran en la web, en el
# reporte y en la consola.
AVISO_LIMITES = (
    "Este resultado orienta y no reemplaza a un especialista ni a una auditoría; "
    "un riesgo bajo no garantiza que la empresa esté protegida.",
    "Las respuestas son autodeclaradas y pueden sobrestimar la seguridad real "
    "(Chidukwani et al., 2026); las respuestas «no sé» se contaron como «no».",
    "El conocimiento proviene de la literatura revisada y no fue validado por un "
    "experto en ciberseguridad.",
    "La prioridad no considera el costo ni el esfuerzo de cada medida.",
)

NOMBRE_NIVEL = {"bajo": "Bajo", "medio": "Medio", "alto": "Alto"}
NOMBRE_PRIORIDAD = {"alta": "Alta", "media": "Media", "baja": "Baja"}

_ESTILO = """
body{font-family:Georgia,'Times New Roman',serif;color:#1a1a1a;max-width:820px;margin:24px auto;padding:0 16px;line-height:1.45}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.15rem;margin:26px 0 8px;border-bottom:1px solid #999;padding-bottom:3px}
.meta{color:#555;font-size:.9rem}table{border-collapse:collapse;width:100%;font-size:.92rem}
th,td{border:1px solid #999;padding:5px 8px;text-align:left;vertical-align:top}th{background:#eee}
.nivel{font-weight:bold}.global{font-size:1.2rem;margin:8px 0}
.aviso{border:1px solid #999;background:#f6f6f6;padding:8px 14px;font-size:.88rem}
pre{white-space:pre-wrap;font-size:.78rem;background:#f6f6f6;padding:8px;border:1px solid #ccc}
.boton{margin:12px 0}.boton button{font-size:1rem;padding:6px 14px}
@media print{.boton{display:none}body{margin:0;max-width:none}h2{break-after:avoid}tr{break-inside:avoid}.salto{break-before:page}}
"""


def _texto_explicacion(resultado):
    lineas = []
    for n, d in enumerate(resultado.disparos, start=1):
        lineas.append(f"{n}. {d.id} [{d.etapa}] {formatear_regla(d.regla)}")
        lineas.append(f"   Motivo: {d.explicacion}")
    return "\n".join(lineas)


def generar_reporte_html(resultado, empresa="", incluir_explicacion=True, fecha=None):
    """Devuelve el reporte como una página HTML completa (cadena).

    «empresa» es un nombre opcional que solo se muestra; nada se guarda.
    «fecha» (datetime) permite fijar la fecha en las pruebas.
    """
    h = resultado.hechos
    fecha = fecha or datetime.now()
    e = escape
    partes = [
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>",
        "<title>Reporte de riesgo de ciberseguridad</title>",
        f"<style>{_ESTILO}</style></head><body>",
        "<div class='boton'><button onclick='window.print()'>Imprimir o guardar como PDF</button></div>",
        "<h1>Reporte de riesgo de ciberseguridad</h1>",
        f"<p class='meta'>{('Empresa: ' + e(empresa) + ' · ') if empresa else ''}"
        f"Fecha: {fecha:%d/%m/%Y} · Asesor de ciberseguridad para pequeñas empresas</p>",
        f"<p class='global'>Riesgo global: <span class='nivel'>"
        f"{e(NOMBRE_NIVEL.get(resultado.riesgo_global, str(resultado.riesgo_global)))}</span></p>",
        "<h2>1. Nivel de riesgo por área</h2>",
        "<table><tr><th>Área</th><th>Probabilidad (0–100)</th><th>Nivel de riesgo</th></tr>",
    ]
    for area in AREAS:
        partes.append(f"<tr><td>{e(area.capitalize())}</td><td>{h[f'p_{area}']:.1f}</td>"
                      f"<td class='nivel'>{e(NOMBRE_NIVEL[h[f'nivel_p_{area}']])}</td></tr>")
    partes.append("</table>")

    lista = lista_priorizada(resultado)
    partes.append("<h2>2. Recomendaciones priorizadas</h2>")
    if lista:
        partes.append("<table><tr><th>N.º</th><th>Prioridad</th><th>Recomendación</th>"
                      "<th>Área</th><th>Práctica evaluada</th></tr>")
        for i in lista:
            partes.append(f"<tr><td>{i['orden']}</td><td class='nivel'>{e(NOMBRE_PRIORIDAD[i['prioridad']])}</td>"
                          f"<td>{e(i['recomendacion'])}</td><td>{e(i['area'].capitalize())}</td>"
                          f"<td>{e(i['pregunta'])}</td></tr>")
        partes.append("</table>")
    else:
        partes.append("<p>No se encontraron hallazgos: todas las prácticas evaluadas están implementadas.</p>")

    partes.append("<h2>3. Respuestas por verificar</h2>")
    if resultado.verificaciones_solicitadas:
        partes.append("<ul>" + "".join(
            f"<li>Verificar las respuestas «no sé» del área {e(a)}; se contaron como «no» "
            "para ser conservadores.</li>" for a in resultado.verificaciones_solicitadas) + "</ul>")
    else:
        partes.append("<p>No hay respuestas «no sé».</p>")

    riesgo = riesgo_desde_hechos(h)
    if riesgo is not None:
        partes.append("<h2>4. Extensión: impacto, bandas y zona</h2>")
        partes.append("<table><tr><th>Área</th><th>Impacto (0–1)</th><th>Riesgo (0–1)</th><th>Banda</th></tr>")
        for area in AREAS:
            partes.append(f"<tr><td>{e(area.capitalize())}</td><td>{riesgo.impacto[area]:.1f}</td>"
                          f"<td>{riesgo.riesgo_area[area]:.3f}</td><td>{e(riesgo.banda_area[area])}</td></tr>")
        partes.append("</table>")
        partes.append(f"<p>Zona global: <b>{e(riesgo.zona)}</b> · riesgo numérico global "
                      f"{riesgo.riesgo_global:.3f} ({e(riesgo.banda_global)}).</p>")

    partes.append("<h2>Límites de este resultado</h2><div class='aviso'><ul>"
                  + "".join(f"<li>{e(t)}</li>" for t in AVISO_LIMITES) + "</ul></div>")
    if incluir_explicacion:
        partes.append("<h2 class='salto'>Anexo. Reglas aplicadas</h2>"
                      "<p class='meta'>Cada regla indica sus condiciones, su conclusión y su fuente.</p>"
                      f"<pre>{e(_texto_explicacion(resultado))}</pre>")
    partes.append("</body></html>")
    return "".join(partes)
