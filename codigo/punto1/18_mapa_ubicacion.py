"""
18_mapa_ubicacion.py - Mapa de la cuenca del rio Chicama hasta El Tambo: (a) la cuenca sola, con su relieve, y (b) su ubicacion en Peru.

Datos:
  * Cuenca: datos/punto1/tarea1/cuenca_el_tambo_glo30_wgs84.geojson (Tarea 1).
  * Relieve: Copernicus DEM GLO-90 (datos/punto1/dem/). El cierre (estacion El Tambo) se ubica en la celda mas baja de la cuenca.
  * Limites de paises: Natural Earth 1:50 m, admin 0 (dominio publico, naturalearthdata.com). La primera corrida descarga la
    capa mundial y guarda solo Peru y sus vecinos en datos/punto1/naturalearth_peru_vecinos.geojson (lo que va en la entrega).
Salida: productos/punto1/figuras/fig_0_1_ubicacion_cuenca.png
"""
from pathlib import Path
import json
import urllib.request

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from shapely.geometry import shape, mapping
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

RAIZ = Path(__file__).resolve().parents[2]
FIG = RAIZ / "productos/punto1/figuras"
NE_LOCAL = RAIZ / "datos/punto1/naturalearth_peru_vecinos.geojson"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
PAISES = ["Peru", "Ecuador", "Colombia", "Brazil", "Bolivia", "Chile"]
CIUDADES = {"Lima": (-77.043, -12.046), "Trujillo": (-79.029, -8.112), "Cajamarca": (-78.510, -7.164)}

if not NE_LOCAL.exists():
    with urllib.request.urlopen(NE_URL, timeout=120) as r:
        mundo = json.load(r)
    sel = [ft for ft in mundo["features"] if ft["properties"]["ADMIN"] in PAISES]
    NE_LOCAL.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"ADMIN": ft["properties"]["ADMIN"]}, "geometry": ft["geometry"]} for ft in sel]}), encoding="utf-8")
paises = {ft["properties"]["ADMIN"]: shape(ft["geometry"]) for ft in json.loads(NE_LOCAL.read_text(encoding="utf-8"))["features"]}
cuenca = shape(json.loads((RAIZ / "datos/punto1/tarea1/cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))["features"][0]["geometry"])

srcs = [rasterio.open(f) for f in sorted((RAIZ / "datos/punto1/dem").glob("*.tif"))]
Z, tr = merge(srcs, bounds=tuple(np.array(cuenca.bounds) + [-0.05, -0.05, 0.05, 0.05]))
Z = Z[0].astype(float)
prof = srcs[0].profile.copy(); prof.update(height=Z.shape[0], width=Z.shape[1], transform=tr, count=1, dtype="float32")
with rasterio.io.MemoryFile() as mf:
    with mf.open(**prof) as ds:
        ds.write(Z.astype("float32"), 1)
        Zc, _ = mask(ds, [mapping(cuenca)], nodata=np.nan, filled=True)
Zc = Zc[0]
i, j = np.unravel_index(np.nanargmin(Zc), Zc.shape)
cierre = (tr.c + (j + 0.5) * tr.a, tr.f + (i + 0.5) * tr.e)
ext = [tr.c, tr.c + tr.a * Z.shape[1], tr.f + tr.e * Z.shape[0], tr.f]
lat0 = cuenca.centroid.y

fig, ax = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [1.35, 1]})
a = ax[0]
ls = LightSource(azdeg=315, altdeg=40)
a.imshow(ls.hillshade(np.nan_to_num(Z, nan=np.nanmean(Z)), vert_exag=0.05, dx=90, dy=90), cmap="gray", extent=ext, alpha=.35)
im = a.imshow(Zc, cmap="terrain", extent=ext, vmin=0, vmax=4500)
for g in getattr(cuenca, "geoms", [cuenca]):
    a.plot(*g.exterior.xy, color="k", lw=1.4)
a.plot(*cierre, "o", ms=9, color="#c2452a", mec="k")
a.annotate(f"El Tambo (cierre, {np.nanmin(Zc):.0f} m)", cierre, xytext=(cierre[0] + 0.04, cierre[1] - 0.12), fontsize=10,
           arrowprops=dict(arrowstyle="-", color="k", lw=.8))
km = 20 / (111.32 * np.cos(np.radians(lat0)))
x0, y0 = cuenca.bounds[2] - km - 0.05, cuenca.bounds[1] + 0.02
a.plot([x0, x0 + km], [y0, y0], "k-", lw=3); a.text(x0 + km / 2, y0 + 0.02, "20 km", ha="center", fontsize=9)
a.set_aspect(1 / np.cos(np.radians(lat0))); a.set_xlabel("longitud (°)"); a.set_ylabel("latitud (°)")
a.set_title("(a) Cuenca del río Chicama hasta El Tambo (2 170 km², Tarea 1)", loc="left", fontsize=11)
fig.colorbar(im, ax=a, shrink=.7, label="elevación (m, Copernicus GLO-90)")
b = ax[1]
for nom, g in paises.items():
    for p in getattr(g, "geoms", [g]):
        b.fill(*p.exterior.xy, color="#e8e2d6" if nom == "Peru" else "#f2f2f2", ec="#9aa3ad", lw=.6)
for p in getattr(cuenca, "geoms", [cuenca]):
    b.fill(*p.exterior.xy, color="#c2452a", ec="#7a2a19", lw=.8)
for c, (x, y) in CIUDADES.items():
    b.plot(x, y, "ks", ms=4); b.text(x + 0.35, y, c, fontsize=9, va="center")
b.annotate("cuenca del Chicama", (cuenca.centroid.x, cuenca.centroid.y), xytext=(-78.0, -5.6), fontsize=10, color="#7a2a19",
           arrowprops=dict(arrowstyle="->", color="#7a2a19"))
b.text(-81.8, -12.5, "Océano\nPacífico", fontsize=10, style="italic", color="#4a6b82")
for nom, (x, y) in {"PERÚ": (-74.5, -9.5), "ECUADOR": (-78.6, -1.6), "BRASIL": (-70.3, -6.2), "BOLIVIA": (-67.6, -15.5), "COLOMBIA": (-73.5, 0.6)}.items():
    b.text(x, y, nom, fontsize=9 if nom != "PERÚ" else 12, color="#5b6475", ha="center", weight="bold" if nom == "PERÚ" else None)
b.set_xlim(-82.5, -67.5); b.set_ylim(-18.8, 1.2); b.set_aspect(1 / np.cos(np.radians(-9)))
b.set_xlabel("longitud (°)"); b.set_title("(b) Ubicación en Perú", loc="left", fontsize=11)
for a_ in ax:
    a_.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig_0_1_ubicacion_cuenca.png", dpi=200); plt.close(fig)
print(f"cierre (celda mas baja): {cierre[0]:.3f}, {cierre[1]:.3f}; -> {(FIG / 'fig_0_1_ubicacion_cuenca.png').relative_to(RAIZ)}")
