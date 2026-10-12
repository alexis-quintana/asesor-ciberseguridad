# Informe en PDF del asesor (biblioteca ReportLab).

from __future__ import annotations

import io
import textwrap
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as lienzo
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from app.inferencia.riesgo import AREAS, CORTE_ALTO, CORTE_MEDIO, PUNTAJE, riesgo_desde_hechos
from app.resultados.estadisticas import NOMBRE_RESPUESTA, RESPUESTAS_ORDEN, calcular_estadisticas
from app.resultados.explicacion import armar_detalle, explicar
from app.resultados.reporte import (AVISO_LIMITES, NOMBRE_NIVEL, NOMBRE_PRIORIDAD,
                                    mensaje_sin_recomendaciones, verificaciones_concretas)

TITULO = "Informe de evaluación de riesgo de ciberseguridad"
SISTEMA = "Asesor de ciberseguridad para pequeñas empresas"

# Texto en grises; el color solo aparece en los gráficos.
TINTA = colors.HexColor("#1A1A1A")
SUAVE = colors.HexColor("#555555")
LINEA = colors.HexColor("#BDBDBD")
# Colores de los gráficos (tonos sobrios).
FONDO_NIVEL = {"bajo": colors.HexColor("#E8F1EB"), "medio": colors.HexColor("#F7EFD9"),
               "alto": colors.HexColor("#F3E3E1")}
TEXTO_NIVEL = {"bajo": colors.HexColor("#2F6B4A"), "medio": colors.HexColor("#7A5A10"),
               "alto": colors.HexColor("#8E3A36")}
BARRA_NIVEL = {"bajo": colors.HexColor("#4F8F6B"), "medio": colors.HexColor("#D2A13E"),
               "alto": colors.HexColor("#B4504B")}
COLOR_RESPUESTA = {"si": colors.HexColor("#4F8F6B"), "parcialmente": colors.HexColor("#D2A13E"),
                   "no": colors.HexColor("#B4504B"), "no_se": colors.HexColor("#9A9AA2")}
NIVEL_DE_PRIORIDAD = {"alta": "alto", "media": "medio", "baja": "bajo"}

MARGEN = 22 * mm
ANCHO = A4[0] - 2 * MARGEN

_REEMPLAZOS = {"≥": ">=", "≤": "<=", "→": "->", "−": "-", "“": '"', "”": '"', "’": "'"}


def _t(texto):
    texto = str(texto)
    for original, nuevo in _REEMPLAZOS.items():
        texto = texto.replace(original, nuevo)
    return texto.encode("cp1252", "replace").decode("cp1252")


def _p(texto):
    return escape(_t(texto))


def _estilos():
    serif = dict(fontName="Times-Roman", textColor=TINTA)
    return {
        "portada_sup": ParagraphStyle("portada_sup", fontName="Helvetica", fontSize=10, leading=14,
                                      textColor=SUAVE),
        "portada_titulo": ParagraphStyle("portada_titulo", fontName="Times-Bold", fontSize=27,
                                         leading=33, textColor=TINTA),
        "portada_sub": ParagraphStyle("portada_sub", fontName="Times-Roman", fontSize=14, leading=19,
                                      textColor=SUAVE),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                             textColor=TINTA, spaceBefore=18, spaceAfter=7, keepWithNext=1),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=9.5, leading=13,
                             textColor=TINTA, spaceBefore=9, spaceAfter=3, keepWithNext=1),
        "texto": ParagraphStyle("texto", fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=5, **serif),
        "nota": ParagraphStyle("nota", fontSize=9, leading=12.5, alignment=TA_LEFT, **{**serif, "textColor": SUAVE}),
        "pie_figura": ParagraphStyle("pie_figura", fontName="Times-Italic", fontSize=9, leading=12,
                                     textColor=SUAVE, spaceBefore=3, spaceAfter=10),
        "titulo_tabla": ParagraphStyle("titulo_tabla", fontName="Times-Italic", fontSize=9, leading=12,
                                       textColor=SUAVE, spaceBefore=6, spaceAfter=4, keepWithNext=1),
        "celda": ParagraphStyle("celda", fontName="Helvetica", fontSize=8.6, leading=11.3, textColor=TINTA),
        "celda_negrita": ParagraphStyle("celda_negrita", fontName="Helvetica-Bold", fontSize=8.6,
                                        leading=11.3, textColor=TINTA),
        "celda_suave": ParagraphStyle("celda_suave", fontName="Helvetica", fontSize=7.6, leading=10,
                                      textColor=SUAVE),
        "celda_enc": ParagraphStyle("celda_enc", fontName="Helvetica-Bold", fontSize=8.2, leading=10.5,
                                    textColor=TINTA),
        "toc": ParagraphStyle("toc", fontName="Times-Roman", fontSize=10.5, leading=17, textColor=TINTA),
        "toc_titulo": ParagraphStyle("toc_titulo", fontName="Helvetica-Bold", fontSize=10, leading=14,
                                     textColor=TINTA, spaceAfter=4),
    }


