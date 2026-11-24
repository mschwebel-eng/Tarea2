"""
13_tendencias_demanda.py - Apartado 1.4: cambios en la demanda evaporativa y su atribucion.

  1. Tendencias (metodos de la Tarea 1): Mann-Kendall con correccion de Hamed y Rao (1998) por autocorrelacion, pendiente
     de Sen con IC 95 %, OLS con errores HAC; por mes calendario (control FDR de Benjamini-Hochberg) y en la serie anual.
     Series: ETo FAO-56 (ERA5-Land, este trabajo) y Thornthwaite (1981-2025); como contraste, PISCOeo_pm, TerraClimate y la
     ETo de la estacion de Cajamarca (GSOD). Sensibilidad a los anos inicial y final (ventanas >= 15 anos).
  2. Atribucion: dETo/dt ~ sum_i (dETo/dx_i)(dx_i/dt), x = {T, ea, u2, Rs}. Las sensibilidades mensuales salen del
     experimento de 1.1.d (diferencias finitas); las tendencias de cada forzante, de Sen por mes calendario.
  3. Paradoja del tanque: ETo frente a Thornthwaite. No hay datos de tanque evaporimetro accesibles para la cuenca.
  4. Bono: descomposicion del cambio de caudal entre 1999-2011 y 2012-2024 con la curva de Fu (aportes de P, ETo y omega),
     con descomposicion de Shapley (exacta: los tres aportes suman el cambio).

Salidas: productos/punto1/tendencias_*.csv, atribucion_*.csv, budyko_descomposicion.csv, figuras/fig_1_4_*.png
"""
from pathlib import Path
import itertools
import json
import sys

import numpy as np
import pandas as pd
import xarray as xr
import pymannkendall as mk
import statsmodels.api as sm
from scipy.stats import theilslopes
from scipy.optimize import brentq
from shapely.geometry import shape, Point
from shapely import prepared
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lectura_era5land import RAIZ

OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"


