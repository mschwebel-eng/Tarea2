"""
06_mapas_microcuenca.py - Mapas de la microcuenca del problema A (ubicacion, cobertura y terreno).

  (a) Ubicacion regional: relieve (Copernicus GLO-30, sombreado), pluviometro DWD 00880, centro de Cottbus, la microcuenca y
      escala de 5 km.
  (b) Cobertura ESA WorldCover 2021 (10 m) alrededor de la microcuenca.
  (c) Terreno DGM1 de Brandeburgo (5 m) con la red de zanjas (area aportante > 0.05 km2) y el cierre.
Las vias de OpenStreetMap no se incluyen: los servidores Overpass respondieron 502 en todos los intentos (limitacion declarada).
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform as wtransform, transform_geom
from shapely.geometry import shape
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.colors import ListedColormap, BoundaryNorm, LightSource
from matplotlib.patches import Patch

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / "datos/punto2/microcuenca"
OUT = RAIZ / "productos/punto2"
FIG = OUT / "figuras"
EST = (14.3168, 51.7759); CENTRO = (14.3343, 51.7563)        # pluviometro y centro de Cottbus (Altmarkt, aprox.)
desc = pd.read_csv(OUT / "microcuenca_dgm_descripcion.csv", index_col=0).iloc[:, 0]
poly = shape(json.loads((DIR / "microcuenca_dgm.geojson").read_text(encoding="utf-8"))["features"][0]["geometry"])
ls = LightSource(azdeg=315, altdeg=35)

fig, ax = plt.subplots(1, 3, figsize=(15.5, 5.4), gridspec_kw={"width_ratios": [1.3, 1, 1]})
# (a) ubicacion
with rasterio.open(DIR / "dem_recorte_cottbus.tif") as s:
    Z = s.read(1).astype(float); tr = s.transform
ext = [tr.c, tr.c + tr.a * Z.shape[1], tr.f + tr.e * Z.shape[0], tr.f]
a = ax[0]
a.imshow(ls.hillshade(Z, vert_exag=6), cmap="gray", extent=ext)
im = a.imshow(Z, cmap="terrain", extent=ext, alpha=.45, vmin=np.percentile(Z, 1), vmax=np.percentile(Z, 99))
a.fill(*poly.exterior.xy, color="#c2452a", alpha=.7, lw=1.5, ec="k")
a.plot(*EST, "k^", ms=10, label="pluviómetro DWD 00880 (Cottbus)")
a.plot(*CENTRO, "ks", ms=6, mfc="w", label="centro de Cottbus")
a.annotate("microcuenca\n0,44 km²", (poly.centroid.x, poly.centroid.y), xytext=(14.17, 51.825), fontsize=9, bbox=dict(fc="w", ec="none", alpha=.8),
           arrowprops=dict(arrowstyle="->", color="k"))
a.plot([14.40, 14.40 + 5 / (111.32 * np.cos(np.radians(51.7)))], [51.695, 51.695], "k-", lw=3)
a.text(14.40, 51.700, "5 km", fontsize=8)
a.set_xlabel("longitud (°)"); a.set_ylabel("latitud (°)"); a.legend(frameon=True, fontsize=8, loc="lower left")
fig.colorbar(im, ax=a, shrink=.65, label="elevación de la superficie (m, Copernicus GLO-30)")
a.set_title(f"(a) Ubicación: a {desc.dist_pluviometro_km:.1f} km del pluviómetro", loc="left", fontsize=10.5)
# (b) cobertura
with rasterio.open(DIR / "worldcover_recorte.tif") as s:
    b = poly.bounds; pad = 0.008
    win = rasterio.windows.from_bounds(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad, s.transform)
    W = s.read(1, window=win); twin = s.window_transform(win)
ext2 = [twin.c, twin.c + twin.a * W.shape[1], twin.f + twin.e * W.shape[0], twin.f]
clases = [10, 20, 30, 40, 50, 60, 80, 90]
colores = ["#006400", "#ffbb22", "#ffff4c", "#f096ff", "#fa0000", "#b4b4b4", "#0064c8", "#0096a0"]
nombres = ["bosque", "arbustal", "pastizal", "cultivos", "urbano", "suelo desnudo", "agua", "humedal"]
cm = ListedColormap(colores); nm = BoundaryNorm([c - 5 for c in clases] + [95], cm.N)
a = ax[1]
a.imshow(W, cmap=cm, norm=nm, extent=ext2, interpolation="nearest")
a.plot(*poly.exterior.xy, color="k", lw=2)
a.plot(desc.lon_cierre, desc.lat_cierre, "o", color="w", mec="k", ms=9)
pres = [k for k, c in enumerate(clases) if (W == c).any()]
a.legend(handles=[Patch(color=colores[k], label=nombres[k]) for k in pres], fontsize=8, loc="lower right", frameon=True)
a.set_xlabel("longitud (°)"); a.set_title("(b) Cobertura (ESA WorldCover 2021, 10 m)", loc="left", fontsize=10.5)
# (c) terreno DGM1
with rasterio.open(DIR / "dgm5m_microcuenca.tif") as s:
    D = s.read(1).astype(float); t3 = s.transform; D[D < -1000] = np.nan
from pysheds.grid import Grid  # solo para la red de zanjas (misma configuracion que 05b)
if not hasattr(np, "in1d"):
    np.in1d = lambda a_, b_, **kw: np.isin(np.ravel(a_), b_, **kw)
g = Grid.from_raster(str(DIR / "dgm5m_microcuenca.tif")); dm = g.read_raster(str(DIR / "dgm5m_microcuenca.tif"))
fd = g.flowdir(g.resolve_flats(g.fill_depressions(g.fill_pits(dm)))); A = np.asarray(g.accumulation(fd)) * 25 / 1e6
pu = shape(transform_geom("EPSG:4326", "EPSG:25833", json.loads((DIR / "microcuenca_dgm.geojson").read_text(encoding="utf-8"))["features"][0]["geometry"]))
bx = pu.bounds; pad = 400
ext3 = [t3.c, t3.c + t3.a * D.shape[1], t3.f + t3.e * D.shape[0], t3.f]
a = ax[2]
Ds = np.where(np.isfinite(D), D, np.nanmean(D))
a.imshow(ls.hillshade(Ds, vert_exag=10, dx=5, dy=5), cmap="gray", extent=ext3)
im3 = a.imshow(D, cmap="terrain", extent=ext3, alpha=.55, vmin=56.5, vmax=59.5)
a.imshow(np.where(A > 0.05, 1.0, np.nan), cmap=ListedColormap(["#1d4ed8"]), extent=ext3, interpolation="nearest")
a.plot(*pu.exterior.xy, color="#c2452a", lw=2.2)
a.plot(desc.utm33_x, desc.utm33_y, "o", color="#c2452a", mec="k", ms=9, label="cierre: zanja que sale a la red de drenaje")
a.set_xlim(bx[0] - pad, bx[2] + pad); a.set_ylim(bx[1] - pad, bx[3] + pad)
a.ticklabel_format(style="plain", useOffset=False); a.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4)); a.set_xlabel("UTM 33N, x (m)"); a.set_ylabel("UTM 33N, y (m)")
a.legend(frameon=True, fontsize=7.5, loc="lower left"); fig.colorbar(im3, ax=a, shrink=.65, label="elevación del terreno (m, DGM1)")
a.set_title("(c) Terreno real (DGM1) y red de zanjas", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_4_mapas_microcuenca.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_2_4_mapas_microcuenca.png'}")