# ----------------------------------------------------------------- gráficos
def _leyenda(d, items, x, y):
    for color, texto in items:
        d.add(Rect(x, y, 8, 8, fillColor=color, strokeColor=None))
        d.add(String(x + 12, y + 0.5, _t(texto), fontName="Helvetica", fontSize=7.5, fillColor=SUAVE))
        x += 18 + len(texto) * 4.1
    return x


def grafico_probabilidad(estad, ancho=ANCHO, alto=112):
    d = Drawing(ancho, alto)
    izq, der, tope, base = 62, 22, 22, 18
    plot = ancho - izq - der
    fila = (alto - tope - base) / len(estad["areas"])
    medio, alto_c = estad["cortes"]["medio"], estad["cortes"]["alto"]

    def x(v):
        return izq + plot * v / 100.0

    for desde, hasta, nivel in ((0, medio, "bajo"), (medio, alto_c, "medio"), (alto_c, 100, "alto")):
        d.add(Rect(x(desde), base, x(hasta) - x(desde), alto - tope - base,
                   fillColor=FONDO_NIVEL[nivel], strokeColor=None))
        d.add(String((x(desde) + x(hasta)) / 2, alto - tope + 8, _t(NOMBRE_NIVEL[nivel].upper()),
                     textAnchor="middle", fontName="Helvetica-Bold", fontSize=7,
                     fillColor=TEXTO_NIVEL[nivel]))
    for v in (0, medio, alto_c, 100):
        d.add(String(x(v), base - 11, str(v), textAnchor="middle", fontName="Helvetica",
                     fontSize=7.5, fillColor=SUAVE))
    for v in (medio, alto_c):
        d.add(Line(x(v), base, x(v), alto - tope, strokeColor=colors.white, strokeWidth=1.2))
    for i, a in enumerate(estad["areas"]):
        yc = alto - tope - fila * (i + 0.5)
        d.add(String(izq - 8, yc - 3, _t(a["area"].capitalize()), textAnchor="end",
                     fontName="Helvetica-Bold", fontSize=8.5, fillColor=TINTA))
        d.add(Rect(x(0), yc - 7, max(x(a["p"]) - x(0), 1), 14,
                   fillColor=BARRA_NIVEL[a["nivel"]], strokeColor=None))
        dentro = x(a["p"]) - x(0) > 34
        d.add(String(x(a["p"]) - 5 if dentro else x(a["p"]) + 5, yc - 3, f"{a['p']:.1f}",
                     textAnchor="end" if dentro else "start", fontName="Helvetica-Bold",
                     fontSize=8.5, fillColor=colors.white if dentro else TINTA))
    return d


