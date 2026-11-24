"""
04_eto_medias_mensuales.py - Apartado 1.1.a, paso 4: error por promediar antes de una ecuacion no lineal.

Se compara, celda por celda y luego en el promedio de la cuenca, la ETo mensual obtenida de cuatro maneras:

  D  : suma de las ETo diarias (referencia, script 03)
  M1 : ec. 6 con las medias mensuales de las variables DIARIAS (Tmax, Tmin, Td, magnitud del viento, Rs)
       -> solo el efecto de promediar antes de la ecuacion (no linealidad pura)
  M2 : como M1 pero sin extremos: es = e0(Tmedia) y Rnl con Tmedia
       -> se suma el efecto de la convexidad de e0(T) (lo que la guia advierte para es)
  M3 : ec. 6 con el producto mensual de ERA5-Land (reanalysis-era5-land-monthly-means): T media de 24 h,
       Td, viento = magnitud de las componentes ya promediadas, ssrd medio diario
       -> se suma la cancelacion de los vectores de viento (y las diferencias propias del producto)
En los calculos mensuales G = 0.07 (T[i+1] - T[i-1]) (ec. 43); en el diario G = 0.

Ademas se revisa el error que ECMWF advierte en las medias mensuales de variables acumuladas
entre 2022-09 y 2024-02, comparando ssrd del producto mensual con la suma de los datos horarios.

Salidas: productos/punto1/eto_mensual_comparacion_promedios.csv, error_promediar_por_mes.csv,
         figuras/fig_1_1a_error_promediar.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fao56 as F
from lectura_era5land import PESOS, RAIZ

Z_CUENCA = 2557.0
P_CUENCA = F.presion_desde_z(Z_CUENCA)
OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475"


def eto_mensual(t, tmax, tmin, td, u10, rs, lat, idx):
    """ETo mensual (mm/mes) con la ec. 6 aplicada a medias mensuales; G con la ec. 43."""
    dias = idx.days_in_month.values
    j_medio = (idx + pd.to_timedelta(dias / 2 - 0.5, unit="D")).day_of_year   # dia central del mes
    es = F.es_diaria(tmax, tmin)
    ea = F.e0(td)
    u2 = F.u2_desde_uz(u10)
    rso = F.rso(F.ra(lat, j_medio), Z_CUENCA)
    rn = (1 - F.ALBEDO_REF) * rs - F.rnl(tmax, tmin, ea, rs, rso)
    ts = pd.Series(np.asarray(t), index=idx)
    g = (0.07 * (ts.shift(-1) - ts.shift(1))).fillna(0).values          # ec. 43
    eto, _, _ = F.eto_pm(np.asarray(t), u2, es, ea, rn, g, P_CUENCA)
    return np.asarray(eto) * dias


pesos = pd.read_csv(PESOS)
cache = pd.read_csv(OUT / "forzantes_diarios_celdas.csv.gz", parse_dates=["fecha"])
ds = xr.open_dataset(RAIZ / "datos/punto1/era5land/mensual/era5land_mensual_1981_2025_chicama.nc")

filas = []
for _, r in pesos.iterrows():
    d = cache[(cache.lat.round(1) == round(r.lat, 1)) & (cache.lon.round(1) == round(r.lon, 1))].set_index("fecha").sort_index()
    d = F.eto_desde_diario(d, r.lat, Z_CUENCA, P_CUENCA)
    m = d.resample("MS").agg({"eto": "sum", "tmax": "mean", "tmin": "mean", "td": "mean", "u10": "mean", "rs": "mean"})
    m["dias"] = d.eto.resample("MS").count()
    m = m[m.dias == m.index.days_in_month]
    tm = (m.tmax + m.tmin) / 2
    m["M1"] = eto_mensual(tm, m.tmax, m.tmin, m.td, m.u10, m.rs, r.lat, m.index)
    m["M2"] = eto_mensual(tm, tm, tm, m.td, m.u10, m.rs, r.lat, m.index)
    # producto mensual de ERA5-Land en la misma celda
    c = ds.sel(latitude=r.lat, longitude=r.lon, method="nearest").to_dataframe()
    c.index = pd.DatetimeIndex(c.index)
    c = c.reindex(m.index)
    t_p = c.t2m - 273.15
    u_vec = np.hypot(c.u10, c.v10)
    rs_p = c.ssrd / 1e6
    m["M3"] = eto_mensual(t_p, t_p, t_p, c.d2m - 273.15, u_vec, rs_p, r.lat, m.index)
    m["u10_vector"] = u_vec
    m["rs_producto"] = rs_p
    m["t_producto"] = t_p
    m["w"] = r.area_en_cuenca_km2
    filas.append(m.assign(lat=r.lat, lon=r.lon))

todo = pd.concat(filas)
cols = ["eto", "M1", "M2", "M3", "u10", "u10_vector", "rs", "rs_producto", "tmax", "tmin", "t_producto"]
cu = todo[cols].multiply(todo.w, axis=0).groupby(level=0).sum().div(todo.w.groupby(level=0).sum(), axis=0)
cu = cu.rename(columns={"eto": "D_suma_diaria"})
cu.index.name = "mes"
cu.round(3).to_csv(OUT / "eto_mensual_comparacion_promedios.csv")

# ECMWF advierte error en medias mensuales de acumuladas 2022-09..2024-02: ¿se ve en ssrd?
razon_rs = cu.rs_producto / cu.rs
malo = (cu.index >= "2022-09-01") & (cu.index <= "2024-02-01")
print(f"ssrd producto/horario: fuera del tramo advertido {razon_rs[~malo].mean():.4f} +- {razon_rs[~malo].std():.4f}; "
      f"dentro (2022-09..2024-02) {razon_rs[malo].mean():.4f} (min {razon_rs[malo].min():.4f}, max {razon_rs[malo].max():.4f})")

ok = cu[~malo]                         # el tramo afectado se excluye de la comparacion de M3
por_mes = pd.DataFrame({
    "D_mm": cu.groupby(cu.index.month).D_suma_diaria.mean(),
    "M1_%": 100 * (cu.M1 / cu.D_suma_diaria - 1).groupby(cu.index.month).mean(),
    "M2_%": 100 * (cu.M2 / cu.D_suma_diaria - 1).groupby(cu.index.month).mean(),
    "M3_%": 100 * (ok.M3 / ok.D_suma_diaria - 1).groupby(ok.index.month).mean(),
    "M3_mm": (ok.M3 - ok.D_suma_diaria).groupby(ok.index.month).mean(),
    "viento_vector/magnitud": (cu.u10_vector / cu.u10).groupby(cu.index.month).mean(),
    "Tmax-Tmin": (cu.tmax - cu.tmin).groupby(cu.index.month).mean(),
})
por_mes.index.name = "mes"
por_mes.round(3).to_csv(OUT / "error_promediar_por_mes.csv")
print(por_mes.round(2).to_string())
tot = lambda c, df=cu: 100 * (df[c].sum() / df.D_suma_diaria.sum() - 1)
print(f"\nanual: M1 {tot('M1'):+.2f} %  M2 {tot('M2'):+.2f} %  M3 {tot('M3', ok):+.2f} %  (respecto a la suma diaria)")

# ------------------------------------------------------------------ figura
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
x = np.arange(1, 13)
fig, ax = plt.subplots(1, 3, figsize=(13, 3.9), gridspec_kw={"width_ratios": [1.25, 1, 1.2]})
a = ax[0]
a.axhline(0, color="k", lw=.8)
a.plot(x, por_mes["M1_%"], "o-", color=GRIS, label="M1: medias de variables diarias")
a.plot(x, por_mes["M2_%"], "s-", color=ROJO, label="M2: + $e_s$ con T media (sin Tmáx/Tmín)")
a.plot(x, por_mes["M3_%"], "^-", color=AZUL, label="M3: producto mensual ERA5-Land")
a.set_xticks(x, [m[0] for m in MESES]); a.set_ylabel("% respecto a la suma de ETo diarias")
a.set_title("(a) Error por promediar, por mes", loc="left", fontsize=10.5); a.legend(frameon=False, fontsize=8)
a = ax[1]
a.plot(x, por_mes["Tmax-Tmin"], "o-", color=ROJO); a.set_ylabel("Tmáx − Tmín (°C)", color=ROJO)
b = a.twinx(); b.plot(x, por_mes["viento_vector/magnitud"], "s-", color=AZUL)
b.set_ylabel("|ū| / media de |u|", color=AZUL); b.spines["right"].set_visible(True)
a.set_xticks(x, [m[0] for m in MESES]); a.set_title("(b) Causas: amplitud térmica y viento", loc="left", fontsize=10.5)
a = ax[2]
a.plot(razon_rs.index, razon_rs, color=GRIS, lw=.8)
a.axvspan(pd.Timestamp("2022-09-01"), pd.Timestamp("2024-02-29"), color=ROJO, alpha=.15, label="tramo advertido por ECMWF")
a.set_ylabel("$R_s$ producto mensual / suma horaria"); a.legend(frameon=False, fontsize=8)
a.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(1985, 2030, 10)]), [str(y) for y in range(1985, 2030, 10)])
a.set_title("(c) Control del producto mensual", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1a_error_promediar.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_1_1a_error_promediar.png'}")
