"""
04_curvas_idf.py - Punto 2.3: curvas IDF de Cottbus, incertidumbre, comparacion con KOSTRA-DWD-2020 y periodo de retorno de
la tormenta del 9 de junio de 2018.

  1. Forma de Koutsoyiannis et al. (1998): i(d, T) = a(T) / (d + theta)^eta, d en horas.
     Paso 1: theta y eta por minimos cuadrados en log sobre los cuantiles GEV-LMOM de cada duracion (T = 2 ... 100),
             con un a_T libre por T. Paso 2: a(T) = cuantil de una GEV-LMOM ajustada a las intensidades reescaladas
             y = i (d + theta)^eta de todas las duraciones juntas (curvas que no se cruzan por construccion).
  2. Bandas: con las 2000 replicas bootstrap de 2.2 se reajusta a_T (theta y eta fijos) -> percentiles 2.5 y 97.5.
  3. KOSTRA-DWD-2020 (DWD; serie de duracion parcial 1951-2020, regionalizada en celdas de ~5 km): celda que contiene la
     estacion; profundidad HN (mm) y su incertidumbre UC (%) para T = 2 ... 100.
  4. Tormenta del 9 de junio de 2018: maximos de cada duracion ese dia (UTC) y su T con la GEV-LMOM; incertidumbre con el bootstrap.

Salidas: productos/punto2/idf_*.csv, kostra_cottbus.csv, evento_2018_06_09.csv, figuras/fig_2_3_*.png
"""
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import distribuciones as Dd

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "productos/punto2"
FIG = OUT / "figuras"
KOS = RAIZ / "datos/punto2/kostra"
DUR = np.array([10, 20, 30, 60, 120, 180, 360, 720, 1440])
DH = DUR / 60
TS = np.array([2, 5, 10, 25, 50, 100])
BASE = "base (80 % año, 90 % may–sep)"
LAT, LON = 51.7759, 14.3168
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"

MX = pd.read_csv(OUT / "maximos_anuales_cottbus.csv", index_col="anio")
val = MX[BASE].astype(bool)
X = {d: MX.loc[val, f"i{d}_mm_h"].dropna().values for d in DUR}
qdT = np.array([Dd.gev(X[d], "LMOM")["q"](TS) for d in DUR])          # (duracion, T)

# ---------------------------------------------------------------- 1) theta y eta
def sse(p):
    th, eta = p
    b = np.log(DH + th)[:, None]
    logq = np.log(qdT)
    logaT = (logq + eta * b).mean(axis=0)                               # a_T optimo para theta, eta dados
    return ((logq - (logaT - eta * b)) ** 2).sum()
res = min((minimize(sse, x0, bounds=[(0, 2), (0.05, 0.999)]) for x0 in [(0.05, 0.7), (0.2, 0.8), (0.5, 0.9)]), key=lambda r: r.fun)
theta, eta = res.x
print(f"IDF: theta = {theta:.4f} h ({60*theta:.1f} min), eta = {eta:.4f}")

# a(T) con una GEV sobre las intensidades reescaladas de todas las duraciones
y = np.concatenate([X[d] * (d / 60 + theta) ** eta for d in DUR])
ajA = Dd.gev(y, "LMOM")
aT = lambda T: ajA["q"](T)
idf = lambda d_h, T: aT(T) / (d_h + theta) ** eta
pred = np.array([[idf(dh, T) for T in TS] for dh in DH])
err = 100 * (pred / qdT - 1)
print(f"a(T): GEV mu = {ajA['par']['mu']:.2f}, sigma = {ajA['par']['sigma']:.2f}, xi = {ajA['par']['xi']:.3f}; "
      f"error frente a los cuantiles por duracion: RMSE {np.sqrt((err**2).mean()):.1f} %, max |error| {np.abs(err).max():.1f} %")
prof_ok = all(np.all(np.diff(idf(DH, T) * DH) > 0) for T in TS)
print(f"la profundidad i*d crece con la duracion: {prof_ok}; eta < 1: {eta < 1}")
pd.DataFrame({"parametro": ["theta_h", "eta", "gev_mu", "gev_sigma", "gev_xi", "rmse_%", "max_abs_error_%"],
              "valor": [theta, eta, ajA["par"]["mu"], ajA["par"]["sigma"], ajA["par"]["xi"], np.sqrt((err ** 2).mean()), np.abs(err).max()]}
             ).round(5).to_csv(OUT / "idf_parametros.csv", index=False)
