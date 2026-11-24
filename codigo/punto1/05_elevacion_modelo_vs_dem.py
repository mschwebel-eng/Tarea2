"""
05_elevacion_modelo_vs_dem.py - Apartado 1.1.a, paso 5: elevacion de ERA5-Land frente al DEM y efecto sobre ETo.

Entradas:
  datos/punto1/era5land/geo_era5land_global.nc  geopotencial invariante de ERA5-Land (ECMWF,
      https://confluence.ecmwf.int/download/attachments/140385202/geo_1279l4_0.1x0.1.grib2_v4_unpack.nc).
      Es global (52 MB): el script guarda el recorte de la cuenca en geopotencial_era5land_chicama.csv,
      que es el archivo que va en la entrega.
  datos/punto1/dem/Copernicus_DSM_COG_30_S0[89]_00_W079_00_DEM.tif  Copernicus GLO-90 (AWS Open Data).
  productos/punto1/forzantes_diarios_celdas.csv.gz (script 03); datos de CAMELS-PE (PISCOt).

Procedimiento:
  1. Elevacion de cada celda en el modelo (z/g) y en el DEM (celda completa y parte dentro de la cuenca).
  2. Gradientes verticales de Tmax, Tmin y Td estimados con las propias 30 celdas de ERA5-Land
     (regresion de su climatologia contra la elevacion del modelo).
  3. Correccion de primer orden: x' = x + (dx/dz) (z_DEM_cuenca - z_modelo) para Tmax, Tmin, Td,
     y nueva ETo. Mide cuanto pesa la elevacion mal representada; no es una "verdad".
  4. Contraste independiente: temperatura media de la cuenca de PISCOt (CAMELS-PE).
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import xarray as xr
import rasterio
from rasterio.merge import merge
from rasterio.features import geometry_mask
from shapely.geometry import shape
import json
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
G0 = 9.80665
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475"

pesos = pd.read_csv(PESOS)

# ------------------------------------------------------------ 1) elevacion del modelo
geo_csv = RAIZ / "datos/punto1/era5land/geopotencial_era5land_chicama.csv"
if not geo_csv.exists():
    ds = xr.open_dataset(RAIZ / "datos/punto1/era5land/geo_era5land_global.nc")
    z = ds.z.isel(time=0)
    vals = [float(z.sel(latitude=r.lat, longitude=360 + r.lon, method="nearest")) / G0 for _, r in pesos.iterrows()]
    pesos.assign(z_modelo_m=np.round(vals, 1))[["lat", "lon", "z_modelo_m"]].to_csv(geo_csv, index=False)
pesos = pesos.merge(pd.read_csv(geo_csv), on=["lat", "lon"])

# ------------------------------------------------------------ 2) DEM por celda y de la cuenca
fuentes = [rasterio.open(p) for p in sorted((RAIZ / "datos/punto1/dem").glob("Copernicus_DSM_COG_30_*_DEM.tif"))]
dem, tr = merge(fuentes)
dem = dem[0].astype(float)
gj = json.loads((RAIZ / "datos/punto1/tarea1/cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))
geoms = [shape(f["geometry"]) for f in gj["features"]]
dentro = geometry_mask(geoms, out_shape=dem.shape, transform=tr, invert=True)
filas_px = np.arange(dem.shape[0]); cols_px = np.arange(dem.shape[1])
lat_px = tr.f + (filas_px + 0.5) * tr.e
lon_px = tr.c + (cols_px + 0.5) * tr.a
z_cuenca_dem = dem[dentro]
print(f"DEM GLO-90 en la cuenca: media {z_cuenca_dem.mean():.0f} m, min {z_cuenca_dem.min():.0f}, max {z_cuenca_dem.max():.0f}"
      f"  (CAMELS-PE: media 2557, min 678, max 4317)")

zc, zcc = [], []
for _, r in pesos.iterrows():
    fi = (lat_px >= r.lat - 0.05) & (lat_px < r.lat + 0.05)
    co = (lon_px >= r.lon - 0.05) & (lon_px < r.lon + 0.05)
    bloque = dem[np.ix_(fi, co)]; m = dentro[np.ix_(fi, co)]
    zc.append(bloque.mean()); zcc.append(bloque[m].mean() if m.any() else np.nan)
pesos["z_dem_celda"] = zc
pesos["z_dem_en_cuenca"] = zcc
pesos["dz"] = pesos.z_dem_en_cuenca - pesos.z_modelo_m
w = pesos.area_en_cuenca_km2
zm_w = np.average(pesos.z_modelo_m, weights=w)
print(f"elevacion ponderada: modelo {zm_w:.0f} m ; DEM de la parte de cada celda dentro de la cuenca "
      f"{np.average(pesos.z_dem_en_cuenca, weights=w):.0f} m")
print(f"diferencia celda a celda (DEM en cuenca - modelo): media {pesos.dz.mean():+.0f} m, "
      f"de {pesos.dz.min():+.0f} a {pesos.dz.max():+.0f} m; |dz| medio {pesos.dz.abs().mean():.0f} m")

# ------------------------------------------------------------ 3) gradientes verticales desde las celdas
cache = pd.read_csv(OUT / "forzantes_diarios_celdas.csv.gz", parse_dates=["fecha"])
clim = cache.groupby(["lat", "lon"])[["tmax", "tmin", "td"]].mean().reset_index()
pesos = pesos.merge(clim, on=["lat", "lon"])
grad = {}
for v in ["tmax", "tmin", "td"]:
    b, a = np.polyfit(pesos.z_modelo_m, pesos[v], 1)
    r2 = np.corrcoef(pesos.z_modelo_m, pesos[v])[0, 1] ** 2
    grad[v] = b
    print(f"gradiente de {v}: {1000*b:+.2f} C/km (R2 = {r2:.2f})")

# ------------------------------------------------------------ 4) ETo con elevacion corregida
orig, corr = [], []
for _, r in pesos.iterrows():
    d = cache[(cache.lat.round(1) == round(r.lat, 1)) & (cache.lon.round(1) == round(r.lon, 1))].set_index("fecha").sort_index()
    e0_ = F.eto_desde_diario(d, r.lat, Z_CUENCA, P_CUENCA).eto
    dc = d.copy()
    for v in ["tmax", "tmin", "td"]:
        dc[v] = d[v] + grad[v] * r.dz
    dc["td"] = np.minimum(dc.td, (dc.tmax + dc.tmin) / 2)      # el rocio no puede superar a la temperatura
    e1 = F.eto_desde_diario(dc, r.lat, Z_CUENCA, P_CUENCA).eto
    orig.append(e0_ * r.area_en_cuenca_km2); corr.append(e1 * r.area_en_cuenca_km2)
W = w.sum()
eto0 = pd.concat(orig, axis=1).sum(axis=1) / W
eto1 = pd.concat(corr, axis=1).sum(axis=1) / W
m0 = eto0.resample("MS").sum(); m1 = eto1.resample("MS").sum()
c0 = m0.groupby(m0.index.month).mean(); c1 = m1.groupby(m1.index.month).mean()
a0 = eto0.resample("YS").sum().iloc[:-1].mean(); a1 = eto1.resample("YS").sum().iloc[:-1].mean()
print(f"ETo anual de la cuenca: modelo {a0:.0f} mm ; con elevacion del DEM {a1:.0f} mm ({100*(a1/a0-1):+.1f} %)")

# ------------------------------------------------------------ 5) contraste con PISCOt (CAMELS-PE)
cam = pd.read_csv(RAIZ / "datos/punto1/tarea1/PE_47E0A2A8.csv", parse_dates=["date"], index_col="date")
t_era = (cache.assign(t=(cache.tmax + cache.tmin) / 2).merge(pesos[["lat", "lon", "area_en_cuenca_km2"]], on=["lat", "lon"])
         .assign(tw=lambda x: x.t * x.area_en_cuenca_km2).groupby("fecha").tw.sum() / W)
comun = t_era.index.intersection(cam.tmean.dropna().index)
print(f"T media de la cuenca {comun.min().year}-{comun.max().year}: ERA5-Land {t_era[comun].mean():.2f} C ; "
      f"PISCOt (CAMELS-PE) {cam.tmean[comun].mean():.2f} C ; Tmax {cam.tmax[comun].mean():.1f} / Tmin {cam.tmin[comun].mean():.1f}")

pesos.round(3).to_csv(OUT / "elevacion_modelo_vs_dem_por_celda.csv", index=False)
pd.DataFrame({"eto_modelo": c0, "eto_z_dem": c1}).rename_axis("mes").round(2).to_csv(OUT / "eto_correccion_elevacion_por_mes.csv")

# ------------------------------------------------------------ figura
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(13, 4))
a = ax[0]
lim = [500, 4400]
a.plot(lim, lim, "k--", lw=.8)
a.scatter(pesos.z_modelo_m, pesos.z_dem_en_cuenca, s=15 + w / 1.5, color=NARANJA, edgecolor="k", lw=.4)
a.set_xlim(lim); a.set_ylim(lim); a.set_aspect("equal")
a.set_xlabel("elevación de la celda en ERA5-Land (m)"); a.set_ylabel("elevación media en el DEM (m)\n(parte de la celda dentro de la cuenca)")
a.set_title("(a) Modelo frente a DEM", loc="left", fontsize=10.5)
a = ax[1]
zs = np.sort(z_cuenca_dem)[::-1]
a.plot(np.linspace(0, 100, len(zs)), zs, color="k", label="DEM GLO-90 (90 m)")
o = pesos.sort_values("z_modelo_m", ascending=False)
a.step(100 * np.r_[0, o.area_en_cuenca_km2.cumsum() / W], np.r_[o.z_modelo_m.iloc[0], o.z_modelo_m], where="post",
       color=NARANJA, label="ERA5-Land (30 celdas)")
a.set_xlabel("% del área de la cuenca por encima"); a.set_ylabel("elevación (m)")
a.set_title("(b) Curva hipsométrica", loc="left", fontsize=10.5); a.legend(frameon=False, fontsize=8.5)
a = ax[2]
for v, col, lab in [("tmax", ROJO, "Tmáx"), ("tmin", AZUL, "Tmín"), ("td", GRIS, "T rocío")]:
    a.scatter(pesos.z_modelo_m, pesos[v], s=12, color=col)
    zz = np.array([1300, 3700]); a.plot(zz, pesos[v].mean() + grad[v] * (zz - pesos.z_modelo_m.mean()), color=col,
                                        label=f"{lab}: {1000*grad[v]:+.1f} °C/km")
a.set_xlabel("elevación de la celda en ERA5-Land (m)"); a.set_ylabel("°C (media 1981–2025)")
a.set_title("(c) Gradientes verticales en ERA5-Land", loc="left", fontsize=10.5); a.legend(frameon=False, fontsize=8.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1a_elevacion.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_1_1a_elevacion.png'}")
