"""
02_control_calidad_maximos.py - Punto 2, apartado 2.1 (datos y control de calidad) y 2.2.1 (series de maximos anuales).

Estacion DWD 00880 Cottbus (51.7759 N, 14.3168 E, 68.66 m; mismo sitio desde 1966), lluvia de 10 min 1991-10-31 a 2025-12-31.
Metadatos del DWD (datos/punto2/dwd_00880/metadatos/):
  * Hora: MEZ (UTC+1) hasta 1999-12-31, UTC desde 2000 -> todo se pasa a UTC. MESS_DATUM es el FIN del intervalo.
  * Instrumentos: NG 200 (contador de gotas) 1991-2007; PLUVIO (pesada) 2007-12-14 a 2020-09-16; rain[e]H3 (pesada) desde 2020-09-17.
  * Error de firmware rain[e] 2021-03-01..09-30: en Cottbus 9 dias de jun-jul 2021 con intensidades altas subestimadas
    (Hinweis_Raine_Firmwareproblem_2021.txt). 2021 se marca y se prueba con y sin el.
Controles: faltantes (-999 o filas ausentes), negativos, valores repetidos, acumulados tras vacios, extremos aislados,
cambio de resolucion por instrumento, completitud anual con tres criterios, y comparacion de cada maximo anual con la lluvia
diaria (RSK) de Cottbus y de dos vecinas: Lindenberg (03015, 50 km) y Doberlug-Kirchhain (01001, 53 km).
Maximos anuales (ano calendario: las tormentas ocurren en mayo-septiembre y el limite de ano cae en invierno) con ventanas
moviles sobre la serie de 10 min; una ventana con algun faltante no cuenta. Correccion de Weiss (1964) por intervalos fijos de
reloj: factor 1/(1 - 1/(8n)), n = numero de intervalos de 10 min de la duracion.

Salidas: productos/punto2/qc_*.csv, maximos_anuales_cottbus.csv, figuras/fig_2_1_*.png
"""
from pathlib import Path
import calendar
import zipfile
import glob

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / "datos/punto2/dwd_00880"
DIA = RAIZ / "datos/punto2/dwd_diario"
OUT = RAIZ / "productos/punto2"
FIG = OUT / "figuras"
FIG.mkdir(parents=True, exist_ok=True)
DUR = [10, 20, 30, 60, 120, 180, 360, 720, 1440]           # minutos
INSTR = [("NG 200 (gotas)", "1991-10-31", "2007-12-13"), ("PLUVIO (pesada)", "2007-12-14", "2020-09-16"),
         ("rain[e]H3 (pesada)", "2020-09-17", "2025-12-31")]
FIRMWARE_2021 = ["2021-06-12", "2021-06-26", "2021-06-29", "2021-06-30", "2021-07-11", "2021-07-13", "2021-07-17",
                 "2021-07-25", "2021-07-26"]
CRITERIOS = {"base (80 % año, 90 % may–sep)": (80, 90), "estricto (90 %, 95 %)": (90, 95), "laxo (70 %, 80 %)": (70, 80)}
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"

# ---------------------------------------------------------------- lectura y hora UTC
partes = []
for z in sorted(DIR.glob("10minutenwerte_nieder_00880_*_hist.zip")):
    with zipfile.ZipFile(z) as zf:
        n = [x for x in zf.namelist() if x.startswith("produkt")][0]
        d = pd.read_csv(zf.open(n), sep=";", skipinitialspace=True)
    d.columns = d.columns.str.strip()
    partes.append(d)
d = pd.concat(partes, ignore_index=True)
t = pd.to_datetime(d.MESS_DATUM.astype(str), format="%Y%m%d%H%M")
t = t.where(t >= "2000-01-01 00:10", t - pd.Timedelta(hours=1))     # MEZ -> UTC antes de 2000
d["t"] = t
d = d.drop_duplicates("t").set_index("t").sort_index()
idx = pd.date_range("1991-10-31 00:10", "2025-12-31 23:50", freq="10min")
r = d.RWS_10.reindex(idx)
falt_cod = int((r == -999).sum()); falt_fila = int(r.isna().sum())
r = r.where(r > -998)                                        # -999 -> faltante
print(f"10-min: {len(idx)} intervalos; faltantes por codigo -999: {falt_cod}, por fila ausente: {falt_fila}; "
      f"negativos validos: {int((r < 0).sum())}")

