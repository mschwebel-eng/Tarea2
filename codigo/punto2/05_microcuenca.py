"""
05_microcuenca.py - Punto 2.4, problema A, paso 1: delimitacion de una microcuenca real (0.1-5 km2) cerca de Cottbus.

Datos:
  * DEM Copernicus GLO-30 (AWS Open Data), mosaico N51 E014. Es un modelo de SUPERFICIE (incluye edificios y arboles):
    en zonas urbanas y de bosque el trazado del flujo es menos fiable (limitacion declarada).
  * ESA WorldCover 2021 v200 (10 m), leido por ventana desde el COG publico (solo el recuadro de trabajo se guarda).
Procedimiento (pysheds): recorte de ~25 x 20 km alrededor de la estacion -> relleno de depresiones -> resolucion de planicies
-> direcciones D8 -> acumulacion. Candidatos de cierre: celdas de cauce con 0.5-4 km2 de area aportante cuya celda aguas
abajo ya drena > 20 km2 (es decir, donde un cauce pequeno entra a un canal o rio mayor), a menos de 15 km del pluviometro.
Se escoge el candidato con mayor desnivel (en una llanura, el mas definido) y se describen area, cauce principal (longitud y
pendiente 10-85 %) y coberturas.

Salidas: datos/punto2/microcuenca/dem_recorte_cottbus.tif, worldcover_recorte.tif, microcuenca.geojson;
         productos/punto2/microcuenca_*.csv, figuras/fig_2_4_microcuenca.png
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import shapes
from shapely.geometry import shape, mapping, Point
from shapely.ops import unary_union
if not hasattr(np, "in1d"):            # pysheds 0.4 usa np.in1d, eliminado en numpy 2.x; np.isin es equivalente
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
EST = (14.3168, 51.7759)                                     # pluviometro DWD 00880
BBOX = (14.15, 51.68, 14.50, 51.87)                          # oeste, sur, este, norte
WC_URL = "/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N51E012_Map.tif"
WC_CLASES = {10: "bosque", 20: "arbustal", 30: "pastizal", 40: "cultivos", 50: "urbano", 60: "suelo desnudo", 80: "agua", 90: "humedal"}

# ---------------------------------------------------------------- recortes
recorte = DIR / "dem_recorte_cottbus.tif"
if not recorte.exists():
    with rasterio.open(DIR / "Copernicus_DSM_COG_10_N51_00_E014_00_DEM.tif") as src:
        w = from_bounds(*BBOX, src.transform)
        z = src.read(1, window=w); tr = src.window_transform(w); prof = src.profile
    prof.update(height=z.shape[0], width=z.shape[1], transform=tr, compress="deflate", tiled=False)
    with rasterio.open(recorte, "w", **prof) as dst:
        dst.write(z, 1)
wc_rec = DIR / "worldcover_recorte.tif"
if not wc_rec.exists():
    try:
        with rasterio.Env(GDAL_HTTP_TIMEOUT=120):
            with rasterio.open(WC_URL) as src:
                w = from_bounds(*BBOX, src.transform)
                wc = src.read(1, window=w); tr = src.window_transform(w); prof = src.profile
        prof.update(height=wc.shape[0], width=wc.shape[1], transform=tr, compress="deflate", tiled=False, driver="GTiff")
        with rasterio.open(wc_rec, "w", **prof) as dst:
            dst.write(wc, 1)
    except Exception as e:
        print(f"FALLO la lectura de WorldCover: {e}")

# ---------------------------------------------------------------- D8
grid = Grid.from_raster(str(recorte))
dem = grid.read_raster(str(recorte))
infl = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(dem)))
fdir = grid.flowdir(infl)
acc = grid.accumulation(fdir)
tr = grid.affine
lat_c = np.array([tr.f + (i + 0.5) * tr.e for i in range(dem.shape[0])])
dy = abs(tr.e) * 111320.0
dx = tr.a * 111320.0 * np.cos(np.radians(lat_c))
area_celda = (dx * dy)[:, None] * np.ones(dem.shape)                # m2 por celda
A = np.asarray(acc) * area_celda / 1e6                               # km2 aportantes (aprox. con el area local)

# celda aguas abajo de cada celda (codificacion D8 de pysheds: N=64, NE=128, E=1, SE=2, S=4, SW=8, W=16, NW=32)
mov = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
F = np.asarray(fdir)
cand = []
filas, cols = np.where((A >= 0.5) & (A <= 4.0))
for i, j in zip(filas, cols):
    d = mov.get(int(F[i, j]))
    if d is None:
        continue
    i2, j2 = i + d[0], j + d[1]
    if not (0 <= i2 < A.shape[0] and 0 <= j2 < A.shape[1]) or A[i2, j2] < 20:
        continue
    x, y = tr * (j + 0.5, i + 0.5)
    dist = np.hypot((x - EST[0]) * 111.32 * np.cos(np.radians(y)), (y - EST[1]) * 111.32)
    if dist <= 15:
        cand.append({"i": i, "j": j, "lon": x, "lat": y, "area_km2": A[i, j], "dist_km": dist})
C = pd.DataFrame(cand)
print(f"candidatos (cauce de 0.5-4 km2 que entra a un cauce de > 20 km2, a < 15 km): {len(C)}")

from rasterio.features import geometry_mask
WC = rasterio.open(wc_rec) if wc_rec.exists() else None
WCA = WC.read(1) if WC else None


def describir(r):
    cat = grid.catchment(x=int(r.j), y=int(r.i), fdir=fdir, xytype="index")   # por indice: evita el ajuste a la celda vecina
    m = np.asarray(cat).astype(bool)
    zc = np.asarray(dem)[m]
    return m, zc


def poligono(m):
    """Poligono principal de la mascara (si hay piezas sueltas, la mayor)."""
    ps = [shape(g) for g, v in shapes(m.astype(np.uint8), mask=m, transform=tr) if v == 1]
    return max(ps, key=lambda p: p.area), len(ps)


def coberturas(poly):
    if WC is None:
        return {}
    mk_ = geometry_mask([mapping(poly)], out_shape=WCA.shape, transform=WC.transform, invert=True)
    vals, cnt = np.unique(WCA[mk_], return_counts=True)
    return {WC_CLASES.get(int(v), str(v)): 100 * c / cnt.sum() for v, c in zip(vals, cnt)}


res = []
for _, r in C.iterrows():
    m, zc = describir(r)
    ap = area_celda[m].sum() / 1e6
    p_, npz = poligono(m)
    cb = coberturas(p_) if 0.3 <= ap <= 6 else {}
    res.append({**r.to_dict(), "relieve_m": zc.max() - zc.min(), "z_cierre": float(np.asarray(dem)[int(r.i), int(r.j)]),
                "area_poligono_km2": ap, "piezas": npz, "bosque_%": cb.get("bosque", np.nan), "urbano_%": cb.get("urbano", np.nan)})
C = pd.DataFrame(res).sort_values("relieve_m", ascending=False)
C["consistente"] = (C.area_poligono_km2 / C.area_km2).between(0.7, 1.3)
C.round(4).to_csv(OUT / "microcuenca_candidatos.csv", index=False)
print(C[["lon", "lat", "area_km2", "area_poligono_km2", "consistente", "dist_km", "relieve_m", "bosque_%", "urbano_%"]].round(2).head(15).to_string(index=False))
# criterios: area 0.5-4 km2 bien delimitada y con poco bosque (el DSM mide copas); entre esas, la de mayor desnivel
ok = C[C.consistente & C.area_poligono_km2.between(0.5, 4.0) & (C["bosque_%"] <= 25)]
print(f"candidatos que cumplen los criterios: {len(ok)}")
sel = ok.iloc[0]

# ---------------------------------------------------------------- microcuenca escogida
m, zc = describir(sel)
D = np.full(dem.shape, np.nan)
# distance_to_outlet devuelve celdas en la extension recortada; se recalcula en la completa para robustez
dist_full = np.asarray(grid.distance_to_outlet(x=int(sel.j), y=int(sel.i), fdir=fdir, xytype="index"))
paso = np.sqrt(dx[:, None] * dy) * np.ones(dem.shape)               # longitud media de un paso de celda (m)
L_celdas = np.nanmax(np.where(m, dist_full, np.nan))
L = L_celdas * np.nanmean(paso[m])
ilej = np.unravel_index(np.nanargmax(np.where(m, dist_full, np.nan)), m.shape)
# perfil del cauce principal: del punto mas lejano al cierre siguiendo D8
perfil = []
i, j = ilej
for _ in range(100000):
    perfil.append((i, j, float(np.asarray(dem)[i, j])))
    if (i, j) == (int(sel.i), int(sel.j)):
        break
    d = mov.get(int(F[i, j]))
    if d is None:
        break
    i, j = i + d[0], j + d[1]
zp = np.array([p[2] for p in perfil])
sp = np.r_[0, np.cumsum([np.hypot((perfil[k][1] - perfil[k - 1][1]) * dx[perfil[k][0]], (perfil[k][0] - perfil[k - 1][0]) * dy)
                         for k in range(1, len(perfil))])]
Lc = sp[-1]
z10 = np.interp(0.10 * Lc, sp, zp[::-1][::-1]) if False else np.interp(Lc - 0.10 * Lc, sp, zp)
z85 = np.interp(Lc - 0.85 * Lc, sp, zp)
S1085 = (z85 - z10) / (0.75 * Lc)
Sglob = (zp[0] - zp[-1]) / Lc
# poligono
poly, piezas = poligono(m)
print(f"poligono: {piezas} pieza(s); se usa la mayor")
(DIR / "microcuenca.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"nombre": "microcuenca Cottbus", "area_km2": float(area_celda[m].sum() / 1e6)},
     "geometry": mapping(poly)}]}), encoding="utf-8")
# coberturas
cob = coberturas(poly)
desc = {"lon_cierre": sel.lon, "lat_cierre": sel.lat, "dist_pluviometro_km": sel.dist_km, "area_km2": area_celda[m].sum() / 1e6,
        "z_cierre_m": zp[-1], "z_max_m": zc.max(), "relieve_m": zc.max() - zc.min(), "z_media_m": zc.mean(),
        "L_cauce_principal_m": Lc, "S_10_85": S1085, "S_global": Sglob, **{f"cobertura_{k}_%": v for k, v in cob.items()}}
pd.Series(desc).round(5).to_csv(OUT / "microcuenca_descripcion.csv", header=["valor"])
print("\nmicrocuenca escogida:"); print(pd.Series(desc).round(4).to_string())
pd.DataFrame({"distancia_m": sp, "z_m": zp}).round(2).to_csv(OUT / "microcuenca_perfil_cauce.csv", index=False)

# ---------------------------------------------------------------- mapa
plt.rcParams.update({"font.size": 10})
fig, ax = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.25, 1, 0.9]})
Z = np.asarray(dem).astype(float)
ext = [tr.c, tr.c + tr.a * Z.shape[1], tr.f + tr.e * Z.shape[0], tr.f]
ls = LightSource(azdeg=315, altdeg=35)
a = ax[0]
a.imshow(ls.hillshade(Z, vert_exag=8), cmap="gray", extent=ext, alpha=.9)
im = a.imshow(Z, cmap="terrain", extent=ext, alpha=.45, vmin=np.percentile(Z, 1), vmax=np.percentile(Z, 99))
red = np.where(A > 20, 1.0, np.nan)
a.imshow(red, cmap=ListedColormap(["#1d4ed8"]), extent=ext, interpolation="nearest")
a.plot(*poly.exterior.xy, color="#c2452a", lw=2)
a.plot(*EST, "k^", ms=9, label="pluviómetro DWD 00880")
a.plot(sel.lon, sel.lat, "o", color="#c2452a", mec="k", ms=8, label="cierre de la microcuenca")
a.set_xlabel("longitud (°)"); a.set_ylabel("latitud (°)"); a.legend(frameon=True, fontsize=8, loc="upper left")
fig.colorbar(im, ax=a, shrink=.7, label="elevación (m)")
a.set_title("(a) Cottbus: relieve y cauces > 20 km²", loc="left", fontsize=10.5)
a = ax[1]
b = poly.bounds; pad = 0.01
w_ = (b[0] - pad, b[2] + pad, b[1] - pad, b[3] + pad)
a.imshow(ls.hillshade(Z, vert_exag=15), cmap="gray", extent=ext)
a.imshow(Z, cmap="terrain", extent=ext, alpha=.5, vmin=zc.min() - 5, vmax=zc.max() + 5)
red2 = np.where(A > 0.1, 1.0, np.nan)
a.imshow(red2, cmap=ListedColormap(["#1d4ed8"]), extent=ext, interpolation="nearest", alpha=.8)
a.plot(*poly.exterior.xy, color="#c2452a", lw=2.2)
xs = [tr.c + (p[1] + .5) * tr.a for p in perfil]; ys = [tr.f + (p[0] + .5) * tr.e for p in perfil]
a.plot(xs, ys, color="#b07a0c", lw=2, label="cauce principal")
a.plot(sel.lon, sel.lat, "o", color="#c2452a", mec="k", ms=9)
a.set_xlim(w_[0], w_[1]); a.set_ylim(w_[2], w_[3]); a.legend(frameon=True, fontsize=8)
a.set_title(f"(b) Microcuenca: {area_celda[m].sum()/1e6:.2f} km², relieve {zc.max()-zc.min():.0f} m", loc="left", fontsize=10.5)
a = ax[2]
if cob:
    orden = sorted(cob.items(), key=lambda kv: -kv[1])
    a.barh([k for k, _ in orden], [v for _, v in orden], color="#5b6475")
    a.set_xlabel("% del área (ESA WorldCover 2021)")
    a.invert_yaxis()
a2 = a.inset_axes([0.35, 0.08, 0.6, 0.38])
a2.plot(sp / 1000, zp, color="#b07a0c"); a2.set_xlabel("km desde la cabecera", fontsize=8); a2.set_ylabel("z (m)", fontsize=8)
a2.tick_params(labelsize=7); a2.set_title(f"cauce: L = {Lc/1000:.2f} km, S₁₀₋₈₅ = {100*S1085:.2f} %", fontsize=8)
a.set_title("(c) Coberturas y perfil del cauce", loc="left", fontsize=10.5)
for s_ in ["top", "right"]:
    a.spines[s_].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig_2_4_microcuenca.png", dpi=200); plt.close(fig)
if WC is not None:
    WC.close()
print(f"-> {FIG.relative_to(RAIZ) / 'fig_2_4_microcuenca.png'}")