def grafico_respuestas(estad, ancho=ANCHO, alto=92):
    d = Drawing(ancho, alto)
    izq, der, tope, base = 62, 22, 22, 4
    plot = ancho - izq - der
    fila = (alto - tope - base) / len(estad["areas"])
    _leyenda(d, [(COLOR_RESPUESTA[r], NOMBRE_RESPUESTA[r]) for r in RESPUESTAS_ORDEN],
             izq, alto - 12)
    for i, a in enumerate(estad["areas"]):
        yc = alto - tope - fila * (i + 0.5)
        d.add(String(izq - 8, yc - 3, _t(a["area"].capitalize()), textAnchor="end",
                     fontName="Helvetica-Bold", fontSize=8.5, fillColor=TINTA))
        x0 = izq
        for r in RESPUESTAS_ORDEN:
            n = a["conteo"][r]
            if not n:
                continue
            w = plot * n / a["total"]
            d.add(Rect(x0, yc - 7, w, 14, fillColor=COLOR_RESPUESTA[r], strokeColor=colors.white,
                       strokeWidth=0.8))
            if w > 14:
                d.add(String(x0 + w / 2, yc - 3, str(n), textAnchor="middle",
                             fontName="Helvetica-Bold", fontSize=8, fillColor=colors.white))
            x0 += w
        d.add(String(izq + plot + 6, yc - 3, f"{a['total']}", fontName="Helvetica", fontSize=8,
                     fillColor=SUAVE))
    return d


def grafico_prioridades(estad, ancho=ANCHO, alto=92):
    d = Drawing(ancho, alto)
    izq, der, tope, base = 62, 22, 22, 4
    plot = ancho - izq - der
    fila = (alto - tope - base) / len(estad["areas"])
    maximo = max([sum(a["recomendaciones"].values()) for a in estad["areas"]] + [1])
    _leyenda(d, [(BARRA_NIVEL[NIVEL_DE_PRIORIDAD[p]], f"Prioridad {NOMBRE_PRIORIDAD[p].lower()}")
                 for p in ("alta", "media", "baja")], izq, alto - 12)
    for i, a in enumerate(estad["areas"]):
        yc = alto - tope - fila * (i + 0.5)
        d.add(String(izq - 8, yc - 3, _t(a["area"].capitalize()), textAnchor="end",
                     fontName="Helvetica-Bold", fontSize=8.5, fillColor=TINTA))
        x0 = izq
        for p in ("alta", "media", "baja"):
            n = a["recomendaciones"][p]
            if not n:
                continue
            w = plot * n / maximo
            d.add(Rect(x0, yc - 7, w, 14, fillColor=BARRA_NIVEL[NIVEL_DE_PRIORIDAD[p]],
                       strokeColor=colors.white, strokeWidth=0.8))
            if w > 12:
                d.add(String(x0 + w / 2, yc - 3, str(n), textAnchor="middle",
                             fontName="Helvetica-Bold", fontSize=8, fillColor=colors.white))
            x0 += w
        d.add(String(x0 + 6, yc - 3, f"{sum(a['recomendaciones'].values())}", fontName="Helvetica",
                     fontSize=8, fillColor=SUAVE))
    return d


# ------------------------------------------------------------------ bloques
class _Numerador:

    def __init__(self):
        self.seccion = self.tabla = self.figura = 0

    def sec(self, titulo):
        self.seccion += 1
        return f"{self.seccion}. {titulo}"

    def tab(self, texto, estilos, largo=False):
        self.tabla += 1
        estilo = estilos["titulo_tabla"]
        if largo:
            estilo = ParagraphStyle("titulo_tabla_largo", parent=estilo, keepWithNext=0)
        return Paragraph(f"<b>Tabla {self.tabla}.</b> {_p(texto)}", estilo)

    def fig(self, grafico, texto, estilos):
        self.figura += 1
        return KeepTogether([grafico, Paragraph(f"<b>Figura {self.figura}.</b> {_p(texto)}",
                                                estilos["pie_figura"])])


def _tabla(filas, anchos, estilos_extra=(), repetir=1):
    t = Table(filas, colWidths=anchos, repeatRows=repetir)
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("TEXTCOLOR", (0, 0), (-1, -1), TINTA),
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, TINTA),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, TINTA),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINEA),
        ("LINEBELOW", (0, -1), (-1, -1), 1.0, TINTA),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(estilo + list(estilos_extra)))
    return t


