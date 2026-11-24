"""
15_gradiente_altitudinal.py - Apartado 1.5.a: ETo y ET por bandas de elevacion.

  * Bandas de 500 m con el DEM Copernicus GLO-90 (la mas baja, 680-1000 m, queda en o bajo la inversion costera).
  * ETo por banda: en cada celda de ERA5-Land, la parte de cada banda recibe los forzantes de la celda corregidos a la
    elevacion media de esa parte con los gradientes del paso 5 (Tmax -5.42, Tmin -5.08, Td -5.32 C/km); gamma con la presion
    de esa elevacion (ec. 7) y Rso con la ec. 37. Rs y viento no se corrigen (no hay pendiente ni orientacion: en la Tarea 1
    cada orientacion ocupa 10-14 % del area). Bajo la inversion la temperatura no baja con la altura: la banda mas baja se marca.
  * ET real, P y PET por banda con TerraClimate (~4 km, climatologia de alta resolucion): cada celda toma la elevacion media
    del DEM dentro de ella.
  * Contraste: ET de ERA5-Land por celda frente a la elevacion del modelo (9 km).

Salidas: productos/punto1/gradiente_bandas.csv, gradiente_terraclimate_celdas.csv, figuras/fig_1_5a_gradiente.png
"""
from pathlib import Path
import glob
import json
import sys

import numpy as np
import pandas as pd
import xarray as xr
import rasterio
from rasterio.merge import merge
from rasterio.features import geometry_mask
from shapely.geometry import shape
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fao56 as F
from lectura_era5land import PESOS, RAIZ

OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
GRAD = {"tmax": -5.42e-3, "tmin": -5.08e-3, "td": -5.32e-3}
BANDAS = [680, 1000, 1500, 2000, 2500, 3000, 3500, 4300]
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"

