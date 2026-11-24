"""
16_niebla_nubosidad.py - Apartado 1.5.c: niebla y nubosidad persistente, y la posibilidad de una entrada de agua oculta.

Pregunta de la guia: si P - Q resulta menor que la ET de los productos, ¿lo explica una entrada que los pluviometros no
registran (niebla, precipitacion horizontal)?
  1. Brecha: ET de los productos (1.2) - (P_L - Q).
  2. Donde hay nubes bajas: nubosidad baja de ERA5 (0.25 grados) en un transecto mar-costa-cuenca a 7.5-7.75 S, por estacion,
     y su ciclo dia-noche junto con la altura de la capa limite (estabilidad).
  3. Donde la capa de nubes toca el terreno: los estratocumulos estan bajo la inversion; la franja de la cuenca entre la base y
     el tope de la inversion (radiosondeos de Trujillo, Tarea 1) es la que puede recibir niebla costera.
  4. Cuanta niebla haria falta para cerrar la brecha en esa franja, comparado con el rango de las notas (#s47).

Salidas: productos/punto1/niebla_*.csv, figuras/fig_1_5c_niebla.png
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
from lectura_era5land import PESOS, RAIZ

OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
NUB = RAIZ / "datos/punto1/era5_nubes"
AZUL, ROJO, NARANJA, GRIS, VERDE, VIOLETA = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f", "#6a4fb3"
# Inversion en los radiosondeos de Trujillo (Tarea 1, Fig. 8-9): base y tope medianos
INV = {"seca (may-sep)": (838, 1203), "húmeda (dic-abr)": (329, 716)}
SECA, HUMEDA = [5, 6, 7, 8, 9], [12, 1, 2, 3, 4]

# ---------------------------------------------------------------- 1) brecha del balance
lp = pd.read_csv(OUT / "et_real_largo_plazo.csv", index_col=0).iloc[:, 0]
brecha = {"TerraClimate": lp.ET_terraclimate - lp.ET_PL, "ERA5-Land": lp.ET_era5land - lp.ET_PL}
print(f"P_L - Q = {lp.ET_PL:.0f} mm/a; brecha frente a TerraClimate {brecha['TerraClimate']:+.0f} mm/a, frente a ERA5-Land "
      f"{brecha['ERA5-Land']:+.0f} mm/a")

# ---------------------------------------------------------------- 2) DEM: franja de la inversion
src = [rasterio.open(p) for p in sorted(glob.glob(str(RAIZ / "datos/punto1/dem/Copernicus_DSM_COG_30_*_DEM.tif")))]
dem, tr = merge(src); dem = dem[0].astype(float)
gj = json.loads((RAIZ / "datos/punto1/tarea1/cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))
z = dem[geometry_mask([shape(f["geometry"]) for f in gj["features"]], out_shape=dem.shape, transform=tr, invert=True)]
franja = {k: 100 * ((z >= b) & (z <= t)).mean() for k, (b, t) in INV.items()}
bajo = {k: 100 * (z < t).mean() for k, (b, t) in INV.items()}
print("area de la cuenca dentro de la capa de inversion:", {k: round(v, 1) for k, v in franja.items()},
      "| bajo el tope:", {k: round(v, 1) for k, v in bajo.items()})

# ---------------------------------------------------------------- 3) nubosidad ERA5
def abrir(nombre):
    ds = xr.open_dataset(NUB / nombre)
    tdim = "valid_time" if "valid_time" in ds.dims else "time"
    return ds.rename({tdim: "t"})


m = abrir("era5_nubes_mensual_1981_2024.nc")
mes = m["t"].dt.month
lcc_s = m.lcc.where(mes.isin(SECA), drop=True).mean("t"); lcc_h = m.lcc.where(mes.isin(HUMEDA), drop=True).mean("t")
blh_s = m.blh.where(mes.isin(SECA), drop=True).mean("t"); blh_h = m.blh.where(mes.isin(HUMEDA), drop=True).mean("t")
tcc_s = m.tcc.where(mes.isin(SECA), drop=True).mean("t"); tcc_h = m.tcc.where(mes.isin(HUMEDA), drop=True).mean("t")
# transecto a la latitud de la cuenca (promedio 7.5-7.75 S)
tra = lambda da: da.sel(latitude=slice(-7.5, -7.75)).mean("latitude")
T = pd.DataFrame({"lon": m.longitude.values, "lcc_seca": tra(lcc_s).values, "lcc_humeda": tra(lcc_h).values,
                  "tcc_seca": tra(tcc_s).values, "tcc_humeda": tra(tcc_h).values,
                  "blh_seca": tra(blh_s).values, "blh_humeda": tra(blh_h).values})
# relieve medio del DEM en cada columna de 0.25 grados del transecto
lon_px = tr.c + (np.arange(dem.shape[1]) + 0.5) * tr.a
lat_px = tr.f + (np.arange(dem.shape[0]) + 0.5) * tr.e
fil = (lat_px <= -7.5) & (lat_px >= -7.75)
T["z_dem"] = [np.nanmean(np.where(dem[np.ix_(fil, np.abs(lon_px - lo) <= 0.125)] > -100,
                                  dem[np.ix_(fil, np.abs(lon_px - lo) <= 0.125)], np.nan))
              if (np.abs(lon_px - lo) <= 0.125).any() else np.nan for lo in T.lon]
T.round(3).to_csv(OUT / "niebla_transecto.csv", index=False)

# nubosidad baja sobre las celdas de la cuenca, por mes
pesos = pd.read_csv(PESOS)
cel = [(float(m.latitude.sel(latitude=r.lat, method="nearest")), float(m.longitude.sel(longitude=r.lon, method="nearest")))
       for _, r in pesos.iterrows()]
cel = sorted(set(cel))
lcc_c = xr.concat([m.lcc.sel(latitude=a, longitude=b) for a, b in cel], dim="c").mean("c").to_series()
lcc_c.index = pd.DatetimeIndex(lcc_c.index)
clim_lcc = lcc_c.groupby(lcc_c.index.month).mean()
mar = m.lcc.sel(latitude=slice(-7.0, -8.0), longitude=slice(-80.0, -79.5)).mean(("latitude", "longitude")).to_series()
mar.index = pd.DatetimeIndex(mar.index)
clim_mar = mar.groupby(mar.index.month).mean()

# ciclo dia-noche (por hora del dia), costa/mar frente a la cuenca
h = abrir("era5_nubes_por_hora_2005_2024.nc")
hora_local = (h["t"].dt.hour - 5) % 24
def ciclo(da, sel_mes):
    d = da.where(h["t"].dt.month.isin(sel_mes), drop=True)
    return d.groupby(hora_local.where(h["t"].dt.month.isin(sel_mes), drop=True)).mean()
reg_mar = dict(latitude=slice(-7.0, -8.0), longitude=slice(-80.0, -79.5))
reg_cue = dict(latitude=slice(-7.375, -8.0), longitude=slice(-78.75, -78.25))
C = {}
for nom, reg in [("mar", reg_mar), ("cuenca", reg_cue)]:
    for v in ["lcc", "blh"]:
        for est, sm in [("seca", SECA), ("humeda", HUMEDA)]:
            s = ciclo(h[v].sel(**reg).mean(("latitude", "longitude")), sm).to_series()
            C[f"{v}_{nom}_{est}"] = s
C = pd.DataFrame(C); C.index.name = "hora_local"
C.round(3).to_csv(OUT / "niebla_ciclo_diurno.csv")
print("\nnubosidad baja media (fraccion): mar seca {:.2f} | cuenca seca {:.2f} | cuenca humeda {:.2f}".format(
    clim_mar.loc[SECA].mean(), clim_lcc.loc[SECA].mean(), clim_lcc.loc[HUMEDA].mean()))
print("capa limite (m): mar, seca, dia/noche {:.0f}/{:.0f} | cuenca, seca, dia/noche {:.0f}/{:.0f}".format(
    C.blh_mar_seca.loc[[12, 13, 14, 15]].mean() if 12 in C.index else C.blh_mar_seca.max(), C.blh_mar_seca.min(),
    C.blh_cuenca_seca.max(), C.blh_cuenca_seca.min()))

# ---------------------------------------------------------------- 4) niebla necesaria
f_seca = franja["seca (may-sep)"] / 100
necesaria = brecha["TerraClimate"] / f_seca if f_seca > 0 else np.nan
pd.Series({"P_menos_Q": lp.ET_PL, "brecha_TerraClimate": brecha["TerraClimate"], "brecha_ERA5Land": brecha["ERA5-Land"],
           "area_franja_inversion_seca_%": franja["seca (may-sep)"], "area_franja_inversion_humeda_%": franja["húmeda (dic-abr)"],
           "niebla_necesaria_en_franja_mm_a": necesaria, "brecha_%_de_P": 100 * brecha["TerraClimate"] / lp.P_L,
           "lcc_cuenca_seca": clim_lcc.loc[SECA].mean(), "lcc_cuenca_humeda": clim_lcc.loc[HUMEDA].mean(),
           "lcc_mar_seca": clim_mar.loc[SECA].mean()}).round(3).to_csv(OUT / "niebla_resumen.csv", header=["valor"])
print(f"para cerrar la brecha con niebla solo en la franja de la inversion ({franja['seca (may-sep)']:.1f} % del area) harian falta "
      f"{necesaria:.0f} mm/a de agua de niebla alli; la brecha es el {100*brecha['TerraClimate']/lp.P_L:.0f} % de P_L")

# ---------------------------------------------------------------- figura
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(14, 4.2), gridspec_kw={"width_ratios": [1.35, 1, 1]})
a = ax[0]
ok_dem = T.z_dem.notna() & (T.lon > -79.05) & (T.lon < -77.95)      # los mosaicos del DEM cubren 79-78 O
a.fill_between(T.lon[ok_dem], 0, T.z_dem[ok_dem], color="#c9b79c", alpha=.8, label="relieve (DEM, solo 79–78° O)")
a.axhspan(*INV["seca (may-sep)"], color=VIOLETA, alpha=.15, label="inversión, estación seca")
a.set_ylabel("elevación (m)"); a.set_ylim(0, 4500); a.set_xlabel("longitud (°)")
b = a.twinx()
b.plot(T.lon, T.lcc_seca, "o-", color=GRIS, label="nubes bajas, estación seca")
b.plot(T.lon, T.lcc_humeda, "s--", color=AZUL, label="nubes bajas, estación húmeda")
b.set_ylim(0, 1); b.set_ylabel("fracción de nubosidad baja (ERA5)"); b.spines["right"].set_visible(True)
a.axvspan(-78.75, -78.25, color=ROJO, alpha=.06)
a.text(-78.5, 4300, "cuenca", ha="center", color=ROJO, fontsize=9)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = b.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, frameon=False, fontsize=7.5, loc="upper left")
a.set_title("(a) Del mar a la cordillera: nubes bajas e inversión", loc="left", fontsize=10.5)
a = ax[1]
xm = np.arange(1, 13)
a.plot(xm, clim_mar, "o-", color=GRIS, label="mar frente a la costa")
a.plot(xm, clim_lcc, "s-", color=ROJO, label="celdas de la cuenca")
a.set_xticks(xm, list("EFMAMJJASOND")); a.set_ylim(0, 1); a.set_ylabel("fracción de nubosidad baja")
a.legend(frameon=False, fontsize=8.5); a.set_title("(b) Ciclo anual de las nubes bajas", loc="left", fontsize=10.5)
a = ax[2]
for nom, c in [("mar", GRIS), ("cuenca", ROJO)]:
    a.plot(C.index, C[f"blh_{nom}_seca"], "o-", color=c, label=f"{nom}, estación seca")
    a.plot(C.index, C[f"blh_{nom}_humeda"], "s--", color=c, alpha=.6, label=f"{nom}, estación húmeda")
a.set_xticks(range(0, 24, 3)); a.set_xlabel("hora local"); a.set_ylabel("altura de la capa límite (m)")
a.legend(frameon=False, fontsize=8); a.set_title("(c) Capa límite: día inestable, noche estable", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_5c_niebla.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_1_5c_niebla.png'}")
