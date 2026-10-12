# Reporte imprimible del asesor.

from __future__ import annotations

from datetime import datetime
from html import escape

from app.conocimiento.ayudas import ayuda
from app.conocimiento.base_conocimientos import VARIABLES
from app.resultados.estadisticas import NOMBRE_RESPUESTA, calcular_estadisticas
from app.resultados.explicacion import explicar
from app.inferencia.riesgo import AREAS, riesgo_desde_hechos

# Límites del sistema (sección 3.8 del informe); se muestran en la web, el reporte y la consola.
AVISO_LIMITES = (
    "Este resultado orienta y no reemplaza a un especialista ni a una auditoría; "
    "un riesgo bajo no garantiza que la empresa esté protegida.",
    "Las respuestas son autodeclaradas y pueden sobrestimar la seguridad real "
    "(Chidukwani et al., 2026); las respuestas «no sé» se contaron como «no» solo para "
    "calcular el riesgo, sin afirmar que falte la práctica.",
    "El conocimiento proviene de la literatura revisada y no fue validado por un "
    "experto en ciberseguridad.",
    "La prioridad no considera el costo ni el esfuerzo de cada medida.",
)

NOMBRE_NIVEL = {"bajo": "Bajo", "medio": "Medio", "alto": "Alto"}
NOMBRE_PRIORIDAD = {"alta": "Alta", "media": "Media", "baja": "Baja"}

_ESTILO = """
:root{--tinta:#1d1d1f;--suave:#5c5c63;--linea:#e3e3e8;--fondo:#f5f5f7;--brand:#3a3a3f;
--bajo:#14693d;--bajo-f:#e6f4ec;--medio:#8a5300;--medio-f:#fff3d9;--alto:#b3261e;--alto-f:#fdeceb;
--b-bajo:#2e9e5b;--b-medio:#e0a100;--b-alto:#c9392f;--b-nose:#8e8e96}
*{box-sizing:border-box}
body{font-family:"Times New Roman",Times,Georgia,serif;
color:var(--tinta);max-width:860px;margin:0 auto;padding:0 20px 40px;line-height:1.55;font-size:16px;background:#fff}
h1,h2,h3,th,.eyebrow,.kpi,.leyenda,table,.boton button,.fila{font-family:Arial,Helvetica,sans-serif}
body{padding-top:24px}
.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.08em;color:var(--brand);text-transform:uppercase;margin:0 0 4px}
h1{font-family:"Times New Roman",Times,serif;font-size:2rem;line-height:1.15;margin:0 0 4px}
h2{font-size:1.2rem;margin:30px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--brand)}
h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:var(--suave);margin:18px 0 6px}
.meta{color:var(--suave);font-size:.9rem;margin:0 0 18px}.suave{color:var(--suave);font-size:.88rem}
.kpis{display:grid;grid-template-columns:1.5fr repeat(4,1fr);gap:10px;margin:6px 0 4px}
.kpi{background:none;padding:10px 12px;border:1px solid var(--linea);border-radius:0;border-top:2px solid var(--tinta)}
.kpi .r{font-size:.66rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--suave)}
.kpi .c{font-size:1.9rem;font-weight:700;line-height:1.15}.kpi .n{font-size:.78rem;color:var(--suave)}
.global{margin:0}.nivel{font-weight:700}
table{border-collapse:collapse;width:100%;font-size:.9rem;margin:8px 0}
th{background:var(--fondo);text-align:left;font-size:.75rem;color:var(--suave);border-bottom:2px solid var(--brand)}
th,td{padding:7px 9px;vertical-align:top;border-bottom:1px solid var(--linea)}
.sub{display:block;color:var(--suave);font-size:.8rem}
.graf{margin:8px 0}.graf svg{width:100%;height:auto;display:block}
.leyenda{display:flex;gap:14px;flex-wrap:wrap;font-size:.78rem;color:var(--suave);margin:2px 0 6px}
.leyenda i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.fila{display:grid;grid-template-columns:90px 1fr 34px;align-items:center;gap:8px;margin:5px 0;font-size:.85rem}
.fila b{font-size:.85rem}.apilada{display:flex;height:18px;border-radius:3px;overflow:hidden}
.apilada span{color:#fff;font-size:.72rem;font-weight:700;text-align:center;line-height:18px;border-right:1px solid #fff}
.aviso{border-left:4px solid var(--brand);background:var(--fondo);padding:8px 16px;font-size:.88rem;border-radius:0 8px 8px 0}
.aviso li{margin:4px 0}
pre{white-space:pre-wrap;font-size:.74rem;background:var(--fondo);padding:10px;border:1px solid var(--linea);border-radius:8px}
.boton{margin:14px 0 4px;text-align:right}.boton button{font-size:.85rem;padding:8px 16px;border:1px solid var(--tinta);border-radius:0;background:#fff;color:var(--tinta);cursor:pointer}
@media print{.boton{display:none}body{max-width:none;padding:0}h2{break-after:avoid}tr,.kpi,.graf{break-inside:avoid}.salto{break-before:page}
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
@media(max-width:640px){.kpis{grid-template-columns:1fr 1fr}}
"""

