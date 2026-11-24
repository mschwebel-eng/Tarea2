"""
Sitio web de la Tarea 2 (evapotranspiracion en el Chicama hasta El Tambo y diseno hidrologico en Cottbus),
en formato de presentacion: una diapositiva a la vez, secciones en el encabezado, navegacion con flechas,
puntos y teclado, y modo claro/oscuro. Estilo copiado del sitio del grupo para Hidroituango
(estilo_deck.css + estilo_extra.css, que siguen los tokens de carlosdhoyos.github.io).

Regla: el sitio solo muestra resultados que existen en productos/ o datos/; lo que aun no se ha calculado
aparece como pendiente, nunca con cifras inventadas. Lluvia en azul, deficit/sequia en rojo.

Uso (desde tarea2):  .venv\\Scripts\\python.exe codigo\\sitio\\construir.py  ->  productos/sitio/index.html
"""
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
SITIO = Path(__file__).resolve().parent
DOCS = RAIZ / "productos" / "sitio"
DOCS.mkdir(parents=True, exist_ok=True)
T1_URL = "https://anajul1a4.github.io/Hidrologia-Chicama-El-Tambo/"
D = {}       # datos que pasan a las graficas (JSON)
sl = []      # diapositivas


def f(v, d=0):
    """Numero con espacio de miles y coma decimal (formato del informe)."""
    s = f"{v:,.{d}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


def tabla(filas, cab):
    th = "".join(f"<th>{html.escape(c)}</th>" for c in cab)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in filas)
    return f"<div class='tw'><table class='tb'><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>"


NOTAS = "https://carlosdhoyos.github.io/cursos/hidrologia/evapotranspiracion.html"


def nt(*nums):
    """Enlaces a diapositivas de las notas del curso (Hoyos, 2026): #sN."""
    return ", ".join(f"<a href='{NOTAS}#s{n}' target='_blank' rel='noopener'>#s{n}</a>" for n in nums)


# Para cada diapositiva: un recuadro de estabilidad/inversion (ESTAB) y una linea de fuentes (FUENTES)
ESTAB, FUENTES = {}, {}


def slide(id_, sec, kicker, titulo, cuerpo, g="d", k="k-data"):
    extra = ""
    if id_ in ESTAB:
        extra += f"<div class='callout violet'><b>Estabilidad e inversión.</b> {ESTAB[id_]}</div>"
    if id_ in FUENTES:
        extra += f"<p class='note'><b>Fuentes:</b> {FUENTES[id_]}</p>"
    sl.append(f"<section class='slide' id='{id_}' data-g='{g}' data-sec='{html.escape(sec)}'>"
              f"<p class='kicker {k}'>{kicker}</p><h2>{titulo}</h2>{cuerpo}{extra}</section>")


IMG = DOCS / "img"
IMG.mkdir(exist_ok=True)


def fig(src, nombre, alt):
    """Copia una figura del informe al sitio (WebP) y devuelve la etiqueta <img> con enlace a tamano completo."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    im.save(IMG / f"{nombre}.webp", "WEBP", quality=88, method=6)
    return (f"<a href='img/{nombre}.webp' target='_blank' rel='noopener' title='Abrir en tamaño completo'>"
            f"<img class='figimg' src='img/{nombre}.webp' width='{im.width}' height='{im.height}' alt='{html.escape(alt)}' "
            f"loading='lazy'></a>")


def tag(estado):
    t = {"hecho": ("done", "hecho"), "curso": ("prog", "en curso"), "pend": ("pend", "pendiente"),
         "dec": ("dec", "decisión del grupo"), "blk": ("blk", "bloqueado")}[estado]
    return f"<span class='tag {t[0]}'>{t[1]}</span>"


# ============================================================================= datos punto 1
T1 = RAIZ / "datos/punto1/tarea1"
pesos = pd.read_csv(T1 / "pesos_era5land_cuenca.csv")
gj = json.loads((T1 / "cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))
anillos = []
for ft in gj["features"]:
    geo = ft["geometry"]
    polys = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
    for p in polys:
        ring = np.array(p[0])
        paso = max(1, len(ring) // 600)                     # simplificar para la web
        anillos.append(ring[::paso].round(4).tolist())
D["cuenca"] = anillos
D["celdas"] = pesos.round(4).to_dict(orient="list")
area_cuenca = pesos.area_en_cuenca_km2.sum()
n_llenas = int((pesos.fraccion_celda >= 0.999).sum())

ERA = RAIZ / "datos/punto1/era5land"
n_horario = len(list((ERA / "horario_puntos").glob("*.zip"))) if (ERA / "horario_puntos").exists() else 0
hay_mensual = (ERA / "mensual" / "era5land_mensual_1981_2025_chicama.nc").exists()
est_desc = "hecho" if (n_horario == len(pesos) and hay_mensual) else "curso"

# ============================================================================= datos punto 2
P2 = RAIZ / "productos/punto2"
comp = pd.read_csv(P2 / "completitud_anual_cottbus_00880.csv")
peru = pd.read_csv(P2 / "disponibilidad_ghcnh_peru.csv")
D["comp"] = comp.replace({np.nan: None}).to_dict(orient="list")
caj = peru[peru.id == "PEI0000SPJR"]
D["caj"] = caj[["anio", "p1h", "p6h", "p24h"]].to_dict(orient="list")
n_validos = int(comp.valido.sum())
anios_val = comp[comp.valido].anio
caj_buenos = int((caj.p6h >= 0.8 * 1460).sum())

# ============================================================================= diapositivas
SEC = [("portada", "", "Inicio"), ("p1-cuenca", "1", "Evapotranspiración"), ("p2-sitio", "2", "Diseño hidrológico"),
       ("estado", "3", "Estado")]

sl.append(f"""<section class='slide portada' id='portada' data-g='' data-sec='Tarea 2 · Hidrología'>
<p class='kicker'>Tarea 2 · Hidrología 2026-2 · UNAL Medellín</p>
<h1>¿Cuánta agua devuelve a la atmósfera el <span class='hl'>Chicama</span>, y qué lluvia debe soportar una obra de drenaje?</h1>
<p class='lead'>Punto 1: demanda evaporativa (ETo FAO-56) y evapotranspiración real de la cuenca del río Chicama hasta El Tambo
({f(area_cuenca)} km², La Libertad, Perú), la misma de la <a href='{T1_URL}'>Tarea 1</a>. Punto 2: curvas IDF y diseño de una
alcantarilla y un tanque de detención con la lluvia de 10 minutos de Cottbus (Alemania).</p>
<div class='cards3'>
<button class='card lift pick' type='button' data-go='p1-cuenca'><h4>1 · Evapotranspiración</h4><p>Cuánta agua vuelve al cielo,
qué la limita cada mes y qué tan seguros estamos.</p></button>
<button class='card lift pick' type='button' data-go='p2-sitio'><h4>2 · Diseño hidrológico</h4><p>Por qué Cottbus, y la serie
de 10 minutos que sostiene la IDF.</p></button>
<button class='card lift pick' type='button' data-go='estado'><h4>3 · Estado del trabajo</h4><p>Qué está hecho, qué está en
curso y qué falta decidir.</p></button>
</div>
<p class='note' style='margin-top:16px'>Este sitio solo muestra resultados ya calculados y verificados; lo que falta aparece como pendiente.</p>
</section>""")

slide("p1-cuenca", "1 · Evapotranspiración", "Punto 1 · Datos",
      "La cuenca y las 30 celdas de ERA5-Land que la cubren", f"""
<div class='two fig'><div class='stack'>
<p>La ETo se calcula con ERA5-Land promediado sobre la cuenca <b>con la misma ponderación espacial de la Tarea 1</b>: cada celda de
0,1° pesa según el área que tiene dentro de la divisoria.</p>
<div class='readout'><div><span>celdas</span><b>{len(pesos)}</b></div><div><span>completas</span><b>{n_llenas}</b></div>
<div><span>área ponderada</span><b>{f(area_cuenca)} km²</b></div></div>
<p class='note'>Una celda de ERA5-Land mide unos 11 × 11 km a esta latitud; la cuenca va de 678 a 4 308 m, así que una sola
celda mezcla valle y cumbre. Por eso el apartado 1.1.a pide comparar la elevación del modelo con la del DEM.</p>
<p class='note'>Fuentes: delimitación propia con Copernicus GLO-30 y pesos de celda de la Tarea 1 (repositorio del grupo).</p>
</div><div class='panel'><div class='maphost' id='g-celdas'></div>
<p class='ts-title'>Color: fracción de cada celda dentro de la cuenca. Línea: divisoria (GLO-30).</p></div></div>""")

vars_h = [("2m_temperature", "Tmáx y Tmín de las 24 h → e<sub>s</sub> = ½[e°(Tmáx)+e°(Tmín)]"),
          ("2m_dewpoint_temperature", "e<sub>a</sub> = e°(T<sub>d</sub>)"),
          ("10m_u / 10m_v wind", "magnitud horaria √(u²+v²), luego promedio y reducción a 2 m (ec. 47)"),
          ("surface_solar_radiation_downwards", "R<sub>s</sub> → R<sub>ns</sub> = 0,77 R<sub>s</sub>; R<sub>nl</sub> con la ec. 39"),
          ("surface_pressure", "γ (constante psicrométrica)")]
slide("p1-datos", "1 · Evapotranspiración", "Punto 1 · 1.1.a",
      "Qué pedimos a ERA5-Land para la ETo de FAO-56", f"""
<div class='two even'><div class='stack'>
<div class='eq data'>ET<sub>o</sub> = [0,408 Δ (R<sub>n</sub> − G) + γ · 900/(T+273) · u<sub>2</sub> (e<sub>s</sub> − e<sub>a</sub>)] / [Δ + γ (1 + 0,34 u<sub>2</sub>)]</div>
{tabla([(f"<code>{v}</code>", u) for v, u in vars_h], ["Variable horaria", "Uso"])}
<p class='note'>Series horarias por punto (<code>reanalysis-era5-land-timeseries</code>), 1981–2025: las medias diarias de
componentes del viento subestiman la velocidad porque los vectores de distintas horas se cancelan.</p>
</div><div class='stack'>
<div class='callout {"green" if est_desc == "hecho" else "blue"}'><b>Descarga {tag(est_desc)}</b><br>
Series horarias: {n_horario} de {len(pesos)} celdas. Medias mensuales por área: {"descargadas" if hay_mensual else "en cola"}.</div>
<div class='card'><h4>Medias mensuales (<code>monthly-means</code>)</h4><p>Para la ETo calculada con medias mensuales (error por
promediar antes de una ecuación no lineal), la radiación neta real (1.2.3), la evaporación total (1.2.4) y la humedad del suelo
(1.3.2). Ojo: variables acumuladas en m d⁻¹ y evaporación negativa por convención.</p></div>
<div class='card'><h4>Lo que no entra en ETo</h4><p>La radiación neta de ERA5-Land es la de la superficie real, con su propio
albedo; la ETo usa la del pasto de referencia (albedo 0,23). La evaporación potencial <code>pev</code> no es ETo.</p></div>
</div></div>""")

# ----------------------------------------------------------------------------- 1.1.a resultados
P1 = RAIZ / "productos/punto1"
FG = P1 / "figuras"
FIG_P2 = RAIZ / "productos/punto2/figuras"
hay_eto = (P1 / "eto_climatologia_mensual.csv").exists()
FAO = "Allen et al. (1998), FAO-56"
FUENTES.update({
    "p1-paso1": f"{FAO}, cap. 3 (datos meteorológicos); notas del curso {nt(23, 55)}; Muñoz-Sabater et al. (2021).",
    "p1-dia": f"{FAO}, ecs. 6–8, 11–14, 21–25, 37–39 y 47 (caps. 2–3); notas {nt(25, 26, 29, 33, 50, 52)}.",
    "p1-ciclo": f"{FAO}, ec. 6; notas {nt(27, 28, 29, 33)}; inversión: radiosondeos de Trujillo, Tarea 1 (Fig. 8–9).",
    "p1-forz": f"notas {nt(25, 36, 37)}; Garreaud (2009); Klein y Hartmann (1993).",
    "p1-serie": f"notas {nt(52)}; Dingman (2015), sec. 6.7.",
    "p1-prom": f"guía 1.1.a; Dingman (2015), tabla 6.2; notas {nt(25, 35, 36, 55)}; aviso de ECMWF sobre las medias mensuales 2022-09 a 2024-02.",
    "p1-elev": f"{FAO}, ec. 7; notas {nt(35, 36)}; DEM Copernicus GLO-90; Tarea 1 (cortes topográficos, Fig. 9).",
    "p1b-estacion": f"{FAO}, ec. 50 (R<sub>s</sub> con ΔT, k<sub>Rs</sub> = 0,16) y anexo 6 (aridez de la estación); notas {nt(36, 37, 54, 55)}; NOAA GSOD.",
    "p1b-productos": f"Abatzoglou et al. (2018); PISCOeo_pm v1.0 (SENAMHI) vía CAMELS-PE; notas {nt(35, 37, 85)}; guía 1.1.b.",
})
ESTAB.update({
    "p1-dia": "En enero la inversión costera es débil y baja (0,3–0,7 km) y sobre la cuenca hay convección: las nubes recortan la radiación "
              "(R<sub>s</sub>/R<sub>so</sub> = 0,59). De noche esas mismas nubes funcionan como una manta: la pérdida de onda larga es solo "
              "2,7 MJ m⁻² d⁻¹, frente a ≈ 5 en las noches despejadas y estables de julio–agosto. El aire húmedo y casi en calma deja α* ≈ 1.",
    "p1-ciclo": "De mayo a septiembre la subsidencia del anticiclón del Pacífico Sur refuerza la inversión costera (91–100 % de los "
                "sondeos, tope a 1,0–1,3 km). Sobre la inversión el aire es seco y estable, no hay nubes convectivas, y la radiación que llega a la "
                "cuenca sube hasta octubre–noviembre. En la temporada de lluvias la inversión es más débil y baja (0,3–0,7 km) y la "
                "convección andina forma nubes que recortan R<sub>s</sub>: por eso la ETo baja justo cuando el Sol está más alto.",
    "p1-forz": "Con cielo despejado bajo la subsidencia, de noche el suelo se enfría y forma una capa estable con inversión de superficie "
               "(Tmín baja); de día la capa límite convectiva crece y «se come» aire seco de la troposfera libre (entrañamiento). "
               "Eso explica a la vez la mayor amplitud térmica, el rocío más bajo y el déficit de vapor máximo de julio–agosto.",
    "p1-prom": "El viento de la cuenca es sobre todo térmico: de día la ladera caliente y el aire inestable lo empujan valle arriba; de noche "
               "el aire frío y estable baja por las laderas. Al cambiar de sentido cada 12 horas, el promedio vectorial se cancela. "
               "El aire nocturno estable, además, frena la turbulencia, y eso FAO-56 no lo corrige (perfil neutro).",
    "p1-elev": "Los gradientes de −5,1 a −5,4 °C/km son menores que el adiabático seco (−9,8 °C/km): es una columna húmeda y bien "
               "mezclada sobre la inversión. Bajo el tope de la inversión (≈ 1,2 km en la estación seca, solo ≈ 5 % de la cuenca) "
               "la temperatura aumenta con la altura, así que esta corrección lineal no vale para el fondo del valle.",
    "p1b-estacion": "Cajamarca está en el fondo de un valle a 2 676 m, por encima de la inversión costera. En las noches despejadas el aire frío "
                    "drena por las laderas y se estanca en el fondo, con una inversión de superficie (aire estable, Tmín baja); de día el "
                    "valle, de poco volumen, se calienta mucho bajo una capa convectiva (aire inestable). Una celda de 9 km con relieve "
                    "suavizado no puede formar esa inversión nocturna ni ese calentamiento: su amplitud térmica es casi la mitad.",
    "p1b-productos": "Lo que más separa a los productos es el término aerodinámico: viento y déficit de vapor, las variables que dependen de la "
                     "capa límite y de la estabilidad. En la estación de lluvias, con la radiación como forzante dominante, coinciden; en la "
                     "estación seca, bajo la inversión reforzada y el aire seco de la subsidencia, se separan: PISCOeo supera a ERA5-Land "
                     "hasta en 25 % en junio–julio.",
})

if hay_eto:
    cl = pd.read_csv(P1 / "eto_climatologia_mensual.csv", index_col="mes")
    em = pd.read_csv(P1 / "eto_mensual_cuenca.csv", index_col=0, parse_dates=True)
    anual = em.eto.resample("YS").sum()[em.dias.resample("YS").count() == 12]
    epm = pd.read_csv(P1 / "error_promediar_por_mes.csv", index_col="mes")
    ele = pd.read_csv(P1 / "elevacion_modelo_vs_dem_por_celda.csv")
    ver = (P1 / "verificacion_eto_un_dia.txt").read_text(encoding="utf-8")
    frad = 100 * cl.eto_rad.sum() / cl.eto.sum()
    MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

    slide("p1-paso1", "1 · Evapotranspiración", "1.1.a · Paso 1", "Los datos: unidades, hora local y control de calidad", f"""
<div class='two even'><div class='stack'>
{tabla([("<code>t2m</code>, <code>d2m</code>", "K", "°C"), ("<code>u10</code>, <code>v10</code>", "m s⁻¹ (componentes, 10 m)", "magnitud √(u²+v²) cada hora"),
        ("<code>ssrd</code>", "J m⁻² en la hora que <b>termina</b> en <code>valid_time</code>", "MJ m⁻² d⁻¹ (suma de 24 h)"),
        ("<code>sp</code>", "Pa", "kPa")], ["Variable", "Viene en", "Se usa en"])}
