"""
10_explicar_diferencias.py - Apartado 1.1.d: explicacion fisica de las diferencias entre metodos.

  1. Terminos de FAO-56: fraccion radiativa y aerodinamica mes a mes, y coeficiente implicito
     alfa* = ETo / E_eq, con E_eq = Delta/(Delta+gamma) (Rn - G)/lambda (notas #s33).
  2. Experimento de sensibilidad (guia 1.1.d): se perturba un forzante a la vez y se recalculan TODOS los metodos:
       T +1 y +2 C con ea constante (el deficit crece)  y  con HR constante (ea crece con T)
       u2 +10 %,  Rs -10 %,  ea +10 %
     En Thornthwaite se mantienen fijos el indice de calor I y el exponente a de la climatologia base.
  3. Verificacion de unidades del recuadro de la guia (146 W m-2 de calor latente).

Salidas: productos/punto1/terminos_fao56_por_mes.csv, sensibilidad_*.csv, figuras/fig_1_1d_*.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fao56 as F
import metodos_etp as M
from lectura_era5land import PESOS, RAIZ

Z_CUENCA = 2557.0
P_CUENCA = F.presion_desde_z(Z_CUENCA)
OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
NOMBRES = {"fao56": "FAO-56 PM", "thornthwaite": "Thornthwaite", "hamon": "Hamon", "hargreaves": "Hargreaves",
           "oudin": "Oudin", "priestley_taylor": "Priestley–Taylor", "makkink": "Makkink*", "dalton": "Dalton (FAO-24)",
           "meyer": "Meyer", "linacre": "Linacre*"}
ESCEN = {"base": "base", "T+1_ea": "T +1 °C\n(eₐ cte)", "T+1_hr": "T +1 °C\n(HR cte)", "T+2_ea": "T +2 °C\n(eₐ cte)",
         "T+2_hr": "T +2 °C\n(HR cte)", "u2+10": "u₂ +10 %", "rs-10": "Rₛ −10 %", "ea+10": "eₐ +10 %"}
AZUL, ROJO, NARANJA, GRIS = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475"


def td_desde_ea(ea):
    """Inversa de la ec. 11 de FAO-56: punto de rocio (C) que corresponde a ea (kPa)."""
    x = np.log(ea / 0.6108)
    return 237.3 * x / (17.27 - x)


def perturbar(d, esc):
    """Devuelve una copia de los forzantes diarios con un forzante perturbado."""
    d = d.copy()
    if esc.startswith("T+"):
        dT = float(esc[2]); es0 = F.es_diaria(d.tmax, d.tmin); ea0 = F.e0(d.td)
        d["tmax"] += dT; d["tmin"] += dT
        if esc.endswith("hr"):                               # HR constante: ea escala con es
            d["td"] = td_desde_ea(ea0 * F.es_diaria(d.tmax, d.tmin) / es0)
    elif esc == "u2+10":
        d["u10"] *= 1.10
    elif esc == "rs-10":
        d["rs"] *= 0.90
    elif esc == "ea+10":
        d["td"] = td_desde_ea(F.e0(d.td) * 1.10)
    return d


def metodos_mensuales(d, lat, z_mod, I, a):
    d = F.eto_desde_diario(d, lat, Z_CUENCA, P_CUENCA)
    j = d.index.day_of_year
    eeq = F.delta(d.t) / (F.delta(d.t) + F.gamma(P_CUENCA)) * d.rn / F.LAMBDA
    m = pd.DataFrame({
        "fao56": d.eto, "eto_rad": d.eto_rad, "eto_aero": d.eto_aero, "eeq": eeq,
        "hamon": M.hamon(d.t, lat, j), "hargreaves": M.hargreaves(d.tmax, d.tmin, d.ra), "oudin": M.oudin(d.t, d.ra),
        "priestley_taylor": M.priestley_taylor(d.t, d.rn, P_CUENCA), "makkink": M.makkink(d.t, d.rs, P_CUENCA),
        "dalton": M.dalton_fao24(d.es, d.ea, d.u2), "meyer": M.meyer(d.es, d.ea, d.u10),
        "linacre": M.linacre(d.t, d.td, z_mod, lat), "vpd": d.vpd, "u2": d.u2,
    }, index=d.index)
    mm = m.drop(columns=["vpd", "u2"]).resample("MS").sum()
    mm[["vpd", "u2"]] = m[["vpd", "u2"]].resample("MS").mean()
    mm = mm[d.eto.resample("MS").count().values == mm.index.days_in_month]
    mm["thornthwaite"], _, _ = M.thornthwaite_mensual(d.t.resample("MS").mean().loc[mm.index], lat, I, a)
    return mm


pesos = pd.read_csv(PESOS).merge(pd.read_csv(RAIZ / "datos/punto1/era5land/geopotencial_era5land_chicama.csv"), on=["lat", "lon"])
cache = pd.read_csv(OUT / "forzantes_diarios_celdas.csv.gz", parse_dates=["fecha"])

res = {e: [] for e in ESCEN}
for _, r in pesos.iterrows():
    d0 = cache[(cache.lat.round(1) == round(r.lat, 1)) & (cache.lon.round(1) == round(r.lon, 1))].set_index("fecha").sort_index()
    tm = ((d0.tmax + d0.tmin) / 2).resample("MS").mean()
    _, I, a = M.thornthwaite_mensual(tm, r.lat)                      # I y a de la climatologia base, fijos
    for e in ESCEN:
        res[e].append(metodos_mensuales(perturbar(d0, e), r.lat, r.z_modelo_m, I, a).assign(w=r.area_en_cuenca_km2))


def cuenca(lst):
    t = pd.concat(lst)
    c = t.drop(columns="w").multiply(t.w, axis=0).groupby(level=0).sum().div(t.w.groupby(level=0).sum(), axis=0)
    return c


C = {e: cuenca(v) for e, v in res.items()}
base = C["base"]

# ---------------------------------------------------------------- 1) terminos y alfa*
mes = base.groupby(base.index.month)
term = pd.DataFrame({"eto": mes.fao56.mean(), "rad": mes.eto_rad.mean(), "aero": mes.eto_aero.mean(),
                     "eeq": mes.eeq.mean(), "vpd": mes.vpd.mean(), "u2": mes.u2.mean()})
term["frac_rad"] = term.rad / term.eto
term["frac_aero"] = term.aero / term.eto
term["alfa_star"] = term.eto / term.eeq
term.index.name = "mes"
term.round(4).to_csv(OUT / "terminos_fao56_por_mes.csv")
r_vpd = np.corrcoef(base.fao56 / base.eeq, base.vpd)[0, 1]
r_u2 = np.corrcoef(base.fao56 / base.eeq, base.u2)[0, 1]
print(term.round(3).to_string())
print(f"alfa* anual = {base.fao56.sum()/base.eeq.sum():.3f}; correlacion mensual de alfa* con DPV r = {r_vpd:.2f}, con u2 r = {r_u2:.2f}")

# ---------------------------------------------------------------- 2) sensibilidad
cols = list(NOMBRES)
anual = pd.DataFrame({e: 100 * (C[e][cols].sum() / base[cols].sum() - 1) for e in ESCEN if e != "base"})
anual.index = [NOMBRES[c] for c in anual.index]
anual.round(2).to_csv(OUT / "sensibilidad_anual_pct.csv")
print("\ncambio de la demanda anual (%) por forzante:"); print(anual.round(1).to_string())

mensual = {}
for e in ESCEN:
    if e == "base":
        continue
    g = 100 * (C[e].fao56 / base.fao56 - 1)
    mensual[e] = g.groupby(g.index.month).mean()
mensual = pd.DataFrame(mensual); mensual.index.name = "mes"
mensual.round(2).to_csv(OUT / "sensibilidad_fao56_por_mes_pct.csv")
print("\nFAO-56: cambio mensual (%):"); print(mensual.round(1).to_string())

# ---------------------------------------------------------------- 3) unidades
lam = 2.45e6
mm_h = 146 / lam * 3600
print(f"\n146 W m-2 / lambda = {146/lam*1e3:.4f} g m-2 s-1 = {mm_h:.3f} mm/h = {mm_h*24:.2f} mm/d "
      f"(el texto dice 3.52 mm/h, {3.52/mm_h:.0f} veces mas); 1 mm/d = {lam/86400:.1f} W m-2")

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
x = np.arange(1, 13)
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4))
a = ax[0]
a.bar(x, 100 * term.frac_rad, color=NARANJA, label="radiativo")
a.bar(x, 100 * term.frac_aero, bottom=100 * term.frac_rad, color=GRIS, label="aerodinámico")
a.set_ylim(70, 100); a.set_ylabel("% de la ETo"); a.set_xticks(x, [m[0] for m in MESES])
a.legend(frameon=False, fontsize=8.5, loc="lower left")
a.set_title("(a) Términos de FAO-56 (eje desde 70 %)", loc="left", fontsize=10.5)
a = ax[1]
a.plot(x, term.alfa_star, "o-", color="k", lw=2, label="α* = ETo / E$_{eq}$")
a.axhline(1.26, color=AZUL, ls="--", lw=1, label="α de Priestley–Taylor (1,26)")
a.axhline(1.0, color=GRIS, ls=":", lw=1)
a.set_ylabel("α*"); a.set_xticks(x, [m[0] for m in MESES]); a.set_ylim(0.95, 1.3)
b = a.twinx(); b.plot(x, term.vpd, "s--", color=ROJO, ms=4, label="DPV (kPa)"); b.plot(x, term.u2, "^:", color=GRIS, ms=4, label="u₂ (m/s)")
b.set_ylabel("DPV (kPa) · u₂ (m/s)"); b.spines["right"].set_visible(True)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = b.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="upper left", ncol=2)
a.set_title("(b) Coeficiente implícito α* y lo que lo mueve", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1d_terminos.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
a = ax[0]
lim = np.nanmax(np.abs(anual.values))
im = a.imshow(anual.values, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
for i in range(anual.shape[0]):
    for j in range(anual.shape[1]):
        v = anual.values[i, j]
        a.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=7.5, color="w" if abs(v) > 0.6 * lim else "k")
a.set_xticks(range(anual.shape[1]), [ESCEN[e] for e in anual.columns], fontsize=8)
a.set_yticks(range(anual.shape[0]), anual.index)
fig.colorbar(im, ax=a, label="cambio de la demanda anual (%)")
a.set_title("(a) Sensibilidad de cada método a cada forzante", loc="left", fontsize=10.5)
a = ax[1]
estilos = {"T+1_ea": ("-", ROJO), "T+1_hr": ("--", ROJO), "u2+10": ("-", GRIS), "rs-10": ("-", NARANJA), "ea+10": ("-", AZUL)}
for e, (ls, c) in estilos.items():
    a.plot(x, mensual[e], ls, color=c, marker="o", ms=3.5, label=ESCEN[e].replace("\n", " "))
a.axhline(0, color="k", lw=.8); a.set_xticks(x, [m[0] for m in MESES]); a.set_ylabel("cambio de ETo FAO-56 (%)")
a.legend(frameon=False, fontsize=8)
a.set_title("(b) FAO-56: en qué meses pesa cada forzante", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1d_sensibilidad.png", dpi=200); plt.close(fig)
print(f"-> figuras en {FIG.relative_to(RAIZ)}")
