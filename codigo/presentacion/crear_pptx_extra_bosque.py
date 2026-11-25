"""
crear_pptx_extra_bosque.py - Presentacion extra (interes personal, no es parte de la entrega): "¿El bosque trae lluvia?"

La intuicion de la esponja (el bosque guarda humedad y trae lluvia) frente a la bomba (el bosque devuelve agua al cielo),
revisada por escalas con los resultados de la microcuenca de Cottbus (codigo/punto2/10_reforestacion_cottbus.py) y con la
literatura. Salida: productos/presentacion/extra_bosque_y_lluvia.pptx
"""
from pathlib import Path

import pandas as pd
from scipy.optimize import brentq
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "productos/presentacion"
BOSQUE, LIMA, AMBAR, BLANCO = RGBColor(0x1E, 0x4A, 0x3B), RGBColor(0xB9, 0xDF, 0xC4), RGBColor(0xF2, 0xB3, 0x3D), RGBColor(0xFF, 0xFF, 0xFF)
OSCURO, ACENTO, PIZARRA, TINTE, TEXTO = RGBColor(0x0F, 0x3D, 0x4C), RGBColor(0xC2, 0x45, 0x2A), RGBColor(0x5B, 0x64, 0x75), RGBColor(0xEC, 0xF2, 0xF4), RGBColor(0x1F, 0x29, 0x33)
VERDE, AGUA = RGBColor(0x2F, 0x7D, 0x4F), RGBColor(0x1D, 0x6F, 0x8C)
FUENTE, W, H = "Arial", 13.333, 7.5

prs = Presentation(); prs.slide_width, prs.slide_height = Inches(W), Inches(H)
VACIA = prs.slide_layouts[6]


def texto(sl, x, y, w, h, parrafos, size=16, color=TEXTO, bold=False, align=PP_ALIGN.LEFT):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    for k, par in enumerate([parrafos] if isinstance(parrafos, str) else parrafos):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph(); p.alignment = align; p.space_after = Pt(6)
        for t, op in (par if isinstance(par, list) else [(par, {})]):
            r = p.add_run(); r.text = t; f = r.font; f.name = FUENTE; f.size = Pt(op.get("size", size)); f.bold = op.get("bold", bold)
            f.italic = op.get("italic", False); f.color.rgb = op.get("color", color)
    return tb


def fondo(sl, c):
    sl.background.fill.solid(); sl.background.fill.fore_color.rgb = c


def caja(sl, x, y, w, h, c, nombre):
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)); s.name = nombre
    s.adjustments[0] = 0.08; s.fill.solid(); s.fill.fore_color.rgb = c; s.line.fill.background(); s.shadow.inherit = False
    return s


def titulo(sl, t, sub=None, oscuro=False):
    texto(sl, 0.6, 0.35, W - 1.2, 0.8, t, size=30, bold=True, color=BLANCO if oscuro else OSCURO)
    if sub:
        texto(sl, 0.6, 1.08, W - 1.2, 0.4, sub, size=15, color=LIMA if oscuro else PIZARRA)


def pie(sl, t, oscuro=False):
    texto(sl, 0.6, H - 0.45, W - 1.2, 0.35, t, size=10, color=LIMA if oscuro else PIZARRA)


def notas(sl, t):
    sl.notes_slide.notes_text_frame.text = t


def grafica(sl, x, y, w, h, cats, series, colores, nombre, leyenda=True, fmt=None):
    cd = CategoryChartData(); cd.categories = cats
    for n, v in series:
        cd.add_series(n, v)
    gf = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd); gf.name = nombre
    ch = gf.chart; ch.has_legend = leyenda
    if leyenda:
        ch.legend.position = XL_LEGEND_POSITION.TOP; ch.legend.include_in_layout = False; ch.legend.font.size = Pt(12); ch.legend.font.name = FUENTE
    for s_, c in zip(ch.series, colores):
        s_.format.fill.solid(); s_.format.fill.fore_color.rgb = c
    pl = ch.plots[0]; pl.gap_width = 70; pl.has_data_labels = True
    pl.data_labels.font.size = Pt(13); pl.data_labels.font.bold = True; pl.data_labels.font.name = FUENTE
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    if fmt:
        pl.data_labels.number_format = fmt; pl.data_labels.number_format_is_linked = False
    for ax in (ch.category_axis, ch.value_axis):
        ax.tick_labels.font.size = Pt(12); ax.tick_labels.font.name = FUENTE; ax.tick_labels.font.color.rgb = PIZARRA
    ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xDD, 0xE3, 0xE8); ch.value_axis.minimum_scale = 0
    return ch