def _enc(estilos, textos):
    return [Paragraph(_p(e), estilos["celda_enc"]) for e in textos]


def _fila_datos(estilos, a, b):
    return [Paragraph(f"<b>{_p(a)}</b>", estilos["celda"]), Paragraph(_p(b), estilos["celda"])]


def _portada(estilos, resultado, empresa, fecha, toc):
    d = armar_detalle(resultado)["global"]
    datos = [
        _fila_datos(estilos, "Sistema", f"{SISTEMA} (sistema experto basado en reglas)"),
        _fila_datos(estilos, "Empresa evaluada", empresa or "No indicada"),
        _fila_datos(estilos, "Fecha de emisión", f"{fecha:%d/%m/%Y}"),
        _fila_datos(estilos, "Método de inferencia", "Encadenamiento hacia adelante, por etapas"),
        _fila_datos(estilos, "Reglas disparadas", f"{len(resultado.disparos)}"),
        _fila_datos(estilos, "Resultado global", f"Riesgo {NOMBRE_NIVEL[resultado.riesgo_global].lower()} "
                    f"(regla {d['regla']})" if d["regla"] else
                    f"Riesgo {NOMBRE_NIVEL[resultado.riesgo_global].lower()}"),
    ]
    tabla = Table(datos, colWidths=[ANCHO * 0.30, ANCHO * 0.70])
    tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LINEABOVE", (0, 0), (-1, 0), 1.0, TINTA),
                               ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINEA),
                               ("LINEBELOW", (0, -1), (-1, -1), 1.0, TINTA),
                               ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                               ("LEFTPADDING", (0, 0), (-1, -1), 5)]))
    return [
        Spacer(1, 18 * mm),
        Paragraph("INFORME TÉCNICO", estilos["portada_sup"]),
        Spacer(1, 6),
        Paragraph(_p(TITULO), estilos["portada_titulo"]),
        Spacer(1, 6),
        Paragraph(_p(SISTEMA), estilos["portada_sub"]),
        Spacer(1, 14 * mm),
        tabla,
        Spacer(1, 12 * mm),
        Paragraph("CONTENIDO", estilos["toc_titulo"]),
        toc,
        Spacer(1, 8 * mm),
        Paragraph("Este informe fue emitido por un sistema experto a partir de las respuestas "
                  "declaradas por el usuario. Tiene carácter orientativo y no reemplaza a una "
                  "auditoría ni a un especialista en ciberseguridad.", estilos["nota"]),
        PageBreak(),
    ]


def _lista_areas(areas, nivel):
    nombres = [a["area"].capitalize() for a in areas if a["nivel"] == nivel]
    if not nombres:
        return ""
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _resumen(estilos, resultado, estad, num):
    nivel = NOMBRE_NIVEL[estad["global_nivel"]].lower()
    n_pract = sum(a["total"] for a in estad["areas"])
    pri = estad["prioridades"]
    frases = [f"La evaluación consideró {n_pract} prácticas de ciberseguridad agrupadas en "
              f"{len(estad['areas'])} áreas. El riesgo global resultante es <b>{nivel}</b>."]
    for nv in ("alto", "medio", "bajo"):
        lista = _lista_areas(estad["areas"], nv)
        if lista:
            frases.append(f"Riesgo {nv}: {lista}.")
    if estad["n_recomendaciones"]:
        frases.append(f"El sistema formuló {estad['n_recomendaciones']} recomendaciones: "
                      f"{pri['alta']} de prioridad alta, {pri['media']} de prioridad media y "
                      f"{pri['baja']} de prioridad baja.")
    if estad["n_verificar"]:
        frases.append(f"Se registraron {estad['n_verificar']} respuesta(s) «No sé»; se contaron como «No» "
                      "para el cálculo y deben verificarse.")
    reg = armar_detalle(resultado)["global"]["regla"]
    filas = [_enc(estilos, ["Indicador", "Resultado"]),
             _fila_datos(estilos, "Riesgo global", NOMBRE_NIVEL[estad["global_nivel"]] + (f" (regla {reg})" if reg else "")),
             _fila_datos(estilos, "Áreas con riesgo alto / medio / bajo",
                         f"{estad['areas_alto']} / {estad['areas_medio']} / "
                         f"{len(estad['areas']) - estad['areas_alto'] - estad['areas_medio']}"),
             _fila_datos(estilos, "Recomendaciones (alta / media / baja)",
                         f"{estad['n_recomendaciones']} ({pri['alta']} / {pri['media']} / {pri['baja']})"),
             _fila_datos(estilos, "Respuestas «No sé»", str(estad["n_verificar"]))]
    return [Paragraph(num.sec("Resumen ejecutivo"), estilos["h2"]),
            Paragraph(" ".join(_p(f) if "<b>" not in f else f for f in frases), estilos["texto"]),
            num.tab("Indicadores principales del resultado.", estilos),
            _tabla(filas, [ANCHO * 0.58, ANCHO * 0.42])]