# ---------------------------------------------------------------- controles
qc = {}
qc["negativos"] = int((r < 0).sum())
# resolucion por instrumento: incremento minimo distinto de cero
for nom, a, b in INSTR:
    s = r.loc[a:b]; s = s[s > 0]
    qc[f"resolucion_{nom}"] = float(np.round(np.diff(np.unique(np.round(s.values, 3)))[:5].min(), 3)) if len(s) > 5 else np.nan
    qc[f"fraccion_10min_con_lluvia_{nom}"] = float((r.loc[a:b] > 0).mean())
# valores repetidos (>= 6 intervalos seguidos con el mismo valor > 0.2 mm)
grp = (r != r.shift()).cumsum()
rep = r.groupby(grp).agg(["first", "size"])
rep = rep[(rep["first"] > 0.2) & (rep["size"] >= 6)]
qc["rachas_repetidas"] = int(len(rep))
# acumulado tras vacio: primer valor despues de >= 1 h de faltante y > 5 mm
tras = r[(r > 5) & r.shift(1).isna() & r.shift(6).isna()]
qc["acumulados_tras_vacio"] = int(len(tras))
# extremos aislados: > 5 mm en 10 min con 30 min de cero antes y despues
cero_antes = r.shift(1).rolling(3).sum() == 0
cero_despues = r[::-1].shift(1).rolling(3).sum()[::-1] == 0
aisl = r[(r > 5) & cero_antes & cero_despues]
qc["extremos_aislados"] = int(len(aisl))
pd.Series(qc).to_csv(OUT / "qc_resumen_10min.csv", header=["valor"])
print("controles:", qc)

# ---------------------------------------------------------------- dias imposibles frente al pluviometro diario
def rsk_estacion(sid):
    dd = []
    for f in sorted((RAIZ / "datos/punto2/dwd_diario").glob(f"tageswerte_KL_{sid}_*.zip")):
        with zipfile.ZipFile(f) as zf:
            n = [x for x in zf.namelist() if x.startswith("produkt")][0]
            x = pd.read_csv(zf.open(n), sep=";", skipinitialspace=True)
        x.columns = x.columns.str.strip(); dd.append(x[["MESS_DATUM", "RSK"]])
    x = pd.concat(dd).drop_duplicates("MESS_DATUM")
    x.index = pd.to_datetime(x.MESS_DATUM.astype(str), format="%Y%m%d")
    return x.RSK.where(x.RSK > -998).sort_index()


rsk880 = rsk_estacion("00880")
s10 = r.resample("D").sum(min_count=1)
rsk3 = rsk880.reindex(s10.index).rolling(3, center=True, min_periods=1).sum()   # dias D-1, D, D+1 (convencion del DWD)
sosp = s10[(s10 > rsk3 + 5) & (s10 > 2 * rsk3)]
pd.DataFrame({"suma_10min_dia_UTC": sosp, "pluviometro_diario_3_dias": rsk3.reindex(sosp.index)}).round(1).to_csv(OUT / "qc_dias_imposibles.csv")
print(f"dias con mas lluvia en 10 min que en el pluviometro diario (D-1..D+1): {len(sosp)}")
print(pd.DataFrame({"10min": sosp, "diario_3d": rsk3.reindex(sosp.index)}).round(1).to_string())
for dia in sosp.index:                                       # esos dias se tratan como faltantes
    r.loc[dia:dia + pd.Timedelta(hours=23, minutes=59)] = np.nan
qc["dias_imposibles_eliminados"] = int(len(sosp))
pd.Series(qc).to_csv(OUT / "qc_resumen_10min.csv", header=["valor"])
mayores = r.nlargest(15).rename("mm_10min").to_frame()          # despues de la limpieza
mayores.index.name = "fin_intervalo_UTC"
mayores["lluvia_diaria_Cottbus_3d"] = [rsk3.get(t_.normalize(), np.nan) for t_ in mayores.index]
mayores.to_csv(OUT / "qc_mayores_10min.csv")
print("15 mayores valores de 10 min (tras la limpieza):"); print(mayores.round(1).to_string())