tab = pd.DataFrame(pred, index=DUR, columns=[f"T{T}" for T in TS]); tab.index.name = "duracion_min"
tab.round(2).to_csv(OUT / "idf_tabla_mm_h.csv")
pd.DataFrame(err, index=DUR, columns=[f"T{T}" for T in TS]).round(2).rename_axis("duracion_min").to_csv(OUT / "idf_error_ajuste_pct.csv")

# ---------------------------------------------------------------- 2) bandas con el bootstrap
rep = pd.read_csv(OUT / "bootstrap_replicas_gev_lmom.csv.gz")
nrep = rep.rep.nunique()
aTb = np.zeros((nrep, len(TS)))
b = np.log(DH + theta)
for k, (r_, g) in enumerate(rep.groupby("rep")):
    g = g.set_index("duracion_min").loc[DUR]
    qb = np.array([Dd._gev_q(m, s, xi, TS) for m, s, xi in zip(g.mu, g.sigma, g.xi)])
    aTb[k] = np.exp((np.log(qb) + eta * b[:, None]).mean(axis=0))
pd.DataFrame(aTb, columns=[f"aT{T}" for T in TS]).round(4).to_csv(OUT / "idf_bootstrap_aT.csv", index=False)
banda = {T: (np.percentile(aTb[:, k], 2.5), np.percentile(aTb[:, k], 97.5)) for k, T in enumerate(TS)}

# ---------------------------------------------------------------- 3) KOSTRA-DWD-2020
geo = pd.read_excel(KOS / "KOSTRA-DWD-2020_geog_Bezug.xlsx", sheet_name="Raster_geog_Bezug")
dist = (geo.X5_CENT_WGS84 - LON) ** 2 * np.cos(np.radians(LAT)) ** 2 + (geo.Y5_CENT_WGS84 - LAT) ** 2
celda = geo.loc[dist.idxmin()]
print(f"KOSTRA: celda INDEX_RC {int(celda.index_rc)} (centro {celda.Y5_CENT_WGS84:.4f} N, {celda.X5_CENT_WGS84:.4f} E)")
filas = []
for d in DUR:
    with zipfile.ZipFile(KOS / f"StatRR_KOSTRA-DWD-2020_D{d:05d}.csv.zip") as zf:
        t = pd.read_csv(zf.open(zf.namelist()[0]), sep=";", decimal=",", dtype={"INDEX_RC": int})
    r = t[t.INDEX_RC == int(celda.index_rc)].iloc[0]
    for T in [2, 5, 10, 20, 50, 100]:
        hn = r[f"HN_{T:03d}A"]; uc = r[f"UC_{T:03d}A"]
        filas.append({"duracion_min": d, "T": T, "HN_mm": hn, "i_mm_h": hn * 60 / d, "UC_%": uc,
                      "i_lo": hn * 60 / d * (1 - uc / 100), "i_hi": hn * 60 / d * (1 + uc / 100),
                      "i_cottbus": idf(d / 60, T), "razon_cottbus/kostra": idf(d / 60, T) / (hn * 60 / d)})
K = pd.DataFrame(filas); K.round(3).to_csv(OUT / "kostra_cottbus.csv", index=False)
print("razon Cottbus/KOSTRA:"); print(K.pivot(index="duracion_min", columns="T", values="razon_cottbus/kostra").round(2).to_string())

# ---------------------------------------------------------------- 4) tormenta del 9 de junio de 2018
partes = []
for z in sorted((RAIZ / "datos/punto2/dwd_00880").glob("10minutenwerte_nieder_00880_2010*_hist.zip")):
    with zipfile.ZipFile(z) as zf:
        n = [x for x in zf.namelist() if x.startswith("produkt")][0]
        dd = pd.read_csv(zf.open(n), sep=";", skipinitialspace=True)
    dd.columns = dd.columns.str.strip(); partes.append(dd)
dd = pd.concat(partes)
s = pd.Series(dd.RWS_10.values, index=pd.to_datetime(dd.MESS_DATUM.astype(str), format="%Y%m%d%H%M")).sort_index()
s = s.where(s > -998).loc["2018-06-08 12:00":"2018-06-11 00:00"]
ev = []
for d in DUR:
    n = d // 10
    sm = s.rolling(n, min_periods=n).sum().loc["2018-06-09"]
    i_ev = sm.max() * (1 / (1 - 1 / (8 * n))) * 60 / d             # con Weiss, como los maximos anuales
    F = Dd.gev(X[d], "LMOM")["F"](i_ev)
    g = rep[rep.duracion_min == d]
    from scipy import stats
    Fb = stats.genextreme.cdf(i_ev, -g.xi.values, g.mu.values, g.sigma.values)
    Tb = 1 / np.clip(1 - Fb, 1e-6, None)
    ev.append({"duracion_min": d, "mm": sm.max(), "i_mm_h": i_ev, "fin_UTC": sm.idxmax(), "T_GEV": 1 / max(1 - F, 1e-6),
               "T_p2.5": np.percentile(Tb, 2.5), "T_p50": np.percentile(Tb, 50), "T_p97.5": np.percentile(Tb, 97.5),
               "T_KOSTRA_aprox": np.interp(i_ev, K[K.duracion_min == d].i_mm_h, K[K.duracion_min == d]["T"], left=1, right=np.inf)})