# ---------------------------------------------------------------- datos (10_reforestacion_cottbus.py)
rp = pd.read_csv(RAIZ / "productos/punto2/reforestacion_cottbus_parametros.csv", index_col=0).valor
esc = pd.read_csv(RAIZ / "productos/punto2/reforestacion_cottbus_escenarios.csv").set_index("escenario")
P, E, fb0 = rp.P_mm, rp.ETo_mm, rp.bosque_hoy
zh = lambda p, w: (1 + w * p) / (1 + w * p + 1 / p)


def recarga(P_, f, tipo):
    phi = E / P_; ep, eb = P_ * zh(phi, .5), P_ * zh(phi, 2.)
    en = eb if tipo == "nativo" else ep + 1.6 * (eb - ep); ex = max(f - fb0, 0)
    return P_ - ((1 - f) * ep + min(f, fb0) * eb + ex * en)


q0 = recarga(P, fb0, "nativo")
P_nec = {t: brentq(lambda x: recarga(x, 1.0, t) - q0, P, 3 * P) for t in ["nativo", "pino"]}
dP_nec = {t: 100 * (v / P - 1) for t, v in P_nec.items()}
q_mas5 = {t: recarga(P * 1.05, 1.0, t) for t in ["nativo", "pino"]}

# 1 ---------------------------------------------------------------- portada
sl = prs.slides.add_slide(VACIA); fondo(sl, BOSQUE)
texto(sl, 0.8, 1.4, 11.5, 0.5, "PRESENTACIÓN EXTRA · POR INTERÉS PROPIO", size=14, bold=True, color=AMBAR)
texto(sl, 0.8, 1.95, 11.5, 1.3, "¿El bosque trae lluvia?", size=48, bold=True, color=BLANCO)
texto(sl, 0.8, 3.15, 11.5, 1.4, ["La esponja y la bomba: qué hace un bosque con el agua de una cuenca,",
                                 "revisado con la microcuenca de Cottbus y la literatura científica"], size=20, color=LIMA)
texto(sl, 0.8, 5.7, 11.5, 0.6, "Marlin Julie Schwebel · Hidrología 202602 · UNAL Medellín", size=14, color=LIMA)
notas(sl, "Esta presentación nace de una duda: yo pensaba que reforestar retiene la humedad, trae lluvia y hace la cuenca menos seca, "
          "pero el modelo de la tarea dio que el bosque le quita agua al acuífero. Aquí reviso por qué las dos ideas tienen parte de razón.")

# 2 ---------------------------------------------------------------- las dos intuiciones
sl = prs.slides.add_slide(VACIA)
titulo(sl, "Dos intuiciones, y las dos tienen parte de razón", "La clave es la escala: el dosel, la cuenca o la región")
for x, c, nom, t, cuerpo in [(0.6, LIMA, "Esponja", "La esponja (mi intuición)",
                              ["Bajo los árboles hay sombra, el aire es más fresco y húmedo y el suelo no se seca.",
                               "Las raíces y la hojarasca hacen que el suelo infiltre más y que escurra menos.",
                               "Los bosques evaporan mucho: ese vapor puede volver como lluvia."]),
                             (6.85, RGBColor(0xF6, 0xD7, 0xCF), "Bomba", "La bomba (el balance de agua)",
                              ["El bosque evapora más que el prado: intercepta lluvia en las copas y transpira con raíces profundas.",
                               "Lo que se evapora ya no llega al acuífero ni a las zanjas.",
                               "En una cuenca pequeña, ese vapor se lo lleva el viento: llueve en otra parte."])]:
    caja(sl, x, 1.75, 5.9, 3.45, c, nom)
    texto(sl, x + 0.3, 1.95, 5.3, 0.6, t, size=22, bold=True, color=OSCURO)
    texto(sl, x + 0.3, 2.7, 5.3, 3.3, [[("•  ", {"bold": True}), (b, {})] for b in cuerpo], size=16)