_COLOR_NIVEL = {"bajo": "#2e9e5b", "medio": "#e0a100", "alto": "#c9392f"}
_COLOR_RESPUESTA = {"si": "#2e9e5b", "parcialmente": "#e0a100", "no": "#c9392f", "no_se": "#8e8e96"}
_NIVEL_PRIORIDAD = {"alta": "alto", "media": "medio", "baja": "bajo"}


def _svg_probabilidad(estad):
    medio, alto = estad["cortes"]["medio"], estad["cortes"]["alto"]
    izq, ancho, fila, tope = 90, 640, 34, 22
    alto_total = tope + fila * len(estad["areas"]) + 22
    x = lambda v: izq + ancho * v / 100.0
    o = [f"<svg viewBox='0 0 {izq + ancho + 20} {alto_total}' role='img' "
         f"aria-label='Probabilidad de riesgo por área'>"]
    for d, h, c, nombre in ((0, medio, "#e6f4ec", "BAJO"), (medio, alto, "#fff3d9", "MEDIO"),
                            (alto, 100, "#fdeceb", "ALTO")):
        o.append(f"<rect x='{x(d):.1f}' y='{tope}' width='{x(h) - x(d):.1f}' "
                 f"height='{fila * len(estad['areas'])}' fill='{c}'/>"
                 f"<text x='{(x(d) + x(h)) / 2:.1f}' y='14' text-anchor='middle' font-size='10' "
                 f"font-weight='700' fill='#5c5c63'>{nombre}</text>")
    for v in (0, medio, alto, 100):
        o.append(f"<text x='{x(v):.1f}' y='{alto_total - 6}' text-anchor='middle' font-size='10' "
                 f"fill='#5c5c63'>{v}</text>")
    for i, a in enumerate(estad["areas"]):
        yc = tope + fila * (i + 0.5)
        o.append(f"<text x='{izq - 10}' y='{yc + 4:.1f}' text-anchor='end' font-size='12' "
                 f"font-weight='700'>{escape(a['area'].capitalize())}</text>"
                 f"<rect x='{x(0):.1f}' y='{yc - 10:.1f}' width='{max(x(a['p']) - x(0), 1):.1f}' height='20' "
                 f"rx='3' fill='{_COLOR_NIVEL[a['nivel']]}'/>"
                 f"<text x='{x(a['p']) - 8:.1f}' y='{yc + 4:.1f}' text-anchor='end' font-size='12' "
                 f"font-weight='700' fill='#fff'>{a['p']:.1f}</text>")
    o.append("</svg>")
    return "".join(o)


