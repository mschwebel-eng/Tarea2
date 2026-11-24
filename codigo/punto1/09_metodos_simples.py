"""
09_metodos_simples.py - Apartado 1.1.c: metodos de otras familias frente a la ETo FAO-56.

Mismas 30 celdas, mismos forzantes diarios (cache del script 03), mismo promedio ponderado de la cuenca.
Metodos diarios -> suma mensual; Thornthwaite directamente mensual.
Metricas por mes calendario frente a FAO-56 (1981-2025): sesgo, MAE, RMSE; ciclo anual: amplitud (max - min de la
climatologia) y fase (mes del maximo). Se marca si el sesgo supera la dispersion de las pruebas de 1.1.b.

Verificacion: cada metodo disponible en pyet se recalcula para un dia y debe coincidir.
Salidas: productos/punto1/metodos_*.csv, figuras/fig_1_1c_*.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fao56 as F
import metodos_etp as M
from lectura_era5land import PESOS, RAIZ

Z_CUENCA = 2557.0
P_CUENCA = F.presion_desde_z(Z_CUENCA)
OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
NOMBRES = {"fao56": "FAO-56 PM", "thornthwaite": "Thornthwaite", "hamon": "Hamon", "hargreaves": "Hargreaves",
           "oudin": "Oudin", "priestley_taylor": "Priestley–Taylor", "dalton": "Dalton (FAO-24)", "meyer": "Meyer",
           "makkink": "Makkink*", "linacre": "Linacre*"}
FAMILIA = {"thornthwaite": "temperatura", "hamon": "temperatura", "hargreaves": "T + Ra", "oudin": "T + Ra",
           "priestley_taylor": "radiación", "makkink": "radiación (nuevo)", "dalton": "transferencia de masa",
           "meyer": "transferencia de masa", "linacre": "T + rocío (nuevo)"}
COLOR = {"thornthwaite": "#c2452a", "hamon": "#e07a5f", "hargreaves": "#b07a0c", "oudin": "#d4a72c",
         "priestley_taylor": "#1d4ed8", "makkink": "#60a5fa", "dalton": "#5b6475", "meyer": "#94a0b4", "linacre": "#2f7d4f"}

pesos = pd.read_csv(PESOS).merge(pd.read_csv(RAIZ / "datos/punto1/era5land/geopotencial_era5land_chicama.csv"), on=["lat", "lon"])
cache = pd.read_csv(OUT / "forzantes_diarios_celdas.csv.gz", parse_dates=["fecha"])

mens = []
for _, r in pesos.iterrows():
    d = cache[(cache.lat.round(1) == round(r.lat, 1)) & (cache.lon.round(1) == round(r.lon, 1))].set_index("fecha").sort_index()
    d = F.eto_desde_diario(d, r.lat, Z_CUENCA, P_CUENCA)
    j = d.index.day_of_year
    m = pd.DataFrame({
        "fao56": d.eto,
        "hamon": M.hamon(d.t, r.lat, j),
        "hargreaves": M.hargreaves(d.tmax, d.tmin, d.ra),
        "oudin": M.oudin(d.t, d.ra),
        "priestley_taylor": M.priestley_taylor(d.t, d.rn, P_CUENCA),
        "makkink": M.makkink(d.t, d.rs, P_CUENCA),
        "dalton": M.dalton_fao24(d.es, d.ea, d.u2),
        "meyer": M.meyer(d.es, d.ea, d.u10),
        "linacre": M.linacre(d.t, d.td, r.z_modelo_m, r.lat),
    }, index=d.index)
    mm = m.resample("MS").sum()
    mm = mm[d.eto.resample("MS").count().values == mm.index.days_in_month]
    tmes = d.t.resample("MS").mean().loc[mm.index]
    mm["thornthwaite"], I, a = M.thornthwaite_mensual(tmes, r.lat)
    mens.append(mm.assign(w=r.area_en_cuenca_km2))
    if r.lat == -7.6 and r.lon == -78.5:
        dia = d.loc["1981-01-15"]; mdia = m.loc["1981-01-15"]; I_c, a_c = I, a; z_c = r.z_modelo_m
todo = pd.concat(mens)
cols = list(NOMBRES)
cu = todo[cols].multiply(todo.w, axis=0).groupby(level=0).sum().div(todo.w.groupby(level=0).sum(), axis=0)
cu.index.name = "mes"
cu.round(3).to_csv(OUT / "metodos_mensual_cuenca.csv")

# ---------------------------------------------------------------- verificacion con pyet (celda central, 15 ene 1981)
print("verificacion con pyet (celda central, 1981-01-15, mm/d):")
try:
    import pyet
    idx = pd.DatetimeIndex(["1981-01-15"]); s = lambda v: pd.Series([float(v)], index=idx)
    lat_r = np.radians(-7.6)
    # Hargreaves: method=0 (Jensen y Allen 2016) es la forma de FAO-56 ec. 52.
    # Linacre: pyet usa la latitud con signo; la formula usa |latitud|, por eso se le pasa +7.6.
    # Diferencias residuales de ~0.3 %: pyet usa lambda variable con T (2.501 - 0.002361 T) en vez de 2.45.
    chk = {
        "hargreaves": pyet.hargreaves(s(dia.t), s(dia.tmax), s(dia.tmin), lat_r, method=0),
        "oudin": pyet.oudin(s(dia.t), lat_r),
        "priestley_taylor": pyet.priestley_taylor(s(dia.t), rn=s(dia.rn), pressure=s(P_CUENCA), alpha=1.26),
        "linacre": pyet.linacre(s(dia.t), z_c, abs(lat_r), tdew=s(dia.td)),
    }
    for k, v in chk.items():
        print(f"   {k:17s} propio {mdia[k]:.3f}   pyet {float(v.iloc[0]):.3f}   dif {100*(mdia[k]/float(v.iloc[0])-1):+.1f} %")
    # Hamon: ninguna variante de pyet es la forma de Lu et al. (2005) de las notas; verificacion a mano
    D_h = M.duracion_dia(-7.6, 15)
    print(f"   hamon a mano: 29.8 * {D_h:.2f} h * e0({dia.t:.2f}) = {F.e0(dia.t):.3f} kPa / ({dia.t:.2f}+273.2) = "
          f"{29.8 * D_h * F.e0(dia.t) / (dia.t + 273.2):.3f}  (propio {mdia['hamon']:.3f})")
except Exception as e:
    print(f"   FALLO verificacion pyet: {e}")
print(f"   Thornthwaite (no esta en pyet): I = {I_c:.1f}, a = {a_c:.2f} en la celda central")

# ---------------------------------------------------------------- metricas
fao = cu.fao56
filas, por_mes = [], []
clim = cu.groupby(cu.index.month).mean()
env = pd.read_csv(OUT / "envolvente_pruebas_demanda.csv", index_col="mes")
semi = (env["max"] - env["min"])                     # ancho de la dispersion de las pruebas de demanda
for c in cols[1:]:
    e = cu[c] - fao
    filas.append({"metodo": NOMBRES[c], "familia": FAMILIA[c], "anual_mm": cu[c].resample("YS").sum().mean(),
                  "sesgo_mm_mes": e.mean(), "sesgo_%": 100 * e.mean() / fao.mean(), "MAE": e.abs().mean(),
                  "RMSE": np.sqrt((e ** 2).mean()), "r": cu[c].corr(fao),
                  "amplitud_mm": clim[c].max() - clim[c].min(), "mes_max": MESES[int(clim[c].idxmax()) - 1],
                  "meses_fuera_dispersion": int(((clim[c] - clim.fao56).abs() > semi).sum())})
    for mes in range(1, 13):
        g = e[e.index.month == mes]
        por_mes.append({"metodo": c, "mes": mes, "sesgo_mm": g.mean(), "sesgo_%": 100 * g.mean() / fao[fao.index.month == mes].mean(),
                        "RMSE": np.sqrt((g ** 2).mean()), "fuera_dispersion": bool(abs(clim.loc[mes, c] - clim.loc[mes, "fao56"]) > semi[mes])})
res = pd.DataFrame(filas)
res.loc[len(res)] = {"metodo": "FAO-56 PM", "familia": "combinado (referencia)", "anual_mm": fao.resample("YS").sum().mean(),
                     "amplitud_mm": clim.fao56.max() - clim.fao56.min(), "mes_max": MESES[int(clim.fao56.idxmax()) - 1]}
res.round(3).to_csv(OUT / "metodos_metricas.csv", index=False)
pm = pd.DataFrame(por_mes); pm.round(3).to_csv(OUT / "metodos_metricas_por_mes.csv", index=False)
clim.round(2).to_csv(OUT / "metodos_climatologia.csv")
pd.set_option("display.width", 200)
print(res.round(2).to_string(index=False))

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
x = np.arange(1, 13)
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.15, 1]})
a = ax[0]
a.fill_between(x, env["min"], env["max"], color="#5b6475", alpha=.15, label="dispersión de las pruebas (1.1.b)")
a.plot(x, clim.fao56, "k-", lw=2.6, label="FAO-56 PM (referencia)")
for c in cols[1:]:
    a.plot(x, clim[c], "-o", ms=3.5, lw=1.4, color=COLOR[c], label=NOMBRES[c])
a.set_xticks(x, [m[0] for m in MESES]); a.set_ylabel("mm/mes")
a.legend(frameon=False, fontsize=7.6, ncol=2, loc="upper left", bbox_to_anchor=(0, 1.0))
a.set_title("(a) Ciclo anual de la demanda, 1981–2025 (*: métodos nuevos)", loc="left", fontsize=10.5)
a = ax[1]
mat = pm.pivot(index="metodo", columns="mes", values="sesgo_%").loc[cols[1:]]
fu = pm.pivot(index="metodo", columns="mes", values="fuera_dispersion").loc[cols[1:]]
lim = np.nanpercentile(np.abs(mat.values), 95)
im = a.imshow(mat.values, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
for i in range(mat.shape[0]):
    for jj in range(12):
        a.text(jj, i, f"{mat.values[i, jj]:+.0f}", ha="center", va="center", fontsize=7,
               fontweight="bold" if fu.values[i, jj] else "normal", color="k")
a.set_xticks(range(12), [m[0] for m in MESES]); a.set_yticks(range(len(mat)), [NOMBRES[c] for c in mat.index])
fig.colorbar(im, ax=a, label="sesgo frente a FAO-56 (%)")
a.set_title("(b) Sesgo por mes (%) · negrita: fuera de la dispersión", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1c_metodos.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_1_1c_metodos.png'}")