texto(sl, 0.6, 5.5, 12.1, 0.6, [[("Las dos describen procesos reales. ", {"bold": True}),
                                  ("La pregunta es cuál pesa más para el agua que queda en la cuenca durante el año.", {})]], size=16)
notas(sl, "La esponja: el bosque guarda humedad bajo el dosel y mejora el suelo. La bomba: el bosque evapora más y saca agua de la cuenca. "
          "Las dos son ciertas; lo que cambia es la escala y la pregunta: humedad del suelo bajo el árbol, agua del acuífero, o lluvia de la región.")

# 3 ---------------------------------------------------------------- escala del dosel
sl = prs.slides.add_slide(VACIA)
titulo(sl, "Bajo el dosel, el bosque sí guarda humedad", "Escala de metros: el microclima y el suelo del bosque")
for k, (cifra, t, cuerpo) in enumerate([
        ("Sombra", "Microclima más fresco y húmedo", "El dosel amortigua el calor: bajo los árboles las máximas son más bajas y el aire más húmedo que en un claro (De Frenne et al., 2019)."),
        ("Suelo", "Infiltra más y escurre menos", "Raíces, hojarasca y materia orgánica abren poros: el agua entra al suelo en vez de correr por encima. Menos erosión (Bruijnzeel, 2004)."),
        ("Hojarasca", "Menos evaporación del suelo", "La capa de hojas tapa el suelo y lo protege del sol y del viento: la superficie se mantiene húmeda más tiempo.")]):
    x = 0.6 + k * 4.15
    caja(sl, x, 1.75, 3.85, 4.2, TINTE, f"Tarjeta {k + 1}")
    texto(sl, x + 0.25, 1.95, 3.4, 0.6, cifra, size=26, bold=True, color=VERDE)
    texto(sl, x + 0.25, 2.65, 3.4, 0.7, t, size=17, bold=True, color=OSCURO)
    texto(sl, x + 0.25, 3.45, 3.4, 2.4, cuerpo, size=15)
texto(sl, 0.6, 6.15, 12.1, 0.6, [[("Por eso el suelo del bosque se siente húmedo. ", {"bold": True, "color": VERDE}),
                                  ("Pero esa humedad la están usando los árboles: es agua que el bosque toma y devuelve al aire.", {})]], size=16)
pie(sl, "De Frenne et al. (2019), Nature Ecology & Evolution; Bruijnzeel (2004), Agriculture, Ecosystems & Environment")
notas(sl, "Aquí la intuición es correcta. Bajo los árboles hace más fresco y más húmedo, y el suelo de bosque infiltra mejor, así que escurre "
          "menos por la superficie y hay menos erosión. Pero que el suelo se sienta húmedo no quiere decir que sobre agua: los árboles la están "
          "usando y la devuelven al aire por las hojas.")

# 4 ---------------------------------------------------------------- escala de la cuenca
sl = prs.slides.add_slide(VACIA)
titulo(sl, "En la cuenca, el bosque bombea agua al cielo", f"Microcuenca de Cottbus: {P:.0f} mm de lluvia y {E:.0f} mm de demanda al año")
e3 = esc.loc[["hoy", "100 % bosque nativo", "100 % monocultivo de pino"]]
grafica(sl, 0.6, 1.6, 7.3, 5.2, ["Hoy (17 % bosque)", "Bosque nativo", "Pino silvestre"],
        [("Evaporación (mm/año)", [round(v) for v in e3.ET_mm]), ("Recarga y zanjas (mm/año)", [round(v) for v in e3.Q_mm])],
        [VERDE, ACENTO], "Grafica escenarios")