def tend(y):
    """Tendencia de una serie anual (indice = ano): Hamed-Rao MK, Sen con IC 95 % y OLS-HAC. Pendientes por decada."""
    y = y.dropna()
    x = np.asarray(y.index, float)
    hr = mk.hamed_rao_modification_test(y.values)
    p, prueba = hr.p, "Hamed-Rao"
    if not np.isfinite(p):                     # la varianza corregida puede salir negativa: se usa MK original y se registra
        p, prueba = mk.original_test(y.values).p, "MK original (Hamed-Rao indefinido)"
    s, i0, lo, hi = theilslopes(y.values, x)
    ols = sm.OLS(y.values, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    return {"n": len(y), "sen_dec": 10 * s, "sen_lo_dec": 10 * lo, "sen_hi_dec": 10 * hi, "p_mk_hr": p, "prueba": prueba,
            "ols_dec": 10 * ols.params[1], "p_ols_hac": ols.pvalues[1], "media": y.mean(), "anios": f"{int(x.min())}-{int(x.max())}"}


def bh(p, q=0.10):
    """Control FDR de Benjamini-Hochberg: devuelve un booleano por prueba."""
    p = np.asarray(p); n = len(p); o = np.argsort(p)
    ok = p[o] <= q * (np.arange(1, n + 1) / n)
    k = np.max(np.where(ok)[0]) + 1 if ok.any() else 0
    r = np.zeros(n, bool); r[o[:k]] = True
    return r


# ---------------------------------------------------------------- series
em = pd.read_csv(OUT / "eto_mensual_cuenca.csv", index_col=0, parse_dates=True)
mt = pd.read_csv(OUT / "metodos_mensual_cuenca.csv", index_col=0, parse_dates=True)
cam = pd.read_csv(RAIZ / "datos/punto1/tarea1/PE_47E0A2A8.csv", parse_dates=["date"], index_col="date")
pis = cam.pet.resample("MS").sum(min_count=28)
gj = json.loads((RAIZ / "datos/punto1/tarea1/cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))
geo = shape(gj["features"][0]["geometry"]) if len(gj["features"]) == 1 else \
    shape({"type": "GeometryCollection", "geometries": [f["geometry"] for f in gj["features"]]})
poly = prepared.prep(geo.buffer(0))
da = xr.open_dataarray(RAIZ / "datos/punto1/terraclimate/terraclimate_pet_chicama_1981_2024.nc")
mask = np.array([[poly.contains(Point(x, y)) for x in da.lon.values] for y in da.lat.values])
tc = da.where(xr.DataArray(mask, coords={"lat": da.lat, "lon": da.lon}, dims=("lat", "lon"))).mean(("lat", "lon")).to_series()
tc.index = pd.DatetimeIndex(tc.index).to_period("M").to_timestamp()
est = pd.read_csv(OUT / "prueba_estacion_cajamarca_diaria.csv", index_col=0, parse_dates=True)
# estacion: media mensual de ETo diaria en meses con >= 20 dias validos; anual = media de las 12 anomalias mensuales
em_est = est.eto_estacion.resample("MS").mean()[est.eto_estacion.resample("MS").count() >= 20]
em_era_p = est.eto_era5land.resample("MS").mean()[est.eto_estacion.resample("MS").count() >= 20]


def anual_desde_anom(s, min_meses=9):
    an = s - s.groupby(s.index.month).transform("mean")
    g = an.groupby(an.index.year)
    return (g.mean() * 365.25)[g.count() >= min_meses]   # anomalia anual en mm/a


series = {
    "ETo FAO-56 (ERA5-Land)": em.eto.resample("YS").sum()[em.dias.resample("YS").count() == 12],
    "Thornthwaite": mt.thornthwaite.resample("YS").sum()[mt.thornthwaite.resample("YS").count() == 12],
    "PISCOeo_pm (SENAMHI)": pis.resample("YS").sum(min_count=12),
    "TerraClimate PET": tc.resample("YS").sum(min_count=12),
}
series = {k: v.set_axis(v.index.year) for k, v in series.items()}
series["Estación Cajamarca (anomalía)"] = anual_desde_anom(em_est)
series["ERA5-Land en Cajamarca, mismos días (anomalía)"] = anual_desde_anom(em_era_p)
T = pd.DataFrame({k: tend(v) for k, v in series.items()}).T
T.index.name = "serie"
T.round(4).to_csv(OUT / "tendencias_demanda_anual.csv")
print("tendencias de la demanda anual (mm/a por decada):")
print(T[["n", "media", "sen_dec", "sen_lo_dec", "sen_hi_dec", "p_mk_hr", "ols_dec", "p_ols_hac"]].round(3).to_string())
# seasonal Kendall con las series mensuales (Hirsch)
for nom, s in [("ETo", em.eto), ("Thornthwaite", mt.thornthwaite)]:
    st = mk.seasonal_test(s.values, period=12)
    print(f"Mann-Kendall estacional {nom}: p = {st.p:.4f}, pendiente de Sen = {10*12*st.slope:.1f} mm/a por decada")

# por mes calendario
fil = []
for nom, s in [("ETo", em.eto), ("Thornthwaite", mt.thornthwaite)]:
    for m_ in range(1, 13):
        y = s[s.index.month == m_]; y.index = y.index.year
        t_ = tend(y); t_.update({"serie": nom, "mes": m_}); fil.append(t_)
TM = pd.DataFrame(fil)
TM["fdr_ok"] = False
for nom in ["ETo", "Thornthwaite"]:
    k = TM.serie == nom
    TM.loc[k, "fdr_ok"] = bh(TM.loc[k, "p_mk_hr"].values)
TM.round(4).to_csv(OUT / "tendencias_demanda_por_mes.csv", index=False)
print(f"meses con tendencia que pasa FDR: ETo {int(TM[(TM.serie=='ETo')].fdr_ok.sum())}/12, "
      f"Thornthwaite {int(TM[(TM.serie=='Thornthwaite')].fdr_ok.sum())}/12")

# sensibilidad a ventanas (serie anual)
def ventanas(y, minlen=15):
    a0, a1 = y.index.min(), y.index.max()
    W = pd.DataFrame(index=range(a0, a1 + 1), columns=range(a0, a1 + 1), dtype=float)
    for i in range(a0, a1 + 1):
        for j in range(i + minlen - 1, a1 + 1):
            yy = y.loc[i:j]
            W.loc[i, j] = 10 * theilslopes(yy.values, yy.index.values)[0]
    return W
VE = ventanas(series["ETo FAO-56 (ERA5-Land)"]); VT = ventanas(series["Thornthwaite"])

# ---------------------------------------------------------------- atribucion
sens = pd.read_csv(OUT / "sensibilidad_fao56_por_mes_pct.csv", index_col="mes")
clim = em.groupby(em.index.month).mean()
rs_d = em.rs / em.dias                                        # MJ m-2 d-1
eto_m = clim.eto
S = pd.DataFrame({
    "T": sens["T+1_ea"] / 100 * eto_m,                                    # mm/mes por C
    "ea": sens["ea+10"] / 100 * eto_m / (0.1 * clim.ea),                  # mm/mes por kPa
    "u2": sens["u2+10"] / 100 * eto_m / (0.1 * clim.u2),                  # mm/mes por m/s
    "Rs": sens["rs-10"] / 100 * eto_m / (-0.1 * rs_d.groupby(rs_d.index.month).mean()),   # mm/mes por MJ m-2 d-1
})
forz_todo = pd.DataFrame({"T": em.t, "ea": em.ea, "u2": em.u2, "Rs": rs_d})


def atribuir(inicio, fin="2025"):
    """Aportes de cada forzante a la tendencia de ETo (mm/a por decada) en un periodo."""
    forz = forz_todo.loc[inicio:fin]; e = em.eto.loc[inicio:fin]
    TR = pd.DataFrame({v: [theilslopes(forz[v][forz.index.month == m_].values, forz.index[forz.index.month == m_].year)[0]
                           for m_ in range(1, 13)] for v in forz}, index=range(1, 13))      # unidad por ano
    contrib = (S * TR).sum() * 10
    direct = 10 * sum(theilslopes(e[e.index.month == m_].values, e.index[e.index.month == m_].year)[0] for m_ in range(1, 13))
    out = pd.Series(dict(contrib))
    out["suma"] = contrib.sum(); out["directa"] = direct; out["residuo"] = direct - contrib.sum()
    tf = pd.Series({f"tendencia_{v}_dec": 10 * TR[v].mean() for v in forz})
    return pd.concat([out, tf])


AT = pd.DataFrame({"1981-2025": atribuir("1981"), "2000-2025": atribuir("2000")})
AT.index.name = "termino"
AT.round(4).to_csv(OUT / "atribucion_tendencia_eto.csv")
contrib, direct = AT.loc[["T", "ea", "u2", "Rs"], "1981-2025"], AT.loc["directa", "1981-2025"]
print("\natribucion de la tendencia de ETo (mm/a por decada; tendencias de forzantes por decada):"); print(AT.round(3).to_string())

# ---------------------------------------------------------------- bono: Budyko
A = pd.read_csv(OUT / "et_real_anual_hidrologico.csv", index_col=0)
fu = lambda phi, w_: 1 + phi - (1 + phi ** w_) ** (1 / w_)
Qf = lambda P, E, w_: P * (1 - fu(E / P, w_))


def periodo(a):
    P, E, Q = a.P_L.mean(), a.eto.mean(), a.Q.mean()
    w_ = brentq(lambda w_: fu(E / P, w_) - (1 - Q / P), 1.0001, 30)
    return P, E, Q, w_


def shapley(p1, p2):
    nombres = ["P", "ETo", "omega"]
    aport = dict.fromkeys(nombres, 0.0)
    ordenes = list(itertools.permutations(range(3)))
    for o in ordenes:
        x = list(p1)
        for k in o:
            antes = Qf(*x); x[k] = p2[k]; aport[nombres[k]] += (Qf(*x) - antes) / len(ordenes)
    return aport


filas = []
for etq, excl in [("todos los años", []), ("sin 2000 ni 2017", [2000, 2017])]:
    a = A.drop(index=[k for k in excl if k in A.index])
    P1, E1, Q1, w1 = periodo(a.loc[1999:2011]); P2, E2, Q2, w2 = periodo(a.loc[2012:2024])
    ap = shapley((P1, E1, w1), (P2, E2, w2))
    filas.append({"caso": etq, "P1": P1, "P2": P2, "ETo1": E1, "ETo2": E2, "omega1": w1, "omega2": w2, "Q1": Q1, "Q2": Q2,
                  "dQ_obs": Q2 - Q1, "dQ_por_P": ap["P"], "dQ_por_ETo": ap["ETo"], "dQ_por_omega": ap["omega"]})
BD = pd.DataFrame(filas)
BD.round(2).to_csv(OUT / "budyko_descomposicion.csv", index=False)
print("\nbono - descomposicion del cambio de caudal 1999-2011 -> 2012-2024 (mm/a):"); print(BD.round(1).to_string(index=False))

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(13, 4.3), gridspec_kw={"width_ratios": [1.3, 1]})
a = ax[0]
estilo = {"ETo FAO-56 (ERA5-Land)": ("k", "-", 2), "Thornthwaite": (ROJO, "-", 1.6), "PISCOeo_pm (SENAMHI)": (NARANJA, "-", 1.1),
          "TerraClimate PET": (AZUL, "-", 1.1), "Estación Cajamarca (anomalía)": (VERDE, "--", 1.1)}
for k, (c, ls, lw) in estilo.items():
    y = series[k]; an = y - y.mean() if "anomalía" not in k else y
    etq = f"{k.replace(' (anomalía)', '')}: {T.loc[k, 'sen_dec']:+.0f} mm/dec (p = {T.loc[k, 'p_mk_hr']:.2f})"
    if "Estación" in k:                       # anos sueltos: puntos, no linea continua
        a.plot(an.index, an, "D", color=c, ms=5, label=etq + f", {int(T.loc[k, 'n'])} años")
    else:
        a.plot(an.index, an, ls, color=c, lw=lw, label=etq)
    xx = np.array([y.index.min(), y.index.max()])
    a.plot(xx, (T.loc[k, "sen_dec"] / 10) * (xx - xx.mean()) + 0, ":", color=c, lw=1)
a.axhline(0, color="k", lw=.5); a.set_ylabel("anomalía de la demanda anual (mm/año)")
a.legend(frameon=False, fontsize=7.5, loc="upper left")
a.set_title("(a) Tendencias de la demanda (Sen; p de Mann–Kendall Hamed–Rao)", loc="left", fontsize=10.5)
a = ax[1]
xm = np.arange(1, 13)
for nom, c, dx in [("ETo", "k", -0.18), ("Thornthwaite", ROJO, 0.18)]:
    d = TM[TM.serie == nom]
    a.errorbar(xm + dx, d.sen_dec, yerr=[d.sen_dec - d.sen_lo_dec, d.sen_hi_dec - d.sen_dec], fmt="o", color=c, ms=4,
               capsize=2, lw=1, label=nom, mfc=c)
    a.scatter((xm + dx)[d.fdr_ok.values], d.sen_dec[d.fdr_ok.values], s=70, facecolor="none", edgecolor=c, lw=1.4)
a.axhline(0, color="k", lw=.6); a.set_xticks(xm, [m[0] for m in MESES]); a.set_ylabel("mm/mes por década")
a.legend(frameon=False, fontsize=8.5); a.set_title("(b) Por mes (IC 95 %; círculo: pasa FDR)", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_4_tendencias.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(1, 3, figsize=(13.5, 4), gridspec_kw={"width_ratios": [1, 1, 1]})
a = ax[0]
lab = ["T", "eₐ", "u₂", "Rₛ", "suma", "directa"]
filas_at = ["T", "ea", "u2", "Rs", "suma", "directa"]
for per, dx, alfa in [("1981-2025", -0.2, 1.0), ("2000-2025", 0.2, 0.45)]:
    val = AT.loc[filas_at, per].values
    a.bar(np.arange(6) + dx, val, width=0.4, color=[ROJO, AZUL, GRIS, NARANJA, "#999", "k"], alpha=alfa,
          edgecolor="k", lw=.4, label=per)
    for i, v in enumerate(val):
        a.text(i + dx, v + (0.4 if v >= 0 else -1.4), f"{v:+.1f}", ha="center", fontsize=7)
a.axhline(0, color="k", lw=.6); a.set_xticks(range(6), lab); a.set_ylabel("aporte a la tendencia de ETo (mm/año por década)")
a.set_ylim(min(-13, AT.loc[filas_at].values.min() - 3), max(12, AT.loc[filas_at].values.max() + 2))
a.legend(frameon=False, fontsize=8, title="sólido / claro", title_fontsize=7.5)
a.set_title("(a) Atribución de la tendencia de ETo", loc="left", fontsize=10.5)
for a, W, nom in [(ax[1], VE, "ETo FAO-56"), (ax[2], VT, "Thornthwaite")]:
    lim = np.nanmax(np.abs(np.r_[VE.values.ravel(), VT.values.ravel()]))
    im = a.imshow(W.values.T, origin="lower", cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto",
                  extent=[W.index.min() - .5, W.index.max() + .5, W.columns.min() - .5, W.columns.max() + .5])
    a.set_xlabel("año inicial"); a.set_ylabel("año final")
    a.set_title(f"(b) {nom}: Sen por ventana" if nom.startswith("ETo") else f"(c) {nom}: Sen por ventana", loc="left", fontsize=10.5)
fig.colorbar(im, ax=ax[1:], label="mm/año por década")
fig.savefig(FIG / "fig_1_4_atribucion.png", dpi=200, bbox_inches="tight"); plt.close(fig)

fig, a = plt.subplots(figsize=(6.2, 3.8))
r0 = BD.iloc[0]
lab = ["ΔQ observado", "por P", "por ETo", "por ω"]
val = [r0.dQ_obs, r0.dQ_por_P, r0.dQ_por_ETo, r0.dQ_por_omega]
a.bar(range(4), val, color=["k", AZUL, ROJO, VERDE])
for i, v in enumerate(val):
    a.text(i + 0.28, v / 2, f"{v:+.1f}", ha="left", va="center", fontsize=8.5)
r1 = BD.iloc[1]
a.scatter(range(4), [r1.dQ_obs, r1.dQ_por_P, r1.dQ_por_ETo, r1.dQ_por_omega], marker="D", color="w", edgecolor="k", zorder=5,
          label="sin 2000 ni 2017")
a.axhline(0, color="k", lw=.6); a.set_xticks(range(4), lab); a.set_ylabel("mm/año")
a.legend(frameon=False, fontsize=8.5)
a.set_title("Bono: cambio de caudal 1999–2011 → 2012–2024 (Fu)", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_4_budyko_bono.png", dpi=200); plt.close(fig)
print(f"-> figuras en {FIG.relative_to(RAIZ)}")
