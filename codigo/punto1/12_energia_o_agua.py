"""
12_energia_o_agua.py - Apartado 1.3: que limita la evapotranspiracion, mes a mes y en el promedio multianual.

  1. Regimen mensual con ET/ETo y ET/P (productos de 1.2). Criterios explicitos (propuesta, a discutir):
       limitado por energia   ET/ETo >= 0.75   (la superficie da casi todo lo que pide la atmosfera)
       limitado por agua      ET/ETo <= 0.40
       transicion             entre ambos
     ET principal: TerraClimate (balance hidrico, ciclo coherente con la cuenca); ERA5-Land como contraste.
  2. Fraccion evaporativa (lambda E / Rn, ERA5-Land) frente a la humedad de la zona de raices (0-100 cm, capas 1-3
     ponderadas por espesor 7/21/72 cm) y ajuste segmentado para buscar el umbral (Dingman, 2015, sec. 6.8).
  3. Budyko con phi = ETo/P (ETo FAO-56 en lugar de ETp: se declara). Fu (1981): ET/P = 1 + phi - (1 + phi^w)^(1/w).
     omega con el punto multianual (balance 1998-2024); trayectoria anual con P - Q (en 1.2, Delta S anual pequeno salvo
     2000 y 2017, que se marcan).
  4. Elasticidad teorica 1 + phi F'(phi)/(1 - F(phi)) y empirica (estimador de mediana; Sankarasubramanian et al., 2001).
  5. Relacion complementaria: demanda frente a ET en anos secos y humedos (Bouchet, 1963).

Salidas: productos/punto1/regimen_*.csv, budyko_*.csv, figuras/fig_1_3_*.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import xarray as xr
from scipy.optimize import brentq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lectura_era5land import PESOS, RAIZ

OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"
U_E, U_A = 0.75, 0.40
MALO = ("2022-09-01", "2024-02-01")

M = pd.read_csv(OUT / "et_real_mensual.csv", index_col=0, parse_dates=True)
A = pd.read_csv(OUT / "et_real_anual_hidrologico.csv", index_col=0)
lp = pd.read_csv(OUT / "et_real_largo_plazo.csv", index_col=0).iloc[:, 0]


def clase(r):
    return "energía" if r >= U_E else ("agua" if r <= U_A else "transición")


# ---------------------------------------------------------------- 1) regimen mensual (1998-2024)
P = M.loc["1998":"2024"]
c = P.groupby(P.index.month).mean()
reg = pd.DataFrame({"P_L": c.P_L, "ETo": c.eto, "ET_TC": c.aet_terraclimate, "ET_ERA": c.et_era5land})
reg["ET/ETo_TC"] = reg.ET_TC / reg.ETo
reg["ET/ETo_ERA"] = reg.ET_ERA / reg.ETo
reg["ET/P_TC"] = reg.ET_TC / reg.P_L
reg["ET/P_ERA"] = reg.ET_ERA / reg.P_L
reg["clase_TC"] = reg["ET/ETo_TC"].map(clase)
reg["clase_ERA"] = reg["ET/ETo_ERA"].map(clase)
reg["temporada_T1"] = ["húmeda"] * 4 + ["seca"] * 5 + ["transición"] * 2 + ["húmeda"]
reg.index.name = "mes"
reg.round(3).to_csv(OUT / "regimen_mensual.csv")
print(reg.round(2).to_string())

# ---------------------------------------------------------------- 2) fraccion evaporativa vs humedad del suelo (ERA5-Land)
pesos = pd.read_csv(PESOS)
ds = xr.open_dataset(RAIZ / "datos/punto1/era5land/mensual/era5land_mensual_1981_2025_chicama.nc")
w = xr.zeros_like(ds.swvl1.isel(valid_time=0, drop=True))
for _, r in pesos.iterrows():
    i = int(np.abs(ds.latitude.values - r.lat).argmin()); j = int(np.abs(ds.longitude.values - r.lon).argmin())
    w[i, j] = r.area_en_cuenca_km2
prom = lambda v: ((ds[v] * w).sum(("latitude", "longitude")) / w.sum()).values
sm = (7 * prom("swvl1") + 21 * prom("swvl2") + 72 * prom("swvl3")) / 100
fe = pd.DataFrame({"sm_raiz": sm, "ef": (-prom("slhf")) / (prom("ssr") + prom("str"))}, index=pd.DatetimeIndex(ds.valid_time.values))
fe = fe[(fe.index < MALO[0]) | (fe.index > MALO[1])]
x, y = fe.sm_raiz.values, fe.ef.values
mejor = None
for th in np.linspace(np.percentile(x, 5), np.percentile(x, 95), 200):     # EF = a + b min(theta - th, 0)
    X = np.column_stack([np.ones_like(x), np.minimum(x - th, 0)])
    coef, res, *_ = np.linalg.lstsq(X, y, rcond=None)
    sse = ((X @ coef - y) ** 2).sum()
    if mejor is None or sse < mejor[0]:
        mejor = (sse, th, coef)
sse_seg, th_c, (a_c, b_c) = mejor
b_lin = np.polyfit(x, y, 1)
sse_lin = ((np.polyval(b_lin, x) - y) ** 2).sum()
n = len(x)
mejora = 1 - sse_seg / sse_lin
print(f"\nhumedad de raices ERA5-Land: {x.min():.3f}-{x.max():.3f} m3/m3; EF {y.min():.2f}-{y.max():.2f}")
print(f"ajuste segmentado: umbral theta* = {th_c:.3f} m3/m3, meseta EF = {a_c:.2f}, pendiente bajo el umbral {b_c:.1f}; "
      f"reduce la suma de errores {100*mejora:.0f} % frente a la recta")
fe.round(4).to_csv(OUT / "regimen_fraccion_evaporativa_humedad.csv")

# ---------------------------------------------------------------- 3) Budyko - Fu
fu = lambda phi, w_: 1 + phi - (1 + phi ** w_) ** (1 / w_)
budyko = lambda phi: np.sqrt(phi * np.tanh(1 / phi) * (1 - np.exp(-phi)))
phi0 = lp.ETo / lp.P_L
ep0 = lp.ET_PL / lp.P_L
omega = brentq(lambda w_: fu(phi0, w_) - ep0, 1.0001, 20)
print(f"\nBudyko: phi = ETo/P = {phi0:.2f}; ET/P = {ep0:.2f}; Budyko (1974) esperaria {budyko(phi0):.2f}; omega de Fu = {omega:.2f}")
A["phi"] = A.eto / A.P_L
A["ETP_balance"] = A.PmQ_L / A.P_L
A["fu_esperado"] = fu(A.phi, omega)
ok = ~A.index.isin([2000, 2017])
w_anual = [brentq(lambda w_: fu(p, w_) - e, 1.0001, 50) if 0 < e < min(1, p) and e > fu(p, 1.0001) else np.nan
           for p, e in zip(A.phi, A.ETP_balance)]
A["omega_anual"] = w_anual

# ---------------------------------------------------------------- 4) elasticidad
dF = lambda phi, w_: 1 - phi ** (w_ - 1) * (1 + phi ** w_) ** (1 / w_ - 1)
eps_teo = 1 + phi0 * dF(phi0, omega) / (1 - fu(phi0, omega))
aa = A[ok]
Pm, Qm = aa.P_L.mean(), aa.Q.mean()
eps_emp = np.median((aa.Q - Qm) / (aa.P_L - Pm) * Pm / Qm)
eps_emp_todos = np.median((A.Q - A.Q.mean()) / (A.P_L - A.P_L.mean()) * A.P_L.mean() / A.Q.mean())
b_ols = np.polyfit((aa.P_L - Pm) / Pm, (aa.Q - Qm) / Qm, 1)[0]
print(f"elasticidad del caudal a la lluvia: teorica (Fu) {eps_teo:.2f}; empirica (mediana) {eps_emp:.2f} "
      f"(con 2000 y 2017: {eps_emp_todos:.2f}); pendiente de regresion {b_ols:.2f}; CAMELS-PE stream_elas 1.57")

# ---------------------------------------------------------------- 5) relacion complementaria
terc = pd.qcut(A.P_L, 3, labels=["secos", "medios", "húmedos"])
comp = A.groupby(terc, observed=True)[["P_L", "eto", "PmQ_L", "aet_terraclimate"]].mean()
r_eto_p = A[["eto", "P_L"]].corr().iloc[0, 1]
r_eto_et = A[["eto", "aet_terraclimate"]].dropna().corr().iloc[0, 1]
# anomalias mensuales en la estacion seca (jun-sep): ETo frente a ET de TerraClimate
S = M.loc["1981":"2024"].copy()
S = S[S.index.month.isin([6, 7, 8, 9])]
an = S[["eto", "aet_terraclimate", "P_L"]].groupby(S.index.month).transform(lambda s: s - s.mean())
r_seca = an[["eto", "aet_terraclimate"]].dropna().corr().iloc[0, 1]
an_h = M.loc["1981":"2024"].copy(); an_h = an_h[an_h.index.month.isin([1, 2, 3, 4])]
anh = an_h[["eto", "aet_terraclimate"]].groupby(an_h.index.month).transform(lambda s: s - s.mean())
r_hum = anh.dropna().corr().iloc[0, 1]
print("\nrelacion complementaria (anos hidrologicos por terciles de P):"); print(comp.round(0).to_string())
print(f"r(ETo anual, P) = {r_eto_p:.2f}; r(ETo anual, ET TerraClimate) = {r_eto_et:.2f}; "
      f"anomalias mensuales ETo vs ET: estacion seca r = {r_seca:.2f}, humeda r = {r_hum:.2f}")

res = pd.Series({"phi": phi0, "ET_P": ep0, "budyko_1974": budyko(phi0), "omega_fu": omega, "eps_teorica": eps_teo,
                 "eps_empirica": eps_emp, "eps_empirica_con_2000_2017": eps_emp_todos, "theta_umbral": th_c, "ef_meseta": a_c,
                 "mejora_segmentado": mejora, "r_eto_P_anual": r_eto_p, "r_eto_et_anual": r_eto_et, "r_anom_seca": r_seca,
                 "r_anom_humeda": r_hum})
res.round(4).to_csv(OUT / "budyko_resumen.csv", header=["valor"])
A.round(3).to_csv(OUT / "budyko_anual.csv")
comp.round(1).to_csv(OUT / "regimen_complementaria_terciles.csv")

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
xm = np.arange(1, 13)
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})
a = ax[0]
a.axhspan(U_E, 1.25, color=NARANJA, alpha=.10); a.axhspan(0, U_A, color=AZUL, alpha=.08)
a.text(12.4, 1.0, "energía", color=NARANJA, fontsize=9, ha="right"); a.text(12.4, 0.2, "agua", color=AZUL, fontsize=9, ha="right")
a.plot(xm, reg["ET/ETo_TC"], "o-", color=ROJO, lw=2, label="ET/ETo · TerraClimate")
a.plot(xm, reg["ET/ETo_ERA"], "s--", color=VERDE, label="ET/ETo · ERA5-Land")
a.plot(xm, reg["ET/P_TC"].clip(upper=1.25), "o:", color=ROJO, alpha=.6, label="ET/P · TerraClimate (corte en 1,25)")
a.axhline(1, color="k", lw=.6)
for k0, k1, lab in [(0.5, 4.5, "húmeda (T1)"), (4.5, 9.5, "seca (T1)"), (9.5, 11.5, "transición")]:
    a.annotate("", xy=(k1, 1.2), xytext=(k0, 1.2), arrowprops=dict(arrowstyle="<->", color=GRIS))
    a.text((k0 + k1) / 2, 1.215, lab, ha="center", fontsize=8, color=GRIS)
a.set_ylim(0, 1.25); a.set_xticks(xm, [m[0] for m in MESES]); a.legend(frameon=False, fontsize=8, loc="center left")
a.set_title("(a) Régimen evaporativo mensual, 1998–2024", loc="left", fontsize=10.5)
a = ax[1]
sc = a.scatter(fe.sm_raiz, fe.ef, c=fe.index.month, cmap="twilight", s=12, alpha=.8)
xs = np.linspace(x.min(), x.max(), 100)
a.plot(xs, a_c + b_c * np.minimum(xs - th_c, 0), "k-", lw=2, label=f"segmentado: θ* = {th_c:.2f} m³/m³")
a.axvline(th_c, color="k", ls=":", lw=1)
fig.colorbar(sc, ax=a, label="mes")
a.set_xlabel("humedad de la zona de raíces, 0–100 cm (m³/m³)"); a.set_ylabel("fracción evaporativa λE/Rₙ")
a.legend(frameon=False, fontsize=8.5, loc="lower right")
a.set_title("(b) ERA5-Land: ¿desde qué humedad manda el agua?", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_3_regimen.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.15, 1]})
a = ax[0]
ph = np.linspace(0.05, 3, 300)
a.plot([0, 1], [0, 1], "k-", lw=1); a.plot([1, 3], [1, 1], "k-", lw=1)
a.plot(ph, budyko(ph), "k--", lw=1.2, label="Budyko (1974)")
for w_, ls in [(1.5, ":"), (2.6, "-.")]:
    a.plot(ph, fu(ph, w_), ls, color=GRIS, lw=1, label=f"Fu, ω = {w_}")
a.plot(ph, fu(ph, omega), "-", color=AZUL, lw=2, label=f"Fu ajustada, ω = {omega:.2f}")
s = a.scatter(A.phi[ok], A.ETP_balance[ok], c=A.index[ok], cmap="viridis", s=28, zorder=4, label="años hidrológicos (P − Q)")
a.scatter(A.phi[~ok], A.ETP_balance[~ok], facecolor="none", edgecolor=ROJO, s=60, zorder=4, label="2000 y 2017 (ΔS ≠ 0)")
a.scatter([phi0], [ep0], marker="*", s=260, color=ROJO, edgecolor="k", zorder=5, label="1998–2024")
fig.colorbar(s, ax=a, label="año")
a.set_xlim(0, 2.6); a.set_ylim(0, 1.05)
a.set_xlabel("índice de aridez φ = ETo / P"); a.set_ylabel("índice evaporativo ET / P")
a.legend(frameon=False, fontsize=7.6, loc="lower right")
a.set_title("(a) La cuenca en el espacio de Budyko", loc="left", fontsize=10.5)
a = ax[1]
a.scatter(A.P_L, A.eto, c=GRIS, s=24, label="ETo (demanda)")
a.scatter(A.P_L, A.aet_terraclimate, c=ROJO, marker="^", s=24, label="ET TerraClimate")
a.scatter(A.P_L, A.PmQ_L, c=AZUL, s=24, label="ET = P − Q")
for col, cc in [("eto", GRIS), ("aet_terraclimate", ROJO), ("PmQ_L", AZUL)]:
    d = A[["P_L", col]].dropna(); d = d[~d.index.isin([2000, 2017])]
    b1, b0 = np.polyfit(d.P_L, d[col], 1); xx = np.array([d.P_L.min(), d.P_L.max()])
    a.plot(xx, b0 + b1 * xx, "-", color=cc, lw=1)
a.set_xlabel("lluvia del año hidrológico P$_L$ (mm)"); a.set_ylabel("mm/año"); a.legend(frameon=False, fontsize=8.5)
a.set_title("(b) Años secos y húmedos: demanda frente a ET", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_3_budyko.png", dpi=200); plt.close(fig)
print(f"-> figuras en {FIG.relative_to(RAIZ)}")