texto(sl, 8.3, 1.7, 4.45, 5.2, [
    [("Más bosque, más evaporación. ", {"bold": True, "color": VERDE}), ("El bosque nativo (roble, carpe, aliso) evapora 66 mm más al año que hoy; el pino silvestre, 106 mm más.", {})],
    [("Menos agua para el acuífero. ", {"bold": True, "color": ACENTO}),
     (f"La recarga baja {abs(e3['dQ_%'].iloc[1]):.0f} % con bosque nativo y {abs(e3['dQ_%'].iloc[2]):.0f} % con pino.", {})],
    [("¿Por qué el pino más? ", {"bold": True}), ("Es siempreverde: intercepta lluvia y transpira también en invierno, cuando el roble no tiene hojas.", {})],
    [("Lo dicen cientos de cuencas ", {"bold": True}), ("en el mundo: forestar pastizales reduce el caudal, y más con pinos (Bosch y Hewlett, 1982; Farley et al., 2005).", {})]], size=15)
pie(sl, "Zhang et al. (2001); Bosch y Hewlett (1982); Farley et al. (2005) · codigo/punto2/10_reforestacion_cottbus.py")
notas(sl, "A la escala de la cuenca manda la bomba. Cottbus es seco: llueven 564 mm y la atmósfera pide 749. Si hay más árboles, evaporan más "
          "y queda menos agua para el acuífero y las zanjas. Esto no lo dice solo mi modelo: lo midieron en cientos de cuencas pareadas en el mundo.")

# 5 ---------------------------------------------------------------- cuanta lluvia haria falta
sl = prs.slides.add_slide(VACIA)
titulo(sl, "¿Y si el bosque trae lluvia? Tendría que traer mucha", "Lluvia extra que haría falta en Cottbus para no perder recarga")
grafica(sl, 0.6, 1.6, 6.6, 5.1, ["Bosque nativo", "Pino silvestre", "Referencia: unos pocos %"],
        [("Lluvia extra (%)", [round(dP_nec["nativo"]), round(dP_nec["pino"]), 5])], [AGUA], "Grafica lluvia necesaria", leyenda=False, fmt='"+"0" %"')
texto(sl, 7.6, 1.7, 5.15, 5.2, [
    [(f"+{dP_nec['nativo']:.0f} % y +{dP_nec['pino']:.0f} %: ", {"bold": True, "color": AGUA}),
     (f"para que la recarga no baje, en Cottbus tendría que llover {P_nec['nativo']:.0f} mm o {P_nec['pino']:.0f} mm al año en vez de {P:.0f} mm.", {})],
    [("Los estudios hablan de pocos por ciento. ", {"bold": True}),
     ("Forestar grandes áreas de Europa podría aumentar algo la lluvia y las nubes (Teuling et al., 2017; Meier et al., 2021), del orden de unos pocos por ciento (la tercera barra, 5 %, es solo una referencia generosa, no un dato medido).", {})],
    [("Aun con 5 % más de lluvia, ", {"bold": True}),
     (f"un pinar dejaría {q_mas5['pino']:.0f} mm de recarga, frente a {q0:.0f} mm de hoy.", {})]], size=15)
pie(sl, "Cálculo con el modelo de la tarea (Zhang et al., 2001); Teuling et al. (2017), Nature Communications; Meier et al. (2021), Nature Geoscience")
notas(sl, "Supongamos que el bosque sí trae lluvia. ¿Cuánta tendría que traer para compensar lo que evapora? Un 25 % más con bosque nativo y un "
          "44 % más con pino. Los estudios en Europa encuentran efectos de pocos por ciento, y a escala de regiones enteras. Ni con un 5 % más de "
          "lluvia el pinar devuelve la recarga.")

# 6 ---------------------------------------------------------------- escala regional y estabilidad
sl = prs.slides.add_slide(VACIA); fondo(sl, OSCURO)
titulo(sl, "El vapor viaja: la lluvia cae lejos", "Escala regional: reciclaje de humedad y estabilidad de la atmósfera", oscuro=True)
pasos = [("1", "El bosque evapora", "más vapor en la capa límite sobre el bosque"),
         ("2", "El viento lo lleva", "a 3 m/s el aire cruza la microcuenca en minutos y recorre cientos de km en un día"),
         ("3", "Se forman nubes", "más vapor baja la base de las nubes: sobre los bosques de Europa hay más cúmulos (Teuling et al., 2017)"),
         ("4", "Llueve donde hay inestabilidad", "la lluvia necesita aire que suba: frentes y tormentas organizadas, a escala de cientos de km")]