<div class='callout blue'><b>Hora local.</b> ERA5-Land está en UTC y Perú en UTC−5. Un día peruano D va de D 06:00 UTC a D+1 05:00 UTC
para la radiación (acumulada en la hora anterior) y de D 05:00 a D+1 04:00 UTC para las variables instantáneas. Sin este corrimiento,
la Tmín de la madrugada quedaría partida entre dos días.</div>
</div><div class='stack'>
<div class='readout'><div><span>celdas</span><b>30</b></div><div><span>horas por celda</span><b>394 464</b></div><div><span>faltantes</span><b class='c-ok'>0</b></div></div>
<div class='card'><h4>Radiación horaria, no acumulada</h4><p>Sube en la mañana, llega al máximo al mediodía local y baja en la tarde. Hay unos pocos
−2 J m⁻² a las 19:00 locales: residuos numéricos, se ponen en 0.</p></div>
<div class='card'><h4>El viento de ERA5-Land es débil</h4><p>El máximo horario en 45 años es de solo 2,6–4,4 m s⁻¹ a 10 m: el relieve suavizado y una
rugosidad alta frenan el viento. Es una limitación para el término aerodinámico.</p></div>
<p class='note'>Script <code>codigo/punto1/lectura_era5land.py</code>; tabla <code>productos/punto1/control_calidad_era5land_horario.csv</code>.</p>
</div></div>""")

    dj = json.loads((P1 / "verificacion_eto_un_dia.json").read_text(encoding="utf-8"))
    D["dia"] = dj
    slide("p1-dia", "1 · Evapotranspiración", "1.1.a · Paso 2", "Un día a mano: así se arma la ETo de FAO-56", f"""
<p class='lead'>Celda central (7,6° S, 78,5° O), 15 de enero de 1981: un día nublado de la temporada de lluvias. La ETo suma dos cosas: la
<b>energía</b> que queda en la superficie y la <b>sed del aire</b>.</p>
<div class='two even'>
<div class='panel'><h3>1 · Energía: de la radiación del tope a R<sub>n</sub></h3><div class='tshost' id='g-dia-energia' style='height:300px'></div>
<p class='ts-title'>MJ m⁻² d⁻¹. De {f(dj['ra'], 1)} que llegan al tope de la atmósfera, solo quedan {f(dj['rn'], 1)} para evaporar
(= {f(dj['rn']*1e6/86400)} W m⁻² = {f(dj['rn']/2.45, 1)} mm d⁻¹ si toda se usara en evaporar). FAO-56 ecs. 21, 37–39.</p></div>
<div class='panel'><h3>2 · Aire: la curva de saturación</h3><div class='tshost' id='g-dia-sat' style='height:300px'></div>
<p class='ts-title'>e<sub>s</sub> = promedio de e°(Tmáx) y e°(Tmín) = {f(dj['es'], 2)} kPa; e<sub>a</sub> = e°(T<sub>rocío</sub>) = {f(dj['ea'], 2)} kPa.
Déficit = {f(dj['es']-dj['ea'], 2)} kPa. Como la curva es convexa, e°(T media) = {f(dj['e_tmedia'], 2)} kPa se queda corta. FAO-56 ecs. 11–14.</p></div>
</div>
<div class='two' style='margin-top:14px;align-items:center'>
<div class='panel'><h3>3 · Resultado: ETo = término radiativo + término aerodinámico</h3><div class='tshost' id='g-dia-eto' style='height:150px'></div></div>
<div class='stack'>
<div class='readout'><div><span>ETo</span><b>{f(dj['eto'], 2)} mm/d</b></div><div><span>radiativo</span><b class='c-sw'>{f(100*dj['rad']/dj['eto'])} %</b></div>
<div><span>α* = ETo/E<sub>eq</sub></span><b>{f(dj['alfa'], 2)}</b></div></div>
<p class='note'>Viento casi en calma (u₂ = {f(dj['u2'], 2)} m/s): la sed del aire apenas suma. α* ≈ 1 significa que la demanda es casi la de equilibrio,
la que habría con aire saturado.</p>
<div class='callout green'><b>Verificado:</b> <code>pyet</code> da {f(dj['eto_pyet'], 3)} mm/d, y el script de la cuenca reproduce el valor para esta celda y día.</div>
</div></div>""")

    slide("p1-ciclo", "1 · Evapotranspiración", "1.1.a · Paso 3", "La demanda de la cuenca: casi constante y dominada por la radiación", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1a_ciclo_anual.png', 'eto_ciclo', 'Ciclo anual de ETo, lluvia y radiación')}</div>
<div class='txtcols'><div>
<div class='readout'><div><span>ETo media anual</span><b>{f(anual.mean())} mm</b></div><div><span>rango entre años</span><b>{f(anual.min())}–{f(anual.max())}</b></div>
<div><span>término radiativo</span><b class='c-sw'>{f(frad)} %</b></div></div>
<p>La ETo varía poco a lo largo del año ({f(cl.eto.min())}–{f(cl.eto.max())} mm/mes) porque a 7,6° S el Sol siempre está alto. Lo que la modula es
<b>la nubosidad</b>: en febrero–abril la radiación en el tope de la atmósfera es máxima, pero las nubes de la temporada de lluvias dejan
pasar menos y la ETo baja. En octubre–noviembre el cielo aún está despejado y el Sol vuelve a estar alto: ahí está el máximo.</p></div>
<div><p>En junio–julio la radiación del tope es mínima (invierno austral) y el término radiativo cae, pero el aire seco y algo más ventoso de la
estación seca sube el término aerodinámico: <b>los dos términos se compensan en parte</b>.</p>
<p>La lluvia supera a la demanda solo de febrero a abril. De mayo a noviembre la ETo es mucho mayor que P: en esos meses la
evapotranspiración real tendrá que estar limitada por el agua, lo que se pondrá a prueba en los apartados 1.2 y 1.3.</p></div></div></div>""")

    slide("p1-forz", "1 · Evapotranspiración", "1.1.a · Paso 3", "Qué cambia en el aire de la estación seca", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1a_forzantes.png', 'eto_forzantes', 'Temperatura, déficit de vapor y viento')}</div>
<div class='txtcols'><div><p>La temperatura media apenas cambia en el año (≈ 14 °C en ERA5-Land): clima isotermal, como se vio en la Tarea 1. Lo que cambia es la
<b>amplitud diaria</b>: en julio–agosto, con cielos despejados, el día se calienta más y la noche se enfría más.</p></div>
<div><p>El punto de rocío cae unos 4 °C en la estación seca: el aire que llega es más seco (subsidencia del anticiclón del Pacífico Sur).
Con aire seco y más amplitud térmica, el déficit de vapor se duplica (0,37 → 0,80 kPa), y el viento a 2 m también es máximo en
julio–agosto, aunque sigue siendo débil.</p></div></div></div>""")

    slide("p1-serie", "1 · Evapotranspiración", "1.1.a · Paso 3", "La serie mensual y la ETo de cada celda", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1a_serie_mensual.png', 'eto_serie', 'Serie mensual de ETo')}</div>
<div class='two even'><div class='panel'>{fig(FG / 'fig_1_1a_eto_elevacion.png', 'eto_celdas', 'ETo por celda frente a elevación')}</div>
<div class='stack'><p>Entre celdas, la ETo cae de ≈ 1 400 mm/año a 1 400 m a ≈ 1 030 mm/año a 3 600 m: <b>unos −170 mm por cada kilómetro</b>.
Con la altura baja la temperatura, y con ella Δ (la pendiente de la curva de saturación) y el déficit de vapor; la radiación casi no cambia.</p>
<p>Por eso la elevación de cada celda importa (paso 5) y por eso el gradiente altitudinal es un buen tema para el apartado 1.5.a.</p>
<p class='note'>Decisiones: ETo calculada en cada celda y luego promediada (calcular con las variables ya promediadas da +0,4 %); γ y R<sub>so</sub> con la
elevación media de la cuenca, 2 557 m (usar la presión de cada celda cambia la ETo +0,1 %). Script <code>03_eto_diaria_cuenca.py</code>.</p></div></div></div>""")

    slide("p1-prom", "1 · Evapotranspiración", "1.1.a · Paso 4", "¿Cuánto se pierde al calcular con medias mensuales?", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1a_error_promediar.png', 'eto_promediar', 'Error por promediar')}</div>
<div class='txtcols'><div>
<p><b>M1</b> (medias de las variables diarias, con Tmáx y Tmín): error de ±0,5 %. La ecuación es casi lineal en R<sub>n</sub>, que domina la ETo.</p>
<p><b>M2</b> (sin extremos, e<sub>s</sub> = e°(T media)): −1 a −3 %. La curva de saturación es convexa, así que e°(T media) &lt; ½[e°(Tmáx)+e°(Tmín)].
El error crece en julio–agosto, cuando la amplitud térmica es mayor.</p></div>
<div><p><b>M3</b> (producto mensual de ERA5-Land): −2,5 a −6,4 %, máximo en julio–agosto. Al promediar las componentes del viento, la magnitud
queda en solo el 20–60 % de la real: las brisas de valle y de montaña cambian de dirección entre el día y la noche y se cancelan. Pesa más en la
estación seca, cuando el término aerodinámico es mayor.</p>
<div class='callout red'><b>Error del producto mensual confirmado:</b> entre 2022-09 y 2024-02 la radiación del producto mensual es solo el 31 % de la real
(el error que advierte ECMWF). Esos meses se excluyen de M3.</div></div></div></div>""")

    slide("p1-elev", "1 · Evapotranspiración", "1.1.a · Paso 5", "Elevación del modelo frente al DEM", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1a_elevacion.png', 'eto_elevacion', 'Elevación de ERA5-Land frente al DEM')}</div>
<div class='txtcols'><div>
<p>En promedio el modelo acierta: 2 641 m frente a 2 554 m del DEM (+87 m). Pero <b>celda a celda</b> se equivoca en 283 m de media y hasta 1 135 m,
y la curva hipsométrica muestra que el modelo no tiene ni el fondo del valle (&lt; 1 500 m) ni las cumbres (&gt; 3 850 m).</p>
<p>Las 30 celdas dan gradientes verticales muy limpios (R² ≈ 0,98): −5,4 °C/km en Tmáx, −5,1 en Tmín y −5,3 en el punto de rocío.</p></div>
<div><p>Corrigiendo T y T<sub>d</sub> a la elevación del DEM, la ETo de la cuenca cambia solo +1,1 % (1 212 → 1 226 mm): los errores de celdas altas y
bajas se compensan, y además T y T<sub>d</sub> bajan juntos, de modo que el déficit de vapor casi no cambia.</p>
<div class='callout amber'><b>Pero ERA5-Land es más frío que PISCOt:</b> 13,9 °C frente a 16,1 °C en 1981–2020. La elevación explica solo ≈ 0,5 °C de esa
diferencia; el resto es sesgo del reanálisis o de PISCOt. Se revisa en 1.1.b con estaciones.</div></div></div></div>""")

hay_b = (P1 / "prueba_productos_climatologia.csv").exists() and (P1 / "prueba_estacion_cajamarca_resumen.csv").exists()
if hay_b:
    rs_ = pd.read_csv(P1 / "prueba_estacion_cajamarca_resumen.csv").set_index("variable")
    at_ = pd.read_csv(P1 / "prueba_estacion_cajamarca_atribucion.csv", index_col=0).iloc[:, 0]
    rf_ = pd.read_csv(P1 / "prueba_restriccion_fisica.csv", index_col=0).iloc[:, 0]
    ce_ = pd.read_csv(P1 / "prueba_estacion_cajamarca_ciclo.csv", index_col="mes")
    cp_ = pd.read_csv(P1 / "prueba_productos_climatologia.csv", index_col="mes")
    eto_e, eto_r = rs_.loc["ETo (mm/d)", "estacion"], rs_.loc["ETo (mm/d)", "era5land"]
    amp_e = rs_.loc["Tmax (C)", "estacion"] - rs_.loc["Tmin (C)", "estacion"]
    amp_r = rs_.loc["Tmax (C)", "era5land"] - rs_.loc["Tmin (C)", "era5land"]

    slide("p1b-estacion", "1 · Evapotranspiración", "1.1.b · Prueba 1", "La estación de Cajamarca: ERA5-Land se queda corto", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1b_estacion.png', 'eto_estacion', 'Prueba con la estación de Cajamarca')}</div>
<div class='txtcols'><div>
<div class='readout'><div><span>días pareados</span><b>{int(ce_.n_dias.sum()):,}</b></div><div><span>ETo estación</span><b>{f(eto_e, 2)} mm/d</b></div>
<div><span>ETo ERA5-Land</span><b class='c-sw'>{f(eto_r, 2)} mm/d</b></div></div>
<p>En el mismo punto y los mismos días, la ETo de la estación es <b>{f(100*(eto_e/eto_r-1))} % mayor</b>, y lo es todo el año (+20 a +26 % según el mes).
Con la celda llevada a la altura real de la estación (el modelo la pone a ≈ 3 090 m, no a 2 676 m) la brecha baja a ≈ 16 %: la elevación explica
solo una parte.</p>
<p>La clave está en la <b>amplitud térmica diaria</b>: {f(amp_e, 1)} °C en la estación frente a {f(amp_r, 1)} °C en ERA5-Land. Una amplitud mayor
sube e<sub>s</sub> (la curva de saturación es convexa) y, en la ec. 50, también la R<sub>s</sub> estimada.</p></div>
<div><p><b>Atribución</b> (una variable de la estación a la vez dentro del cálculo de ERA5-Land): temperatura {f(at_.iloc[0], 2)}, radiación
{f(at_.iloc[3], 2)}, viento {f(at_.iloc[2], 2)} y rocío {f(at_.iloc[1], 2)} mm/d. La suma ({f(at_.sum(), 2)}) no llega a la diferencia total
({f(eto_e-eto_r, 2)}): el resto son interacciones no lineales.</p>
<div class='callout amber'><b>Cautelas.</b> La R<sub>s</sub> de la estación no se mide, se estima con ΔT (ec. 50), y con la misma ecuación ERA5-Land daría aún
menos. El rocío y el viento de GSOD promedian horas diurnas: T<sub>mín</sub> − T<sub>rocío</sub> sale negativo, así que la prueba de aridez de Allen (&lt; 2 °C)
no se puede aplicar con rigor. Y es un solo punto, en el fondo de un valle.</div></div></div></div>""")

    slide("p1b-productos", "1 · Evapotranspiración", "1.1.b · Pruebas 2 y 3", "Productos de demanda: el mismo total por caminos distintos", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1b_productos.png', 'eto_productos', 'Comparación con PISCOeo y TerraClimate')}</div>
<div class='txtcols'><div>
<div class='readout'><div><span>ERA5-Land (FAO-56)</span><b class='c-sw'>{f(cp_.eto_era5land.sum())} mm/a</b></div>
<div><span>PISCOeo_pm</span><b>{f(cp_.pet_piscoeo.sum())}</b></div><div><span>TerraClimate</span><b>{f(cp_.pet_terraclimate.sum())}</b></div></div>
<p class='note'>Medias de 1981–2020, el periodo común de los tres productos.</p>
<p><b>TerraClimate da casi el mismo total que ERA5-Land, pero por otra vía:</b> recibe 23 % menos radiación (179 frente a 232 W m⁻²) y lo compensa con
un viento 3–4 veces mayor y un aire más seco. Es una <b>compensación de errores</b>: el total coincide aunque los mecanismos no.</p></div>
<div><p><b>PISCOeo_pm (SENAMHI)</b> es 10 % mayor en el año y hasta 25 % en junio–julio. Usa temperaturas de estaciones peruanas (PISCOt), más cálidas
que ERA5-Land, sobre todo de noche (Tmín 10,8 frente a 8,3 °C).</p>
<p><b>Restricción física (1998–2024):</b> ETo = {f(rf_.ETo_era5land_mm)} mm/a frente a P − Q = {f(rf_.P_menos_Q_mm)} mm/a (P = {f(rf_.P_mm)}, Q = {f(rf_.Q_mm)}).
La demanda casi triplica a la evapotranspiración real posible: la cuenca está limitada por agua y la restricción se cumple con holgura.</p>
<p class='note'>La banda gris (mínimo y máximo de las tres estimaciones por mes) es la dispersión que usaremos en 1.1.d para decidir si un método simple falla.</p>
</div></div></div>""")