# ---------------------------------------------------------------- completitud y validez
anios = range(1991, 2026)
comp = []
for a in anios:
    s = r.loc[str(a)]
    esp = (366 if calendar.isleap(a) else 365) * 144
    v = s.loc[f"{a}-05-01":f"{a}-09-30"]
    comp.append({"anio": a, "pct_anio": 100 * s.notna().sum() / esp, "pct_may_sep": 100 * v.notna().sum() / (153 * 144),
                 "instrumento": next(nom for nom, x0, x1 in INSTR if pd.Timestamp(f"{a}-07-01") <= pd.Timestamp(x1)),
                 "firmware_2021": a == 2021})
C = pd.DataFrame(comp).set_index("anio")
for nom, (ua, uv) in CRITERIOS.items():
    C[nom] = (C.pct_anio >= ua) & (C.pct_may_sep >= uv)
print("\nanos validos por criterio:", {k: int(C[k].sum()) for k in CRITERIOS})

# ---------------------------------------------------------------- maximos anuales con ventanas moviles
M = {}
for dmin in DUR:
    n = dmin // 10
    suma = r.rolling(n, min_periods=n).sum()               # ventana con algun faltante -> NaN
    g = suma.groupby(suma.index.year)
    M[f"P{dmin}_mm"] = g.max()
    M[f"t{dmin}"] = g.idxmax()
