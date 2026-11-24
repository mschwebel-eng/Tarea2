"""
crear_pptx.py - Presentacion de 10 minutos (11 diapositivas + 1 de reserva) en .pptx, para abrir y editar en Google Presentaciones.

Fuentes Arial (disponible en Google Presentaciones). Figuras de productos/punto1/figuras y productos/punto2/figuras; la grafica
mensual (diapositiva 4) y la de reforestacion (reserva) son graficas nativas editables.
Salida: productos/presentacion/T2_202602_GNN_presentacion.pptx
"""
from pathlib import Path

import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parents[2]
F1, F2 = RAIZ / "productos/punto1/figuras", RAIZ / "productos/punto2/figuras"
OUT = RAIZ / "productos/presentacion"; OUT.mkdir(parents=True, exist_ok=True)

OSCURO, ACENTO, PIZARRA, TINTE, BLANCO, TEXTO = (RGBColor(0x0F, 0x3D, 0x4C), RGBColor(0xC2, 0x45, 0x2A), RGBColor(0x5B, 0x64, 0x75),
                                               RGBColor(0xEC, 0xF2, 0xF4), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0x1F, 0x29, 0x33))
AGUA = RGBColor(0x1D, 0x6F, 0x8C)
FUENTE = "Arial"
W, H = 13.333, 7.5

prs = Presentation(); prs.slide_width, prs.slide_height = Inches(W), Inches(H)
VACIA = prs.slide_layouts[6]