hay_c = (P1 / "metodos_metricas.csv").exists()
if hay_c:
    mt = pd.read_csv(P1 / "metodos_metricas.csv")
    FUENTES["p1c-metodos"] = (f"notas {nt(60, 61, 62, 63, 64, 65, 34)}; Thornthwaite (1948); Hamon (1961) en la forma de Lu et al. (2005); "
                              "Hargreaves y Samani (1985); Oudin et al. (2005); Priestley y Taylor (1972); Meyer (1915); Penman (1948)/FAO-24; "
                              "Makkink (1957); Linacre (1977); Dingman (2015), sec. 6.7.")
    FUENTES["p1c-fisica"] = f"notas {nt(33, 34, 62, 63, 64, 67, 75)}; Milly y Dunne (2016); Allen et al. (1998), cap. 4."
    ESTAB["p1c-fisica"] = ("Los métodos que «ven» la humedad (Dalton, Meyer y Linacre) tienen su máximo en julio–agosto: es el aire seco que baja con "
                           "la subsidencia del anticiclón y que la capa límite convectiva mezcla hacia la superficie cada tarde, sobre la inversión. "
                           "Los de radiación tienen su máximo en octubre–noviembre, cuando el cielo sigue despejado y el Sol está alto. FAO-56, con "
                           "un viento tan débil, sigue sobre todo a la radiación; por eso la familia que más se le parece es la radiativa.")
    filas_m = []
    for _, r in mt.iterrows():
        if r.metodo.startswith("FAO"):
            continue
        filas_m.append((html.escape(r.metodo), html.escape(r.familia), f(r.anual_mm), f(r["sesgo_%"], 0) + " %", f(r.RMSE, 1),
                        f(r.r, 2), f(r.amplitud_mm), r.mes_max, f"{int(r.meses_fuera_dispersion)}/12"))
    ref = mt[mt.metodo.str.startswith("FAO")].iloc[0]
    slide("p1c-metodos", "1 · Evapotranspiración", "1.1.c · Métodos simples", "Nueve métodos frente a FAO-56", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1c_metodos.png', 'metodos', 'Métodos simples frente a FAO-56')}</div>
<div>{tabla(filas_m, ["Método", "Familia", "mm/año", "Sesgo", "RMSE (mm/mes)", "r", "Amplitud (mm)", "Máximo", "Fuera de la dispersión"])}
<p class='note'>FAO-56: {f(ref.anual_mm)} mm/año, amplitud del ciclo {f(ref.amplitud_mm)} mm, máximo en {ref.mes_max}. Métricas sobre la serie mensual
1981–2025 de la cuenca. «Fuera de la dispersión»: meses en que la diferencia con FAO-56 supera el ancho de la banda de las pruebas de 1.1.b.
Verificación: Hargreaves, Oudin, Priestley–Taylor y Linacre coinciden con <code>pyet</code> (±0,4 %); Hamon y Thornthwaite, a mano.
* = métodos nuevos, que no están en la tabla de la guía.</p></div></div>""")

    slide("p1c-fisica", "1 · Evapotranspiración", "1.1.c · Interpretación", "Cada familia ve una parte distinta de la física", f"""
<div class='two even'><div class='stack'>
<div class='card'><h4>Radiación: Makkink* gana, Priestley–Taylor sobra 21 %</h4><p>El 90 % de la ETo es radiativa, así que los métodos de radiación
siguen bien el ciclo (r ≈ 0,97). <b>Makkink</b> (pasto, clima húmedo de los Países Bajos) acierta en el año (−2 %) y en la fase (máximo en noviembre).
<b>Priestley–Taylor</b> con α = 1,26 sobreestima porque FAO-56 incluye la resistencia del pasto (70 s m⁻¹) y aquí el aire casi no se mueve: el α
implícito es ≈ 1,04.</p></div>
<div class='card'><h4>Temperatura y radiación extraterrestre: Hargreaves funciona, Oudin no</h4><p><b>Hargreaves</b> (+6 %) usa Tmáx − Tmín como indicador de nubosidad:
la amplitud térmica es mayor con cielo despejado. <b>Oudin</b> (−17 %) solo ve R<sub>a</sub>, que es máxima en enero bajo las nubes: tiene la fase al revés.</p></div>
</div><div class='stack'>
<div class='card'><h4>Temperatura sola: Thornthwaite y Hamon, −40 %</h4><p>Se calibraron en latitudes medias, donde T y radiación suben juntas en verano. En
los Andes tropicales a 2 500 m hace frío (≈ 14 °C) con un Sol intenso: la temperatura no representa la energía disponible. Su ciclo es plano y su máximo
cae en diciembre.</p></div>
<div class='card'><h4>Transferencia de masa: Dalton y Meyer ven solo el aire</h4><p>Siguen u × (e<sub>s</sub> − e<sub>a</sub>): −50 % en la temporada de lluvias y ≈ 0 en julio–agosto,
con una amplitud de ≈ 67 mm, más del doble de la de FAO-56. Además son fórmulas de lagos, que usan e<sub>s</sub> a la temperatura del agua.</p></div>
<div class='card'><h4>Linacre*: bien con lluvias, +25 % en la estación seca</h4><p>Su término 15(T − T<sub>d</sub>) responde al aire seco como si el viento fuera
«normal». Con u₂ = 2 m/s, FAO-56 también daría ≈ 123 mm en agosto: Linacre responde a un forzante, el viento, que no incluye.</p></div>
</div></div>
<div class='callout blue'><b>Respuestas de la guía.</b> (1) Mejor ajuste: Makkink (RMSE 3,9 mm/mes, sesgo −2 %), luego Hargreaves. (2) Es esperable porque la demanda
es radiativa, pero puede ser una compensación: con más viento (TerraClimate, PISCOeo) Makkink se quedaría corto en la estación seca. (3) Thornthwaite y
Hamon se alejan todos los meses (por debajo); Dalton y Meyer en la temporada de lluvias; Priestley–Taylor por encima; casi todos superan la dispersión
de las pruebas. Con solo temperatura usaríamos <b>Hargreaves</b> (árbol de decisión de las notas).</div>""")

hay_d = (P1 / "sensibilidad_anual_pct.csv").exists()
if hay_d:
    tm_ = pd.read_csv(P1 / "terminos_fao56_por_mes.csv", index_col="mes")
    sa_ = pd.read_csv(P1 / "sensibilidad_anual_pct.csv", index_col=0)
    FUENTES["p1d-terminos"] = f"guía 1.1.d; notas {nt(33, 36, 37, 50, 51, 52)}; Priestley y Taylor (1972); Allen et al. (1998), ec. 6."
    FUENTES["p1d-sens"] = f"guía 1.1.d; notas {nt(25, 63, 64, 68, 93)}; Milly y Dunne (2016)."
    FUENTES["p1d-sintesis"] = f"notas {nt(23, 62, 63, 64, 65, 75)}; Shaw et al. (2010), sec. 10.3; Hargreaves y Samani (1985); Makkink (1957); Linacre (1977)."
    ESTAB["p1d-terminos"] = ("α* sube de 1,01 en la temporada de lluvias a 1,10 en julio: es la huella del aire seco que la capa límite convectiva "
                             "mezcla desde la troposfera libre (entrañamiento), que en la estación seca está seca por la subsidencia sobre la inversión. "
                             "Nunca llega a 1,26 porque el pasto tiene resistencia (70 s m⁻¹) y porque de noche el aire estable casi no se mezcla. "
                             "FAO-56 no corrige la estabilidad: supone un perfil de viento neutro.")
    ESTAB["p1d-sens"] = ("Que la humedad (e<sub>a</sub>) importe poco en FAO-56 no quiere decir que el aire seco no importe: importa poco porque aquí casi no hay "
                         "viento que lo renueve. En un valle con viento (o con el viento de TerraClimate) el término aerodinámico pesaría 2–3 veces más, "
                         "y con él el viento y la humedad, que dependen de la capa límite y de su estabilidad.")
    ESTAB["p1d-sintesis"] = ("Los métodos que fallan más en la estación seca (Linacre, Dalton, Meyer, por encima; Oudin, por debajo) son los que reaccionan "
                             "solo a una parte del cambio que trae la inversión reforzada: aire seco y cielo despejado llegan juntos, y FAO-56 combina los dos.")
    slide("p1d-terminos", "1 · Evapotranspiración", "1.1.d · Explicar las diferencias", "Los dos términos de FAO-56 y el coeficiente α*", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1d_terminos.png', 'terminos', 'Términos de FAO-56 y alfa implícito')}</div>
<div class='txtcols'><div>
<p>El <b>término aerodinámico</b> va del {f(100*tm_.frac_aero.min())} % de la ETo en febrero al {f(100*tm_.frac_aero.max())} % en julio. Aun en la estación seca, la
energía radiativa pone más de 5/6 de la demanda.</p>
<p><b>α* = ETo/E<sub>eq</sub></b> mide cuánto se aleja la demanda de la de equilibrio, la que habría con aire saturado y sin mezcla. Va de
{f(tm_.alfa_star.min(), 2)} (febrero) a {f(tm_.alfa_star.max(), 2)} (julio), con 1,04 en el año, y sigue al déficit de vapor y al viento (r ≈ 0,9 en las dos
series mensuales).</p></div>
<div><p><b>Por qué no se compara solo con 1,26:</b> Priestley y Taylor encontraron α ≈ 1,26 sobre superficies mojadas, sin resistencia de superficie.
FAO-56 tiene la resistencia del pasto de referencia (70 s m⁻¹), que baja α* aun con aire no saturado. Por eso α* &lt; 1,26 todo el año; los valores altos de la
estación seca sí señalan aire seco.</p></div></div></div>""")

    slide("p1d-sens", "1 · Evapotranspiración", "1.1.d · Sensibilidad", "¿Qué forzante mueve la demanda? Experimento de sensibilidad", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_1d_sensibilidad.png', 'sensibilidad', 'Experimento de sensibilidad')}</div>
<div class='txtcols'><div>
<p><b>En FAO-56 manda la radiación:</b> R<sub>s</sub> −10 % baja la ETo {f(-sa_.loc['FAO-56 PM', 'rs-10'], 1)} % todo el año (un poco menos en julio, cuando pesa más el aire).
Un grado más sube la ETo {f(sa_.loc['FAO-56 PM', 'T+1_ea'], 1)} % con e<sub>a</sub> constante y {f(sa_.loc['FAO-56 PM', 'T+1_hr'], 1)} % con HR constante: la diferencia es pequeña
porque, sin viento, el déficit que crece casi no se transporta. u₂ +10 % solo suma {f(sa_.loc['FAO-56 PM', 'u2+10'], 1)} % (0,8 % en julio–agosto).</p></div>
<div><p><b>Respuesta al calentamiento:</b> Thornthwaite sube {f(sa_.loc['Thornthwaite', 'T+1_ea'], 0)} % por grado (3,4 veces FAO-56), Hamon {f(sa_.loc['Hamon', 'T+1_ea'], 0)} % y Oudin
{f(sa_.loc['Oudin', 'T+1_ea'], 0)} %: leen el calentamiento como si llegara más energía, aunque la radiación no cambió (Milly y Dunne, 2016). Hargreaves responde casi como
FAO-56 ({f(sa_.loc['Hargreaves', 'T+1_ea'], 1)} %). Dalton y Meyer dan +21 % si e<sub>a</sub> queda fija y +6,5 % si la HR queda fija: dependen por completo de lo que pase con la humedad.</p>
<p><b>Responden a algo que no incluyen:</b> Priestley–Taylor reacciona a la humedad (+{f(sa_.loc['Priestley–Taylor', 'ea+10'], 1)} % con e<sub>a</sub> +10 %) a través de la onda larga
de R<sub>n</sub>; los métodos de temperatura responden a la «energía» a través de T; y ninguno de ellos ve una nubosidad mayor (R<sub>s</sub> −10 % no los cambia).</p></div></div></div>""")

    sint = [("Thornthwaite, Hamon", "todos (−35 a −50 %), peor en ago–nov", "calibración de latitudes medias: en los Andes tropicales hace frío con un Sol intenso"),
            ("Oudin", "jun–ago (−26 %)", "solo ve R<sub>a</sub>, mínima en junio; ni nubes ni aire seco"),
            ("Hargreaves", "feb–mar (+10 a +12 %)", "Tmáx − Tmín ≈ 9 °C bajo las nubes sugiere más sol del que llega; calibrado en clima semiárido (California)"),
            ("Priestley–Taylor", "todo el año (+15 a +25 %), menos en jul–ago", "α = 1,26 sin resistencia de superficie; FAO-56 tiene α* ≈ 1,0–1,1"),
            ("Makkink*", "feb–mar (−7 %)", "usa R<sub>s</sub>, no R<sub>n</sub>; constante calibrada en pasto de los Países Bajos"),
            ("Dalton, Meyer", "temporada de lluvias (−50 %)", "solo transferencia de masa; fórmulas de lagos con e<sub>s</sub> del aire"),
            ("Linacre*", "jun–ago (+19 a +26 %)", "el término de aire seco supone un viento moderado que ERA5-Land no tiene")]
    mm_h = 146 / 2.45e6 * 3600
    slide("p1d-sintesis", "1 · Evapotranspiración", "1.1.d · Síntesis", "Por qué y cuándo se aparta cada método", f"""
{tabla(sint, ["Método", "Cuándo se aparta más", "Por qué"])}
<div class='two even'><div class='callout green'><b>Si solo tuviéramos temperatura: Hargreaves.</b> Árbol de decisión de las notas (#s75), paso 4: con Tmáx y Tmín,
Hargreaves–Samani. Aquí se justifica con datos: sesgo +6 %, fase correcta (máximo en octubre) y una respuesta al calentamiento como la de FAO-56. Thornthwaite,
el método «de temperatura media», se descarta: −43 % y una sensibilidad exagerada al calentamiento.</div>
<div class='callout amber'><b>Verificar unidades (guía, Shaw et al., 2010).</b> 146 W m⁻² / 2,45×10⁶ J kg⁻¹ = 5,96×10⁻⁵ kg m⁻² s⁻¹ = <b>{f(mm_h, 3)} mm/h</b>
({f(mm_h*24, 2)} mm/d), no 3,52 mm/h, que es unas 16 veces más. Ese 3,52 sale si se usa λ en J g⁻¹ (g m⁻² s⁻¹ leído como mm s⁻¹) y se multiplica por 60
en vez de por 3 600. Regla: 1 mm/d ≈ 28,4 W m⁻²; la ETo media de la cuenca, 3,3 mm/d, equivale a ≈ 94 W m⁻².</div></div>""")

hay_12 = (P1 / "et_real_largo_plazo.csv").exists()
if hay_12:
    lp_ = pd.read_csv(P1 / "et_real_largo_plazo.csv", index_col=0).iloc[:, 0]
    er_ = pd.read_csv(P1 / "et_real_propagacion_error.csv")
    FUENTES["p12-balance"] = (f"guía 1.2; notas {nt(14, 15, 79, 81)}; McMillan et al. (2012) para la incertidumbre del caudal; PISCOp v2.1 (Aybar et al., 2020) "
                              "e IMERG V07 de la Tarea 1; GRACE no se usa (resolución ~10⁵ km² frente a 2 170 km²; Peters-Lidard et al., 2018).")
    FUENTES["p12-productos"] = (f"notas {nt(28, 31, 85, 87)}; Muñoz-Sabater et al. (2021); Abatzoglou et al. (2018); aviso de ECMWF sobre las medias "
                                "mensuales 2022-09 a 2024-02.")
    ESTAB["p12-balance"] = ("Los dos años con P − Q anómalo son años de calentamiento del mar: 2000 (tras El Niño de 1997–98) y 2017 (Niño costero). "
                            "Con el mar caliente la inversión se debilita y la convección llega a cotas bajas, donde hay pocos pluviómetros: P<sub>L</sub> "
                            "subestima esas lluvias y el agua que se guardó en suelos y acuíferos sale después por el río (ΔS ≠ 0). P − Q no es ET en esos años.")
    ESTAB["p12-productos"] = ("Con solo ≈ 24 % de R<sub>n</sub> usado en evaporar, ≈ 3/4 de la energía calienta el aire (calor sensible, razón de Bowen ≈ 3 según el "
                              "balance). Ese calor hace crecer la capa límite convectiva de día, hasta chocar con el aire estable de la inversión y de la "
                              "subsidencia de arriba. ERA5-Land, con un suelo demasiado húmedo, reparte casi mitad y mitad (Bowen 0,6 en lluvias, 1,6 en agosto).")
    slide("p12-balance", "1 · Evapotranspiración", "1.2 · ET real por balance", "¿Cuánta agua vuelve al cielo? El balance P − Q", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_2_balance.png', 'et_balance', 'Balance de largo plazo y año a año')}</div>
<div class='txtcols'><div>
<div class='readout'><div><span>ET = P<sub>L</sub> − Q</span><b>{f(lp_.ET_PL)} ± {f(er_.sigma_ET[0])} mm/a</b></div>
<div><span>ET/P</span><b>{f(lp_.ET_PL/lp_.P_L, 2)}</b></div><div><span>ET/ETo</span><b>{f(lp_.ET_PL/lp_.ETo, 2)}</b></div></div>
<p>De {f(lp_.P_L)} mm de lluvia al año (P<sub>L</sub>, 1998–2024), {f(lp_.Q)} mm salen por el río y <b>≈ {f(lp_.ET_PL)} mm vuelven a la atmósfera</b>. Es solo el
{f(100*lp_.ET_PL/lp_.ETo)} % de lo que pide la atmósfera: la cuenca está <b>limitada por agua</b>.</p>
<p>Con IMERG la ET sería de solo {f(lp_.ET_PI)} mm/a, con una fracción evaporativa de 0,08 en una cuenca con pasto, arbustal y bosque: no es creíble.
Confirma que IMERG subestima la lluvia (Tarea 1: 65 % de P<sub>L</sub>).</p></div>
<div><p><b>Propagación del error.</b> El sesgo de la lluvia pasa entero a ET. Con σ<sub>P</sub> = |P<sub>L</sub> − P<sub>I</sub>|/2 = {f(er_.sigma_P[0])} mm y σ<sub>Q</sub> = 15 % de Q
= {f(er_.sigma_Q[0])} mm: σ<sub>ET</sub> = {f(er_.sigma_ET[0])} mm, el <b>{f(er_.iloc[0, 4])} % de ET</b>. Si toda la diferencia entre productos fuera error, σ<sub>ET</sub>
llegaría a {f(er_.sigma_ET[1])} mm ({f(er_.iloc[1, 4])} %). La lluvia, no el caudal, domina la incertidumbre.</p>
<p><b>Año a año</b> (octubre–septiembre, desde el mínimo de almacenamiento) P − Q va de ≈ 400 a ≈ 690 mm y apenas sigue a la lluvia (r = 0,29): la ET es casi constante. Ningún año
es negativo ni supera R<sub>n</sub>/λ. Las excepciones son 2000 y 2017. Mes a mes, P − Q es negativo de mayo a agosto: el río drena el almacenamiento; eso no es ET.</p>
<p class='note'>No encontramos torres de covarianza de remolinos en los Andes del norte del Perú (la consulta automática a AmeriFlux falló: falta verificar a mano).</p>
</div></div></div>""")

    slide("p12-productos", "1 · Evapotranspiración", "1.2 · Productos y techo energético", "Los productos de ET real: cada uno hereda su propia lluvia", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_2_ciclo.png', 'et_ciclo', 'Ciclo anual de la ET real')}
<div class='callout teal' style='margin-top:10px'><b>¿Por qué la ET baja justo cuando la demanda sube?</b> La ETo es lo que evaporaría un pasto <i>siempre regado</i>;
la ET real es lo que la cuenca puede dar con el agua que tiene. En marzo (213 mm de lluvia) la ET de TerraClimate llega al 96 % de la ETo: manda la
<b>energía</b>. En agosto (3 mm de lluvia) el suelo está seco, las plantas cierran los estomas y la ET cae al 11 % de la ETo: manda el <b>agua</b>.
Y la relación también va al revés (Bouchet, 1963; notas {nt(68)}): la energía que no se usa en evaporar calienta y seca el aire (la razón de Bowen sube de
0,6 a 1,6 en ERA5-Land), así que <b>la demanda sube porque la ET baja</b>. La capa límite, más caliente, crece y mezcla aire aún más seco de encima de la
inversión ({nt(37)}). ERA5-Land baja menos (49 % en agosto) porque su suelo, con 2,3 veces más lluvia, entra húmedo a la estación seca.</div></div>
<div class='txtcols'><div>
{tabla([("Balance P<sub>L</sub> − Q", "observaciones", f(lp_.P_L), f(lp_.ET_PL), f(lp_.ET_PL / (lp_.Rn_lambda), 2)),
        ("ERA5-Land", "modelo de superficie (HTESSEL)", f(lp_.P_era5land), f(lp_.ET_era5land), f(lp_.ET_era5land / lp_.Rn_lambda, 2)),
        ("TerraClimate", "balance hídrico mensual", f(lp_.P_terraclimate), f(lp_.ET_terraclimate), f(lp_.ET_terraclimate / lp_.Rn_lambda, 2))],
       ["Estimación", "Principio", "P (mm/a)", "ET (mm/a)", "λET / Rn"])}
<p><b>Techo energético:</b> R<sub>n</sub> real de ERA5-Land = {f(lp_.Rn_wm2)} W m⁻² = {f(lp_.Rn_lambda)} mm/a. Todas las estimaciones quedan muy por debajo: no hace falta
advección para explicar la ET.</p></div>
<div><p><b>ERA5-Land</b> da {f(lp_.ET_era5land)} mm/a, más que toda la lluvia observada, porque su propio reanálisis hace llover {f(lp_.P_era5land)} mm/a (2,3 veces P<sub>L</sub>):
con el suelo siempre húmedo, sigue evaporando 55–75 mm/mes en la estación seca. <b>TerraClimate</b> ({f(lp_.ET_terraclimate)} mm/a) queda a +17 % del balance,
pero por compensación: su lluvia es menor ({f(lp_.P_terraclimate)} mm/a) y evapora casi toda (ET/P = 0,94), con muy poco caudal. Para el total multianual el
balance es la mejor estimación; para el ciclo anual dependemos de productos, y el de TerraClimate (máximo en marzo, mínimo de 12 mm en agosto) es el más
coherente con una cuenca limitada por agua.</p>
<div class='callout red'><b>Control:</b> el error de ECMWF también afecta la evaporación mensual: entre 2022-09 y 2024-02 ERA5-Land da el 30 % de lo normal. Se excluye.</div>
</div></div></div>""")

hay_13 = (P1 / "budyko_resumen.csv").exists()
if hay_13:
    bz = pd.read_csv(P1 / "budyko_resumen.csv", index_col=0).iloc[:, 0]
    rg = pd.read_csv(P1 / "regimen_mensual.csv", index_col="mes")
    ct = pd.read_csv(P1 / "regimen_complementaria_terciles.csv", index_col=0)
    FUENTES["p13-regimen"] = f"guía 1.3; notas {nt(19, 27, 43, 58)}; Dingman (2015), sec. 6.8; Muñoz-Sabater et al. (2021); Abatzoglou et al. (2018)."
    FUENTES["p13-budyko"] = (f"notas {nt(15, 69, 70, 71, 73, 68)}; Budyko (1974); Fu (1981); Sankarasubramanian et al. (2001); Bouchet (1963); "
                             "Brutsaert y Parlange (1998); CAMELS-PE (stream_elas).")
    FUENTES["p13-sintesis"] = f"notas {nt(15, 27, 68, 71)}; Tarea 1 (secciones 3.2 y 3.7)."
    ESTAB["p13-regimen"] = ("Los meses limitados por agua (mayo–septiembre) son los de la inversión reforzada (91–100 % de los sondeos): la subsidencia "
                            "tapa la convección, no llueve y el suelo se seca. La energía que ya no se evapora calienta el aire (la razón de Bowen sube) y la "
                            "capa límite convectiva crece hasta la base del aire estable. En la temporada de lluvias la inversión se debilita, hay convección y "
                            "lluvia, y la ET vuelve a estar limitada por la energía, recortada por las nubes.")
    ESTAB["p13-budyko"] = ("La relación complementaria tiene un mecanismo atmosférico: en un año o un mes seco la superficie entrega más calor sensible, la "
                           "capa límite se calienta y crece, mezcla aire seco de la troposfera libre y el déficit de vapor sube. Explicación alternativa que "
                           "estos datos no separan: un año seco también tiene menos nubes y más radiación, y eso sube la ETo sin ningún efecto del suelo.")
    ESTAB["p13-sintesis"] = ("La inversión explica tanto la estación seca como el régimen evaporativo: mientras la tapa de subsidencia está firme, la cuenca no "
                             "recibe agua y su ET queda limitada por el agua aunque la atmósfera tenga más sed que nunca.")
    slide("p13-regimen", "1 · Evapotranspiración", "1.3 · ¿Manda la energía o el agua?", "Mes a mes: energía en marzo, agua de mayo a septiembre", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_3_regimen.png', 'regimen', 'Régimen evaporativo mensual y humedad del suelo')}</div>
<div class='txtcols'><div>
<p><b>Criterios</b> (propuestos, con ET de TerraClimate): limitado por energía si ET/ETo ≥ 0,75; por agua si ET/ETo ≤ 0,40; transición entre ambos.</p>
{tabla([("energía", "feb, mar", "pico de la temporada húmeda"), ("transición", "ene, abr, oct, dic", "bordes de la temporada húmeda"),
        ("agua", "may–sep, nov", "temporada seca")], ["Régimen", "Meses (TerraClimate)", "Temporada de la Tarea 1"])}
<p>La clasificación coincide con las temporadas de la Tarea 1. Con ERA5-Land casi todo el año sale limitado por energía, porque su suelo está húmedo de más (1.2).</p></div>
<div><p><b>¿Hay meses con ET &gt; P?</b> Sí: de mayo a septiembre la ET de TerraClimate es de 1 a 4 veces la lluvia. Esa agua sale del <b>almacenamiento del
suelo</b> llenado en febrero–abril, y quizá de las areniscas fisuradas que sostienen el caudal de estiaje (Tarea 1).</p>
<p><b>Humedad del suelo (ERA5-Land):</b> por encima de θ* ≈ {f(bz.theta_umbral, 2)} m³/m³ la fracción evaporativa se estanca en ≈ {f(bz.ef_meseta, 2)}: manda la energía.
Por debajo cae casi en línea recta: manda el agua. Julio–septiembre están bajo el umbral casi todos los años (96–100 %); junio y octubre, la mayoría (59–63 %). Cautela: es el umbral del modelo (su función de estrés),
no una observación, y el ajuste segmentado solo mejora un {f(100*bz.mejora_segmentado)} % frente a una recta.</p></div></div></div>""")

    slide("p13-budyko", "1 · Evapotranspiración", "1.3 · Budyko, elasticidad y relación complementaria", "En el promedio manda el agua, y la cuenca «desperdicia» lluvia", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_3_budyko.png', 'budyko', 'Espacio de Budyko y relación complementaria')}</div>
<div class='txtcols'><div>
<div class='readout'><div><span>φ = ETo/P</span><b>{f(bz.phi, 2)}</b></div><div><span>ET/P</span><b>{f(bz.ET_P, 2)}</b></div>
<div><span>Budyko esperaría</span><b class='c-lw'>{f(bz.budyko_1974, 2)}</b></div><div><span>ω de Fu</span><b>1,6–1,8</b></div></div>
<p>Con φ &gt; 1 la cuenca está <b>limitada por agua</b> en el promedio. Pero evapora mucho menos que lo que predice Budyko: ω = {f(bz.omega_fu, 2)} con todos los años y 1,77
sin 2000 ni 2017, frente a ≈ 2,6 en promedio mundial. ω bajo significa que la lluvia «se va» por el río antes de poder evaporarse. Se usó ETo en lugar de la ETp de
Budyko: la ETo del pasto es menor que la de una superficie mojada, y eso desplaza φ hacia la izquierda.</p>
<p><b>Por qué ω es bajo:</b> el 81 % de la lluvia cae en diciembre–abril, cuando la demanda es menor por las nubes; los suelos se saturan y las laderas
(27° en promedio) escurren rápido; cuando la demanda es máxima (agosto–noviembre), ya no hay agua. Alternativa: si P<sub>L</sub> subestima la lluvia de las
cabeceras (Tarea 1), ET/P estaría subestimado y ω sería mayor.</p></div>
<div><p><b>Elasticidad del caudal a la lluvia:</b> teórica (Fu) {f(bz.eps_teorica, 2)}, empírica {f(bz.eps_empirica, 2)} (estimador de mediana); CAMELS-PE da 1,57. Una lluvia
10 % menor reduce el caudal ≈ 15 %.</p>
<p><b>Relación complementaria:</b> en los años secos la demanda es mayor ({f(ct.loc['secos', 'eto'])} frente a {f(ct.loc['húmedos', 'eto'])} mm/a en los húmedos; r(ETo, P) =
{f(bz.r_eto_P_anual, 2)}) mientras la ET baja ({f(ct.loc['secos', 'PmQ_L'])} frente a {f(ct.loc['húmedos', 'PmQ_L'])} mm/a por balance). En la estación seca, las
anomalías mensuales de ETo y ET van en sentidos opuestos (r = {f(bz.r_anom_seca, 2)}). Sí se observa, con la ETo FAO-56 de ERA5-Land como demanda.</p></div></div></div>""")

    slide("p13-sintesis", "1 · Evapotranspiración", "1.3 · Síntesis", "El régimen evaporativo de la cuenca del Chicama", f"""
<div class='two even'><div class='stack'>
<div class='callout teal'><b>Clasificación propuesta: limitado por agua con alternancia estacional.</b> En el promedio multianual manda el agua (φ = {f(bz.phi, 2)},
ET/ETo = 0,36). En el pico de lluvias (febrero–marzo) manda la energía, recortada por las nubes; de mayo a septiembre manda el agua y la ET vive del agua
guardada en el suelo. La cuenca aprovecha poco su lluvia (ω ≈ 1,6–1,8): la lluvia llega concentrada y desfasada de la demanda.</div>
<div class='card'><h4>Criterios usados</h4><p>ET/ETo ≥ 0,75 energía; ≤ 0,40 agua (mensual, TerraClimate). φ = ETo/P &gt; 1 (multianual). Umbral de humedad del suelo
θ* ≈ {f(bz.theta_umbral, 2)} m³/m³ en ERA5-Land.</p></div></div>
<div class='stack'>
<div class='card'><h4>¿Cambia la hipótesis de la Tarea 1?</h4><p>La Tarea 1 encontró que el balance «no cerraba» (R/P 0,48 frente a 0,16 de Budyko) y lo atribuyó a errores
de lluvia, a la PET o al caudal. Ahora hay una explicación física: el agua vuelve a la atmósfera sobre todo en la temporada de lluvias y al comienzo de la seca
(ET ≈ ETo en febrero–marzo); después la cuenca se queda sin agua. El ω bajo describe esa estacionalidad, no solo un error. La subestimación de la lluvia en las
cabeceras sigue siendo una explicación alternativa que no podemos descartar.</p></div>
<div class='card'><h4>Lo que es dato, modelo o hipótesis</h4><p><b>Observado:</b> P, Q y el balance de largo plazo. <b>Producto o modelo:</b> el ciclo mensual de ET
(TerraClimate), la humedad del suelo y su umbral (ERA5-Land). <b>Interpretación:</b> el mecanismo de la relación complementaria y el papel de la inversión.</p></div>
</div></div>""")

hay_14 = (P1 / "atribucion_tendencia_eto.csv").exists()
if hay_14:
    td_ = pd.read_csv(P1 / "tendencias_demanda_anual.csv", index_col=0)
    at_ = pd.read_csv(P1 / "atribucion_tendencia_eto.csv", index_col=0)
    bd_ = pd.read_csv(P1 / "budyko_descomposicion.csv")
    tm4 = pd.read_csv(P1 / "tendencias_demanda_por_mes.csv")
    e_ = td_.loc["ETo FAO-56 (ERA5-Land)"]; th_ = td_.loc["Thornthwaite"]
    FUENTES["p14-tendencias"] = (f"guía 1.4; notas {nt(62, 63, 93)}; Hamed y Rao (1998); Sen (1968); Benjamini y Hochberg (1995); Milly y Dunne (2016); "
                                 "Tarea 1, sección 3.4.")
    FUENTES["p14-atribucion"] = f"notas {nt(93, 94)}; Roderick y Farquhar (2002); McVicar et al. (2012); Hersbach et al. (2020)."
    FUENTES["p14-bono"] = f"notas {nt(73)}; Fu (1981); Tarea 1, sección 3.4 (tendencia de caudal)."
    ESTAB["p14-atribucion"] = ("La caída de la radiación desde 2000 apunta a más nubes, y en esta cuenca las nubes dependen de la estabilidad: con una "
                               "inversión más débil hay más convección. Pero también puede ser un cambio del propio reanálisis (las observaciones que asimila "
                               "ERA5 cambian con el tiempo) o de los aerosoles. Con estos datos no se puede distinguir entre esas tres causas.")
    ESTAB["p14-tendencias"] = ("La temperatura sube unos 0,2 °C por década, como en la Tarea 1. Thornthwaite traduce cada grado en demanda como si llegara "
                               "más energía; FAO-56 no, porque la demanda depende sobre todo de la radiación, es decir, de las nubes, que a su vez dependen de "
                               "la inversión y de la convección.")
    slide("p14-tendencias", "1 · Evapotranspiración", "1.4 · Cambios en la demanda", "La demanda sube, pero Thornthwaite exagera", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_4_tendencias.png', 'tendencias', 'Tendencias de la demanda evaporativa')}</div>
<div class='txtcols'><div>
<p><b>ETo FAO-56</b> sube {f(e_.sen_dec, 1)} mm/año por década (Sen; IC 95 % {f(e_.sen_lo_dec, 1)} a {f(e_.sen_hi_dec, 1)}; Mann–Kendall con Hamed–Rao,
p = {f(e_.p_mk_hr, 2)}): +{f(100*e_.sen_dec/e_.media, 1)} % por década. <b>Thornthwaite</b> sube {f(th_.sen_dec, 1)} mm/año por década, que es
+{f(100*th_.sen_dec/th_.media, 1)} % de su media: casi <b>3 veces más en términos relativos</b>, como predijo la sensibilidad de 1.1.d. En Thornthwaite
los 12 meses pasan el control FDR; en ETo solo {int(tm4[(tm4.serie=='ETo')].fdr_ok.sum())}, todos de la estación seca (junio–septiembre).</p></div>
<div><p><b>Productos independientes:</b> PISCOeo (+12,5, hasta 2016) y TerraClimate (+11) también suben, con p ≈ 0,05–0,07. La estación de Cajamarca da
+50 mm por década, pero con solo 13 años sueltos: no es comparable (ERA5-Land, en esos mismos días, da +5).</p>
<p><b>Sensibilidad a la ventana:</b> casi toda la subida de ETo ocurre entre 1981 y ~2005. Las ventanas que empiezan después de 2000 dan tendencias
negativas, mientras Thornthwaite sigue subiendo. El signo depende del periodo: no hay una tendencia robusta en las dos últimas décadas.</p></div></div></div>""")

    slide("p14-atribucion", "1 · Evapotranspiración", "1.4 · Atribución y paradoja del tanque", "¿Qué forzante explica la tendencia? Temperatura arriba, sol abajo", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_4_atribucion.png', 'atribucion', 'Atribución de la tendencia de ETo')}</div>
<div class='txtcols'><div>
<p><b>Método:</b> dETo/dt ≈ Σ (∂ETo/∂x<sub>i</sub>)(dx<sub>i</sub>/dt), con las sensibilidades mensuales del experimento de 1.1.d y la tendencia de Sen de cada
forzante por mes. La suma reproduce la tendencia directa: el residuo (interacciones y no linealidad) es de solo {f(at_.loc['residuo', '1981-2025'], 1)} mm por década.</p>
{tabla([(t, f(at_.loc[k, '1981-2025'], 1), f(at_.loc[k, '2000-2025'], 1)) for t, k in
        [("Temperatura", "T"), ("Humedad (e<sub>a</sub>)", "ea"), ("Viento (u₂)", "u2"), ("Radiación (R<sub>s</sub>)", "Rs"), ("<b>Suma</b>", "suma"),
         ("<b>Directa</b>", "directa")]], ["Aporte (mm/año por década)", "1981–2025", "2000–2025"])}</div>
<div><p><b>1981–2025:</b> la temperatura (+{f(at_.loc['tendencia_T_dec', '1981-2025'], 2)} °C/década) explica ≈ 3/4 de la subida; la radiación, el resto.</p>
<p><b>2000–2025, la paradoja del tanque en versión local:</b> la temperatura sigue subiendo, pero la radiación solar baja
({f(at_.loc['tendencia_Rs_dec', '2000-2025'], 2)} MJ m⁻² d⁻¹ por década) y la humedad sube un poco. Juntas compensan el calentamiento, y la ETo baja
({f(at_.loc['directa', '2000-2025'], 1)} mm por década) mientras Thornthwaite sigue subiendo. Thornthwaite no puede ver esa compensación porque no tiene
radiación. Al revés de Roderick y Farquhar (2002), aquí el viento casi no cambia: la compensación es por la radiación, no por el «aquietamiento» del viento.</p>
<p class='note'>No hay datos de tanque evaporímetro accesibles para la cuenca.</p></div></div></div>""")

    b0, b1 = bd_.iloc[0], bd_.iloc[1]
    slide("p14-bono", "1 · Evapotranspiración", "1.4 · Bono (+0,1)", "¿Cambió el caudal por la lluvia, por la demanda o por la cuenca?", f"""
<div class='two'><div class='panel'>{fig(FG / 'fig_1_4_budyko_bono.png', 'budyko_bono', 'Descomposición del cambio de caudal con Budyko')}</div>
<div class='stack'>
<p>Con la curva de Fu, Q = P [1 − F(ETo/P, ω)]. Entre 1999–2011 y 2012–2024 se separa el cambio de caudal en lo debido a P, a ETo y a ω (descomposición de
Shapley: los tres aportes suman exactamente el cambio). ω agrupa los cambios de cobertura, almacenamiento y regulación.</p>
{tabla([("Todos los años", f(b0.dQ_obs, 1), f(b0.dQ_por_P, 1), f(b0.dQ_por_ETo, 1), f(b0.dQ_por_omega, 1)),
        ("Sin 2000 ni 2017", f(b1.dQ_obs, 1), f(b1.dQ_por_P, 1), f(b1.dQ_por_ETo, 1), f(b1.dQ_por_omega, 1))],
       ["Caso", "ΔQ (mm/a)", "por P", "por ETo", "por ω"])}
<p>El caudal casi no cambió (−2 mm/año sobre ≈ 336), lo que concuerda con la falta de tendencia de la Tarea 1 (−0,6 m³/s por década, p = 0,53). <b>El aumento de la
demanda aportó menos de 1 mm/año</b>: la ETo subió solo ≈ 4 mm/año entre los dos periodos y la cuenca, limitada por agua, apenas lo siente. Sin los dos años
anómalos el caudal baja 18 mm/año y casi todo cae en ω, el término residual: una señal pequeña y sensible a cuáles años se incluyen.</p>
</div></div>""")

hay_15a = (P1 / "gradiente_bandas.csv").exists()
if hay_15a:
    gb = pd.read_csv(P1 / "gradiente_bandas.csv")
    FUENTES["p15a-gradiente"] = (f"guía 1.5.a; de Jong et al. (2005); notas {nt(27, 35, 47)}; Abatzoglou et al. (2018); DEM Copernicus GLO-90; "
                                 "Tarea 1 (CHIRPS: la lluvia sube de ≈ 400 mm en el cierre a ≈ 900 mm en las cabeceras).")
    ESTAB["p15a-gradiente"] = ("La banda más baja (680–1 000 m, 2,8 % del área) queda dentro o debajo de la inversión de la estación seca: allí la "
                               "temperatura no baja con la altura y además los estratocúmulos recortan el sol, así que su ETo corregida con un gradiente lineal "
                               "probablemente está sobreestimada. Por encima de la inversión, la lluvia crece con la altura porque el aire húmedo del este "
                               "asciende por las laderas y se enfría (ascenso orográfico y convección de verano).")
    g0, g6 = gb.iloc[0], gb.iloc[-1]
    filas_g = [(r.banda + " m", f(r["area_%"], 1), f(r.eto_era5land_corr), f(r.pet_tc), f(r.ppt_tc), f(r.aet_tc), f(r["aet/pet_tc"], 2))
               for _, r in gb.iterrows()]
    slide("p15a-gradiente", "1 · Evapotranspiración", "1.5.a · Gradiente altitudinal", "Más arriba, menos demanda pero más ET real", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_5a_gradiente.png', 'gradiente', 'Gradiente altitudinal de la ET')}</div>
<div class='txtcols'><div>
{tabla(filas_g, ["Banda", "% área", "ETo ERA5-L.", "PET TC", "P TC", "ET real TC", "ET/PET"])}
<p class='note'>mm/año, 1998–2024. ETo ERA5-Land corregida a la altura de cada banda con los gradientes del paso 5; TC = TerraClimate (~4 km).</p></div>
<div><p><b>La ET no disminuye con la altura: aumenta.</b> La demanda baja ≈ 110 mm por km (aire más frío), pero la lluvia sube ≈ 210 mm por km. Como la cuenca
está limitada por agua, la ET sigue a la lluvia: de {f(g0.aet_tc)} mm/año en el fondo del valle a {f(g6.aet_tc)} en las cumbres, y la limitación por agua se relaja
(ET/PET de {f(g0['aet/pet_tc'], 2)} a {f(g6['aet/pet_tc'], 2)}).</p>
<p><b>¿Hay un máximo intermedio?</b> No dentro de la cuenca. Las dos rectas (lluvia y demanda) se cruzan cerca de los 4 300 m, justo en la divisoria: el máximo de ET
estaría ahí, y por encima la ET pasaría a estar limitada por la energía. En una montaña más alta veríamos el máximo intermedio de de Jong et al. (2005).</p>
<p><b>Qué resuelve un producto de 9 km:</b> las celdas de ERA5-Land van de ≈ 1 400 a 3 600 m y no representan el 11 % más bajo de la cuenca (bajo 1 500 m) ni las cumbres; su ET (cuadros verdes)
no muestra el gradiente porque su lluvia está inflada en toda la cuenca. Corregida por bandas, la ETo de la cuenca cambia solo +1,4 % (1 211 → 1 228 mm): las bandas
altas y bajas se compensan. Cautela: TerraClimate evapora el 95 % de su lluvia en todas las bandas, así que la forma del gradiente es más confiable que sus valores
absolutos.</p></div></div></div>""")

hay_15c = (P1 / "niebla_resumen.csv").exists()
if hay_15c:
    nr = pd.read_csv(P1 / "niebla_resumen.csv", index_col=0).iloc[:, 0]
    cd = pd.read_csv(P1 / "niebla_ciclo_diurno.csv", index_col="hora_local")
    FUENTES["p15c-niebla"] = (f"guía 1.5.c; notas {nt(36, 37, 47)}; Hersbach et al. (2020), ERA5; Klein y Hartmann (1993); Garreaud (2009); "
                              "Tarea 1 (radiosondeos de Trujillo, Fig. 8–9).")
    ESTAB["p15c-niebla"] = (f"La capa límite muestra la estabilidad: sobre la cuenca, en la estación seca, crece hasta ≈ {f(cd.blh_cuenca_seca.max())} m al mediodía "
                            f"(aire inestable, convectivo) y se aplasta a ≈ {f(cd.blh_cuenca_seca.min())} m de noche (aire muy estable, con inversión de superficie). "
                            f"Sobre el mar, bajo la inversión de subsidencia, se queda en ≈ {f(cd.blh_mar_seca.min())}–{f(cd.blh_mar_seca.max())} m día y noche: "
                            "es la capa marina tapada donde viven los estratocúmulos.")
    slide("p15c-niebla", "1 · Evapotranspiración", "1.5.c · Niebla y nubosidad", "¿Hay una entrada de agua oculta bajo la inversión?", f"""
<div class='stackfig'><div class='panel'>{fig(FG / 'fig_1_5c_niebla.png', 'niebla', 'Nubosidad baja, inversión y capa límite')}</div>
<div class='txtcols'><div>
<p><b>La pregunta:</b> la ET de los productos supera a P − Q ({f(nr.P_menos_Q)} mm/a): TerraClimate por {f(nr.brecha_TerraClimate)} mm/a ({f(nr['brecha_%_de_P'])} % de la lluvia) y
ERA5-Land por {f(nr.brecha_ERA5Land)}. ¿Puede la niebla, que los pluviómetros no registran, aportar esa agua?</p>
<p><b>Niebla costera: no alcanza.</b> Los estratocúmulos viven bajo la inversión, y solo el {f(nr['area_franja_inversion_seca_%'], 1)} % de la cuenca (838–1 203 m) queda en esa franja en la
estación seca; en la húmeda, casi nada ({f(nr['area_franja_inversion_humeda_%'], 1)} %). Para cerrar la brecha de TerraClimate solo con niebla allí harían falta
≈ {f(nr.niebla_necesaria_en_franja_mm_a)} mm/año de agua de niebla, el doble de la lluvia de toda la cuenca: no es plausible. Además, en ERA5 la nubosidad baja de la estación
seca está sobre el mar ({f(nr.lcc_mar_seca, 2)}) y apenas entra en la cuenca ({f(nr.lcc_cuenca_seca, 2)}).</p></div>
<div><p><b>Nubes en las laderas altas: posible.</b> Sobre la cuenca la nubosidad baja es máxima en la temporada de lluvias ({f(nr.lcc_cuenca_humeda, 2)} en febrero–marzo): nubes
orográficas y convectivas que envuelven el pajonal y los bosques de las laderas altas. Allí la precipitación horizontal puede sumar de pocos a más de 20 % del agua
que llega al suelo (notas #s47), y una brecha del 9 % de P cae en ese rango. Pero hay dos explicaciones alternativas que estos datos no descartan: TerraClimate
evapora el 95 % de su lluvia por construcción, y P<sub>L</sub> puede subestimar la lluvia de las cabeceras. Verificarlo exigiría colectores de niebla o lluvia bajo dosel.</p>
<div class='callout blue'><b>Por qué elegimos 1.5.a y 1.5.c y descartamos los demás:</b> la cuenca va de 680 a 4 300 m (gradiente) y tiene la inversión costera y nubes de
ladera (niebla). No tiene nieve ni glaciares (d), ni lagos, embalses o riego importantes (e: 2,4 % agrícola según WorldCover en la Tarea 1; CAMELS-PE registra un solo embalse, de uso minero, y el
valle regado del Chicama queda aguas abajo de El Tambo); la intercepción (b) y la
resistencia del dosel (f) pedirían datos de cobertura y de área foliar que no evaluamos en la Tarea 1.</div></div></div></div>""")

plan = [("1.1.a", "ETo FAO-56 diaria → mensual; error por promediar", "hecho" if hay_eto else ("curso" if est_desc != "hecho" else "pend")),
        ("1.1.b", "Pruebas de la referencia (estación, PISCOeo, TerraClimate, P − Q)", "hecho" if hay_b else "pend"),
        ("1.1.c", "Métodos simples (7 de la tabla + 2 nuevos: Makkink y Linacre)", "hecho" if hay_c else "pend"),
        ("1.1.d", "Términos radiativo y aerodinámico, α*, sensibilidad", "hecho" if hay_d else "pend"),
        ("1.2", "ET real: balance P − Q, techo energético, productos", "hecho" if hay_12 else "pend"),
        ("1.3", "Energía o agua: régimen mensual, Budyko–Fu, elasticidad", "hecho" if hay_13 else "pend"),
        ("1.4", "Tendencias y atribución de la tendencia de ETo (+ bono de Budyko)", "hecho" if hay_14 else "pend"),
        ("1.5", "Gradiente altitudinal (1.5.a) y niebla bajo la inversión (1.5.c)", "hecho" if (hay_15a and hay_15c) else "pend")]
if (P1 / "budyko_resumen.csv").exists() and (P1 / "niebla_resumen.csv").exists():
    from scipy.optimize import brentq
    bz = pd.read_csv(P1 / "budyko_resumen.csv", index_col=0).valor
    nz = pd.read_csv(P1 / "niebla_resumen.csv", index_col=0).valor
    sz = pd.read_csv(P1 / "sensibilidad_anual_pct.csv", index_col=0)
    attr = pd.read_csv(RAIZ / "datos/punto1/tarea1/PE_47E0A2A8_atributos.csv", index_col=0).iloc[:, 0]
    ETo0 = 1211.0                                                         # ETo media anual FAO-56 de 1.1.a (mm)
    phi0, w0 = float(bz.phi), float(bz.omega_fu)
    P0 = ETo0 / phi0; ET0 = P0 * float(bz.ET_P)
    f0 = float(attr.forest_perc)
    fu = lambda phi, w: 1 + phi - (1 + phi ** w) ** (1 / w)
    zh = lambda phi, w: (1 + w * phi) / (1 + w * phi + 1 / phi)            # Zhang et al. (2001)
    Rz = zh(phi0, 2.0) / zh(phi0, 0.5)                                       # razon ET bosque / pastizal a esta aridez
    def dw_para(R):
        return brentq(lambda d: fu(phi0, w0 + (1 - f0 / 100) * d) / fu(phi0, w0 - f0 / 100 * d) - R, 0.01, (w0 - 1.001) / (f0 / 100))
    dw_nat = dw_para(Rz); dw_pl = dw_para(1 + 1.6 * (Rz - 1))
    sT = float(sz.loc["FAO-56 PM", "T+1_hr"]) / 100
    _cm = pd.read_csv(P1 / "eto_mensual_comparacion_promedios.csv"); Rs_wm2 = float(_cm.rs.mean()) * 1e6 / 86400
    Rn_wm2 = float(pd.read_csv(P1 / "et_real_largo_plazo.csv", index_col=0).valor["Rn_lambda"]) * 2.45e6 / 3.1536e7
    D["refo"] = {"f0": f0, "P0": P0, "ETo0": ETo0, "ET0": ET0, "w0": w0, "sT": sT, "rs": Rs_wm2, "rn": Rn_wm2, "dalb": 0.08,
                 "dw": {"nat": dw_nat, "pl": dw_pl}, "franja": float(nz["area_franja_inversion_seca_%"]) / 100}
    FUENTES["p15-refo"] = ("Budyko (1974) en la forma de Fu (1981), con ω calibrado en 1.3; Zhang et al. (2001) para la diferencia bosque–pastizal (w = 2,0 y 0,5); "
                           "Bosch y Hewlett (1982) para la comprobación y el factor 1,6 de las plantaciones de coníferas o eucalipto frente a latifoliadas; "
                           "Bonan (2008) y Rotenberg y Yakir (2010) para el efecto del bosque en la temperatura según el clima; Eltahir y Bras (1996) para el reciclaje local; "
                           "Bruijnzeel et al. (2011) para la captura de niebla; CAMELS-PE (cobertura de bosque de la cuenca); notas " + nt(36, 47) + ".")
    ESTAB["p15-refo"] = ("El bosque cambia el balance de energía de la superficie: refleja menos (albedo ≈ 0,12 frente a ≈ 0,20 del pastizal) y es más rugoso, así que "
                         "mezcla mejor el aire. Como evapora más, una parte mayor de la energía se va en calor latente (baja la razón de Bowen), pero como también absorbe "
                         "más sol, en esta cuenca limitada por agua el calor sensible sube en valor absoluto: la capa límite queda algo más húmeda y "
                         "también más caliente y profunda de día, lo que la acerca al nivel de condensación. En la estación seca, la inversión de subsidencia sigue "
                         "tapando la convección: el vapor extra se queda debajo como nubosidad baja y no llueve. Solo en la estación húmeda, con la atmósfera inestable, "
                         "parte de ese vapor puede volver a caer en la cuenca; por eso el reciclaje local es pequeño (≈ 5 % en 2 000 km²). La niebla solo la atrapa el "
                         "bosque que quede dentro de la franja de la inversión (1.5.c).")
    slide("p15-refo", "1 · Evapotranspiración", "1.5 · Extensión interactiva", "¿Y si reforestamos la cuenca del Chicama?", f"""
<div class='two even'><div class='stack'>
<div class='panel'>
<div class='ctl'><label for='rf-f'>Bosque</label><input id='rf-f' type='range' min='0' max='100' step='1' value='{f0:.0f}'><output id='rf-fo'></output></div>
<div class='ctl'><label for='rf-tipo'>Tipo</label><select id='rf-tipo'><option value='nat'>bosque nativo (andino, latifoliado)</option>
<option value='pl'>plantación (pino o eucalipto)</option></select><span></span></div>
<div class='ctl'><label for='rf-beta'>Efecto en T</label><input id='rf-beta' type='range' min='-1' max='1' step='0.1' value='0'><output id='rf-betao'></output></div>
<div class='ctl'><label for='rf-rho'>Reciclaje</label><input id='rf-rho' type='range' min='0' max='0.2' step='0.01' value='0.05'><output id='rf-rhoo'></output></div>
<div class='ctl'><label for='rf-fog'>Niebla</label><input id='rf-fog' type='range' min='0' max='1000' step='50' value='300'><output id='rf-fogo'></output></div>
<p class='note'>Hoy la cuenca tiene {f(f0)} % de bosque (CAMELS-PE). «Reciclaje»: fracción de la ET extra que vuelve a llover en la cuenca. «Niebla»: agua que atrapa
cada m² de bosque dentro de la franja de la inversión ({f(100*D['refo']['franja'], 1)} % de la cuenca, 1.5.c), en mm/año. «Efecto en T»: cambio neto de la
temperatura del aire por cada 100 % de bosque, en °C; su signo es incierto (ver el balance de energía).</p>
<div class='readout' id='rf-out'></div></div>
<div class='panel'><div id='g-refo' style='height:300px'></div></div></div>
<div><div class='eq'>ET/P = 1 + φ − (1 + φ<sup>ω</sup>)<sup>1/ω</sup>, &nbsp; φ = ETo/P, &nbsp; ω = ω₀ + Δω·(f − f₀)</div>
<p><b>Cómo funciona:</b> (1) la temperatura cambia según el control «Efecto en T»: el bosque enfría al evaporar (calor latente), pero calienta al
absorber más sol (albedo ≈ 0,12 frente a ≈ 0,20); el panel de energía muestra cuál gana. (2) ETo cambia {f(100*sT, 1)} % por °C (sensibilidad de 1.1.d). (3) Más bosque significa raíces más profundas e interceptación: sube ω. Δω se calibró para que pasar de pastizal
a bosque nativo aumente la ET {f(100*(Rz-1))} %, como en las curvas de Zhang et al. (2001) a esta aridez (φ = {f(phi0, 2)}), y 1,6 veces más para pino o eucalipto
(Bosch y Hewlett, 1982). (4) La lluvia sube por reciclaje y por niebla. (5) El caudal es Q = P − ET.</p>
<p id='rf-txt'></p>
<p><b>Calor latente frente a albedo:</b> evaporar 1 mm/año de agua consume 0,078 W/m². Pasar al 100 % de bosque nativo sube la ET ≈ 70 mm/año, es decir
≈ +5 W/m² de calor latente (+8 con pino o eucalipto), pero el bosque más oscuro absorbe ≈ +16 W/m² más de sol. En una cuenca limitada por agua, la ET no
puede crecer tanto: la mayor parte de la energía extra se va en <b>calor sensible</b>, que calienta la capa límite. La razón de Bowen baja (de 3,1 a ≈ 2,9), pero
el calor sensible sube en valor absoluto. Por eso el bosque húmedo tropical enfría (Bonan, 2008), mientras un bosque en clima seco puede calentar el aire
(Rotenberg y Yakir, 2010). Aquí el signo es incierto, entre ≈ −0,4 y +0,4 °C; el caudal casi no cambia con él (±2 mm).</p>
<p><b>Lo que enseña:</b> reforestar <b>reduce el caudal</b>, se enfríe o se caliente el aire, y aunque atraiga algo de lluvia. Es el resultado clásico de las cuencas pareadas
(Bosch y Hewlett, 1982), y en los Andes se ha visto con plantaciones de pino en páramo y jalca (Buytaert et al., 2007). Para que la lluvia extra compense, el reciclaje
tendría que acercarse a 1, imposible en 2 000 km². Y la niebla solo cuenta en una franja muy pequeña. Lo que el modelo no incluye: los cambios en la infiltración y en
el flujo de la estación seca, la erosión y la escala regional (deforestación amazónica).</p>
<p class='note'>Modelo de equilibrio anual, de orden de magnitud; los supuestos (β, Δω, reciclaje, niebla) se pueden mover para ver cuánto pesan.</p></div></div>""")


slide("p1-plan", "1 · Evapotranspiración", "Punto 1 · Hoja de ruta", "Del dato a la interpretación física",
      tabla([(a, d, tag(e)) for a, d, e in plan], ["Apartado", "Contenido", "Estado"]) +
      "<p class='note'>La Tarea 1 dejó dos pistas que el punto 1 debe revisar: P/PET = 0,62 (subhúmedo seco) y un balance que no "
      "cierra (R/P observado 0,48 frente a 0,16 de Budyko).</p>")

filas_sitio = [
    ("Cajamarca aeropuerto (SPJR)", "≈ 50 km NE, 2 676 m", "6 h (nunca horaria)",
     f"{caj_buenos} años con ≥ 80 % de reportes de 6 h", tag("blk")),
    ("San Marcos (84479)", "≈ 60 km E", "1 h", "solo 2026", tag("blk")),
    ("Estaciones automáticas SENAMHI en la cuenca", "dentro", "1 h", "desde ~2014 (≤ 12 años, a pedido)", tag("blk")),
    ("<b>Cottbus, DWD 00880</b>", "Alemania", "<b>10 min</b>", f"<b>{n_validos} años válidos</b> ({anios_val.min()}–{anios_val.max()})",
     tag("hecho")),
]
slide("p2-sitio", "2 · Diseño hidrológico", "Punto 2 · 2.1", "¿Por qué el punto 2 se hace en Cottbus?", f"""
<p class='lead'>La guía ordena los criterios: primero la longitud del registro, luego la resolución, luego la calidad, y la
cercanía a la cuenca del punto 1 solo desempata.</p>
{tabla(filas_sitio, ["Serie", "Ubicación", "Resolución", "Registro útil", "Cumple"])}
<div class='callout amber'><b>Consecuencia:</b> la microcuenca del problema A debe estar cerca de Cottbus, en el mismo régimen
climático (llanura de Brandeburgo, tormentas convectivas de verano), no en el Chicama.</div>""", k="k-arch", g="a")

slide("p2-peru", "2 · Diseño hidrológico", "Punto 2 · Perú", "Cerca de El Tambo no hay lluvia subdiaria suficiente", f"""
<div class='two fig'><div class='stack'>
<p>La estación andina más cercana con datos en GHCNh, el aeropuerto de Cajamarca, <b>nunca reportó lluvia horaria</b>. Solo tiene
acumulados de 6 h, y con cobertura alta en pocos años.</p>
<p>Con 6 h, la resolución más gruesa que admite la guía, la IDF para duraciones de minutos exigiría extrapolar con una ley de
escala; además Cajamarca está al otro lado de la divisoria continental.</p>
<p class='note'>Un año completo tiene 1 460 reportes de 6 h (línea punteada). Fuente: NOAA GHCNh, script
<code>codigo/punto2/00_disponibilidad_ghcnh_peru.py</code>.</p>
</div><div class='panel'><div class='maphost sm' id='g-caj'></div></div></div>""", k="k-arch", g="a")

slide("p2-cottbus", "2 · Diseño hidrológico", "Punto 2 · 2.1.4", "Cottbus: 10 minutos y 30 años válidos", f"""
<div class='two fig'><div class='stack'>
<div class='readout'><div><span>resolución</span><b>10 min</b></div><div><span>registro</span><b>1991–2025</b></div>
<div><span>años válidos</span><b class='c-ok'>{n_validos}</b></div></div>
<p>Criterio inicial de año válido: <b>≥ 80 %</b> de los intervalos con dato en el año y <b>≥ 90 %</b> en mayo–septiembre, la
temporada de tormentas. Los años con huecos en verano (1992, 1994, 1996, 1998) quedan para la prueba de sensibilidad que pide
la guía.</p>
<p class='note'>El DWD marca el faltante con −999, así que se distingue de un cero. Pendiente de revisar: la hora viene en hora
local alemana hasta 1999 y en UTC desde 2000 (ver metadatos del ZIP).</p>
<p class='note'>Fuente: DWD Climate Data Center. Script <code>codigo/punto2/01_completitud_dwd_cottbus.py</code>.</p>
</div><div class='stack'><div class='panel'><div class='tshost' id='g-comp'></div></div>
<div class='panel'><div class='tshost' id='g-max'></div>
<p class='ts-title'>Máximo anual de lluvia en 10 minutos (descriptivo: todavía sin ajuste de distribuciones).</p></div></div></div>""",
      k="k-arch", g="a")

P2D = RAIZ / "productos/punto2"
if (P2D / "qc_dias_imposibles.csv").exists():
    qd = pd.read_csv(P2D / "qc_dias_imposibles.csv")
    FUENTES["p21-calidad"] = ("guía 2.1; metadatos del DWD para la estación 00880 (hora, instrumentos, aviso del firmware rain[e] de 2021); "
                              "lluvia diaria del DWD (Cottbus, Lindenberg, Doberlug-Kirchhain); Weiss (1964).")
    slide("p21-calidad", "2 · Diseño hidrológico", "Punto 2 · 2.1", "Control de calidad: lo que encontramos en la serie de Cottbus", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_1_calidad.png', 'calidad_cottbus', 'Control de calidad de Cottbus')}</div>
<div class='txtcols'><div>
{tabla([("Hora", "MEZ (UTC+1) hasta 1999, UTC desde 2000", "todo pasado a UTC"),
        ("Instrumentos", "contador de gotas NG 200 (1991–2007), PLUVIO de pesada (2007–2020), rain[e]H3 de pesada (2020–)", "posible salto: revisar en 2.2.6"),
        ("Días imposibles", f"{len(qd)} días con más lluvia en 10 min que en el pluviómetro diario (D−1 a D+1), casi todos 1991–1994", "eliminados (faltantes)"),
        ("Firmware 2021", "9 días de jun–jul con intensidades subestimadas (aviso del DWD)", "2021 marcado; sensibilidad en 2.2"),
        ("2014-08-03", "10 min: 48,6 mm; pluviómetro diario: 102,6 mm", "se conserva, como incertidumbre"),
        ("Faltantes, repetidos, acumulados", "códigos −999, 7 rachas repetidas, 1 acumulado tras un vacío, 17 extremos aislados", "revisados uno a uno")],
       ["Control", "Hallazgo", "Decisión"])}</div>
<div><p><b>Picos falsos del contador de gotas:</b> entre 1991 y 1994 aparecen picos de ≈ 10 mm en días secos (por ejemplo, 29,5 mm en una hora el 9 de octubre de 1993,
con 4 mm en el pluviómetro diario). Tras eliminarlos, ningún máximo horario supera la lluvia del día.</p>
<p><b>Años válidos:</b> 30 con el criterio base (≥ 80 % del año y ≥ 90 % de mayo–septiembre), 29 con el estricto (90/95) y 32 con el laxo (70/80); la sensibilidad
de los cuantiles a ese criterio se mide en 2.2. Año calendario: las tormentas caen en mayo–septiembre y el corte de año queda en invierno.</p>
<p><b>Weiss (1964):</b> los datos son intervalos fijos de reloj de 10 min, así que el máximo de una ventana fija subestima el de una móvil continua. Factor
1/(1 − 1/(8n)): 1,14 para 10 min, 1,07 para 20 min, 1,04 para 30 min, 1,02 para 1 h y menos de 1 % desde 2 h.</p>
<p class='note'>Scripts <code>codigo/punto2/01_completitud_dwd_cottbus.py</code> y <code>02_control_calidad_maximos.py</code>.</p></div></div></div>""", k="k-arch", g="a")

if (P2D / "bootstrap_ic_gev_lmom.csv").exists():
    aq = pd.read_csv(P2D / "ajuste_cuantiles.csv"); ab = pd.read_csv(P2D / "ajuste_bondad.csv")
    ic2 = pd.read_csv(P2D / "bootstrap_ic_gev_lmom.csv"); es2 = pd.read_csv(P2D / "ajuste_estacionariedad.csv")
    se2 = pd.read_csv(P2D / "ajuste_sensibilidad.csv"); dl2 = pd.read_csv(P2D / "ajuste_diagrama_lmom.csv", index_col=0).iloc[:, 0]
    q60 = aq[aq.duracion_min == 60]
    filas_q60 = [(f"{r.dist} · {r.metodo}", *[f(r[f'T{T}'], 1) for T in [2, 10, 25, 50, 100]]) for _, r in q60.iterrows()]
    i60 = ic2[ic2.duracion_min == 60].set_index("T")
    bm = ab.groupby(["dist", "metodo"])[["KS_D", "AD", "PPCC"]].mean()
    FUENTES["p22-ajustes"] = ("guía 2.2; Chow et al. (1988), cap. 12; Hosking y Wallis (1997); Coles (2001); Gringorten (1963); "
                              "verificado con lmoments3 y con scipy (convención c = −ξ en genextreme).")
    FUENTES["p22-incertidumbre"] = "guía 2.2.4–2.2.6; Hosking y Wallis (1997); Hamed y Rao (1998); Sen (1968)."
    slide("p22-ajustes", "2 · Diseño hidrológico", "Punto 2 · 2.2", "Tres distribuciones, tres métodos: cuánto cambia el cuantil", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_2_ajustes.png', 'ajustes', 'Gráficas de probabilidad')}</div>
<div class='txtcols'><div>
{tabla(filas_q60, ["60 min (mm/h)", "T = 2", "10", "25", "50", "100"])}
<p class='note'>Intensidades con la corrección de Weiss; 30 años válidos; posiciones de Gringorten (recomendada para Gumbel y GEV porque no subestima
el periodo de retorno de los mayores valores, como Weibull). Tabla completa de 9 duraciones en <code>productos/punto2/ajuste_cuantiles.csv</code>.</p></div>
<div><p><b>Hasta T ≈ 10 años todas coinciden; después se abren.</b> El cuantil de 100 años de 60 min va de 46 a 52 mm/h entre las 9 combinaciones (13 %), y en
180 min hasta 40 %: lo que se extrapola más allá de los datos depende de la forma supuesta de la cola.</p>
<p><b>Forma de la GEV (ξ, L-momentos):</b> −0,13 en 10 min (cola acotada: una celda convectiva tiene un límite de lluvia en 10 min), ≈ 0 entre 20 min y 1 h
y entre 12 y 24 h (casi Gumbel), y +0,18 a +0,22 en 2–3 h (cola pesada: tormentas organizadas que duran horas).</p>
<p><b>Bondad de ajuste:</b> ninguna combinación se rechaza con KS al 5 % (con 30 datos no rechazar no es demostrar). En promedio, la GEV por L-momentos tiene el
menor KS ({f(bm.loc[('GEV', 'LMOM'), 'KS_D'], 3)}) y Anderson–Darling ({f(bm.loc[('GEV', 'LMOM'), 'AD'], 2)}) y el mayor PPCC ({f(bm.loc[('GEV', 'LMOM'), 'PPCC'], 3)})
de las 9.</p></div></div></div>""", k="k-arch", g="a")

    sb = se2.set_index(["caso", "duracion_min"])
    slide("p22-incertidumbre", "2 · Diseño hidrológico", "Punto 2 · 2.2", "Elección, incertidumbre y estacionariedad", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_2_lmom_bootstrap.png', 'lmom_bootstrap', 'Diagrama de L-momentos y bootstrap')}</div>
<div class='txtcols'><div>
<div class='callout teal'><b>Elegida: GEV por L-momentos.</b> (1) Es la distribución límite de los máximos de bloque (Fisher–Tippett; Coles, 2001). (2) Tiene el mejor ajuste
promedio. (3) Los L-momentos son estables con 30 datos; la máxima verosimilitud dio una forma inestable (ξ = 0,30 en 3 h) y los momentos dependen de la
asimetría muestral. <b>Contraste:</b> el promedio del diagrama (τ₃ = {f(dl2.tau3_medio, 2)}, τ₄ = {f(dl2.tau4_medio, 2)}) cae sobre la logística generalizada (GLO), pero la variabilidad
muestral de τ₄ con 30 años es ±{f(dl2.sd_tau4_bootstrap_60min, 2)}, el doble de la distancia entre GEV y GLO: los datos no las distinguen. La GLO da cuantiles de 100 años
2–7 % mayores; se usará en la sensibilidad del diseño.</div></div>
<div><p><b>Bootstrap (2 000 remuestreos):</b> el IC 95 % del cuantil de 60 min va de {f(100*i60.loc[2, 'ancho_rel'])} % del valor en T = 2 a {f(100*i60.loc[100, 'ancho_rel'])} % en T = 100
({f(i60.loc[100, 'lo'], 0)}–{f(i60.loc[100, 'hi'], 0)} mm/h). Más allá de T ≈ 2N = 60 años el resultado depende casi por completo de la cola supuesta.</p>
<p><b>Estacionariedad:</b> ninguna duración tiene tendencia significativa (Mann–Kendall con Hamed–Rao, p ≥ 0,15; Sen +2 a +8 % por década) ni diferencias entre las tres
épocas de instrumento (Kruskal–Wallis, p ≥ 0,50). Se asume estacionariedad, con la cautela de que las pendientes son positivas.</p>
<p><b>Sensibilidad (GEV-LMOM, T = 100):</b> el criterio de años válidos cambia el cuantil &lt; 3 % y quitar 2021 &lt; 3 %. En cambio, si en 2014 vale el pluviómetro diario
(102,6 mm) y no la serie de 10 min (48,6 mm), el de 24 h sube de {f(sb.loc[('base', 1440), 'T100'], 2)} a {f(sb.loc[('base, 2014 = pluviómetro diario', 1440), 'T100'], 2)} mm/h
(+33 %). Para la microcuenca (duraciones de minutos) no importa.</p></div></div></div>""", k="k-arch", g="a")

if (P2D / "idf_parametros.csv").exists():
    ip = pd.read_csv(P2D / "idf_parametros.csv").set_index("parametro").valor
    ks_ = pd.read_csv(P2D / "kostra_cottbus.csv"); ev_ = pd.read_csv(P2D / "evento_2018_06_09.csv").set_index("duracion_min")
    it_ = pd.read_csv(P2D / "idf_tabla_mm_h.csv", index_col="duracion_min")
    FUENTES["p23-idf"] = ("guía 2.3; Koutsoyiannis et al. (1998); KOSTRA-DWD-2020 (Deutscher Wetterdienst, datos abiertos, celda 121203); "
                          "Svensson y Jones (2010) para la reducción areal.")
    ESTAB["p23-idf"] = ("La tormenta del 9 de junio de 2018 fue convectiva: 51,6 mm en una hora (52,6 mm en todo el evento) y casi nada en Lindenberg (5,7 mm) ni en "
                        "Doberlug-Kirchhain (2,2 mm), a 50 km. Una celda convectiva crece cuando la atmósfera es inestable en toda la troposfera "
                        "(aire cálido y húmedo abajo, frío arriba) y descarga en minutos sobre pocos kilómetros cuadrados: por eso sus periodos de retorno "
                        "son altos en 10–60 min y bajos en 24 h, y por eso la reducción areal importa tanto en duraciones cortas.")
    rk = ks_.pivot(index="duracion_min", columns="T", values="razon_cottbus/kostra")
    slide("p23-idf", "2 · Diseño hidrológico", "Punto 2 · 2.3", "Las curvas IDF de Cottbus y la IDF oficial alemana", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_3_idf.png', 'idf', 'Curvas IDF de Cottbus')}</div>
<div class='txtcols'><div>
<div class='eq'>i(d, T) = a(T) / (d + {f(ip.theta_h, 3)})<sup>{f(ip.eta, 3)}</sup> &nbsp;&nbsp; [i en mm/h, d en h]</div>
<p>a(T) es el cuantil de una GEV (μ = {f(ip.gev_mu, 2)}, σ = {f(ip.gev_sigma, 2)}, ξ = {f(ip.gev_xi, 3)}) ajustada por L-momentos a las intensidades reescaladas de las 9
duraciones (Koutsoyiannis et al., 1998). Error frente a los cuantiles de cada duración: {f(ip['rmse_%'], 1)} % en promedio y {f(ip['max_abs_error_%'], 0)} % como máximo (en 2–3 h,
donde la cola es más pesada). η &lt; 1 y la profundidad crece con la duración; las curvas no se cruzan. <b>Rango de validez:</b> 10 min a 24 h y T = 2 a 100 años; más
allá de T ≈ 60 años (2N) es extrapolación. Bandas: IC 95 % del bootstrap para T = 10 y 100.</p>
{tabla([(f"{d} min" if d < 60 else f"{d//60} h", *[f(it_.loc[d, f'T{T}'], 1) for T in [2, 10, 25, 100]]) for d in [10, 20, 30, 60, 120, 1440]],
       ["Duración", "T = 2", "10", "25", "100"])}</div>
<div><p><b>Frente a KOSTRA-DWD-2020</b> (celda de 5 km que contiene la estación; series de duración parcial 1951–2020): nuestra IDF está entre {f(rk.values.min(), 2)} y {f(rk.values.max(), 2)}
veces la oficial, siempre dentro de su incertidumbre (±18–27 %). Somos 3–11 % mayores entre 20 min y 3 h, y 7–17 % menores en 12–24 h. Posibles causas: periodos distintos
(1993–2025 frente a 1951–2020), la corrección de Weiss que aplicamos, la regionalización de KOSTRA, que suaviza entre estaciones, y el caso dudoso de 2014 en 24 h.
KOSTRA da valores puntuales regionalizados, no promedios de área: la razón entre las dos <b>no</b> es un factor de reducción areal.</p>
<p><b>Tormenta del 9 de junio de 2018:</b> 22 mm en 10 min, 38,5 mm en 20 min y 51,6 mm en 1 h. Con nuestra IDF tiene T ≈ {f(ev_.loc[10, 'T_GEV'])} años en 10 min,
≈ {f(ev_.loc[20, 'T_GEV'])} en 20 min y ≈ {f(ev_.loc[60, 'T_GEV'])} en 1 h, pero solo ≈ {f(ev_.loc[1440, 'T_GEV'])} años en 24 h. El IC 95 % va de ≈ {f(ev_.loc[60, 'T_p2.5'])} años a «nunca»
(algunas réplicas tienen una cola acotada por debajo del evento): con 30 años de datos, un evento de ese tamaño solo puede decirse «raro, probablemente más de 25 años». KOSTRA lo
pone por encima de 100 años entre 20 y 60 min.</p></div></div></div>""", k="k-arch", g="a")

if (P2D / "problemaA_montecarlo.csv").exists():
    mcd = pd.read_csv(P2D / "microcuenca_dgm_descripcion.csv", index_col=0).iloc[:, 0]
    pA = pd.read_csv(P2D / "problemaA_sensibilidad.csv"); rkA = pd.read_csv(P2D / "problemaA_ranking_incertidumbre.csv", index_col=0)
    mcA = pd.read_csv(P2D / "problemaA_montecarlo.csv", index_col=0).valor; esA = pd.read_csv(P2D / "problemaA_escala.csv")
    ceA = pd.read_csv(P2D / "problemaA_costo_esperado.csv")
    dis = pA.iloc[0]

    FUENTES["p24-microcuenca"] = ("guía 2.4 (microcuenca de 0,1–5 km²); DGM1 de Brandeburgo (LGB, licencia dl-de/by-2-0), remuestreado a 5 m; "
                                  "ESA WorldCover 2021 (10 m); Copernicus GLO-30; dirección de flujo D8 con pysheds (O'Callaghan y Mark, 1984). "
                                  "Script <code>codigo/punto2/05b_microcuenca_dgm.py</code> y <code>06_mapas_microcuenca.py</code>.")
    ESTAB["p24-microcuenca"] = ("La microcuenca y el pluviómetro están en la misma llanura, a 12 m de diferencia de altura y sin relieve entre ellos: comparten la masa de aire, "
                                "la capa límite y su ciclo diario. Las lluvias que dimensionan una alcantarilla aquí son tormentas convectivas de verano: el suelo calentado "
                                "vuelve inestable la capa límite por la tarde y las celdas se forman sin necesidad de montaña. Por la noche la inversión de radiación deja "
                                "niebla en los prados, pero no da lluvia de diseño. En el Chicama, en cambio, la inversión de subsidencia del Pacífico y el relieve hacen que "
                                "la lluvia cambie mucho con la altura (1.5.a): allí un pluviómetro a 7 km y 1 000 m más abajo no serviría.")
    slide("p24-microcuenca", "2 · Diseño hidrológico", "Punto 2 · 2.4 · Problema A", "La microcuenca: una zanja de prados a 7 km del pluviómetro", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_4_mapas_microcuenca.png', 'mapas_microcuenca', 'Mapas de la microcuenca')}</div>
<div class='txtcols'><div>
{tabla([("Área", f"{f(mcd.area_km2, 2)} km²", "dentro de 0,1–5 km² (guía)"),
        ("Cierre", f"{f(mcd.lon_cierre, 4)}° E, {f(mcd.lat_cierre, 4)}° N", f"a {f(mcd.dist_pluviometro_km, 1)} km del pluviómetro 00880"),
        ("Cauce principal", f"{f(mcd.L_cauce_principal_m, 0)} m", f"pendiente {f(100*mcd.S_global, 2)} % (10–85: {f(100*mcd.S_10_85, 2)} %)"),
        ("Relieve", f"{f(mcd.relieve_m, 1)} m ({f(mcd.z_cierre_m, 1)}–{f(mcd.z_max_m, 1)} m)", f"pendiente media {f(100*mcd.pendiente_media_cuenca, 2)} %"),
        ("Cobertura", f"pastizal {f(mcd['cobertura_pastizal_%'])} %, bosque {f(mcd['cobertura_bosque_%'])} %", "sin zonas urbanas")],
       ["", "Valor", "Comentario"])}
<p class='note'><b>Por qué no el Spree:</b> hasta Cottbus drena más de 2 000 km² con embalses (Spremberg) y una regulación fuerte: el método racional supone lluvia uniforme
en toda la cuenca durante tc, y eso solo vale en cuencas pequeñas.</p></div>
<div><p><b>Por qué esta microcuenca sirve para la tarea:</b></p><ul class='pts'>
<li><b>Tamaño:</b> {f(mcd.area_km2, 2)} km², en el rango del método racional; una celda convectiva (5–10 km) la cubre entera, así que la lluvia del pluviómetro se aplica casi sin reducción (FRA ≈ 0,98).</li>
<li><b>Es una cuenca real:</b> se delimitó en el modelo de terreno lidar DGM1, que mide el suelo. El primer intento con Copernicus (un modelo de superficie)
confundía el dosel del bosque con relieve y daba cuencas falsas.</li>
<li><b>Misma lluvia:</b> a {f(mcd.dist_pluviometro_km, 1)} km del pluviómetro, en la misma llanura, sin efecto orográfico. La IDF de 2.3 se puede usar directamente.</li>
<li><b>Hay dónde poner una alcantarilla:</b> la zanja de salida cruza un camino rural antes de entrar a la red de drenaje del Spree.</li>
<li><b>La cobertura se conoce</b> (WorldCover), así que C puede estimarse con tablas.</li></ul>
<p><b>Limitaciones:</b> el terreno es casi plano ({f(mcd.relieve_m, 1)} m de relieve), con zanjas artificiales que la D8 sigue solo en parte; tc es incierto (ver la siguiente diapositiva). No hay
vías en el mapa porque los servidores de OpenStreetMap no respondieron.</p></div></div></div>""", k="k-arch", g="a")

    FUENTES["p24-diseno"] = ("guía 2.4; Chow et al. (1988), §15.1 y tabla 15.1.1 (C para zonas planas, según T), tabla 13.1.1 (periodos de diseño); Kirpich (1940); "
                             "Témez (1978); NRCS (1986), TR-55; NERC (1975), Flood Studies Report (reducción areal); Manning a tubo lleno, concreto n = 0,013. "
                             "Script <code>codigo/punto2/07_problema_A.py</code>.")
    ESTAB["p24-diseno"] = ("La intensidad de diseño (≈ 27 mm/h durante 1,7 h) es la de una tormenta convectiva organizada de verano: necesita una atmósfera inestable en "
                           "toda la troposfera. Un chubasco aislado de 10–20 min es más intenso, pero aquí no llega a llenar el tubo porque el agua tarda ≈ 100 min en "
                           "recorrer la cuenca. Si la capa límite está estable (inversión nocturna o invierno), la lluvia es estratiforme y débil: no dimensiona nada. "
                           "Un tc largo hace que la alcantarilla «vea» tormentas largas, y por eso el tc pesa tanto en el diámetro.")
    slide("p24-diseno", "2 · Diseño hidrológico", "Punto 2 · 2.4 · Problema A", "El método racional: un tubo de 1,00 m, y la incertidumbre que más pesa es el tc", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_4_problemaA.png', 'problemaA', 'Tiempo de concentración y sensibilidad del diámetro')}</div>
<div class='txtcols'><div>
<div class='eq'>Q<sub>p</sub> = C · i(t<sub>c</sub>, T) · A · FRA / 3,6 = {f(0.335, 3)} · {f(26.57, 1)} · {f(mcd.area_km2, 3)} · {f(0.976, 3)} / 3,6 = <b>{f(dis.Q_m3_s, 2)} m³/s</b></div>
<p><b>Periodo de retorno por riesgo:</b> vida útil n = 30 años y riesgo aceptado R = 70 % (consecuencias bajas: un camino rural y prados) dan
T = 1/[1 − (1 − R)<sup>1/n</sup>] = 25,4 → <b>T = 25 años</b>, como recomienda Chow para vías secundarias (10–25 años). El riesgo sigue siendo alto: 71 % de que se
supere al menos una vez en 30 años.</p>
<p><b>tc:</b> Kirpich 102 min (elegido: el más usado para cuencas pequeñas con cauce definido), Témez 113, velocidad en la zanja 88 (V = 0,35 m/s) y retardo del SCS 258 min
(con CN = 55; sobreestima en cuencas muy planas). <b>C</b> = {f(0.335, 3)}, ponderado por área y creciente con T.</p>
<p><b>Diámetro:</b> Manning a tubo lleno, S₀ = 0,5 %, da D = {f(dis.D_calc_m, 2)} m → <b>DN 1,00 m</b> (capacidad 1,70 m³/s, factor de seguridad 1,61).</p></div>
<div><p><b>¿Qué incertidumbre pesa más?</b> (rango del diámetro calculado, frente al diseño)</p>
{tabla([(k, f"{f(r.D_min, 2)}–{f(r.D_max, 2)} m", f"{f(r['rango_vs_diseno_%'])} %") for k, r in rkA.iterrows()], ["Fuente", "D calculado", "Rango"])}
<p><b>Lectura:</b> la fórmula de tc mueve más el resultado que la propia lluvia. En un terreno de 1,4 m de desnivel en 1,85 km, el agua corre despacio y cada fórmula la
imagina distinta. Le sigue el intervalo de confianza de la IDF (30 años de datos) y después C. La elección de la distribución casi no cambia nada (1 %): a T = 25 todas
interpolan, no extrapolan (2.2). Solo el retardo del SCS, C − 20 % y el límite inferior de la IDF bajarían a DN 0,80 m.</p></div></div></div>""", k="k-arch", g="a")

    ec = esA.set_index("cuenca")
    FUENTES["p24-riesgo"] = ("guía 2.4.6–2.4.8; Monte Carlo con las 2 000 réplicas bootstrap de la GEV (remuestreo de años completos, igual para todas las duraciones); "
                             "Leclerc y Schaake (1972) para la reducción areal de cuencas grandes; Tarea 1 (área y cauce del Chicama).")
    ESTAB["p24-riesgo"] = ("En el Chicama la lluvia la organiza el relieve: el aire del Pacífico queda bajo la inversión de subsidencia y no sube; la lluvia llega del este "
                           "en la tarde, con convección forzada por la ladera, y se concentra en la parte alta. Ninguna tormenta cubre 2 170 km² a la vez con la "
                           "misma intensidad. Por eso la reducción areal cae a 0,67 en una hora y el racional deja de valer: allí se necesita un hidrograma unitario o un "
                           "modelo distribuido, con lluvia distinta en cada banda de altura.")
    slide("p24-riesgo", "2 · Diseño hidrológico", "Punto 2 · 2.4 · Problema A", "Riesgo efectivo y escala: el tubo real falla mucho menos que lo nominal", f"""
<div class='two even'><div class='panel'>{fig(FIG_P2 / 'fig_2_4_problemaA_montecarlo.png', 'problemaA_mc', 'Monte Carlo de la probabilidad de falla')}
<p class='note'>Cada iteración toma una réplica bootstrap de la IDF, un tc (triangular entre 88 y 258 min, moda en Kirpich), C ± 20 %, n de 0,011 a 0,015 y S₀ de 0,4 a
0,6 %, y calcula la probabilidad anual de que la lluvia supere la capacidad del DN 1,00 m.</p></div>
<div><p><b>Resultado:</b> probabilidad anual efectiva de falla {f(mcA.p_efectiva, 4)} (T efectivo ≈ {f(mcA.T_efectivo, 0)} años) frente a la nominal 0,04; riesgo en 30 años
<b>{f(100*mcA.riesgo_efectivo_30a)} %</b> frente al 71 % nominal. Entre iteraciones va de {f(mcA.p_efectiva_p5, 3)} a {f(mcA.p_efectiva_p95, 3)} (percentiles 5–95).</p>
<p><b>¿Por qué tan distinto?</b> No es que la incertidumbre ayude: es el <b>salto al diámetro comercial</b>. El cálculo pide 0,84 m y se instala 1,00 m, que con el valor
central ya alcanza hasta T ≈ 100 años (D = 0,99 m). La incertidumbre ensancha la distribución (8 % de las iteraciones casi nunca se llenan; el 5 % peor falla una
vez cada ≈ 70 años), pero el promedio queda lejos del nominal. Conclusión: hay que reportar el riesgo del tubo instalado, no el del cálculo.</p>
<p><b>Escala (2.4.8):</b></p>
{tabla([(c, f"{f(r.area_km2, 2 if r.area_km2 < 10 else 0)} km²", f"{f(r.tc_Kirpich_min)} min", f(r.FRA_1h, 2), f(r.FRA_en_tc, 2)) for c, r in ec.iterrows()],
       ["Cuenca", "Área", "tc", "FRA 1 h", "FRA en tc"])}
<p>En el Chicama, tc ≈ 6,4 h y la lluvia media de una hora sobre la cuenca es 33 % menor que la del pluviómetro. Además, el caudal depende de la humedad previa del suelo, del
almacenamiento en la cuenca y de que la lluvia caiga solo en la parte alta (1.3). Un C constante no representa nada de eso.</p></div></div>""", k="k-arch", g="a")

    base = ceA[ceA.caso.str.startswith("base")]
    m0 = base.total.min(); rng5 = base[base.total <= 1.05 * m0]["T"]
    c25 = base[base["T"] == 25].total.iloc[0]
    FUENTES["p25-bono"] = ("guía 2.5.1; Chow et al. (1988), §13.3 (diseño por análisis de riesgo y costo esperado); factor de recuperación de capital con r y n = 30 años. "
                           "Funciones de costo y daño adimensionales de la guía (múltiplos de C0, el costo de la obra para T = 2). Q(p) se calculó con FRA; como el costo depende de Q<sub>d</sub>/Q<sub>2</sub> y el daño de (Q − Q<sub>d</sub>)/Q<sub>d</sub>, el factor se cancela y el resultado es el mismo.")
    ESTAB["p25-bono"] = ("El daño esperado depende de la cola de la distribución de la lluvia: las crecientes que superan el tubo son tormentas convectivas raras, con "
                         "inestabilidad muy profunda. Con 30 años de registro esa cola se conoce mal (2.2), y el mínimo del costo cae justo donde ya extrapolamos. "
                         "Si el clima más cálido hace la atmósfera más inestable y húmeda (≈ 7 % más vapor por °C, Clausius–Clapeyron), la cola engorda y el T "
                         "óptimo sube.")
    slide("p25-bono", "2 · Diseño hidrológico", "Punto 2 · 2.5.1 · Bono", "Diseño de mínimo costo esperado: el óptimo es plano y cae más allá de T = 100", f"""
<div class='two even'><div class='panel'>{fig(FIG_P2 / 'fig_2_5_bono_costo.png', 'bono_costo', 'Costo anual esperado frente al periodo de retorno')}</div>
<div><div class='eq'>costo anual(T) = C<sub>obra</sub>(T) · FRC(r, n) + ∫<sub>0</sub><sup>1/T</sup> daño(Q(p)) dp</div>
<p><b>Funciones de la guía:</b> la obra cuesta (Q<sub>T</sub>/Q<sub>2</sub>)<sup>0,6</sup> veces C0 (economía de escala); el daño crece con el exceso de caudal hasta
D<sub>máx</sub> = 20 C0; r = 6 %, n = 30 años. Sensibilidad: D<sub>máx</sub> × 0,5 y × 2, r = 3 % y 9 %.</p>
<p><b>Resultado:</b> el mínimo está en T ≈ {f(base.loc[base.total.idxmin(), 'T'])} años, pero la curva es muy plana: entre T = {f(rng5.min())} y {f(rng5.max())} el costo está a menos
de 5 % del mínimo. Según los supuestos, el óptimo va de 200 a 750 años. Con T = 25 el costo esperado es {f(c25 / m0, 1)} veces el mínimo: casi todo es daño esperado.</p>
<p><b>¿Por qué tan alto?</b> El cuantil crece despacio con T (ξ ≈ 0, casi Gumbel) y el tubo cuesta poco más por ser más grande. Pasar de T = 25 a 100 no cambia el diámetro
comercial (DN 1,00 m en ambos casos), así que la decisión real es entre DN 1,00 y 1,20 m.</p>
<div class='callout teal'><b>Cautela:</b> todo el tramo del óptimo está en zona de extrapolación (T &gt; 2N = 60 años), donde la IDF depende de la cola supuesta, y las funciones de costo son
idealizadas. La conclusión robusta no es «T = 500». Es esta: con estos órdenes de magnitud, un T de 25 años queda corto en costo, y el DN 1,00 m (que ya cubre T ≈ 100) es una
buena elección.</div></div></div>""", k="k-arch", g="a")


if (P2D / "problemaB_resumen.csv").exists():
    rb = pd.read_csv(P2D / "problemaB_resumen.csv", index_col=0).valor
    trb = pd.read_csv(P2D / "problemaB_trapecios.csv"); bab = pd.read_csv(P2D / "problemaB_bloques.csv").set_index("posicion")
    sbb = pd.read_csv(P2D / "problemaB_sensibilidad.csv").set_index("caso")
    Vc = bab.loc["centro", "V_tanque_m3"]; Asc = bab.loc["centro", "As_m2"]
    r100 = lambda v: f(round(v, -2))
    FUENTES["p24b-tanque"] = ("guía 2.4, problema B; Chow et al. (1988), §15.4 (detención, racional modificado), §8.2 (tránsito de piscina nivelada por indicación de "
                              "almacenamiento), tabla 15.1.1 (C urbano) y tabla 15.1.2 (ajuste de Kirpich × 0,4 para superficies de asfalto o concreto); Kuiry y Sen (2021), cap. 3 "
                              "(orificio). Script <code>codigo/punto2/08_problema_B.py</code>.")
    ESTAB["p24b-tanque"] = ("Urbanizar cambia también el aire: el asfalto y los techos guardan calor y lo devuelven por la tarde (isla de calor). Eso refuerza la "
                            "inestabilidad de la capa límite sobre la zona urbana y puede disparar o intensificar la convección, justo el tipo de lluvia que llena el "
                            "tanque. De noche, la superficie urbana se enfría menos y la inversión nocturna es más débil que sobre los prados. El diseño usa la IDF "
                            "actual: no incluye ese efecto ni el calentamiento (bono 2.5.3).")
    slide("p24b-tanque", "2 · Diseño hidrológico", "Punto 2 · 2.4 · Problema B", "Urbanizar triplica el pico: un tanque de ≈ 7 900 m³ lo devuelve al caudal previo", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_4_problemaB.png', 'problemaB', 'Hidrogramas, tránsito y volumen del tanque')}</div>
<div class='txtcols'><div>
{tabla([("C (T = 25)", f(rb.C_pre, 3), f(rb.C_post, 3)),
        ("tc", f"{f(rb.tc_pre_min)} min (Kirpich)", f"{f(rb.tc_post_min)} min (Kirpich × 0,4)"),
        ("i(tc, 25)", "26,6 mm/h", "53,9 mm/h"),
        ("Q pico", f"{f(rb.O_max_m3_s, 2)} m³/s", f"{f(rb.Qp_post_m3_s, 2)} m³/s ({f(rb.Qp_post_m3_s / rb.O_max_m3_s, 1)} veces)")],
       ["", "Antes (prados)", "Después (urbano)"])}
<p class='note'>Escenario del grupo: 50 % impermeable (mitad vías de asfalto, mitad techos) y 50 % prados urbanos. El tc urbano se comprobó con cunetas y tuberías a 1 m/s
más 10 min de entrada: también da 41 min. Racional puro, sin FRA (≈ 0,98).</p>
<p><b>Por qué sube tanto:</b> dos efectos se multiplican. C pasa de 0,34 a 0,58 (llueve lo mismo, pero se infiltra menos), y tc baja de 102 a 41 min. Con un tc más
corto la alcantarilla «ve» lluvias más cortas, que son más intensas: i se duplica.</p></div>
<div><p><b>Tanque:</b> prismático (S = A<sub>s</sub> h), profundidad máxima {f(rb.h_max_m, 1)} m y orificio libre con C<sub>d</sub> = 0,6, dimensionado para que a tanque
lleno salga exactamente el caudal previo: A<sub>o</sub> = {f(rb.Ao_m2, 3)} m² (<b>D ≈ {f(100*rb.D_orificio_m)} cm</b>).</p>
<p><b>Trapecios:</b> la duración crítica es <b>{f(rb.d_critica_trapecio_min)} min</b> ({r100(rb.V_trapecio_m3)} m³). Las lluvias más cortas tienen más pico pero poco volumen;
las más largas, mucho volumen pero un pico que el orificio ya deja pasar (desde 4 h el pico no supera {f(rb.O_max_m3_s, 2)} m³/s y no hace falta tanque). El cálculo
aproximado de Chow, sin tránsito, da {r100(rb.V_aprox_sin_transito_m3)} m³.</p>
<p><b>Bloques alternos (6 h, pico al centro):</b> <b>{r100(Vc)} m³</b>, un {f(100 * (Vc / rb.V_trapecio_m3 - 1))} % más. Ese hietograma contiene a la vez la lluvia de 25 años de
<i>todas</i> las duraciones, de 10 min a 6 h: lleva {r100(bab.loc['centro', 'V_entrada_m3'])} m³ de escorrentía, contra {r100(trb.set_index('d_min').loc[60, 'V_entrada_m3'])} m³ del
trapecio crítico. <b>Recomendación:</b> V ≈ 7 900 m³, A<sub>s</sub> ≈ {r100(Asc)} m² (≈ {f(np.sqrt(Asc))} × {f(np.sqrt(Asc))} m, el 1,2 % de la cuenca) y orificio de 65 cm.</p>
<p class='note'><b>Verificación:</b> antes de urbanizar, el mismo hietograma con tiempo–área da {f(rb.pico_pre_verificacion_m3_s, 3)} m³/s, igual al pico del racional.
La profundidad no cambia el volumen: con un orificio, O = O<sub>máx</sub>·√(S/V) para cualquier h<sub>máx</sub>, y solo cambian el área y el orificio.</p></div></div></div>""", k="k-arch", g="a")

    FUENTES["p24b-pico"] = ("guía 2.4, problema B, 2 y 4; Chow et al. (1988), §14.4 (bloques alternos); Huff (1967) para la posición del pico en tormentas "
                            "convectivas; Kuiry y Sen (2021), cap. 3.")
    ESTAB["p24b-pico"] = ("En una tormenta convectiva el pico suele llegar pronto: la corriente ascendente se carga de agua y, al caer la lluvia, se vuelve una corriente "
                          "descendente fría que corta la entrada de aire húmedo y la celda se debilita. Por eso las tormentas de verano de Cottbus se parecen más al "
                          "patrón «pico al inicio» (Huff, primer cuartil). Las lluvias frontales estratiformes, con atmósfera estable sobre una capa fría, son más "
                          "uniformes y largas, y casi nunca llenan este tanque. El diseño usa el patrón más exigente (centro), no el más frecuente.")
    filas_s = [(c, r100(r.V_trapecio_critico_m3) if np.isfinite(r.V_trapecio_critico_m3) else "—", r100(r.V_bloques_inicio_m3), r100(r.V_bloques_centro_m3), r100(r.V_bloques_final_m3))
               for c, r in sbb.iterrows() if not c.startswith("h_max")]
    slide("p24b-pico", "2 · Diseño hidrológico", "Punto 2 · 2.4 · Problema B", "¿Por qué importa dónde cae el pico de la lluvia?", f"""
<div class='stackfig'><div class='panel'>{fig(FIG_P2 / 'fig_2_4_problemaB_hietogramas.png', 'problemaB_hiet', 'Hietogramas de bloques alternos')}</div>
<div class='txtcols'><div>
{tabla([(p, r100(bab.loc[p, 'V_tanque_m3']), f(bab.loc[p, 't_pico_h_min']), f(bab.loc[p, 'vaciado_tras_escorrentia_h'], 1)) for p in ["inicio", "centro", "final"]],
       ["Pico al…", "Volumen del tanque (m³)", "Tanque lleno en el minuto", "Vaciado tras la lluvia (h)"])}
<p><b>Pico al inicio ({r100(bab.loc['inicio', 'V_tanque_m3'])} m³):</b> el pico llega con el tanque vacío. Después solo queda lluvia débil, por debajo de lo que el orificio deja
salir, y el tanque se vacía antes de que termine la tormenta.</p>
<p><b>Pico al centro o al final (≈ 7 700–7 900 m³, +20 %):</b> antes del pico ya cayeron 2–3 h de lluvia moderada. Con poca agua en el tanque el orificio tiene poca carga y
deja salir poco, así que esa lluvia previa se va acumulando. Cuando llega el pico, parte del volumen ya está ocupado. El pico al centro exige un poco más que al final porque
la lluvia que sigue al pico todavía supera la salida.</p></div>
<div><p><b>Sensibilidad del volumen (m³):</b></p>
{tabla(filas_s, ["Caso", "Trapecio crítico", "Inicio", "Centro", "Final"])}
<p><b>Lectura:</b> C es lo que más mueve el volumen (±20 % en C da −28 % y +29 %). El tc urbano lo cambia entre 5 y 10 % (20 o 60 min en vez de 41). La duración del hietograma
casi no importa más allá de 3 h, porque la cola de lluvia débil sale por el orificio sin acumularse. Con la duración crítica de 1 h, las 6 h escogidas (≈ 9 tc) son de sobra.</p></div></div></div>""", k="k-arch", g="a")


DEC1 = [
    ("Demanda de referencia en 1.2–1.4", "ERA5-Land FAO-56, con banda de −10 a −25 %", "Es la única con todas las variables de FAO-56 por hora; la estación de Cajamarca y los productos dan el tamaño del sesgo (1.1.b), que se propaga como incertidumbre."),
    ("Umbrales de régimen ET/ETo", "0,75 (energía) y 0,40 (agua)", "Separan bien los meses en la gráfica de fracción evaporativa frente a humedad del suelo (1.3) y quedan cerca del umbral del ajuste segmentado; falta probar cuánto cambia la clasificación con ±0,05."),
    ("ω de Budyko–Fu", "rango 1,6–1,8 (central 1,57 del balance)", "Un único valor ocultaría que ET real tiene ±158 mm de incertidumbre; el rango expresa esa incertidumbre."),
    ("Apartado opcional 1.6", "Hacerlo: 1.6.1, déficit climático Σ(ETo − P) de mayo a septiembre", "Vale +0,2, usa datos ya calculados y conecta con el punto 2 (frecuencia con GEV-LMOM). Riesgo: la guía lo ata a usar la misma cuenca en el punto 2; se declara y se analiza la serie del Chicama."),
    ("Verificación de fuentes", "Leer McMillan et al. (2012) y confirmar en FLUXNET que no hay torres en la región", "La política exige haber leído las fuentes citadas: si no se confirma, se quita la cita."),
]
DEC2 = [
    ("Días imposibles (1991–1994)", "Eliminarlos (22 días)", "10 min con más lluvia que el pluviómetro diario es físicamente imposible; dejarlos inflaría los máximos de la época del contador de gotas."),
    ("Año válido", "≥ 80 % del año y ≥ 90 % de mayo–septiembre (30 años)", "Protege la temporada de tormentas; la sensibilidad (29 o 32 años) cambia los cuantiles menos de 3 %."),
    ("2014-08-03 y firmware 2021", "Conservarlos, con sensibilidad", "No hay prueba de error en 10 min; quitarlos cambia &lt; 3 % los cuantiles cortos que usa el diseño."),
    ("Distribución", "GEV por L-momentos", "Límite teórico de los máximos de bloque, mejor ajuste promedio y estimación estable con 30 datos."),
    ("Microcuenca", "Zanja de 0,44 km² en el DGM1, a 7,2 km", "Cumple el rango de la guía, mismo régimen climático y cuenca real delimitada con lidar."),
    ("Valores de C", "Chow, tabla 15.1.1 (zonas planas), según T", "Es la tabla que pide la guía; hay que comprobar cada valor en el libro antes de entregar."),
    ("Fórmula de tc de diseño", "Kirpich (102 min)", "Es la de la guía para cuencas pequeñas con cauce definido; queda en el medio de las cuatro; la incertidumbre se reporta (29 % del diámetro)."),
    ("Periodo de retorno", "T = 25 años (n = 30, R = 70 %)", "Consecuencias bajas (camino rural, prados) y coincide con la práctica de Chow para vías secundarias."),
    ("Tubo", "S₀ = 0,5 %, concreto n = 0,013; CN = 55 para el SCS", "Valores típicos de alcantarilla y de pastizal en suelos arenosos del Spree; entran en el Monte Carlo como rangos."),
    ("Urbanización (problema B)", "50 % impermeable, tc = Kirpich × 0,4", "Densidad residencial media; el ajuste × 0,4 de Chow para asfalto coincide con el cálculo por cunetas a 1 m/s (41 min)."),
    ("Tanque", "h<sub>máx</sub> = 1,5 m, C<sub>d</sub> = 0,6, diseño con pico al centro (≈ 7 900 m³)", "Nivel freático somero en la llanura del Spree; la profundidad no cambia el volumen. El pico al centro es el más exigente de los tres."),
    ("Bonos de 2.5", "Hacer 2.5.3 (escalado de 7 % por °C) además de 2.5.1", "Barato con lo ya hecho, responde la pregunta de clima de la síntesis y cambia el diámetro y el riesgo efectivo de la obra."),
    ("Tormenta de 2018", "Buscar noticias o informes del DWD", "Confirmaría que el máximo es real y no un error del instrumento."),
]
FUENTES["decisiones"] = "guía, sección «Uso de IA y responsabilidad del grupo» (Nivel A): quien entrega justifica las decisiones metodológicas y debe poder explicarlas."
slide("decisiones", "3 · Estado", "Decisiones del grupo", "Propuesta para cada decisión abierta (para revisar y aprobar)", f"""
<div class='two even'><div><h3>Punto 1</h3>{tabla(DEC1, ["Decisión", "Propuesta", "Por qué"])}
<div class='callout teal'><b>Trabajo individual</b> de Marlin Julie Schwebel. Pendiente: número del grupo para el nombre del ZIP
(T2_202602_GNN_Schwebel.zip).</div>
<p class='note'>Son recomendaciones: según la política de IA, cada decisión la aprueba la autora, que debe poder explicarla en la presentación. Las que se cambien se
recalculan con los scripts.</p></div>
<div><h3>Punto 2</h3>{tabla(DEC2, ["Decisión", "Propuesta", "Por qué"])}</div></div>""")


slide("estado", "3 · Estado", "Estado del trabajo", "Qué está hecho y qué sigue", f"""
<div class='two even'><div class='stack'>
<div class='card'><h4>Hecho {tag("hecho")}</h4><p><b>Punto 1 completo de 1.1 a 1.5</b> (ETo FAO-56 verificada, nueve métodos, sensibilidad, ET real por balance,
régimen y Budyko, tendencias, gradiente altitudinal y niebla). <b>Punto 2:</b> control de calidad, ajuste de extremos, IDF frente a KOSTRA, microcuenca,
problema A con Monte Carlo y escala, problema B (tanque de detención), bono 2.5.1.</p></div>
<div class='card'><h4>Decisiones de la autora {tag("dec")}</h4><p>Umbrales de régimen 0,75/0,40; ω como rango 1,6–1,8; GEV por L-momentos; regla de días imposibles;
valores de C (verificar en la tabla 15.1.1 de Chow); T = 25 por riesgo (n = 30, R = 70 %); S₀ = 0,5 % y n = 0,013; CN = 55; costos del bono.</p></div>
</div><div class='panel'><h3>Lo que sigue</h3><ul class='pts'>
<li>Síntesis del punto 2 (lluvia de diseño, incertidumbre, riesgo real, efecto del clima y de la cobertura).</li>
<li>Síntesis del punto 1 y esquema conceptual actualizado; 1.6.1 (déficit climático) y bono 2.5.3 (+7 % por °C).</li>
<li>Informe PDF, presentación PDF, README y ZIP con la estructura de la guía (sin credenciales ni bases completas).</li>
</ul></div></div>""")

# ============================================================================= pagina
def limpio(o):
    if isinstance(o, dict):
        return {k: limpio(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [limpio(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


# orden: los bonos de 2.5 van despues de los problemas de 2.4
_b = [x for x in sl if "id='p25-bono'" in x]
if _b:
    sl.remove(_b[0]); sl.insert(next(k for k, x in enumerate(sl) if "id='estado'" in x), _b[0])

nav = "".join(f"<button type='button' class='mod' data-go='{g}'><span>{n}</span> {t}</button>" for g, n, t in SEC[1:])
css = (SITIO / "estilo_deck.css").read_text(encoding="utf-8") + (SITIO / "estilo_extra.css").read_text(encoding="utf-8")
js = (SITIO / "graficas.js").read_text(encoding="utf-8")
pagina = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Evapotranspiración y diseño</title>
<meta name="description" content="Tarea 2 de Hidrología: evapotranspiración en la cuenca del río Chicama hasta El Tambo y diseño hidrológico con la lluvia de 10 minutos de Cottbus.">
<script>(function(){{var d=document.documentElement,t;try{{t=localStorage.getItem('theme')}}catch(e){{}}if(t)d.dataset.theme=t;}})()</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;1,8..60,400&display=swap" rel="stylesheet">
<style>{css}</style>
<script src="assets/plotly-2.35.2.min.js"></script>
</head><body>
<div class="deck">
<header class="top"><a class="back" href="{T1_URL}">← Tarea 1</a>
<nav class="series" aria-label="Secciones">{nav}</nav><div class="sec" id="secLabel"><b></b></div>
<button class="theme-tg" id="themeTg" type="button" aria-label="Cambiar entre modo claro y oscuro"><svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg><svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><span class="tlbl"></span></button>
</header>
<main id="main">
{''.join(sl)}
</main>
<footer class="nav-bar"><button class="nav" id="prev" type="button" aria-label="Diapositiva anterior">← <span class="navlbl">Anterior</span></button>
<div class="dots" id="dots"></div><span class="counter" id="counter"></span>
<button class="nav" id="next" type="button" aria-label="Diapositiva siguiente"><span class="navlbl">Siguiente</span> →</button></footer>
</div>
<script>const D = {json.dumps(limpio(D), ensure_ascii=False, separators=(',', ':'), allow_nan=False)};</script>
<script>{js}</script>
</body></html>"""
(DOCS / "index.html").write_text(pagina, encoding="utf-8")
print(f"index.html: {len(pagina.encode('utf-8')) / 1e6:.2f} MB, {len(sl)} diapositivas -> {DOCS.relative_to(RAIZ)}")