def _metodologia(estilos, resultado, estad, num):
    det = armar_detalle(resultado)["global"]
    p = PUNTAJE
    parrafos = [
        "El sistema evalúa 48 prácticas de ciberseguridad, 12 por cada una de las cuatro áreas "
        "(cuentas, respaldos, correo y redes). Cada respuesta se convierte en un puntaje de riesgo: "
        f"Sí = {p['si']:g}, Parcialmente = {p['parcialmente']:g}, No = {p['no']:g} y No sé = {p['no_se']:g} "
        "(la respuesta «No sé» se trata como «No», por prudencia). La probabilidad de riesgo de cada "
        "área es el promedio de los 12 puntajes de sus prácticas, en una escala de 0 a 100.",
        f"El nivel de cada área es bajo si la probabilidad es menor que {CORTE_MEDIO}, medio si es "
        f"menor que {CORTE_ALTO} y alto desde {CORTE_ALTO}. El esquema de puntajes y rangos sigue a "
        "Sihwi et al. (2016); los valores puntuales y los cortes son una adaptación del equipo.",
        "El riesgo global se concluye mediante reglas que cuentan las áreas con riesgo alto y medio"
        + (f". En este caso se aplicó la regla {det['regla']} ({det['motivo'].split(': ', 1)[-1].rstrip('.')})." if det["regla"] else "."),
        "Las recomendaciones se ordenan por prioridad (alta, media o baja) según el nivel de riesgo "
        "del área y la criticidad de cada práctica.",
    ]
    return [Paragraph(num.sec("Alcance y metodología"), estilos["h2"])] + [
        Paragraph(_p(t), estilos["texto"]) for t in parrafos]


def _tabla_areas(estilos, estad):
    filas = [_enc(estilos, ["Área", "Sí", "Parc.", "No", "No sé", "Probabilidad (0–100)", "Nivel de riesgo"])]
    for a in estad["areas"]:
        c = a["conteo"]
        filas.append([Paragraph(f"<b>{_p(a['area'].capitalize())}</b>", estilos["celda"]),
                      str(c["si"]), str(c["parcialmente"]), str(c["no"]), str(c["no_se"]),
                      f"{a['p']:.1f}", Paragraph(_p(NOMBRE_NIVEL[a["nivel"]]), estilos["celda_negrita"])])
    return _tabla(filas, [ANCHO * 0.17, ANCHO * 0.08, ANCHO * 0.09, ANCHO * 0.08, ANCHO * 0.09,
                          ANCHO * 0.26, ANCHO * 0.23])


def _resultados(estilos, estad, num):
    return [Paragraph(num.sec("Resultados por área"), estilos["h2"]),
            Paragraph(_p(f"La Tabla {num.tabla + 1} resume las respuestas y el nivel de riesgo de cada área; "
                         f"la Figura {num.figura + 1} muestra la probabilidad calculada sobre las zonas de "
                         "riesgo bajo, medio y alto."), estilos["texto"]),
            num.tab("Respuestas, probabilidad y nivel de riesgo por área.", estilos),
            _tabla_areas(estilos, estad),
            Spacer(1, 12),
            num.fig(grafico_probabilidad(estad),
                    "Probabilidad de riesgo por área (escala de 0 a 100).", estilos),
            num.fig(grafico_respuestas(estad),
                    "Distribución de las respuestas por área (número de prácticas).", estilos)]


