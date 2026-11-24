"""
05b_microcuenca_dgm.py - Punto 2.4, problema A: delimitacion definitiva de la microcuenca con un modelo del TERRENO.

Por que: el script 05 encontro la zona con el DEM Copernicus GLO-30, que es un modelo de SUPERFICIE: en la llanura de Cottbus
las copas de los bosques (20-30 m) aparecen como "colinas" y falsean el cauce y su pendiente (escalon de ~15 m en el perfil).
Aqui se usa el DGM1 de Brandeburgo (LGB, laser aereo, 1 m, datos abiertos dl-de/by-2-0), 35 mosaicos de 1 km2 en UTM 33N
(EPSG:25833), promediados a 5 m. Procedimiento D8 (pysheds) igual que en la Tarea 1; el cierre se ajusta a la celda de mayor
area aportante (< 5 km2) a menos de 400 m del cierre propuesto en el script 05.

Salidas: datos/punto2/microcuenca/dgm5m_microcuenca.tif, microcuenca_dgm.geojson;
         productos/punto2/microcuenca_dgm_descripcion.csv, microcuenca_dgm_perfil.csv, figuras/fig_2_4_microcuenca.png
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge
from rasterio.enums import Resampling
from rasterio.features import shapes, geometry_mask
from rasterio.warp import transform as wtransform, transform_geom
from shapely.geometry import shape, mapping
if not hasattr(np, "in1d"):            # pysheds usa np.in1d, eliminado en numpy 2.x
    np.in1d = lambda a, b, **kw: np.isin(np.ravel(a), b, **kw)
from pysheds.grid import Grid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LightSource

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / "datos/punto2/microcuenca"
OUT = RAIZ / "productos/punto2"
FIG = OUT / "figuras"
RES = 5.0
WC_CLASES = {10: "bosque", 20: "arbustal", 30: "pastizal", 40: "cultivos", 50: "urbano", 60: "suelo desnudo", 80: "agua", 90: "humedal"}
desc05 = pd.read_csv(OUT / "microcuenca_descripcion.csv", index_col=0).iloc[:, 0]
x0, y0 = wtransform("EPSG:4326", "EPSG:25833", [desc05.lon_cierre], [desc05.lat_cierre]); x0, y0 = x0[0], y0[0]

# ---------------------------------------------------------------- mosaico a 5 m
dgm5 = DIR / "dgm5m_microcuenca.tif"
if not dgm5.exists():
    srcs = [rasterio.open(f"/vsizip/{z.as_posix()}/{z.stem}.tif") for z in sorted((DIR / "dgm1_brandenburg").glob("dgm_*.zip"))]
    z, tr = merge(srcs, res=RES, resampling=Resampling.average)
    prof = srcs[0].profile.copy()
    prof.update(height=z.shape[1], width=z.shape[2], transform=tr, count=1, dtype="float32", compress="deflate", tiled=False,
                nodata=-9999.0)
    zz = z[0].astype("float32"); zz[~np.isfinite(zz)] = -9999.0
    with rasterio.open(dgm5, "w", **prof) as dst:
        dst.write(zz, 1)
    for s in srcs:
        s.close()

grid = Grid.from_raster(str(dgm5))
dem = grid.read_raster(str(dgm5))
infl = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(dem)))
fdir = grid.flowdir(infl)
acc = grid.accumulation(fdir)
tr = grid.affine
A = np.asarray(acc) * RES * RES / 1e6                     # km2
Z = np.asarray(dem).astype(float); Z[Z < -1000] = np.nan

# cierre: celda de mayor area < 5 km2 a menos de 400 m del cierre del script 05
cols = np.arange(A.shape[1]); rows = np.arange(A.shape[0])
X = tr.c + (cols + 0.5) * tr.a; Y = tr.f + (rows + 0.5) * tr.e
dd = np.hypot(X[None, :] - x0, Y[:, None] - y0)
cand = np.where((dd <= 400) & (A <= 5.0), A, -1)
i0, j0 = np.unravel_index(np.argmax(cand), A.shape)
xo, yo = X[j0], Y[i0]
cat = grid.catchment(x=int(j0), y=int(i0), fdir=fdir, xytype="index")   # por indice: evita el ajuste a la celda vecina
m = np.asarray(cat).astype(bool)
area = m.sum() * RES * RES / 1e6
print(f"cierre ajustado a {np.hypot(xo-x0, yo-y0):.0f} m del propuesto; area aportante {A[i0, j0]:.3f} km2; poligono {area:.3f} km2")

# cauce principal: celda mas lejana (distancia de flujo) -> cierre
dist = np.asarray(grid.distance_to_outlet(x=int(j0), y=int(i0), fdir=fdir, xytype="index"))
il = np.unravel_index(np.nanargmax(np.where(m, dist, np.nan)), m.shape)
mov = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
F = np.asarray(fdir); perfil = []; i, j = il
for _ in range(200000):
    perfil.append((i, j, Z[i, j]))
    if (i, j) == (i0, j0):
        break
    d = mov.get(int(F[i, j]))
    if d is None:
        break
    i, j = i + d[0], j + d[1]
zp = np.array([p[2] for p in perfil])
sp = np.r_[0, np.cumsum([RES * np.hypot(perfil[k][0] - perfil[k - 1][0], perfil[k][1] - perfil[k - 1][1]) for k in range(1, len(perfil))])]
Lc = sp[-1]
z10, z85 = np.interp(0.90 * Lc, sp, zp), np.interp(0.15 * Lc, sp, zp)   # 10 % y 85 % de la longitud desde el cierre
S1085 = (z85 - z10) / (0.75 * Lc); Sg = (zp[0] - zp[-1]) / Lc
zc = Z[m]
# pendiente media de la cuenca (para formulas de flujo laminar/difuso)
gy, gx = np.gradient(np.where(np.isfinite(Z), Z, np.nanmean(Z)), RES)
Sm = np.nanmean(np.hypot(gx, gy)[m])

ps = [shape(g) for g, v in shapes(m.astype(np.uint8), mask=m, transform=tr) if v == 1]
poly = max(ps, key=lambda p: p.area)
poly_wgs = shape(transform_geom("EPSG:25833", "EPSG:4326", mapping(poly)))
(DIR / "microcuenca_dgm.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"nombre": "microcuenca Cottbus (DGM1 Brandeburgo)", "area_km2": float(area)},
     "geometry": mapping(poly_wgs)}]}), encoding="utf-8")

cob = {}
wc_rec = DIR / "worldcover_recorte.tif"
with rasterio.open(wc_rec) as src:
    wc = src.read(1); mk_ = geometry_mask([mapping(poly_wgs)], out_shape=wc.shape, transform=src.transform, invert=True)
    v, c = np.unique(wc[mk_], return_counts=True)
    cob = {WC_CLASES.get(int(a), str(a)): 100 * b / c.sum() for a, b in zip(v, c)}
lon_o, lat_o = wtransform("EPSG:25833", "EPSG:4326", [xo], [yo])
dpl = np.hypot((lon_o[0] - 14.3168) * 111.32 * np.cos(np.radians(51.78)), (lat_o[0] - 51.7759) * 111.32)
desc = {"lon_cierre": lon_o[0], "lat_cierre": lat_o[0], "utm33_x": xo, "utm33_y": yo, "dist_pluviometro_km": dpl,
        "area_km2": area, "perimetro_km": poly.length / 1000, "z_cierre_m": zp[-1], "z_max_m": np.nanmax(zc), "z_media_m": np.nanmean(zc),
        "relieve_m": np.nanmax(zc) - np.nanmin(zc), "L_cauce_principal_m": Lc, "S_10_85": S1085, "S_global": Sg,
        "pendiente_media_cuenca": Sm, **{f"cobertura_{k}_%": val for k, val in cob.items()}}
pd.Series(desc).round(6).to_csv(OUT / "microcuenca_dgm_descripcion.csv", header=["valor"])
pd.DataFrame({"distancia_m": sp, "z_m": zp}).round(3).to_csv(OUT / "microcuenca_dgm_perfil.csv", index=False)
print(pd.Series(desc).round(4).to_string())

# perfil del DSM Copernicus a lo largo del mismo cauce (para mostrar el efecto de los arboles)
with rasterio.open(DIR / "dem_recorte_cottbus.tif") as src:
    lon_p, lat_p = wtransform("EPSG:25833", "EPSG:4326", [tr.c + (p[1] + .5) * tr.a for p in perfil], [tr.f + (p[0] + .5) * tr.e for p in perfil])
    zdsm = np.array([v[0] for v in src.sample(zip(lon_p, lat_p))])

# ---------------------------------------------------------------- figura
plt.rcParams.update({"font.size": 10})
fig, ax = plt.subplots(1, 3, figsize=(15, 5.3), gridspec_kw={"width_ratios": [1.15, 1, 0.95]})
ext = [tr.c, tr.c + tr.a * Z.shape[1], tr.f + tr.e * Z.shape[0], tr.f]
ls = LightSource(azdeg=315, altdeg=35)
Zs = np.where(np.isfinite(Z), Z, np.nanmean(Z))
a = ax[0]
a.imshow(ls.hillshade(Zs, vert_exag=6, dx=RES, dy=RES), cmap="gray", extent=ext)
im = a.imshow(Z, cmap="terrain", extent=ext, alpha=.5, vmin=np.nanpercentile(Z, 1), vmax=np.nanpercentile(Z, 99))
a.imshow(np.where(A > 0.05, 1.0, np.nan), cmap=ListedColormap(["#1d4ed8"]), extent=ext, interpolation="nearest")
a.plot(*poly.exterior.xy, color="#c2452a", lw=2.2)
a.plot([tr.c + (p[1] + .5) * tr.a for p in perfil], [tr.f + (p[0] + .5) * tr.e for p in perfil], color="#b07a0c", lw=1.8, label="cauce principal")
a.plot(xo, yo, "o", color="#c2452a", mec="k", ms=9, label="cierre (alcantarilla)")
a.set_xlabel("UTM 33N, x (m)"); a.set_ylabel("UTM 33N, y (m)"); a.ticklabel_format(style="plain", useOffset=False)
a.legend(frameon=True, fontsize=8, loc="lower left"); fig.colorbar(im, ax=a, shrink=.7, label="elevación del terreno (m)")
a.set_title(f"(a) Microcuenca sobre el DGM1 (5 m): {area:.2f} km²", loc="left", fontsize=10.5)
a = ax[1]
a.plot(sp / 1000, zdsm, color="#5b6475", lw=1.2, label="Copernicus GLO-30 (superficie: copas y techos)")
a.plot(sp / 1000, zp, color="#b07a0c", lw=2, label="DGM1 Brandeburgo (terreno)")
a.set_xlabel("km desde la cabecera"); a.set_ylabel("elevación (m)"); a.legend(frameon=False, fontsize=8)
a.set_title(f"(b) Perfil del cauce: L = {Lc/1000:.2f} km, S₁₀₋₈₅ = {100*S1085:.2f} %", loc="left", fontsize=10.5)
for s_ in ["top", "right"]:
    a.spines[s_].set_visible(False)
a = ax[2]
orden = sorted(cob.items(), key=lambda kv: -kv[1])
a.barh([k for k, _ in orden], [val for _, val in orden], color="#5b6475"); a.invert_yaxis()
a.set_xlabel("% del área (ESA WorldCover 2021)")
for s_ in ["top", "right"]:
    a.spines[s_].set_visible(False)
a.set_title(f"(c) Coberturas · a {dpl:.1f} km del pluviómetro", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_4_microcuenca.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_2_4_microcuenca.png'}")