for k, (n, t, d) in enumerate(pasos):
    x = 0.6 + k * 3.12
    c = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(1.85), Inches(0.75), Inches(0.75)); c.name = f"Paso {n}"
    c.fill.solid(); c.fill.fore_color.rgb = AMBAR; c.line.fill.background()
    tf = c.text_frame; tf.paragraphs[0].alignment = PP_ALIGN.CENTER; r = tf.paragraphs[0].add_run(); r.text = n
    r.font.size = Pt(22); r.font.bold = True; r.font.name = FUENTE; r.font.color.rgb = OSCURO
    texto(sl, x, 2.8, 2.9, 0.6, t, size=18, bold=True, color=BLANCO)
    texto(sl, x, 3.45, 2.9, 2.0, d, size=14, color=LIMA)
texto(sl, 0.6, 5.55, 12.1, 1.2, [
    [("Reciclaje de humedad: ", {"bold": True, "color": AMBAR}),
     ("el vapor que evapora un continente vuelve a llover, pero lejos y repartido (van der Ent et al., 2010). En la Amazonía, el aire que pasó sobre bosque trae más lluvia (Spracklen et al., 2012). ", {"color": BLANCO}),
     ("En 0,44 km², casi nada de ese vapor llueve encima de la propia microcuenca.", {"color": BLANCO, "bold": True})]], size=15)
pie(sl, "van der Ent et al. (2010), Water Resources Research; Spracklen et al. (2012), Nature; Ellison et al. (2017), Global Environmental Change", oscuro=True)
notas(sl, "Aquí entra la estabilidad. El bosque sí agrega vapor a la capa límite, y con más vapor la base de las nubes baja: en Europa se ven más "
          "cúmulos sobre los bosques. Pero para que llueva el aire tiene que subir mucho, y eso lo deciden los frentes y las tormentas organizadas. "
          "Además, el viento se lleva el vapor en minutos. Por eso el bosque trae lluvia a escala de continente, como en la Amazonía, pero no a "
          "la escala de una cuenca pequeña.")

# 7 ---------------------------------------------------------------- entonces
sl = prs.slides.add_slide(VACIA)
titulo(sl, "Entonces, ¿plantar o no plantar?", "Depende de para qué: no hay un bosque bueno para todo")
filas = [("Recargar el acuífero de Cottbus", "Prado o brezal", "El pino es lo peor: −65 % de recarga"),
         ("Frenar la erosión y la escorrentía superficial", "Bosque", "Suelo protegido y que infiltra"),
         ("Refrescar el microclima y la biodiversidad", "Bosque nativo mixto", "Sombra y especies locales"),
         ("Convertir los pinares actuales", "Robledal y hayedo mixto", "Evapora menos que el pino en invierno")]
caja(sl, 0.6, 1.65, 12.1, 0.6, OSCURO, "Encabezado tabla")
for j, (t, x, w) in enumerate([("Objetivo", 0.8, 4.8), ("Mejor opción", 5.7, 2.9), ("Por qué", 8.7, 3.9)]):
    texto(sl, x, 1.72, w, 0.5, t, size=15, bold=True, color=BLANCO)
for i, fila in enumerate(filas):
    y = 2.35 + i * 0.82
    caja(sl, 0.6, y, 12.1, 0.72, TINTE if i % 2 == 0 else BLANCO, f"Fila {i + 1}")
    for (t, x, w), b in zip(zip(fila, [0.8, 5.7, 8.7], [4.8, 2.9, 3.9]), [False, True, False]):
        texto(sl, x, y + 0.13, w, 0.55, t, size=15, bold=b, color=VERDE if b else TEXTO)