def _tabla_recomendaciones(estilos, estad):
    filas = [_enc(estilos, ["N.º", "Prioridad", "Recomendación", "Área"])]
    for it in estad["recomendaciones"]:
        filas.append([str(it["orden"]),
                      Paragraph(_p(NOMBRE_PRIORIDAD[it["prioridad"]]), estilos["celda_negrita"]),
                      [Paragraph(_p(it["recomendacion"]), estilos["celda"]),
                       Paragraph(_p(it["pregunta"]), estilos["celda_suave"])],
                      Paragraph(_p(it["area"].capitalize()), estilos["celda"])])
    return _tabla(filas, [ANCHO * 0.07, ANCHO * 0.13, ANCHO * 0.62, ANCHO * 0.18])


def _recomendaciones(estilos, resultado, estad, num):
    out = [Paragraph(num.sec("Recomendaciones priorizadas"), estilos["h2"])]
    if not estad["recomendaciones"]:
        out.append(Paragraph(_p(mensaje_sin_recomendaciones(resultado)), estilos["texto"]))
        return out
    out += [Paragraph(_p(f"Se formularon {estad['n_recomendaciones']} recomendaciones. La Figura "
                         f"{num.figura + 1} las distribuye por área y prioridad; la Tabla {num.tabla + 1} "
                         "las lista en orden de ejecución, con la práctica evaluada de la que provienen."),
                      estilos["texto"]),
            num.fig(grafico_prioridades(estad), "Recomendaciones por área y prioridad.", estilos),
            num.tab("Recomendaciones en orden de prioridad.", estilos, largo=True),
            _tabla_recomendaciones(estilos, estad)]
    return out


def _verificaciones(estilos, resultado, num):
    out = [Paragraph(num.sec("Respuestas por verificar"), estilos["h2"])]
    if not resultado.verificaciones_solicitadas:
        return out + [Paragraph("No hay respuestas «No sé».", estilos["texto"])]
    out.append(Paragraph("Estas respuestas «No sé» se contaron como «No» solo para calcular el riesgo, "
                         "sin afirmar que falte la práctica. Verifíquelas así:", estilos["texto"]))
    for grupo in verificaciones_concretas(resultado):
        out.append(Paragraph(_p(grupo["area"].capitalize()), estilos["h3"]))
        filas = [[Paragraph(_p(p["pregunta"]), estilos["celda"]),
                  Paragraph(_p(p["verificar"]), estilos["celda_suave"])] for p in grupo["preguntas"]]
        t = Table(filas, colWidths=[ANCHO * 0.5, ANCHO * 0.5])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINEA),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                               ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
        out.append(t)
    return out


def _extension(estilos, resultado, num):
    riesgo = riesgo_desde_hechos(resultado.hechos)
    if riesgo is None:
        return []
    filas = [_enc(estilos, ["Área", "Impacto (0–1)", "Riesgo (0–1)", "Banda"])]
    for a in AREAS:
        filas.append([Paragraph(f"<b>{_p(a.capitalize())}</b>", estilos["celda"]),
                      f"{riesgo.impacto[a]:.1f}", f"{riesgo.riesgo_area[a]:.3f}",
                      _t(riesgo.banda_area[a].replace("_", " "))])
    banda_global = riesgo.banda_global.replace("_", " ")
    return [Paragraph(num.sec("Extensión: impacto, bandas y zona"), estilos["h2"]),
            num.tab("Impacto declarado y riesgo numérico por área.", estilos),
            _tabla(filas, [ANCHO * 0.3, ANCHO * 0.23, ANCHO * 0.23, ANCHO * 0.24]),
            Spacer(1, 6),
            Paragraph(f"Zona global: <b>{_p(riesgo.zona)}</b>. Riesgo numérico global "
                      f"{riesgo.riesgo_global:.3f} ({_p(banda_global)}).", estilos["texto"])]


