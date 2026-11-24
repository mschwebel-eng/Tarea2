"""
08_prueba_productos_demanda.py - Apartado 1.1.b, pruebas 2 y 3: productos independientes de demanda,
y la restriccion fisica ETo frente a P - Q.

  * PISCOeo_pm v1.0 (SENAMHI), via CAMELS-PE (columna pet, mm/d): Penman-Monteith con datos del Peru.
  * TerraClimate (Abatzoglou et al., 2018): pet = ETo Penman-Monteith (pasto de referencia) calculada con
    su propia climatologia de alta resolucion + anomalias; se usan tambien tmax, tmin, vpd, ws y srad
    para ver QUE variable separa a TerraClimate de ERA5-Land.
    Promedio de la cuenca: celdas de ~4 km cuyo centro cae dentro de la divisoria (GLO-30 de la Tarea 1).
  * Restriccion fisica (guia, 1.1.b): ETo multianual debe superar a P - Q.
Periodo comun: 1981-2020 para la comparacion de productos (PISCOt/PISCOeo llegan a 2020 en CAMELS-PE).

Salidas: productos/punto1/prueba_productos_*.csv, figuras/fig_1_1b_productos.png
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import shape, Point
from shapely import prepared
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lectura_era5land import RAIZ

OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
TC = RAIZ / "datos/punto1/terraclimate"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475"

# --- cuenca
gj = json.loads((RAIZ / "datos/punto1/tarea1/cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))
poly = prepared.prep(shape(gj["features"][0]["geometry"]).buffer(0)) if len(gj["features"]) == 1 else \
    prepared.prep(shape({"type": "GeometryCollection", "geometries": [f["geometry"] for f in gj["features"]]}).buffer(0))

# --- ERA5-Land (scripts 03 y 05)
em = pd.read_csv(OUT / "eto_mensual_cuenca.csv", index_col=0, parse_dates=True)

# --- CAMELS-PE: P, Q, PISCOeo_pm
cam = pd.read_csv(RAIZ / "datos/punto1/tarea1/PE_47E0A2A8.csv", parse_dates=["date"], index_col="date")
cm = cam[["prec", "pet", "flow_obs", "tmax", "tmin"]].resample("MS").agg(
    {"prec": "sum", "pet": "sum", "flow_obs": "mean", "tmax": "mean", "tmin": "mean"})
cm["n_pet"] = cam.pet.resample("MS").count()
cm.loc[cm.n_pet < 28, "pet"] = np.nan


# --- TerraClimate promedio de cuenca
def tc_cuenca(v):
    da = xr.open_dataarray(TC / f"terraclimate_{v}_chicama_1981_2024.nc")
    lat, lon = da.lat.values, da.lon.values
    m = np.array([[poly.contains(Point(x, y)) for x in lon] for y in lat])
    s = da.where(xr.DataArray(m, coords={"lat": lat, "lon": lon}, dims=("lat", "lon"))).mean(("lat", "lon"))
    return s.to_series(), int(m.sum())


tc = {}
for v in ["pet", "tmax", "tmin", "vpd", "ws", "srad", "aet", "ppt"]:
    tc[v], ncel = tc_cuenca(v)
tc = pd.DataFrame(tc)
tc.index = pd.DatetimeIndex(tc.index).to_period("M").to_timestamp()
print(f"TerraClimate: {ncel} celdas de ~4 km dentro de la cuenca")

# --- tabla mensual comun 1981-2020
per = slice("1981-01-01", "2020-12-01")
T = pd.DataFrame({
    "eto_era5land": em.eto, "pet_piscoeo": cm.pet, "pet_terraclimate": tc.pet,
    "tmax_era": em.tmax, "tmin_era": em.tmin, "tmax_tc": tc.tmax, "tmin_tc": tc.tmin,
    "tmax_pisco": cm.tmax, "tmin_pisco": cm.tmin,
    "vpd_era": em.vpd, "vpd_tc": tc.vpd, "u2_era": em.u2, "u2_tc": tc.ws * 4.87 / np.log(67.8 * 10 - 5.42),
    "rs_era_wm2": em.rs / em.dias * 1e6 / 86400, "srad_tc_wm2": tc.srad,
}).loc[per]
T.round(3).to_csv(OUT / "prueba_productos_mensual.csv")
clim = T.groupby(T.index.month).mean()
clim.index.name = "mes"
clim.round(3).to_csv(OUT / "prueba_productos_climatologia.csv")

anual = T[["eto_era5land", "pet_piscoeo", "pet_terraclimate"]].resample("YS").sum(min_count=12).mean()
print("\ndemanda media anual 1981-2020 (mm/a):"); print(anual.round(0).to_string())
print("\nforzantes medios 1981-2020 (ERA5-Land | TerraClimate | PISCOt):")
print(f"  Tmax {T.tmax_era.mean():.1f} | {T.tmax_tc.mean():.1f} | {T.tmax_pisco.mean():.1f} C")
print(f"  Tmin {T.tmin_era.mean():.1f} | {T.tmin_tc.mean():.1f} | {T.tmin_pisco.mean():.1f} C")
print(f"  VPD  {T.vpd_era.mean():.2f} | {T.vpd_tc.mean():.2f} kPa ;  viento u2 ERA {T.u2_era.mean():.2f} | TC {T.u2_tc.mean():.2f} m/s")
print(f"  Rs   {T.rs_era_wm2.mean():.0f} | {T.srad_tc_wm2.mean():.0f} W m-2")

# metricas por mes calendario de cada producto frente a ERA5-Land
met = []
for c in ["pet_piscoeo", "pet_terraclimate"]:
    d = (T[c] - T.eto_era5land)
    for mes, g in d.groupby(d.index.month):
        met.append({"producto": c, "mes": mes, "sesgo_mm": g.mean(), "sesgo_%": 100 * g.mean() / T.eto_era5land[g.index].mean(),
                    "r": np.corrcoef(T[c][g.index].dropna(), T.eto_era5land[T[c][g.index].dropna().index])[0, 1]})
met = pd.DataFrame(met)
met.round(3).to_csv(OUT / "prueba_productos_metricas_por_mes.csv", index=False)

# envolvente de las pruebas (para 1.1.d): min y max por mes de las estimaciones de demanda
env = clim[["eto_era5land", "pet_piscoeo", "pet_terraclimate"]]
pd.DataFrame({"min": env.min(axis=1), "max": env.max(axis=1)}).round(2).to_csv(OUT / "envolvente_pruebas_demanda.csv")

# --- restriccion fisica: ETo frente a P - Q (periodo con caudal, 1998-2024 como en la Tarea 1)
pq = cam.loc["1998":"2024"]
P, Q = pq.prec.sum() / 27, pq.flow_obs.mean() * 365.25
eto_98 = em.eto.loc["1998":"2024"].sum() / 27
print(f"\nrestriccion fisica 1998-2024: P = {P:.0f} mm/a, Q = {Q:.0f} mm/a, P - Q = {P-Q:.0f} mm/a  <  ETo = {eto_98:.0f} mm/a"
      f"  -> {'se cumple' if eto_98 > P-Q else 'NO se cumple'} (ETo/(P-Q) = {eto_98/(P-Q):.2f})")
pd.Series({"P_mm": P, "Q_mm": Q, "P_menos_Q_mm": P - Q, "ETo_era5land_mm": eto_98,
           "PET_piscoeo_mm": anual.pet_piscoeo, "PET_terraclimate_mm": anual.pet_terraclimate}).round(1).to_csv(
    OUT / "prueba_restriccion_fisica.csv", header=["valor"])

# --- figura
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
x = np.arange(1, 13)
fig, ax = plt.subplots(1, 3, figsize=(13, 3.9), gridspec_kw={"width_ratios": [1.25, 1, 1]})
a = ax[0]
a.fill_between(x, env.min(axis=1), env.max(axis=1), color=GRIS, alpha=.15, label="dispersión de las pruebas")
a.plot(x, clim.eto_era5land, "o-", color=NARANJA, label="ETo FAO-56, ERA5-Land (este trabajo)")
a.plot(x, clim.pet_piscoeo, "s-", color=ROJO, label="PISCOeo_pm (SENAMHI, CAMELS-PE)")
a.plot(x, clim.pet_terraclimate, "^-", color=AZUL, label="TerraClimate (PM)")
a.set_xticks(x, [m[0] for m in MESES]); a.set_ylabel("mm/mes"); a.legend(frameon=False, fontsize=8)
a.set_title("(a) Demanda de la cuenca, 1981–2020", loc="left", fontsize=10.5)
a = ax[1]
a.plot(x, clim.tmax_era, "-", color=NARANJA, label="ERA5-Land"); a.plot(x, clim.tmin_era, "-", color=NARANJA)
a.plot(x, clim.tmax_tc, "--", color=AZUL, label="TerraClimate"); a.plot(x, clim.tmin_tc, "--", color=AZUL)
a.plot(x, clim.tmax_pisco, ":", color="k", label="PISCOt"); a.plot(x, clim.tmin_pisco, ":", color="k")
a.set_xticks(x, [m[0] for m in MESES]); a.set_ylabel("°C"); a.legend(frameon=False, fontsize=8)
a.set_title("(b) Tmáx (arriba) y Tmín (abajo)", loc="left", fontsize=10.5)
a = ax[2]
a.plot(x, clim.vpd_era, "o-", color=NARANJA, label="DPV ERA5-Land"); a.plot(x, clim.vpd_tc, "^-", color=AZUL, label="DPV TerraClimate")
a.set_ylabel("déficit de vapor (kPa)"); a.set_xticks(x, [m[0] for m in MESES])
b = a.twinx(); b.plot(x, clim.u2_era, "o:", color=NARANJA); b.plot(x, clim.u2_tc, "^:", color=AZUL)
b.set_ylabel("viento a 2 m (m/s, punteado)"); b.spines["right"].set_visible(True)
a.legend(frameon=False, fontsize=8, loc="upper left")
a.set_title("(c) Aire: déficit de vapor y viento", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1b_productos.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_1_1b_productos.png'}")