def _barras_apiladas(estad, clave, orden, color, rotulo, total):
    filas = []
    for a in estad["areas"]:
        valores = a[clave]
        base = total(a)
        segmentos = "".join(
            f"<span style='width:{100.0 * valores[k] / base:.2f}%;background:{color(k)}' "
            f"title='{escape(rotulo(k))}: {valores[k]}'>{valores[k] if 100.0 * valores[k] / base >= 7 else ''}</span>"
            for k in orden if valores[k])
        filas.append(f"<div class='fila'><b>{escape(a['area'].capitalize())}</b>"
                     f"<div class='apilada'>{segmentos}</div><span class='suave'>{sum(valores.values())}</span></div>")
    leyenda = "".join(f"<span><i style='background:{color(k)}'></i>{escape(rotulo(k))}</span>" for k in orden)
    return f"<div class='leyenda'>{leyenda}</div>" + "".join(filas)


def mensaje_sin_recomendaciones(resultado):
    if resultado.prioridades or resultado.recomendaciones_adicionales:
        return None
    desconocidas = resultado.hechos.get("respuestas_desconocidas", 0)
    if desconocidas:
        return (f"No se generaron recomendaciones porque no hubo respuestas «No» ni "
                f"«Parcialmente». Hay {desconocidas} respuesta(s) «No sé»: no permiten saber "
                "qué falta, pero se contaron como «No» al calcular el riesgo. "
                "Verifíquelas con las indicaciones de abajo.")
    return ("Según sus respuestas, todas las prácticas evaluadas están implementadas («Sí»). "
            "Esto no garantiza que la empresa esté protegida.")


def verificaciones_concretas(resultado):
    grupos = []
    for area in AREAS:
        preguntas = [{"clave": c, "pregunta": v["pregunta"], "verificar": ayuda(c)["verificar"]}
                     for c, v in VARIABLES.items()
                     if v["area"] == area and resultado.hechos.get(c) == "no_se"]
        if preguntas:
            grupos.append({"area": area, "preguntas": preguntas})
    return grupos