def _limites(estilos, num):
    return [Paragraph(num.sec("Limitaciones del resultado"), estilos["h2"])] + [
        Paragraph(f"{i}. {_p(t)}", estilos["texto"]) for i, t in enumerate(AVISO_LIMITES, start=1)]


def _anexo(estilos, resultado):
    lineas = []
    for linea in _t(explicar(resultado)).splitlines():
        sangria = len(linea) - len(linea.lstrip())
        lineas.extend(textwrap.wrap(linea, 112, subsequent_indent=" " * (sangria + 4),
                                    initial_indent="", break_long_words=True) or [""])
    estilo = ParagraphStyle("pre", fontName="Courier", fontSize=6.6, leading=8.2, textColor=TINTA)
    return [PageBreak(),
            Paragraph("Anexo A. Reglas aplicadas", estilos["h2"]),
            Paragraph("Cada regla indica sus condiciones, su conclusión y su fuente.", estilos["nota"]),
            Spacer(1, 6),
            Preformatted("\n".join(lineas), estilo)]


# -------------------------------------------------------------------- página
class _Documento(SimpleDocTemplate):

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "h2":
            self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))


class _LienzoNumerado(lienzo.Canvas):

    pie_fecha = ""
    encabezado = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._decorar(total)
            super().showPage()
        super().save()

    def _decorar(self, total):
        self.setStrokeColor(LINEA)
        self.setLineWidth(0.5)
        self.setFillColor(SUAVE)
        if self._pageNumber > 1:
            self.setFont("Helvetica", 7.8)
            self.drawString(MARGEN, A4[1] - 13 * mm, _t(TITULO))
            self.drawRightString(A4[0] - MARGEN, A4[1] - 13 * mm, _t(self.encabezado))
            self.line(MARGEN, A4[1] - 15 * mm, A4[0] - MARGEN, A4[1] - 15 * mm)
        self.line(MARGEN, 15 * mm, A4[0] - MARGEN, 15 * mm)
        self.setFont("Helvetica", 7.8)
        self.drawString(MARGEN, 10.5 * mm, _t(f"{SISTEMA} · {self.pie_fecha}"))
        self.drawRightString(A4[0] - MARGEN, 10.5 * mm, f"Página {self._pageNumber} de {total}")


def generar_reporte_pdf(resultado, empresa="", incluir_explicacion=True, fecha=None):
    fecha = fecha or datetime.now()
    estilos = _estilos()
    estad = calcular_estadisticas(resultado)
    num = _Numerador()
    memoria = io.BytesIO()
    doc = _Documento(
        memoria, pagesize=A4, leftMargin=MARGEN, rightMargin=MARGEN, topMargin=22 * mm,
        bottomMargin=22 * mm, title=TITULO, author=SISTEMA, subject="Diagnóstico de ciberseguridad",
        creator=SISTEMA)
    toc = TableOfContents()
    toc.dotsMinLevel = 0
    toc.levelStyles = [ParagraphStyle("toc0", parent=estilos["toc"], leftIndent=0, rightIndent=14)]

    historia = _portada(estilos, resultado, empresa, fecha, toc)
    historia += _resumen(estilos, resultado, estad, num)
    historia += _metodologia(estilos, resultado, estad, num)
    historia += _resultados(estilos, estad, num)
    historia += _recomendaciones(estilos, resultado, estad, num)
    historia += _verificaciones(estilos, resultado, num)
    historia += _extension(estilos, resultado, num)
    historia += _limites(estilos, num)
    if incluir_explicacion:
        historia += _anexo(estilos, resultado)

    class Lienzo(_LienzoNumerado):
        pie_fecha = f"Emitido el {fecha:%d/%m/%Y}"
        encabezado = empresa or ""

    doc.multiBuild(historia, canvasmaker=Lienzo)
    return memoria.getvalue()