MX = pd.DataFrame({k: v for k, v in M.items() if k.startswith("P")}).loc[list(anios)]
weiss = {d_: 1 / (1 - 1 / (8 * (d_ // 10))) for d_ in DUR}
for d_ in DUR:
    MX[f"P{d_}_weiss"] = MX[f"P{d_}_mm"] * weiss[d_]
    MX[f"i{d_}_mm_h"] = MX[f"P{d_}_weiss"] * 60 / d_
    MX[f"fecha{d_}"] = pd.Series(M[f"t{d_}"]).loc[list(anios)].values
# coherencia: la profundidad no puede bajar al crecer la duracion
prof = MX[[f"P{d_}_mm" for d_ in DUR]].values
incoh = int((np.diff(prof, axis=1) < -1e-6).sum())
print(f"incoherencias profundidad-duracion: {incoh}")
MX = MX.join(C)
MX.index.name = "anio"

# ---------------------------------------------------------------- comparacion con la lluvia diaria
def diario(sid):
    fs = sorted(DIA.glob(f"tageswerte_KL_{sid}_*.zip"))
    dd = []
    for f in fs:
        with zipfile.ZipFile(f) as zf:
            n = [x for x in zf.namelist() if x.startswith("produkt")][0]
            x = pd.read_csv(zf.open(n), sep=";", skipinitialspace=True)
        x.columns = x.columns.str.strip()
        dd.append(x[["MESS_DATUM", "RSK"]])
    x = pd.concat(dd).drop_duplicates("MESS_DATUM")
    x.index = pd.to_datetime(x.MESS_DATUM.astype(str), format="%Y%m%d")
    return x.RSK.where(x.RSK > -998).sort_index()
RSK = {"Cottbus": diario("00880"), "Lindenberg": diario("03015"), "Doberlug-Kirchhain": diario("01001")}
filas = []
for a in anios:
    for d_ in [60, 1440]:
        te = MX.loc[a, f"fecha{d_}"]
        if pd.isna(te):
            continue
        dia = pd.Timestamp(te).normalize()
        fila = {"anio": a, "duracion_min": d_, "fin_UTC": te, "mm_evento": MX.loc[a, f"P{d_}_mm"]}
        for k, s in RSK.items():                            # dia del evento y +-1 dia (convencion del dia de medicion del DWD)
            fila[f"{k}_max_diario_mm"] = s.reindex(pd.date_range(dia - pd.Timedelta(days=1), dia + pd.Timedelta(days=1))).max()
        filas.append(fila)
CMP = pd.DataFrame(filas)
CMP["razon_evento/diario_Cottbus"] = CMP.mm_evento / CMP.Cottbus_max_diario_mm
CMP["bandera"] = np.where((CMP.duracion_min == 1440) & ((CMP["razon_evento/diario_Cottbus"] > 1.5) | (CMP["razon_evento/diario_Cottbus"] < 0.5)),
                          "revisar", "")
CMP.round(2).to_csv(OUT / "qc_maximos_vs_diario.csv", index=False)
print("\nmaximos de 24 h frente a la lluvia diaria de Cottbus: razon mediana "
      f"{CMP[CMP.duracion_min==1440]['razon_evento/diario_Cottbus'].median():.2f}; a revisar: {int((CMP.bandera=='revisar').sum())}")
print(CMP[CMP.duracion_min == 60][["anio", "fin_UTC", "mm_evento", "Cottbus_max_diario_mm", "Lindenberg_max_diario_mm",
                                    "Doberlug-Kirchhain_max_diario_mm"]].round(1).to_string(index=False))

# firmware 2021: ¿el maximo de 2021 cae en un dia afectado?
f21 = [str(pd.Timestamp(MX.loc[2021, f"fecha{d_}"]).date()) in FIRMWARE_2021 for d_ in DUR]
MX["max_en_dia_firmware"] = False
MX.loc[2021, "max_en_dia_firmware"] = any(f21)
print(f"2021: maximos en dias afectados por el firmware: {sum(f21)} de {len(DUR)} duraciones")

MX.round(3).to_csv(OUT / "maximos_anuales_cottbus.csv")

# ---------------------------------------------------------------- figura
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(14, 4.2), gridspec_kw={"width_ratios": [1.15, 1.15, 0.9]})
colores_i = ["#eef1f6", "#e0e7f5", "#f5ead6"]
for a_ in ax[:2]:
    for (nom, x0, x1), c in zip(INSTR, colores_i):
        a_.axvspan(pd.Timestamp(x0).year - .5 + (pd.Timestamp(x0).dayofyear / 366),
                   pd.Timestamp(x1).year + .5 - (1 - pd.Timestamp(x1).dayofyear / 366), color=c, zorder=0)
a = ax[0]
base = list(CRITERIOS)[0]
cols = [AZUL if v else "#aaa" for v in C[base]]
a.bar(C.index, C.pct_anio, color=cols, label="% del año con dato")
a.plot(C.index, C.pct_may_sep, "D", color=ROJO, ms=4, label="% may–sep")
a.axhline(80, color=GRIS, ls=":"); a.axhline(90, color=GRIS, ls=":")
a.set_ylim(0, 105); a.set_ylabel("% de intervalos de 10 min con dato")
a.legend(frameon=False, fontsize=8, loc="lower right")
for (nom, x0, x1) in INSTR:
    a.text((pd.Timestamp(x0).year + pd.Timestamp(x1).year) / 2, 102, nom.split(" ")[0], ha="center", fontsize=7.5, color=GRIS)
a.set_title("(a) Completitud (gris: año descartado)", loc="left", fontsize=10.5)
a = ax[1]
for d_, c in [(10, ROJO), (60, NARANJA), (1440, AZUL)]:
    y = MX[f"i{d_}_mm_h"]
    ok = MX[base]
    a.plot(MX.index[ok], y[ok], "o-", color=c, ms=4, lw=1, label=f"{d_} min" if d_ < 1440 else "24 h")
    a.plot(MX.index[~ok], y[~ok], "x", color=c, ms=6)
a.set_yscale("log"); a.set_ylabel("intensidad máxima anual (mm/h, con Weiss)")
a.scatter([2021], [MX.loc[2021, "i10_mm_h"]], s=140, facecolor="none", edgecolor="k", label="2021 (firmware)")
a.legend(frameon=False, fontsize=8, ncol=2)
a.set_title("(b) Máximos anuales (x: año descartado)", loc="left", fontsize=10.5)
a = ax[2]
c24 = CMP[CMP.duracion_min == 1440]
a.scatter(c24.Cottbus_max_diario_mm, c24.mm_evento, color="k", s=18, label="Cottbus")
lim = [0, max(c24.mm_evento.max(), c24.Cottbus_max_diario_mm.max()) * 1.05]
a.plot(lim, lim, "k--", lw=.8)
a.set_xlabel("lluvia diaria del DWD (máx. del día ±1, mm)"); a.set_ylabel("máximo anual de 24 h, 10 min (mm)")
a.set_title("(c) Máximo de 24 h frente a la lluvia diaria", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_1_calidad.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_2_1_calidad.png'}")