def generar_reporte_html(resultado, empresa="", incluir_explicacion=True, fecha=None):
    h = resultado.hechos
    fecha = fecha or datetime.now()
    e = escape
    est = calcular_estadisticas(resultado)
    nivel = est["global_nivel"]
    pri = est["prioridades"]
    partes = [
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>Informe de evaluación de riesgo de ciberseguridad</title>",
        f"<style>{_ESTILO}</style></head><body>",
        "<div class='boton'><button onclick='window.print()'>Imprimir o guardar como PDF</button></div>",
        "<p class='eyebrow'>Asesor de ciberseguridad para pequeñas empresas</p>",
        "<h1>Informe de evaluación de riesgo de ciberseguridad</h1>",
        f"<p class='meta'>{('Empresa: ' + e(empresa) + ' · ') if empresa else ''}Fecha: {fecha:%d/%m/%Y}</p>",
        "<div class='kpis'>",
        f"<div class='kpi g-{nivel}'><div class='r'>Riesgo global</div>"
        f"<div class='c t-{nivel}'>{e(NOMBRE_NIVEL.get(nivel, str(nivel)))}</div>"
        f"<div class='n'>{est['areas_alto']} área(s) alta(s) y {est['areas_medio']} media(s)</div></div>",
        f"<div class='kpi'><div class='r'>Medidas</div><div class='c'>{est['n_recomendaciones']}</div>"
        "<div class='n'>recomendadas, por prioridad</div></div>",
        f"<div class='kpi'><div class='r'>Prioridad alta</div><div class='c t-alto'>{pri['alta']}</div>"
        "<div class='n'>conviene empezar aquí</div></div>",
        f"<div class='kpi'><div class='r'>Media y baja</div><div class='c'>{pri['media']} + {pri['baja']}</div>"
        "<div class='n'>para planificar</div></div>",
        f"<div class='kpi'><div class='r'>Por verificar</div><div class='c'>{est['n_verificar']}</div>"
        "<div class='n'>respuestas «No sé»</div></div>",
        "</div>",
        "<h2>1. Nivel de riesgo por área</h2>",
        f"<p class='suave'>La probabilidad de cada área es el promedio de los puntajes de sus 12 prácticas "
        f"(bajo si es menor que {est['cortes']['medio']}, medio si es menor que {est['cortes']['alto']} y alto "
        f"desde {est['cortes']['alto']}). A más puntos, más riesgo.</p>",
        f"<div class='graf'>{_svg_probabilidad(est)}</div>",
        "<table><tr><th>Área</th><th>Sí</th><th>Parc.</th><th>No</th><th>No sé</th>"
        "<th>Probabilidad (0–100)</th><th>Nivel de riesgo</th></tr>",
    ]
    for a in est["areas"]:
        c = a["conteo"]
        partes.append(f"<tr><td><b>{e(a['area'].capitalize())}</b></td><td>{c['si']}</td>"
                      f"<td>{c['parcialmente']}</td><td>{c['no']}</td><td>{c['no_se']}</td>"
                      f"<td>{a['p']:.1f}</td>"
                      f"<td class='{a['nivel']} nivel'>{e(NOMBRE_NIVEL[a['nivel']])}</td></tr>")
    partes.append("</table>")
    partes.append("<h3>Respuestas por área</h3>")
    partes.append(_barras_apiladas(est, "conteo", ("si", "parcialmente", "no", "no_se"),
                                   lambda k: _COLOR_RESPUESTA[k], lambda k: NOMBRE_RESPUESTA[k],
                                   lambda a: a["total"]))

    lista = est["recomendaciones"]
    partes.append("<h2>2. Recomendaciones priorizadas</h2>")
    if lista:
        maximo = max(sum(a["recomendaciones"].values()) for a in est["areas"]) or 1
        partes.append("<h3>Recomendaciones por área y prioridad</h3>")
        partes.append(_barras_apiladas(
            est, "recomendaciones", ("alta", "media", "baja"),
            lambda k: _COLOR_NIVEL[_NIVEL_PRIORIDAD[k]], lambda k: f"Prioridad {NOMBRE_PRIORIDAD[k].lower()}",
            lambda a: maximo))
        partes.append("<table><tr><th>N.º</th><th>Prioridad</th><th>Recomendación</th><th>Área</th></tr>")
        for i in lista:
            partes.append(f"<tr><td>{i['orden']}</td>"
                          f"<td class='{i['prioridad']} nivel'>{e(NOMBRE_PRIORIDAD[i['prioridad']])}</td>"
                          f"<td>{e(i['recomendacion'])}<span class='sub'>{e(i['pregunta'])}</span></td>"
                          f"<td>{e(i['area'].capitalize())}</td></tr>")
        partes.append("</table>")
    else:
        partes.append(f"<p>{e(mensaje_sin_recomendaciones(resultado))}</p>")

    partes.append("<h2>3. Respuestas por verificar</h2>")
    if resultado.verificaciones_solicitadas:
        partes.append("<p>Estas respuestas «no sé» se contaron como «no» solo para calcular "
                      "el riesgo, sin afirmar que falte la práctica. Verifíquelas así:</p><ul>")
        for grupo in verificaciones_concretas(resultado):
            partes.append(f"<li><b>{e(grupo['area'].capitalize())}</b><ul>" + "".join(
                f"<li>{e(p['pregunta'])} <i>{e(p['verificar'])}</i></li>"
                for p in grupo["preguntas"]) + "</ul></li>")
        partes.append("</ul>")
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
                      "<p class='suave'>Cada regla indica sus condiciones, su conclusión y su fuente.</p>"
                      f"<pre>{e(explicar(resultado))}</pre>")
    partes.append("</body></html>")
    return "".join(partes)
