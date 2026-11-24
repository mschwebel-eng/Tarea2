"""
11_et_real.py - Apartado 1.2: evapotranspiracion real por varios caminos y su incertidumbre.

Caminos:
  (1) Balance hidrico de largo plazo ET = P - Q (1998-2024), con P_L (PISCOp v2.1 via CAMELS-PE) y con P_I (IMERG V07),
      y Q de la Tarea 1 (escorrentia R mensual con faltantes rellenados). Tambien P - Q por ano hidrologico (oct-sep:
      el caudal es minimo en sep-oct, cuando el almacenamiento llega a su punto mas bajo).
  (2) Propagacion del error: sigma_ET^2 = sigma_P^2 + sigma_Q^2. sigma_P a partir de la diferencia P_L - P_I;
      sigma_Q = 15 % de Q (rango tipico 10-20 % para caudales aforados; McMillan et al., 2012).
  (3) Techo energetico Rn/lambda con la radiacion neta REAL de ERA5-Land (ssr + str, superficie con su propio albedo),
      y fraccion evaporativa lambda ET / Rn.
  (4) Productos de ET real de familias distintas:
        ERA5-Land total evaporation (modelo de superficie HTESSEL; e < 0 por convencion de signo)
        TerraClimate aet (balance hidrico mensual de suelo tipo Thornthwaite-Mather; Abatzoglou et al., 2018)
  Las medias mensuales de variables acumuladas de ERA5-Land tienen un error entre 2022-09 y 2024-02 (aviso de ECMWF,
  confirmado en el paso 4 de 1.1.a): esos meses se excluyen de ERA5-Land.

Salidas: productos/punto1/et_real_*.csv, figuras/fig_1_2_*.png
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
from lectura_era5land import PESOS, RAIZ

LAMBDA = 2.45e6          # J kg-1
OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
T1 = RAIZ / "datos/punto1/tarea1"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"
SIGMA_Q_REL = 0.15
INI_AH = 10              # ano hidrologico: octubre - septiembre
MALO = ("2022-09-01", "2024-02-01")

# ---------------------------------------------------------------- series de la Tarea 1
t1 = pd.read_csv(T1 / "series_mensuales_camels_pe_1998_2025.csv", parse_dates=["fecha"], index_col="fecha")
pi = pd.read_csv(T1 / "imerg_cuenca_mensual.csv", parse_dates=["fecha"], index_col="fecha").P_I_mm_mes
S = pd.DataFrame({"P_L": t1.P_L_mm_mes, "P_I": pi, "Q": t1.R_mm_mes})

# ---------------------------------------------------------------- ERA5-Land mensual: ET, Rn real (promedio ponderado de las 30 celdas)
pesos = pd.read_csv(PESOS)
ds = xr.open_dataset(RAIZ / "datos/punto1/era5land/mensual/era5land_mensual_1981_2025_chicama.nc")
w = xr.DataArray(np.zeros((ds.sizes["latitude"], ds.sizes["longitude"])), coords={"latitude": ds.latitude, "longitude": ds.longitude},
                 dims=("latitude", "longitude"))
for _, r in pesos.iterrows():                    # celda mas cercana (las coordenadas son flotantes)
    i = int(np.abs(ds.latitude.values - r.lat).argmin()); j = int(np.abs(ds.longitude.values - r.lon).argmin())
    w[i, j] = r.area_en_cuenca_km2
prom = lambda v: (ds[v] * w).sum(("latitude", "longitude")) / w.sum()
idx = pd.DatetimeIndex(ds.valid_time.values)
dias = idx.days_in_month.values
E = pd.DataFrame({
    "et_era5land": -prom("e").values * 1000 * dias,                     # m d-1 (negativa) -> mm/mes
    "rn_era5land_mm": (prom("ssr") + prom("str")).values * dias / LAMBDA,   # J m-2 d-1 -> mm/mes equivalentes
    "rn_era5land_wm2": (prom("ssr") + prom("str")).values / 86400,
    "le_era5land_wm2": -prom("slhf").values / 86400, "h_era5land_wm2": -prom("sshf").values / 86400,
    "p_era5land": prom("tp").values * 1000 * dias,                      # lluvia propia del reanalisis (m d-1 -> mm/mes)
}, index=idx)
# control del error de ECMWF: la ET del tramo advertido frente a la climatologia del mismo mes
clim_e = E.et_era5land.groupby(E.index.month).transform(lambda s: s[(s.index < MALO[0]) | (s.index > MALO[1])].mean())
razon_e = (E.et_era5land / clim_e)
tramo = (E.index >= MALO[0]) & (E.index <= MALO[1])
print(f"ET ERA5-Land / climatologia del mes: fuera del tramo {razon_e[~tramo].mean():.2f}; en 2022-09..2024-02 {razon_e[tramo].mean():.2f}")
E.loc[tramo, ["et_era5land", "rn_era5land_mm", "rn_era5land_wm2", "le_era5land_wm2", "h_era5land_wm2", "p_era5land"]] = np.nan

# ---------------------------------------------------------------- TerraClimate aet (celdas con centro dentro de la cuenca)
gj = json.loads((T1 / "cuenca_el_tambo_glo30_wgs84.geojson").read_text(encoding="utf-8"))
geo = shape(gj["features"][0]["geometry"]) if len(gj["features"]) == 1 else \
    shape({"type": "GeometryCollection", "geometries": [f["geometry"] for f in gj["features"]]})
poly = prepared.prep(geo.buffer(0))
da = xr.open_dataarray(RAIZ / "datos/punto1/terraclimate/terraclimate_aet_chicama_1981_2024.nc")
mask = np.array([[poly.contains(Point(x, y)) for x in da.lon.values] for y in da.lat.values])
aet = da.where(xr.DataArray(mask, coords={"lat": da.lat, "lon": da.lon}, dims=("lat", "lon"))).mean(("lat", "lon")).to_series()
aet.index = pd.DatetimeIndex(aet.index).to_period("M").to_timestamp()
dp = xr.open_dataarray(RAIZ / "datos/punto1/terraclimate/terraclimate_ppt_chicama_1981_2024.nc")
ppt_tc = dp.where(xr.DataArray(mask, coords={"lat": dp.lat, "lon": dp.lon}, dims=("lat", "lon"))).mean(("lat", "lon")).to_series()
ppt_tc.index = pd.DatetimeIndex(ppt_tc.index).to_period("M").to_timestamp()
eto = pd.read_csv(OUT / "eto_mensual_cuenca.csv", index_col=0, parse_dates=True).eto

M = S.join(E, how="outer").join(aet.rename("aet_terraclimate"), how="outer").join(ppt_tc.rename("p_terraclimate"), how="outer") \
     .join(eto.rename("eto"), how="outer")
M.index.name = "mes"
M.round(3).to_csv(OUT / "et_real_mensual.csv")

# ---------------------------------------------------------------- (1) balance de largo plazo 1998-2024
P98 = M.loc["1998":"2024"]
n = 27
lp = {"P_L": P98.P_L.sum() / n, "P_I": P98.P_I.sum() / n, "Q": P98.Q.sum() / n}
lp["ET_PL"] = lp["P_L"] - lp["Q"]
lp["ET_PI"] = lp["P_I"] - lp["Q"]
# productos: media anual en los meses validos (climatologia mensual x 12 para no sesgar por los meses excluidos)
cm = M.loc["1998":"2024"].groupby(M.loc["1998":"2024"].index.month).mean()
lp["ET_era5land"] = cm.et_era5land.sum()
lp["ET_terraclimate"] = M.loc["1998":"2024"].aet_terraclimate.groupby(M.loc["1998":"2024"].index.month).mean().sum()
lp["P_era5land"] = cm.p_era5land.sum()
lp["P_terraclimate"] = M.loc["1998":"2024"].p_terraclimate.groupby(M.loc["1998":"2024"].index.month).mean().sum()
lp["ET/P_era5land_propia"] = lp["ET_era5land"] / lp["P_era5land"]
lp["ET/P_terraclimate_propia"] = lp["ET_terraclimate"] / lp["P_terraclimate"]
lp["Rn_lambda"] = cm.rn_era5land_mm.sum()
lp["ETo"] = cm.eto.sum()
lp["Rn_wm2"] = cm.rn_era5land_wm2.mean()

# ---------------------------------------------------------------- (2) propagacion del error
dP = lp["P_L"] - lp["P_I"]
sQ = SIGMA_Q_REL * lp["Q"]
casos = {"sigma_P = |P_L - P_I| / 2": abs(dP) / 2, "sigma_P = |P_L - P_I|": abs(dP)}
err = []
for k, sP in casos.items():
    s = np.hypot(sP, sQ)
    err.append({"caso": k, "sigma_P": sP, "sigma_Q": sQ, "sigma_ET": s, "fraccion_de_ET_%": 100 * s / lp["ET_PL"]})
err = pd.DataFrame(err)
err.round(1).to_csv(OUT / "et_real_propagacion_error.csv", index=False)

# ---------------------------------------------------------------- (3) techo energetico y fraccion evaporativa
fe = {k: lp[k] / lp["Rn_lambda"] for k in ["ET_PL", "ET_PI", "ET_era5land", "ET_terraclimate"]}
pd.Series({**lp, **{f"FE_{k}": v for k, v in fe.items()}}).round(3).to_csv(OUT / "et_real_largo_plazo.csv", header=["valor"])
print("\nbalance de largo plazo 1998-2024 (mm/a):")
for k, v in lp.items():
    print(f"   {k:16s} {v:8.1f}")
print("fraccion evaporativa lambda ET / Rn:", {k: round(v, 2) for k, v in fe.items()})
print(err.round(1).to_string(index=False))

# ---------------------------------------------------------------- por ano hidrologico (oct-sep)
ah = M.index.year + (M.index.month >= INI_AH)
A = M.groupby(ah).agg(P_L=("P_L", "sum"), P_I=("P_I", "sum"), Q=("Q", "sum"), n_Q=("Q", "count"), n_PI=("P_I", "count"),
                      et_era5land=("et_era5land", "sum"), n_era=("et_era5land", "count"),
                      aet_terraclimate=("aet_terraclimate", "sum"), n_tc=("aet_terraclimate", "count"),
                      rn_lambda=("rn_era5land_mm", "sum"), eto=("eto", "sum"))
A.index.name = "ano_hidrologico"
A = A[(A.n_Q == 12)]
A["PmQ_L"] = A.P_L - A.Q
A["PmQ_I"] = np.where(A.n_PI == 12, A.P_I - A.Q, np.nan)
for c, nc in [("et_era5land", "n_era"), ("aet_terraclimate", "n_tc"), ("rn_lambda", "n_era")]:
    A.loc[A[nc] < 12, c] = np.nan
A["dif_PmQ_ERA"] = A.PmQ_L - A.et_era5land
A["bandera"] = np.select([A.PmQ_L < 0, A.PmQ_L > A.rn_lambda, (A.PmQ_L - A.aet_terraclimate).abs() > 200],
                         ["P-Q negativo", "P-Q > Rn/lambda", "|P-Q - TerraClimate| > 200 mm"], "")
A.round(1).to_csv(OUT / "et_real_anual_hidrologico.csv")
print("\nP - Q por ano hidrologico (oct-sep):")
print(A[["P_L", "Q", "PmQ_L", "PmQ_I", "et_era5land", "aet_terraclimate", "rn_lambda", "bandera"]].round(0).to_string())
r_era = A[["PmQ_L", "et_era5land"]].dropna().corr().iloc[0, 1]
r_tc = A[["PmQ_L", "aet_terraclimate"]].dropna().corr().iloc[0, 1]
r_pq = A[["P_L", "PmQ_L"]].corr().iloc[0, 1]
print(f"correlacion anual P-Q con ERA5-Land {r_era:.2f}, con TerraClimate {r_tc:.2f}; P-Q con P {r_pq:.2f}")

clim = M.loc["1998":"2024"].groupby(M.loc["1998":"2024"].index.month).mean()
clim["PmQ_L"] = clim.P_L - clim.Q
clim.index.name = "mes"
clim.round(2).to_csv(OUT / "et_real_climatologia.csv")

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(13, 4.3), gridspec_kw={"width_ratios": [1, 1.5]})
a = ax[0]
nom = ["ETo\n(demanda)", "R$_n$/λ\n(techo)", "P$_L$ − Q", "P$_I$ − Q", "ERA5-\nLand", "Terra-\nClimate"]
val = [lp["ETo"], lp["Rn_lambda"], lp["ET_PL"], lp["ET_PI"], lp["ET_era5land"], lp["ET_terraclimate"]]
col = [GRIS, NARANJA, AZUL, AZUL, VERDE, ROJO]
b = a.bar(range(6), val, color=col, alpha=.85)
b[3].set_alpha(.4)
a.errorbar([2], [lp["ET_PL"]], yerr=[[err.sigma_ET[0]], [err.sigma_ET[0]]], fmt="none", ecolor="k", capsize=5, lw=1.2)
for i, v in enumerate(val):
    a.text(i, v + 25, f"{v:.0f}", ha="center", fontsize=8.5)
a.set_xticks(range(6), nom, fontsize=8.5); a.set_ylabel("mm/año")
a.set_title("(a) Largo plazo, 1998–2024", loc="left", fontsize=10.5)
a = ax[1]
x = A.index
a.plot(x, A.P_L, "-", color=AZUL, alpha=.35, lw=1, label="P$_L$")
a.plot(x, A.PmQ_L, "o-", color=AZUL, lw=1.6, label="P$_L$ − Q (balance)")
a.fill_between(x, A.PmQ_L - err.sigma_ET[0], A.PmQ_L + err.sigma_ET[0], color=AZUL, alpha=.10, label="± σ$_{ET}$")
a.plot(x, A.et_era5land, "s-", color=VERDE, ms=4, label="ERA5-Land")
a.plot(x, A.aet_terraclimate, "^-", color=ROJO, ms=4, label="TerraClimate")
a.plot(x, A.rn_lambda, "--", color=NARANJA, lw=1.2, label="R$_n$/λ")
neg = A[A.bandera != ""]
a.scatter(neg.index, neg.PmQ_L, s=90, facecolor="none", edgecolor="k", lw=1.2, zorder=5, label="año marcado")
a.axhline(0, color="k", lw=.6); a.set_ylim(-150, 2450)
a.set_ylabel("mm/año"); a.set_xlabel("año hidrológico (oct–sep, rotulado por el año en que termina)")
a.legend(frameon=False, fontsize=7.8, ncol=4, loc="upper left")
a.set_title("(b) Año a año", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_2_balance.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(13, 4), gridspec_kw={"width_ratios": [1.4, 1]})
a = ax[0]; xm = np.arange(1, 13)
a.plot(xm, clim.eto, "-", color=GRIS, lw=2, label="ETo (demanda)")
a.plot(xm, clim.rn_era5land_mm, "--", color=NARANJA, label="R$_n$/λ (techo)")
a.plot(xm, clim.et_era5land, "s-", color=VERDE, label="ET ERA5-Land")
a.plot(xm, clim.aet_terraclimate, "^-", color=ROJO, label="ET TerraClimate")
a.bar(xm, clim.P_L, color=AZUL, alpha=.15, label="P$_L$")
a.plot(xm, clim.PmQ_L, "o:", color=AZUL, label="P$_L$ − Q mensual (no es ET)")
a.axhline(0, color="k", lw=.6); a.set_xticks(xm, [m[0] for m in MESES]); a.set_ylabel("mm/mes")
a.legend(frameon=False, fontsize=8, ncol=2); a.set_title("(a) Ciclo anual, 1998–2024", loc="left", fontsize=10.5)
a = ax[1]
a.plot(razon_e.index, razon_e, color=GRIS, lw=.8)
a.axvspan(pd.Timestamp(MALO[0]), pd.Timestamp("2024-02-29"), color=ROJO, alpha=.15, label="tramo advertido por ECMWF (excluido)")
a.set_ylabel("ET ERA5-Land / media del mes"); a.legend(frameon=False, fontsize=8)
a.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(1985, 2030, 10)]), [str(y) for y in range(1985, 2030, 10)])
a.set_title("(b) Control del producto mensual de ERA5-Land", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_2_ciclo.png", dpi=200); plt.close(fig)
print(f"-> figuras en {FIG.relative_to(RAIZ)}")
