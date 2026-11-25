"""
09_mapa_ubicacion.py - Mapa de la microcuenca del problema A: (a) la microcuenca sola, sobre el terreno DGM1, y (b) su ubicacion en Alemania.

Datos:
  * Microcuenca: datos/punto2/microcuenca/microcuenca_dgm.geojson y terreno dgm5m_microcuenca.tif (05b_microcuenca_dgm.py).
  * Limites de paises: Natural Earth 1:50 m, admin 0 (dominio publico). La primera corrida descarga la capa mundial y guarda solo
    Alemania y sus vecinos en datos/punto2/naturalearth_alemania_vecinos.geojson (lo que va en la entrega).
Salida: productos/punto2/figuras/fig_0_2_ubicacion_microcuenca.png
"""
from pathlib import Path
import json
import urllib.request

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform_geom
from shapely.geometry import shape
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / "datos/punto2/microcuenca"
FIG = RAIZ / "productos/punto2/figuras"
NE_LOCAL = RAIZ / "datos/punto2/naturalearth_alemania_vecinos.geojson"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
PAISES = ["Germany", "Poland", "Czechia", "Austria", "Switzerland", "France", "Belgium", "Netherlands", "Luxembourg", "Denmark"]
CIUDADES = {"Berlín": (13.405, 52.520), "Cottbus": (14.334, 51.756), "Hamburgo": (9.993, 53.551), "Múnich": (11.576, 48.137),
            "Colonia": (6.960, 50.938)}
EST = (14.3168, 51.7759)                                            # pluviometro DWD 00880

if not NE_LOCAL.exists():
    with urllib.request.urlopen(NE_URL, timeout=120) as r:
        mundo = json.load(r)
    sel = [ft for ft in mundo["features"] if ft["properties"]["ADMIN"] in PAISES]
    NE_LOCAL.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"ADMIN": ft["properties"]["ADMIN"]}, "geometry": ft["geometry"]} for ft in sel]}), encoding="utf-8")
paises = {ft["properties"]["ADMIN"]: shape(ft["geometry"]) for ft in json.loads(NE_LOCAL.read_text(encoding="utf-8"))["features"]}
gj = json.loads((DIR / "microcuenca_dgm.geojson").read_text(encoding="utf-8"))["features"][0]["geometry"]
mc_ll = shape(gj); mc_utm = shape(transform_geom("EPSG:4326", "EPSG:25833", gj))
desc = pd.read_csv(RAIZ / "productos/punto2/microcuenca_dgm_descripcion.csv", index_col=0).iloc[:, 0]

with rasterio.open(DIR / "dgm5m_microcuenca.tif") as s:
    D = s.read(1).astype(float); t = s.transform
D[D < -1000] = np.nan
ext = [t.c, t.c + t.a * D.shape[1], t.f + t.e * D.shape[0], t.f]
bx = mc_utm.bounds; pad = 250

fig, ax = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [1.1, 1]})
a = ax[0]
ls = LightSource(azdeg=315, altdeg=35)
a.imshow(ls.hillshade(np.where(np.isfinite(D), D, np.nanmean(D)), vert_exag=10, dx=5, dy=5), cmap="gray", extent=ext)
im = a.imshow(D, cmap="terrain", extent=ext, alpha=.55, vmin=56.5, vmax=59.5)
a.fill(*mc_utm.exterior.xy, color="#c2452a", alpha=.18)
a.plot(*mc_utm.exterior.xy, color="#c2452a", lw=2.2)
a.plot(desc.utm33_x, desc.utm33_y, "o", ms=9, color="#c2452a", mec="k")
a.annotate("cierre: la zanja cruza un camino", (desc.utm33_x, desc.utm33_y), xytext=(desc.utm33_x + 60, desc.utm33_y + 230), fontsize=10,
           arrowprops=dict(arrowstyle="-", color="k", lw=.8))
a.plot([bx[2] - 500, bx[2]], [bx[1] - pad / 2, bx[1] - pad / 2], "k-", lw=3)
a.text(bx[2] - 250, bx[1] - pad / 2 + 25, "500 m", ha="center", fontsize=9)
a.set_xlim(bx[0] - pad, bx[2] + pad); a.set_ylim(bx[1] - pad, bx[3] + pad); a.set_aspect("equal")
a.set_xticks([]); a.set_yticks([])
a.set_title(f"(a) Microcuenca del problema A: {desc.area_km2:.2f} km²".replace(".", ","), loc="left", fontsize=11)
fig.colorbar(im, ax=a, shrink=.7, label="elevación del terreno (m, DGM1 a 5 m)")
b = ax[1]
for nom, g in paises.items():
    for p in getattr(g, "geoms", [g]):
        b.fill(*p.exterior.xy, color="#e8e2d6" if nom == "Germany" else "#f2f2f2", ec="#9aa3ad", lw=.6)
for c, (x, y) in CIUDADES.items():
    if c != "Cottbus":
        b.plot(x, y, "ks", ms=4); b.text(x + 0.2, y, c, fontsize=9, va="center")
b.plot(*EST, "^", ms=10, color="k")
b.plot(mc_ll.centroid.x, mc_ll.centroid.y, "o", ms=8, color="#c2452a", mec="k")
b.annotate(f"Cottbus: pluviómetro DWD 00880 (▲)\ny microcuenca (●) a {desc.dist_pluviometro_km:.1f} km".replace(".", ",", 1),
           EST, xytext=(14.6, 50.3), fontsize=9.5, arrowprops=dict(arrowstyle="->", color="k"))
for nom, (x, y) in {"ALEMANIA": (10.2, 51.0), "POLONIA": (17.3, 52.3), "CHEQUIA": (15.3, 49.6), "FRANCIA": (6.0, 48.0), "AUSTRIA": (14.0, 47.6)}.items():
    b.text(x, y, nom, fontsize=12 if nom == "ALEMANIA" else 9, color="#5b6475", ha="center", weight="bold" if nom == "ALEMANIA" else None)
b.set_xlim(4.5, 18.5); b.set_ylim(46.8, 55.3); b.set_aspect(1 / np.cos(np.radians(51)))
b.set_xlabel("longitud (°)"); b.set_ylabel("latitud (°)"); b.set_title("(b) Ubicación en Alemania (Brandeburgo, llanura del Spree)", loc="left", fontsize=11)
b.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig_0_2_ubicacion_microcuenca.png", dpi=200); plt.close(fig)
print(f"-> {(FIG / 'fig_0_2_ubicacion_microcuenca.png').relative_to(RAIZ)}")