texto(sl, 0.6, 5.75, 12.1, 1.0, [[("En Brandeburgo ya se hace: ", {"bold": True, "color": VERDE}),
                                  ("se están convirtiendo monocultivos de pino en bosques mixtos de roble y haya, en parte para recuperar la recarga del "
                                   "agua subterránea, que bajó con el crecimiento de los pinares (Natkhin et al., 2012).", {})]], size=15)
pie(sl, "Natkhin et al. (2012), Journal of Hydrology; Bosch y Hewlett (1982); Farley et al. (2005)")
notas(sl, "La respuesta no es plantar siempre ni nunca. Si lo que se quiere es agua en el acuífero, el prado es mejor y el pino es lo peor. "
          "Si se quiere frenar la erosión, refrescar y ganar biodiversidad, el bosque nativo es mejor. En Brandeburgo están cambiando pinares por "
          "bosques mixtos de roble y haya, en parte porque los pinares bajaron la recarga.")

# 7b --------------------------------------------------------------- que medida si sirve (BTU Cottbus)
sl = prs.slides.add_slide(VACIA)
titulo(sl, "¿Qué medida sí sirve contra la sequía en Cottbus?", "No plantar más bosque, sino cambiar el bosque y retener el agua")
rec = esc.loc[["hoy", "100 % bosque nativo", "100 % monocultivo de pino"], "Q_mm"]
grafica(sl, 0.6, 1.6, 4.9, 4.0, ["Prado (hoy)", "Bosque nativo", "Pino silvestre"], [("Recarga (mm/año)", [round(v) for v in rec])],
        [AGUA], "Grafica recarga", leyenda=False)
texto(sl, 0.6, 5.6, 4.9, 0.6, [[("Waldumbau: ", {"bold": True, "color": VERDE}),
                                (f"de pino a bosque nativo, la recarga sube de {rec.iloc[2]:.0f} a {rec.iloc[1]:.0f} mm/año (+{100 * (rec.iloc[1] / rec.iloc[2] - 1):.0f} %).", {})]], size=14)
medidas = [("1", "Convertir los pinares en bosque mixto", "Roble, carpe y haya en lugar de pino: sin hojas en invierno, cuando más se recarga el acuífero (Waldumbau)."),
           ("2", "No forestar los prados abiertos", "Si el objetivo es el agua, el prado recarga más que cualquier bosque."),
           ("3", "Retener el agua en las zanjas", "Pequeños diques (Kulturstaue) y escalones (Sohlschwellen): el agua se infiltra en vez de irse rápido al Spree.")]
for k, (n, t, d) in enumerate(medidas):
    y = 1.65 + k * 1.2
    c = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(5.9), Inches(y), Inches(0.6), Inches(0.6)); c.name = f"Medida {n}"
    c.fill.solid(); c.fill.fore_color.rgb = VERDE; c.line.fill.background()
    tf = c.text_frame; tf.paragraphs[0].alignment = PP_ALIGN.CENTER; r = tf.paragraphs[0].add_run(); r.text = n
    r.font.size = Pt(18); r.font.bold = True; r.font.name = FUENTE; r.font.color.rgb = BLANCO
    texto(sl, 6.65, y - 0.05, 6.1, 0.45, t, size=17, bold=True, color=OSCURO)
    texto(sl, 6.65, y + 0.38, 6.1, 0.8, d, size=14)
caja(sl, 5.9, 5.2, 6.85, 1.75, TINTE, "Investigacion BTU")
texto(sl, 6.1, 5.28, 6.5, 1.65, [
    [("En la BTU Cottbus: ", {"bold": True, "color": VERDE}),
     ("el grupo de Hidrología del Prof. Christoph Hinz estudia cómo la evaporación, que según el uso del suelo es «hoch variabel», «bestimmt letztlich die Grundwasserneubildung» "
      "en los paisajes post-minería de la Lusacia, y en el sitio Hühnerwasser (proyecto SoilWater) mide cómo cada especie de árbol cambia el agua del suelo.", {})],
    [("Contraste: ", {"bold": True}), ("en la Lusacia se recarga el 13–25 % de la lluvia según suelo y uso; el modelo da 29 % (prado), 17 % (nativo) y 10 % (pino).", {})]], size=12)