# ---------------------------------------------------------------- DEM y cuenca
src = [rasterio.open(p) for p in sorted(glob.glob(str(RAIZ / "datos/punto1/dem/Copernicus_DSM_COG_30_*_DEM.tif")))]
dem, tr = merge(src); dem = dem[0].astype(float)
gj = json.loads((RAIZ / "datos/punto1/tarea1/cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))
dentro = geometry_mask([shape(f["geometry"]) for f in gj["features"]], out_shape=dem.shape, transform=tr, invert=True)
fi, co = np.nonzero(dentro)
lat_px = tr.f + (fi + 0.5) * tr.e
lon_px = tr.c + (co + 0.5) * tr.a
z_px = dem[fi, co]
banda_px = np.digitize(z_px, BANDAS[1:-1])               # 0 .. 6
etq = [f"{BANDAS[i]}–{BANDAS[i+1]}" for i in range(len(BANDAS) - 1)]

# ---------------------------------------------------------------- ETo por banda (ERA5-Land corregido)
pesos = pd.read_csv(PESOS).merge(pd.read_csv(RAIZ / "datos/punto1/era5land/geopotencial_era5land_chicama.csv"), on=["lat", "lon"])
cel_lat = np.round(np.round(lat_px / 0.1) * 0.1, 1); cel_lon = np.round(np.round(lon_px / 0.1) * 0.1, 1)
px = pd.DataFrame({"lat": cel_lat, "lon": cel_lon, "banda": banda_px, "z": z_px})
grupos = px.groupby(["lat", "lon", "banda"]).agg(n=("z", "size"), z=("z", "mean")).reset_index()
cache = pd.read_csv(OUT / "forzantes_diarios_celdas.csv.gz", parse_dates=["fecha"])
filas = []
for (la, lo), g in grupos.groupby(["lat", "lon"]):
    r = pesos[(pesos.lat.round(1) == la) & (pesos.lon.round(1) == lo)]
    if r.empty:
        continue
    zmod = float(r.z_modelo_m.iloc[0])
    d0 = cache[(cache.lat.round(1) == la) & (cache.lon.round(1) == lo)].set_index("fecha").sort_index()
    for _, b in g.iterrows():
        d = d0.copy()
        for v, gz in GRAD.items():
            d[v] = d0[v] + gz * (b.z - zmod)
        d["td"] = np.minimum(d.td, (d.tmax + d.tmin) / 2)
        e = F.eto_desde_diario(d, la, b.z, F.presion_desde_z(b.z))
        filas.append({"lat": la, "lon": lo, "banda": int(b.banda), "n": b.n, "z": b.z, "eto_anual": e.eto.mean() * 365.25,
                      "t": e.t.mean(), "vpd": e.vpd.mean(), "z_modelo": zmod})
EB = pd.DataFrame(filas)

# ---------------------------------------------------------------- TerraClimate por celda (~4 km)
def tc_clim(v):
    da = xr.open_dataarray(RAIZ / f"datos/punto1/terraclimate/terraclimate_{v}_chicama_1981_2024.nc")
    return da.sel(time=slice("1998", "2024")).groupby("time.year").sum().mean("year")
tcv = {v: tc_clim(v) for v in ["aet", "pet", "ppt"]}
lat_tc, lon_tc = tcv["aet"].lat.values, tcv["aet"].lon.values
ii = np.abs(lat_px[:, None] - lat_tc[None, :]).argmin(axis=1)
jj = np.abs(lon_px[:, None] - lon_tc[None, :]).argmin(axis=1)
pt = pd.DataFrame({"i": ii, "j": jj, "z": z_px, "banda": banda_px})
TCc = pt.groupby(["i", "j"]).agg(n=("z", "size"), z=("z", "mean")).reset_index()
TCc = TCc[TCc.n >= 50]                                     # celdas con buena parte dentro de la cuenca
for v in tcv:
    TCc[v] = [float(tcv[v].values[a, b]) for a, b in zip(TCc.i, TCc.j)]
TCc["banda"] = np.digitize(TCc.z, BANDAS[1:-1])
TCc.round(3).to_csv(OUT / "gradiente_terraclimate_celdas.csv", index=False)

# ---------------------------------------------------------------- tabla por banda
tot = len(z_px)
B = pd.DataFrame({"banda": etq})
B["area_%"] = [100 * (banda_px == k).sum() / tot for k in range(len(etq))]
B["z_media"] = [z_px[banda_px == k].mean() if (banda_px == k).any() else np.nan for k in range(len(etq))]
wavg = lambda df, c: np.average(df[c], weights=df.n) if len(df) else np.nan
B["eto_era5land_corr"] = [wavg(EB[EB.banda == k], "eto_anual") for k in range(len(etq))]
B["t_media"] = [wavg(EB[EB.banda == k], "t") for k in range(len(etq))]
for v in ["pet", "ppt", "aet"]:
    B[f"{v}_tc"] = [wavg(TCc[TCc.banda == k], v) for k in range(len(etq))]
B["aet/pet_tc"] = B.aet_tc / B.pet_tc
B["aet/ppt_tc"] = B.aet_tc / B.ppt_tc
B["celdas_tc"] = [int((TCc.banda == k).sum()) for k in range(len(etq))]
B.round(3).to_csv(OUT / "gradiente_bandas.csv", index=False)
pd.set_option("display.width", 200)
print(B.round(2).to_string(index=False))
eto_cuenca_corr = np.average(EB.eto_anual, weights=EB.n)
print(f"\nETo de la cuenca reconstruida por bandas: {eto_cuenca_corr:.0f} mm/a (ERA5-Land por celdas: 1211; con elevacion del DEM: 1226)")
b_eto = np.polyfit(TCc.z, TCc.pet, 1)[0] * 1000; b_p = np.polyfit(TCc.z, TCc.ppt, 1)[0] * 1000
print(f"TerraClimate por celda: PET {b_eto:+.0f} mm/a por km; P {b_p:+.0f} mm/a por km; "
      f"ET maxima en la celda a {TCc.loc[TCc.aet.idxmax(), 'z']:.0f} m ({TCc.aet.max():.0f} mm/a)")

# ERA5-Land ET por celda (contraste a 9 km)
em = pd.read_csv(OUT / "et_real_mensual.csv", index_col=0, parse_dates=True)
ds = xr.open_dataset(RAIZ / "datos/punto1/era5land/mensual/era5land_mensual_1981_2025_chicama.nc")
sel = (ds.valid_time < np.datetime64("2022-09-01")) & (ds.valid_time >= np.datetime64("1998-01-01"))
dias = xr.DataArray(pd.DatetimeIndex(ds.valid_time.values).days_in_month.values, dims="valid_time")
eta = (-ds.e * 1000 * dias).sel(valid_time=sel).groupby("valid_time.year").sum().mean("year")
era_cel = [(r.z_modelo_m, float(eta.sel(latitude=r.lat, longitude=r.lon, method="nearest"))) for _, r in pesos.iterrows()]

# ---------------------------------------------------------------- figura
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.35, 1]})
a = ax[0]
a.axhspan(838, 1203, color="#a68cf0", alpha=.18, label="inversión, estación seca (Tarea 1)")
a.scatter(TCc.ppt, TCc.z, s=10, color=AZUL, alpha=.5, label="P · TerraClimate (celdas 4 km)")
a.scatter(TCc.pet, TCc.z, s=10, color=GRIS, alpha=.5, label="PET · TerraClimate")
a.scatter(TCc.aet, TCc.z, s=12, color=ROJO, alpha=.7, label="ET real · TerraClimate")
a.scatter([e for _, e in era_cel], [z for z, _ in era_cel], s=26, marker="s", facecolor="none", edgecolor=VERDE,
          label="ET real · ERA5-Land (celdas 9 km, elevación del modelo)")
a.plot(B.eto_era5land_corr, B.z_media, "k-o", lw=2, label="ETo FAO-56 por banda (ERA5-Land corregido)")
a.set_xlabel("mm/año (1998–2024)"); a.set_ylabel("elevación (m)")
a.legend(frameon=False, fontsize=7.6, loc="lower right")
a.set_title("(a) Lluvia, demanda y ET real con la altura", loc="left", fontsize=10.5)
a = ax[1]
y = np.arange(len(B))
a.barh(y, B["area_%"], color="#ddd", label="% del área")
b2 = a.twiny()
b2.plot(B["aet/pet_tc"], y, "o-", color=ROJO, label="ET/PET")
b2.plot(B["aet/ppt_tc"], y, "s--", color=AZUL, label="ET/P")
b2.set_xlim(0, 1.05); b2.set_xlabel("cociente (TerraClimate)")
a.set_yticks(y, [f"{e} m" for e in B.banda]); a.set_xlabel("% del área de la cuenca")
h1, l1 = a.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="lower right")
a.set_title("(b) Por banda: área y limitación por agua", loc="left", fontsize=10.5, pad=28)
fig.tight_layout(); fig.savefig(FIG / "fig_1_5a_gradiente.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_1_5a_gradiente.png'}")