def texto(sl, x, y, w, h, parrafos, size=16, color=TEXTO, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, nombre=None):
    """parrafos: str o lista de str / lista de (texto, dict) por parrafo; cada parrafo puede ser lista de runs (texto, opciones)."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if nombre:
        tb.name = nombre
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.03)
    if isinstance(parrafos, str):
        parrafos = [parrafos]
    for k, par in enumerate(parrafos):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(6)
        runs = par if isinstance(par, list) else [(par, {})]
        for t, op in runs:
            r = p.add_run(); r.text = t
            f = r.font; f.name = FUENTE; f.size = Pt(op.get("size", size)); f.bold = op.get("bold", bold)
            f.italic = op.get("italic", False); f.color.rgb = op.get("color", color)
    return tb


def fondo(sl, color):
    bg = sl.background.fill; bg.solid(); bg.fore_color.rgb = color


def titulo(sl, t, sub=None):
    texto(sl, 0.6, 0.35, W - 1.2, 0.8, t, size=30, bold=True, color=OSCURO, nombre="Titulo")
    if sub:
        texto(sl, 0.6, 1.08, W - 1.2, 0.4, sub, size=15, color=PIZARRA, nombre="Subtitulo")


def figura(sl, ruta, x, y, w_max, h_max):
    iw, ih = Image.open(ruta).size; r = iw / ih
    w = min(w_max, h_max * r); h = w / r
    pic = sl.shapes.add_picture(str(ruta), Inches(x + (w_max - w) / 2), Inches(y), Inches(w), Inches(h))
    pic.name = ruta.stem
    return y + h


def tarjeta(sl, x, y, w, h, cifra, etiqueta, color_cifra=ACENTO):
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.12; s.fill.solid(); s.fill.fore_color.rgb = TINTE; s.line.fill.background(); s.shadow.inherit = False
    s.name = "Tarjeta"
    texto(sl, x + 0.15, y + 0.08, w - 0.3, 0.62, cifra, size=26, bold=True, color=color_cifra)
    texto(sl, x + 0.15, y + 0.68, w - 0.3, h - 0.74, etiqueta, size=13, color=TEXTO)


def tarjetas(sl, items, y=5.55, h=1.45):
    n = len(items); gap = 0.3; w = (W - 1.2 - gap * (n - 1)) / n
    for k, (c, e) in enumerate(items):
        tarjeta(sl, 0.6 + k * (w + gap), y, w, h, c, e)


def pie(sl, t):
    texto(sl, 0.6, H - 0.42, W - 1.2, 0.3, t, size=10, color=PIZARRA, nombre="Fuente")


def notas(sl, t):
    sl.notes_slide.notes_text_frame.text = t


def estandar(t, sub, fig, items, fuente, nota):
    sl = prs.slides.add_slide(VACIA); titulo(sl, t, sub)
    figura(sl, fig, 0.6, 1.55, W - 1.2, 3.85)
    tarjetas(sl, items); pie(sl, fuente); notas(sl, nota)
    return sl


def lateral(t, sub, fig, items, fuente, nota, recorte=None):
    sl = prs.slides.add_slide(VACIA); titulo(sl, t, sub)
    if recorte:
        im = Image.open(fig); im = im.crop((0, 0, int(im.size[0] * recorte), im.size[1]))
        fig = OUT / f"{fig.stem}_recorte.png"; im.save(fig)
    figura(sl, fig, 0.6, 1.65, 7.9, 5.2)
    for k, (c, e) in enumerate(items):
        tarjeta(sl, 8.85, 1.65 + k * 1.72, 3.9, 1.52, c, e)
    pie(sl, fuente); notas(sl, nota)
    return sl


# 1 ------------------------------------------------------------------ portada
sl = prs.slides.add_slide(VACIA); fondo(sl, OSCURO)
texto(sl, 0.8, 1.5, 11.5, 0.5, "TAREA 2 · HIDROLOGÍA 202602", size=14, bold=True, color=RGBColor(0x9C, 0xC9, 0xD6))
texto(sl, 0.8, 2.0, 11.5, 1.4, "Dos caras del ciclo del agua", size=46, bold=True, color=BLANCO)
texto(sl, 0.8, 3.25, 11.5, 1.2, ["El agua que sube: evapotranspiración en la cuenca del río Chicama hasta El Tambo (Perú)",
                                 "El agua que baja: lluvia intensa y diseño de una obra en Cottbus (Alemania)"], size=18, color=BLANCO)
texto(sl, 0.8, 5.6, 11.5, 0.9, ["Marlin Julie Schwebel", "Universidad Nacional de Colombia, sede Medellín · Prof. Carlos David Hoyos"],
      size=14, color=RGBColor(0x9C, 0xC9, 0xD6))
notas(sl, "20 s. Dos preguntas: cuánta agua pide la atmósfera a la cuenca del Chicama y cuánta le devuelve; y qué lluvia debe aguantar una "
          "obra de drenaje, con qué riesgo. El hilo de toda la presentación es la estabilidad de la atmósfera: la inversión decide cuándo y "
          "dónde llueve en el Chicama, y la inestabilidad produce las tormentas que dimensionan la obra en Cottbus.")

# 2 ------------------------------------------------------------------ demanda
estandar("La atmósfera pide 1 211 mm al año, y la manda el sol",
         "ETo FAO-56 con ERA5-Land horario, 30 celdas, 1981–2025",
         F1 / "fig_1_1a_ciclo_anual.png",
         [("1 211 mm/año", "demanda casi constante: 88 a 117 mm por mes"),
          ("−7,3 %", "con 10 % menos de radiación; +1 °C solo sube 2,5–3 %"),
          ("−43 %", "error de Thornthwaite, que solo mira la temperatura")],
         "Allen et al. (1998), FAO-56; Priestley y Taylor (1972); notas del curso #s36",
         "1 min. La ETo es lo que evaporaría un pasto siempre regado: la sed de la atmósfera. Es casi igual todo el año. En la época seca el aire "
         "está más seco, pero llega menos energía neta y se compensa. El experimento de sensibilidad muestra que el sol manda: 10 % menos de "
         "radiación baja la demanda 7 %, mientras un grado más la sube solo 2,5 a 3 %. Por eso Thornthwaite, que solo usa temperatura, se "
         "equivoca 43 %. Ojo: ERA5-Land da 19 % menos que la estación de Cajamarca; la demanda tiene una banda de −10 a −25 %.")

# 3 ------------------------------------------------------------------ ET real
lateral("Cuando sube la demanda, baja la ET real",
         "ET real por balance P − Q frente a la demanda, ciclo medio mensual",
         F1 / "fig_1_2_ciclo.png",
         [("442 ± 158 mm", "ET real por balance: 833 mm de lluvia menos 391 mm de caudal"),
          ("36 %", "de la demanda: falta agua, no energía (Rn/λ = 1 806 mm)"),
          ("Bouchet (1963)", "relación complementaria: el suelo seco calienta y seca el aire")],
         "Bouchet (1963); Brutsaert y Stricker (1979); Tarea 1 y CAMELS-PE",
         "1 min 15 s. La cuenca devuelve 442 mm, con una incertidumbre de ±158 mm. Lo raro es que en los meses en que la demanda sube, la ET real "
         "baja. Es la relación complementaria: cuando el suelo se seca, la energía que ya no se usa para evaporar calienta y seca el aire, y "
         "ese aire tiene más sed. La demanda alta es un síntoma de que falta agua, no la causa de más evaporación.", recorte=0.57)

# 4 ------------------------------------------------------------------ regimen (grafica nativa)
sl = prs.slides.add_slide(VACIA)
titulo(sl, "La lluvia llega cuando sobra: por eso hay caudal",
       "Lluvia, demanda y caudal medios por mes (mm)")
cl = pd.read_csv(RAIZ / "productos/punto1/et_real_climatologia.csv")
meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
cd = CategoryChartData(); cd.categories = meses
cd.add_series("Lluvia P", [round(v) for v in cl.P_L]); cd.add_series("Demanda ETo", [round(v) for v in cl.eto]); cd.add_series("Caudal Q", [round(v) for v in cl.Q])
gf = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.55), Inches(7.6), Inches(5.4), cd); gf.name = "Grafica mensual"
ch = gf.chart; ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.TOP; ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12); ch.legend.font.name = FUENTE
for s, c in zip(ch.series, [AGUA, RGBColor(0xB0, 0x7A, 0x0C), ACENTO]):
    s.format.fill.solid(); s.format.fill.fore_color.rgb = c
ch.plots[0].gap_width = 60; ch.plots[0].overlap = -10
for ax in (ch.category_axis, ch.value_axis):
    ax.tick_labels.font.size = Pt(12); ax.tick_labels.font.name = FUENTE; ax.tick_labels.font.color.rgb = PIZARRA
ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xDD, 0xE3, 0xE8); ch.value_axis.format.line.fill.background()
texto(sl, 8.6, 1.6, 4.15, 5.3, [
    [("Feb–abr: manda la energía. ", {"bold": True, "color": AGUA}), ("Llueve más de lo que el sol puede evaporar (marzo: 213 frente a 93 mm). El suelo se llena y el sobrante va al río.", {})],
    [("Jun–sep: manda el agua. ", {"bold": True, "color": ACENTO}), ("Sobra energía, pero no hay lluvia. El caudal que queda es agua subterránea de marzo.", {})],
    [("Resultado: ", {"bold": True}), ("la cuenca evapora el 53 % de la lluvia; la curva de Budyko diría 82 % (φ = 1,47).", {})],
    [("Las nubes de la estación inestable tapan el sol justo cuando hay más agua.", {"italic": True, "color": PIZARRA})]], size=15)
pie(sl, "Budyko (1974); Fu (1981); Milly (1994); Tarea 1, ERA5-Land y CAMELS-PE")
notas(sl, "1 min 30 s. Esta es la paradoja: si la cuenca está limitada por agua, ¿por qué hay caudal? Porque limitada por agua es una afirmación "
          "del año. En febrero, marzo y abril llueve más de lo que la energía puede evaporar; esos meses mandan la energía. El suelo es un balde "
          "de tamaño fijo: se rebalsa y el sobrante va al río. De junio a septiembre sobra energía pero no hay agua. Por eso la cuenca evapora el "
          "53 % de la lluvia y no el 82 % que dice Budyko: Milly (1994) mostró que la estacionalidad aleja a las cuencas de la curva. La "
          "estabilidad lo refuerza: en la época de lluvias la atmósfera es inestable y nublada, y llega menos sol justo cuando hay más agua.")

# 5 ------------------------------------------------------------------ inversion y altitud
estandar("La inversión guarda humedad, pero no trae agua",
         "1.5.c niebla y nubes bajas de ERA5 · 1.5.a gradiente altitudinal",
         F1 / "fig_1_5c_niebla.png",
         [("4,3 %", "de la cuenca toca la franja de la inversión en la época seca"),
          ("1 755 mm/año", "de niebla harían falta en esa franja para cerrar el balance: imposible"),
          ("241 → 785 mm", "la ET real sube con la altura, aunque la demanda baja (arriba llueve más)")],
         "Klein y Hartmann (1993); Garreaud (2009); Bruijnzeel et al. (2011); notas del curso #s47",
         "1 min. Frente a la costa, el aire que baja del anticiclón se calienta y queda sobre el aire frío del mar: es la inversión. Debajo hay "
         "estratocúmulos y niebla; encima el aire es seco, y por eso hay demanda. La pregunta era si la niebla es una entrada de agua oculta. No: "
         "la franja de la inversión toca solo el 4 % de la cuenca, y haría falta una niebla de 1 755 mm al año para cerrar el balance. Además, la "
         "ET real sube con la altura: abajo falta agua, arriba llueve más.")

# 6 ------------------------------------------------------------------ tendencias
estandar("La demanda sube, pero desde 2000 llega menos sol",
         "Tendencia de la ETo y aporte de cada forzante (mm por década)",
         F1 / "fig_1_4_atribucion.png",
         [("+9,2 mm/década", "tendencia de la ETo 1981–2025 (Mann–Kendall, p = 0,01)"),
          ("+8,1 frente a −9,7", "desde 2000: lo que suma la temperatura lo resta la radiación"),
          ("+15 mm/década", "con Thornthwaite: exagera porque solo ve la temperatura")],
         "Roderick y Farquhar (2002); Wild (2009); Brutsaert y Parlange (1998)",
         "40 s. La demanda sube 9 mm por década. Al separar los forzantes, la temperatura suma unos 8 mm por década, pero desde el año 2000 la "
         "radiación resta casi 10: llega menos sol, por aerosoles o nubes. Thornthwaite da 15 mm por década porque no ve la radiación. Es la "
         "misma lección de la diapositiva 2: usar solo la temperatura engaña.")

# 7 ------------------------------------------------------------------ IDF
estandar("Cottbus: una IDF que concuerda con la oficial",
         "30 años de lluvia cada 10 min (DWD 00880); cerca de El Tambo no hay series así",
         F2 / "fig_2_3_idf.png",
         [("30 años", "válidos tras eliminar 22 días imposibles del contador de gotas"),
          ("0,83–1,11", "veces la IDF oficial alemana KOSTRA-DWD-2020"),
          ("51,6 mm en 1 h", "tormenta convectiva del 9-jun-2018: T ≈ 111 años en 1 h, 7 años en 24 h")],
         "Koutsoyiannis et al. (1998); Hosking (1990); Weiss (1964); DWD, KOSTRA-DWD-2020",
         "1 min. Para diseñar hace falta lluvia cada pocos minutos durante muchos años: en Cottbus hay 30 años válidos. Limpiamos picos falsos del "
         "pluviómetro antiguo y ajustamos una GEV por L-momentos, la distribución límite de los máximos. La IDF concuerda con la oficial alemana. "
         "La tormenta de 2018 fue convectiva: atmósfera inestable, aire cálido y húmedo abajo, descarga en minutos. Es rarísima en 1 hora y común "
         "en 24 horas. Más allá de 60 años, el doble del registro, el resultado depende de la cola supuesta.")

# 8 ------------------------------------------------------------------ problema A
estandar("Un tubo de 1,00 m; lo más incierto es el tc",
         "Microcuenca de 0,44 km² a 7,2 km del pluviómetro · método racional · T = 25 por riesgo",
         F2 / "fig_2_4_problemaA.png",
         [("T = 25 años", "vida útil de 30 años y riesgo aceptado de 70 %"),
          ("DN 1,00 m", "Q = 1,05 m³/s (C = 0,34, tc = 102 min, i = 26,6 mm/h); el cálculo pide 0,84 m"),
          ("29 % frente a 1 %", "lo que mueve el diámetro el tc frente a la distribución")],
         "Chow et al. (1988), cap. 13 y 15; Kirpich (1940); Grimaldi et al. (2012)",
         "1 min 15 s. La microcuenca es una zanja de prados a 7 km del pluviómetro, en la misma llanura: la IDF vale directamente. Con una vida útil "
         "de 30 años y un riesgo de 70 % sale T = 25 años, como recomienda Chow para vías secundarias. El caudal es 1,05 m³/s y el tubo, 1,00 m. "
         "Lo más importante: las cuatro fórmulas del tiempo de concentración dan entre 88 y 258 minutos, y eso mueve el diámetro 29 %. La "
         "distribución lo mueve 1 %, porque a T = 25 se interpola dentro de los datos.")

# 9 ------------------------------------------------------------------ riesgo efectivo y escala (dos columnas)
sl = prs.slides.add_slide(VACIA)
titulo(sl, "El tubo instalado falla mucho menos que lo nominal", "Monte Carlo de 20 000 iteraciones · argumento de escala")
figura(sl, F2 / "fig_2_4_problemaA_montecarlo.png", 0.6, 1.6, 6.8, 5.2)
tarjeta(sl, 7.6, 1.6, 2.45, 1.45, "10 %", "riesgo real en 30 años")
tarjeta(sl, 10.3, 1.6, 2.45, 1.45, "71 %", "riesgo nominal (T = 25)", color_cifra=PIZARRA)
texto(sl, 7.6, 3.25, 5.15, 3.6, [
    [("¿Por qué? ", {"bold": True}), ("El cálculo pide 0,84 m y se instala 1,00 m, que ya aguanta T ≈ 100 años. Hay que reportar el riesgo del tubo instalado.", {})],
    [("Escala: ", {"bold": True, "color": ACENTO}), ("en el Chicama (2 170 km², tc ≈ 6,4 h) la lluvia media de una hora es 33 % menor que la del pluviómetro. Ninguna tormenta cubre toda la cuenca: el método racional no vale.", {})]],
      size=15)
pie(sl, "Chow et al. (1988), §13.2; NERC (1975); Leclerc y Schaake (1972)")
notas(sl, "1 min. En cada iteración tomé una IDF posible del bootstrap, un tiempo de concentración, un C, la rugosidad y la pendiente, y calculé la "
          "probabilidad de que la lluvia supere la capacidad del tubo. El riesgo real en 30 años es 10 %, no 71 %. No es que la incertidumbre "
          "ayude: es el salto al diámetro comercial. En el Chicama, en cambio, el método no sirve: la lluvia la organizan el relieve y la "
          "inversión, ninguna tormenta cubre 2 170 km² y la reducción areal cae a 0,67 en una hora.")

# 10 ----------------------------------------------------------------- problema B
estandar("Urbanizar sube el pico 3,5 veces: tanque de 7 900 m³",
         "Racional modificado, bloques alternos con tiempo–área y tránsito de piscina nivelada",
         F2 / "fig_2_4_problemaB.png",
         [("× 3,5", "el pico: C pasa de 0,34 a 0,58 y tc de 102 a 41 min"),
          ("7 900 m³", "tanque de 1,5 m de profundidad con un orificio de 65 cm"),
          ("+20 %", "de volumen si el pico de la lluvia llega al centro o al final")],
         "Chow et al. (1988), §8.2 y §15.4; Leopold (1968); Huff (1967)",
         "40 s. Si la cuenca se urbaniza, se infiltra menos y el agua llega más rápido: el pico se multiplica por 3,5. Un tanque de unos 7 900 m³ "
         "lo devuelve al caudal previo. Si el pico de la lluvia llega al centro o al final, la lluvia previa ya llenó parte del tanque, porque el "
         "orificio con poca carga deja salir poco: hace falta 20 % más. Las tormentas convectivas reales suelen tener el pico al inicio.")

# 11 ----------------------------------------------------------------- conclusiones
sl = prs.slides.add_slide(VACIA); fondo(sl, OSCURO)
texto(sl, 0.8, 0.6, 11.7, 0.8, "Tres conclusiones", size=34, bold=True, color=BLANCO)
items = [("1", "En el Chicama manda el sol en la demanda y el agua en la evaporación real: la lluvia llega concentrada, el suelo se rebalsa y la cuenca genera caudal pese a la aridez."),
         ("2", "La inversión explica la costa nublada y seca, pero la niebla no es una entrada de agua que cierre el balance."),
         ("3", "Recomiendo un tubo de 1,00 m para T = 25 años: el diámetro calculado va de 0,63 a 0,91 m según los supuestos, y el riesgo real es ≈ 10 % en 30 años. Lo que más reduciría la incertidumbre es medir el tiempo de concentración.")]
for k, (n, t) in enumerate(items):
    y = 1.75 + k * 1.65
    c = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.8), Inches(y), Inches(0.75), Inches(0.75))
    c.fill.solid(); c.fill.fore_color.rgb = ACENTO; c.line.fill.background(); c.name = f"Numero {n}"
    tf = c.text_frame; tf.paragraphs[0].alignment = PP_ALIGN.CENTER; r = tf.paragraphs[0].add_run(); r.text = n
    r.font.size = Pt(24); r.font.bold = True; r.font.name = FUENTE; r.font.color.rgb = BLANCO
    texto(sl, 1.85, y - 0.05, 10.6, 1.4, t, size=18, color=BLANCO)
notas(sl, "30 s. Una frase por punto. Si sobra tiempo: si el clima se calienta, las lluvias convectivas cortas se intensifican y el riesgo de la "
          "obra sube; si la cuenca se urbaniza, hace falta el tanque.")

# 12 ----------------------------------------------------------------- reserva: reforestacion (grafica nativa)
sl = prs.slides.add_slide(VACIA)
titulo(sl, "Reserva: reforestar sube la ET y quita caudal", "Budyko–Fu con ω según la cobertura de bosque · balance de energía de la superficie (mm/año)")
cd = CategoryChartData(); cd.categories = ["Hoy (15 % bosque)", "100 % bosque nativo", "100 % pino o eucalipto"]
cd.add_series("ET real", [437, 508, 545]); cd.add_series("Caudal Q", [387, 330, 296])
gf = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.6), Inches(6.9), Inches(5.2), cd); gf.name = "Grafica reforestacion"
ch = gf.chart; ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.TOP; ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12); ch.legend.font.name = FUENTE
for s_, c in zip(ch.series, [RGBColor(0x2F, 0x7D, 0x4F), ACENTO]):
    s_.format.fill.solid(); s_.format.fill.fore_color.rgb = c
pl = ch.plots[0]; pl.gap_width = 70; pl.has_data_labels = True
pl.data_labels.font.size = Pt(13); pl.data_labels.font.bold = True; pl.data_labels.font.name = FUENTE; pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
for ax in (ch.category_axis, ch.value_axis):
    ax.tick_labels.font.size = Pt(12); ax.tick_labels.font.name = FUENTE; ax.tick_labels.font.color.rgb = PIZARRA
ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xDD, 0xE3, 0xE8); ch.value_axis.minimum_scale = 0
texto(sl, 7.85, 1.65, 4.9, 5.2, [
    [("+5 W/m² ", {"bold": True, "color": RGBColor(0x2F, 0x7D, 0x4F)}), ("de calor latente: la ET sube ≈ 70 mm/año (+8 W/m² con pino o eucalipto).", {})],
    [("+16 W/m² ", {"bold": True, "color": RGBColor(0xB0, 0x7A, 0x0C)}), ("de sol absorbido: el bosque es más oscuro (albedo 0,12 frente a 0,20).", {})],
    [("Gana el calor sensible: ", {"bold": True}), ("la ET no puede gastar toda esa energía porque falta agua. La razón de Bowen baja (3,1 → 2,9), pero el aire puede calentarse: ΔT entre −0,4 y +0,4 °C.", {})],
    [("−15 % a −24 % de caudal, ", {"bold": True, "color": ACENTO}), ("sea cual sea el signo de ΔT (Bosch y Hewlett, 1982).", {})]], size=15)
pie(sl, "Zhang et al. (2001); Bonan (2008); Rotenberg y Yakir (2010); Bosch y Hewlett (1982); reciclaje 5 %, niebla 300 mm/año en la franja")
notas(sl, "Solo si preguntan qué pasaría si cambia la cobertura. Más bosque sube el parámetro ω de Budyko: raíces más profundas e interceptación, "
          "así que evapora más y quita caudal. Evaporar consume energía, el calor latente: unos 5 W/m² más. Pero el bosque es más oscuro y absorbe "
          "unos 16 W/m² más de sol. Como falta agua, la evaporación no alcanza a gastar esa energía y sube el calor sensible: el aire puede "
          "calentarse en vez de enfriarse, como en bosques de zonas secas (Rotenberg y Yakir, 2010). En los trópicos húmedos, en cambio, el bosque "
          "enfría (Bonan, 2008). El caudal baja igual, porque depende de la ET y no de la temperatura.")

ruta = OUT / "T2_202602_GNN_presentacion.pptx"
prs.save(ruta)
print(f"-> {ruta.relative_to(RAIZ)} ({len(prs.slides)} diapositivas)")