pie(sl, "Charlas «Wassergespräch Lausitz»: Hinz (BTU, 2019) y Hildmann (BTU, 2023); proyecto SoilWater (BTU); documento del Bundestag 20(16)250-A")
notas(sl, "Entonces, ¿qué sirve contra la sequía? No plantar más bosque sobre los prados, sino cambiar el bosque que ya existe: convertir los "
          "pinares en bosques mixtos de roble, carpe y haya, que pierden las hojas en invierno, cuando más se recarga el acuífero. En el modelo, "
          "pasar de pino a bosque nativo sube la recarga de 57 a 96 mm al año. Y retener el agua en las zanjas con pequeños diques, para que se "
          "infiltre. Esto se estudia en la BTU de Cottbus: el grupo de Hidrología del profesor Christoph Hinz muestra que la evaporación, que "
          "depende del uso del suelo, decide la recarga, y en el sitio Hühnerwasser mide el efecto de cada especie de árbol. Las medidas de "
          "Waldumbau y retención en zanjas las presentó el Dr. Christian Hildmann en el mismo ciclo de charlas de la BTU.")

# 7c --------------------------------------------------------------- incendios
sl = prs.slides.add_slide(VACIA)
titulo(sl, "Bosque mixto: menos sequía y menos incendios", "La misma medida ayuda con los dos problemas de Brandeburgo")
for k, (cifra, etq) in enumerate([("> 30 %", "de los incendios forestales de Alemania ocurren en Brandeburgo"),
                                   ("≈ 69 %", "de los bosques de Brandeburgo son de pino"),
                                   ("507 incendios", "y ≈ 1 411 ha quemadas en Brandeburgo en 2022"),
                                   ("65 %", "de los incendios de Alemania ocurren en bosques de coníferas")]):
    x, y = 0.6 + (k % 2) * 3.05, 1.65 + (k // 2) * 1.75
    caja(sl, x, y, 2.85, 1.55, TINTE, f"Dato {k + 1}")
    texto(sl, x + 0.15, y + 0.1, 2.6, 0.55, cifra, size=24, bold=True, color=ACENTO)
    texto(sl, x + 0.15, y + 0.68, 2.6, 0.85, etq, size=12.5)
texto(sl, 6.95, 1.65, 5.8, 3.6, [
    [("¿Por qué arde más el pino? ", {"bold": True, "color": ACENTO}),
     ("Sus acículas forman una capa suelta, seca y con resina, y bajo los pinos crecen pastos secos. Las hojas de roble y haya forman una capa compacta que retiene humedad y arde mal.", {})],
    [("Los datos de Brandeburgo: ", {"bold": True, "color": VERDE}),
     ("los pinares puros se dañaron mucho más que los rodales con alguna especie de hoja ancha, y el daño baja cuanta más hoja ancha hay (Instituto Thünen, 2022). En un modelo de riesgo de incendios, el porcentaje de bosque de hoja ancha es de los factores más importantes (Horn, 2024).", {})],
    [("El matiz: ", {"bold": True}),
     ("la ventaja viene sobre todo de la hojarasca, más que del microclima, y se pierde en los días de sequía extrema (Schunk et al., 2017).", {})]], size=14)
caja(sl, 0.6, 5.3, 12.15, 1.55, BOSQUE, "Doble beneficio")
texto(sl, 0.85, 5.4, 5.6, 1.4, [[("Contra la sequía", {"bold": True, "color": AMBAR, "size": 16})],
                                [(f"De pino a bosque nativo, la recarga sube de {rec.iloc[2]:.0f} a {rec.iloc[1]:.0f} mm/año en la microcuenca.", {"color": BLANCO})]], size=14)
texto(sl, 6.75, 5.4, 5.8, 1.4, [[("Contra los incendios", {"bold": True, "color": AMBAR, "size": 16})],
                                [("Menos combustible seco y con resina: menos daño cuando hay fuego.", {"color": BLANCO})]], size=14)
pie(sl, "Thünen-Institut, Project brief 2022/24; MIK Brandenburg, Waldbrandstatistik 2022; UBA; Horn (2024), TU Berlin; Schunk et al. (2017) · datos de Brandeburgo, no solo de Cottbus")
notas(sl, "Brandeburgo es el estado alemán con más incendios forestales, y casi el 70 % de sus bosques son de pino. Los datos muestran que los "
          "pinares puros se queman con mucho más daño que los bosques con especies de hoja ancha: las acículas secas y con resina arden fácil, "
          "mientras las hojas de roble y haya forman una capa compacta y húmeda. El matiz es que la diferencia está sobre todo en la hojarasca, y "
          "en los días de sequía extrema se pierde. La buena noticia es que la misma medida, convertir los pinares en bosques mixtos, ayuda contra "
          "la sequía y contra los incendios. Ojo: son datos de todo Brandeburgo, no específicos de Cottbus.")

# 8 ---------------------------------------------------------------- conclusion y referencias
sl = prs.slides.add_slide(VACIA); fondo(sl, BOSQUE)
texto(sl, 0.8, 0.5, 11.7, 0.8, "Mi intuición, revisada", size=34, bold=True, color=BLANCO)
for k, (ok, t) in enumerate([("✓", "El bosque guarda humedad bajo el dosel y mejora el suelo: cierto a escala de metros."),
                             ("✓", "El bosque puede traer lluvia: cierto a escala de regiones y continentes, y en pocos por ciento."),
                             ("✗", "La cuenca queda menos seca: no. En Cottbus el bosque evapora más y la recarga baja 41 % (nativo) o 65 % (pino).")]):
    y = 1.6 + k * 1.05
    texto(sl, 0.8, y, 0.6, 0.8, ok, size=30, bold=True, color=AMBAR if ok == "✓" else RGBColor(0xF0, 0x8A, 0x7A))
    texto(sl, 1.5, y + 0.08, 11.0, 0.9, t, size=18, color=BLANCO)
texto(sl, 0.8, 4.85, 11.7, 0.4, "Para leer más", size=16, bold=True, color=AMBAR)
texto(sl, 0.8, 5.2, 11.7, 2.1, [
    "Bosch y Hewlett (1982) J. Hydrol. 55 · Farley, Jobbágy y Jackson (2005) Global Change Biol. 11 · Zhang, Dawes y Walker (2001) Water Resour. Res. 37",
    "Bruijnzeel (2004) Agric. Ecosyst. Environ. 104 · De Frenne et al. (2019) Nat. Ecol. Evol. 3 · van der Ent et al. (2010) Water Resour. Res. 46",
    "Spracklen, Arnold y Taylor (2012) Nature 489 · Teuling et al. (2017) Nat. Commun. 8 · Meier et al. (2021) Nat. Geosci. 14",
    "Ellison et al. (2017) Global Environ. Change 43 · Natkhin et al. (2012) J. Hydrol. 448–449",
    "BTU Cottbus-Senftenberg: charlas «Wassergespräch Lausitz» de C. Hinz (2019) y C. Hildmann (2023); proyecto SoilWater (Hühnerwasser)",
    "Incendios: Thünen-Institut, Project brief 2022/24 · Schunk et al. (2017) Agric. For. Meteorol. · Horn (2024) TU Berlin · MIK Brandenburg, Waldbrandstatistik"], size=11.5, color=LIMA)
notas(sl, "Mi intuición tenía dos partes ciertas y una que no: el bosque sí guarda humedad bajo los árboles y sí puede traer lluvia a gran escala, "
          "pero en la cuenca evapora más de lo que trae. Estas referencias las saqué para seguir leyendo; conviene revisarlas antes de citarlas.")

ruta = OUT / "extra_bosque_y_lluvia.pptx"
prs.save(ruta)
print(f"-> {ruta.relative_to(RAIZ)} ({len(prs.slides)} diapositivas); lluvia necesaria: nativo +{dP_nec['nativo']:.0f} %, pino +{dP_nec['pino']:.0f} %")