EV = pd.DataFrame(ev); EV.round(2).to_csv(OUT / "evento_2018_06_09.csv", index=False)
print("tormenta 2018-06-09:"); print(EV[["duracion_min", "mm", "i_mm_h", "T_GEV", "T_p2.5", "T_p97.5", "T_KOSTRA_aprox"]].round(1).to_string(index=False))

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(14.5, 4.6), gridspec_kw={"width_ratios": [1.35, 0.85, 1]})
a = ax[0]
dg = np.logspace(np.log10(10), np.log10(1440), 200) / 60
cols = {2: "#94a0b4", 5: "#5b6475", 10: AZUL, 25: VERDE, 50: NARANJA, 100: ROJO}
for k, T in enumerate(TS):
    a.plot(dg * 60, idf(dg, T), "-", color=cols[T], lw=1.6, label=f"T = {T} años")
    a.scatter(DUR, qdT[:, k], color=cols[T], s=14, zorder=4)
for T in [10, 100]:
    lo, hi = banda[T]
    a.fill_between(dg * 60, lo / (dg + theta) ** eta, hi / (dg + theta) ** eta, color=cols[T], alpha=.12)
    kk = K[K["T"] == T]
    a.errorbar(kk.duracion_min * 1.06, kk.i_mm_h, yerr=[kk.i_mm_h - kk.i_lo, kk.i_hi - kk.i_mm_h], fmt="s", color=cols[T],
               mfc="w", ms=5, capsize=2, lw=.8, label=f"KOSTRA-DWD-2020, T = {T}")
a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel("duración (min)"); a.set_ylabel("intensidad (mm/h)")
a.set_xticks([10, 20, 30, 60, 120, 360, 720, 1440], ["10", "20", "30", "60", "120", "360", "720", "1440"])
a.legend(frameon=False, fontsize=7.5, ncol=2)
a.set_title(f"(a) IDF de Cottbus: i = a(T)/(d + {theta:.2f} h)^{eta:.2f}", loc="left", fontsize=10.5)
a = ax[1]
for T, c in [(10, AZUL), (100, ROJO)]:
    kk = K[K["T"] == T]
    a.plot(kk.duracion_min, kk["razon_cottbus/kostra"], "o-", color=c, label=f"T = {T}")
    a.fill_between(kk.duracion_min, 1 - kk["UC_%"] / 100, 1 + kk["UC_%"] / 100, color=c, alpha=.08)
a.axhline(1, color="k", lw=.8); a.set_xscale("log"); a.set_xlabel("duración (min)"); a.set_ylabel("Cottbus (este trabajo) / KOSTRA")
a.set_xticks([10, 60, 360, 1440], ["10", "60", "360", "1440"]); a.legend(frameon=False, fontsize=8.5)
a.set_title("(b) Frente a la IDF oficial", loc="left", fontsize=10.5)
a = ax[2]
for k, T in enumerate(TS):
    a.plot(dg * 60, idf(dg, T), "-", color=cols[T], lw=1, alpha=.7)
a.plot(EV.duracion_min, EV.i_mm_h, "k-D", lw=2, ms=5, label="tormenta del 9-jun-2018")
for _, r in EV.iterrows():
    if r.duracion_min in (10, 20, 60, 360):
        a.annotate(f"T≈{r.T_GEV:.0f}", (r.duracion_min, r.i_mm_h), xytext=(5, 5), textcoords="offset points", fontsize=8)
a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel("duración (min)"); a.set_ylabel("intensidad (mm/h)")
a.set_xticks([10, 20, 30, 60, 120, 360, 720, 1440], ["10", "20", "30", "60", "120", "360", "720", "1440"])
a.legend(frameon=False, fontsize=8.5); a.set_title("(c) La tormenta del 9 de junio de 2018", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_3_idf.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_2_3_idf.png'}")
