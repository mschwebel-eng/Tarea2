"""
07_problema_A.py - Punto 2.4, problema A: alcantarilla con el metodo racional en la microcuenca de Cottbus
(y bono 2.5.1: diseno de minimo costo esperado).

Microcuenca: productos/punto2/microcuenca_dgm_descripcion.csv (DGM1 de Brandeburgo, 0.44 km2, pastizal 83 %, bosque 17 %).
  1. Coeficiente C ponderado por area, dependiente de T: Chow et al. (1988), tabla 15.1.1 (zonas planas 0-2 %):
     pastizal 0.25/0.28/0.30/0.34/0.37/0.41 y bosque 0.22/0.25/0.28/0.31/0.35/0.39 para T = 2/5/10/25/50/100 (verificar en la tabla).
  2. tc con cuatro formulas: Kirpich (1940), Temez (1978), retardo del SCS (NRCS, 1986) y velocidad de Manning en la zanja.
  3. T por riesgo: vida util n = 30 anos, riesgo aceptable 70 % (consecuencias bajas: pastizal y camino rural) -> T = 25;
     practica: alcantarillas de vias de trafico intermedio 10-25 anos (Chow et al., 1988, tabla 13.1.1).
  4. Qp = C i(tc, T) A FRA / 3.6; FRA del Flood Studies Report (NERC, 1975). Manning a tubo lleno, concreto n = 0.013,
     pendiente de la alcantarilla S0 = 0.5 %; diametro comercial superior.
  5. Sensibilidad: tc, C +-20 %, limites del IC de la IDF, otras distribuciones (Gumbel, log-Pearson III, GLO).
  6. Monte Carlo (20 000): replicas bootstrap de la GEV por duracion, C, tc, n y S0 -> probabilidad anual efectiva de falla.
  7. Escala: por que el racional no vale en el Chicama (2 170 km2).
  8. Bono 2.5.1: costo anualizado de la obra + dano anual esperado para varios T.

Salidas: productos/punto2/problemaA_*.csv, figuras/fig_2_4_problemaA*.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import distribuciones as Dd

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "productos/punto2"
FIG = OUT / "figuras"
rng = np.random.default_rng(20261120)
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"
DUR = np.array([10, 20, 30, 60, 120, 180, 360, 720, 1440])
TS = np.array([2, 5, 10, 25, 50, 100])

mc = pd.read_csv(OUT / "microcuenca_dgm_descripcion.csv", index_col=0).iloc[:, 0]
A = mc.area_km2; L = mc.L_cauce_principal_m; S = mc.S_global; Sw = mc.pendiente_media_cuenca
f_past = mc.get("cobertura_pastizal_%", 0) / 100; f_bos = mc.get("cobertura_bosque_%", 0) / 100
ip = pd.read_csv(OUT / "idf_parametros.csv").set_index("parametro").valor
th, eta = ip.theta_h, ip.eta
aT = lambda T: Dd._gev_q(ip.gev_mu, ip.gev_sigma, ip.gev_xi, T)
idf = lambda d_min, T: aT(T) / (d_min / 60 + th) ** eta

# ---------------------------------------------------------------- 1) C(T)
C_PAST = dict(zip(TS, [0.25, 0.28, 0.30, 0.34, 0.37, 0.41]))
C_BOS = dict(zip(TS, [0.22, 0.25, 0.28, 0.31, 0.35, 0.39]))
Cw = lambda T: (f_past * np.interp(T, TS, list(C_PAST.values())) + f_bos * np.interp(T, TS, list(C_BOS.values()))) / (f_past + f_bos)

# ---------------------------------------------------------------- 2) tc
H = S * L                                                            # desnivel del cauce principal (m)
tc = {}
tc["Kirpich (1940)"] = 0.0195 * L ** 0.77 * S ** -0.385
tc["Témez (1978)"] = 60 * 0.3 * ((L / 1000) / S ** 0.25) ** 0.76
CN = 55                                                              # pastizal en buen estado, suelos arenosos (grupos A-B)
Sp = 1000 / CN - 10
tlag_h = (L * 3.28084) ** 0.8 * (Sp + 1) ** 0.7 / (1900 * (100 * Sw) ** 0.5)
tc["Retardo SCS (NRCS, 1986)"] = 60 * tlag_h / 0.6
n_z, R_z = 0.035, 0.30                                               # zanja de tierra con pasto; radio hidraulico supuesto
V = (1 / n_z) * R_z ** (2 / 3) * S ** 0.5
tc["Velocidad en la zanja (Manning)"] = L / V / 60
TC = pd.Series(tc, name="tc_min")
TC_DIS = tc["Kirpich (1940)"]
print("tiempos de concentracion (min):"); print(TC.round(0).to_string())
print(f"   (desnivel del cauce {H:.2f} m en {L:.0f} m; velocidad en la zanja {V:.2f} m/s; pendiente media de la cuenca {100*Sw:.2f} %)")

# ---------------------------------------------------------------- 3) periodo de retorno por riesgo
n_vida, R_acep = 30, 0.70
NANIOS = 30                                                          # anos validos del registro (2.1)
T_riesgo = 1 / (1 - (1 - R_acep) ** (1 / n_vida))
T_DIS = 25
riesgo = lambda T, n: 1 - (1 - 1 / T) ** n
print(f"\nT por riesgo (n = {n_vida}, R = {R_acep:.0%}): {T_riesgo:.1f} anos -> T = {T_DIS} (riesgo real {riesgo(T_DIS, n_vida):.0%})")

# ---------------------------------------------------------------- 4) caudal y diametro
def fra(A_km2, d_h):
    """Flood Studies Report (NERC, 1975): FRA = 1 - b d^-a, valido para A < 20 km2 en esta forma."""
    b = 0.0394 * A_km2 ** 0.354
    a = 0.40 - 0.0208 * np.log(4.6 - np.log(A_km2))
    return 1 - b * d_h ** (-a)
N_MAN, S0 = 0.013, 0.005
DN = np.array([0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.20, 1.40, 1.60, 1.80, 2.00, 2.20, 2.50, 3.00])
Dcalc = lambda Q, n=N_MAN, s0=S0: (n * Q / (0.312 * s0 ** 0.5)) ** (3 / 8)
Dcom = lambda Q, n=N_MAN, s0=S0: DN[np.searchsorted(DN, Dcalc(Q, n, s0))]
Qcap = lambda D, n=N_MAN, s0=S0: 0.312 / n * D ** (8 / 3) * s0 ** 0.5
Qp = lambda tcm, T, C=None, escala=1.0: (Cw(T) if C is None else C) * idf(tcm, T) * escala * A * fra(A, tcm / 60) / 3.6
C_DIS = Cw(T_DIS); i_DIS = idf(TC_DIS, T_DIS); FRA_DIS = fra(A, TC_DIS / 60)
Q_DIS = Qp(TC_DIS, T_DIS); D_DIS = Dcom(Q_DIS)
print(f"diseno: C = {C_DIS:.3f}, tc = {TC_DIS:.0f} min, i = {i_DIS:.2f} mm/h, FRA = {FRA_DIS:.3f} -> Qp = {Q_DIS:.3f} m3/s; "
      f"D calculado {Dcalc(Q_DIS):.3f} m -> comercial {D_DIS:.2f} m (capacidad {Qcap(D_DIS):.3f} m3/s, FS = {Qcap(D_DIS)/Q_DIS:.2f})")

# ---------------------------------------------------------------- 5) sensibilidad
aq = pd.read_csv(OUT / "ajuste_cuantiles.csv")
def razon_dist(dist, met, T=T_DIS, tcm=TC_DIS):
    """Razon cuantil(dist)/cuantil(GEV-LMOM) a la duracion tc (interpolada en log d)."""
    g = aq[(aq.dist == "GEV") & (aq.metodo == "LMOM")].set_index("duracion_min")[f"T{T}"]
    o = aq[(aq.dist == dist) & (aq.metodo == met)].set_index("duracion_min")[f"T{T}"]
    return np.exp(np.interp(np.log(tcm), np.log(DUR), np.log(o.loc[DUR].values / g.loc[DUR].values)))
icb = pd.read_csv(OUT / "bootstrap_ic_gev_lmom.csv"); icb = icb[icb["T"] == T_DIS].set_index("duracion_min").loc[DUR]
lo = np.exp(np.interp(np.log(TC_DIS), np.log(DUR), np.log(icb.lo / icb.q)))     # IC 95 % del cuantil a la duracion tc
hi = np.exp(np.interp(np.log(TC_DIS), np.log(DUR), np.log(icb.hi / icb.q)))
print(f"IC 95 % del cuantil de {T_DIS} anos a tc: {lo:.2f} a {hi:.2f} veces el valor central")
casos = [("diseño", Q_DIS)]
for nom, v in tc.items():
    casos.append((f"tc: {nom} ({v:.0f} min)", Qp(v, T_DIS)))
casos += [("C −20 %", Qp(TC_DIS, T_DIS, C=0.8 * C_DIS)), ("C +20 %", Qp(TC_DIS, T_DIS, C=1.2 * C_DIS)),
          ("IDF: límite inferior IC 95 %", Qp(TC_DIS, T_DIS, escala=lo)), ("IDF: límite superior IC 95 %", Qp(TC_DIS, T_DIS, escala=hi)),
          ("distribución: Gumbel (LMOM)", Qp(TC_DIS, T_DIS, escala=razon_dist("Gumbel", "LMOM"))),
          ("distribución: log-Pearson III (LMOM)", Qp(TC_DIS, T_DIS, escala=razon_dist("log-Pearson III", "LMOM"))),
          ("distribución: GLO (LMOM)", Qp(TC_DIS, T_DIS, escala=razon_dist("GLO (contraste)", "LMOM")))]
SE = pd.DataFrame(casos, columns=["caso", "Q_m3_s"])
SE["D_calc_m"] = SE.Q_m3_s.map(Dcalc); SE["D_comercial_m"] = SE.Q_m3_s.map(Dcom)
SE.round(4).to_csv(OUT / "problemaA_sensibilidad.csv", index=False)
fuentes = {"tc (4 fórmulas)": SE[SE.caso.str.startswith("tc")].D_calc_m, "C ± 20 %": SE[SE.caso.str.startswith("C ")].D_calc_m,
           "IC 95 % de la IDF": SE[SE.caso.str.startswith("IDF")].D_calc_m, "distribución": SE[SE.caso.str.startswith("distrib")].D_calc_m}
RK = pd.DataFrame({k: {"D_min": v.min(), "D_max": v.max(), "rango_m": v.max() - v.min()} for k, v in fuentes.items()}).T
RK["rango_vs_diseno_%"] = 100 * RK.rango_m / Dcalc(Q_DIS)
RK = RK.sort_values("rango_m", ascending=False)
RK.round(4).to_csv(OUT / "problemaA_ranking_incertidumbre.csv")
print("\nsensibilidad:"); print(SE.round(3).to_string(index=False)); print("\nranking de fuentes:"); print(RK.round(3).to_string())

# ---------------------------------------------------------------- 6) Monte Carlo del riesgo efectivo
rep = pd.read_csv(OUT / "bootstrap_replicas_gev_lmom.csv.gz")
P = {d: rep[rep.duracion_min == d].sort_values("rep")[["mu", "sigma", "xi"]].values for d in DUR}
NMC = 20000
b = rng.integers(0, P[10].shape[0], NMC)
tcs = rng.triangular(TC.min(), TC_DIS, TC.max(), NMC)
Cs = C_DIS * rng.uniform(0.8, 1.2, NMC)
ns = rng.uniform(0.011, 0.015, NMC); s0s = rng.uniform(0.004, 0.006, NMC)
Qc = Qcap(D_DIS, ns, s0s)
istar = 3.6 * Qc / (Cs * A * fra(A, tcs / 60))
k = np.clip(np.searchsorted(DUR, tcs) - 1, 0, len(DUR) - 2)
d1, d2 = DUR[k], DUR[k + 1]
def pex(dd, kk):
    par = np.array([P[x][bb] for x, bb in zip(dd, kk)])
    return 1 - stats.genextreme.cdf(istar, -par[:, 2], par[:, 0], par[:, 1])
p1, p2 = np.clip(pex(d1, b), 1e-9, 1), np.clip(pex(d2, b), 1e-9, 1)
w = (np.log(tcs) - np.log(d1)) / (np.log(d2) - np.log(d1))
p = np.exp((1 - w) * np.log(p1) + w * np.log(p2))
p_eff = p.mean()
MC = pd.Series({"p_nominal": 1 / T_DIS, "p_efectiva": p_eff, "T_efectivo": 1 / p_eff, "riesgo_nominal_30a": riesgo(T_DIS, n_vida),
                "riesgo_efectivo_30a": 1 - (1 - p_eff) ** n_vida, "FS_diseno": Qcap(D_DIS) / Q_DIS,
                "p_efectiva_p5": np.percentile(p, 5), "p_efectiva_p95": np.percentile(p, 95), "D_comercial_m": D_DIS})
MC.round(5).to_csv(OUT / "problemaA_montecarlo.csv", header=["valor"])
print("\nMonte Carlo:"); print(MC.round(4).to_string())

# ---------------------------------------------------------------- 7) escala: el Chicama
A_ch, L_ch, H_ch = 2170.0, 80000.0, 4308 - 684                       # Tarea 1: area, cauce principal ~80 km, desnivel
tc_ch = 0.0195 * L_ch ** 0.77 * (H_ch / L_ch) ** -0.385
def fra_ls(A_km2, d_h):
    """Leclerc y Schaake (1972), ajuste de las curvas del TP-29 del US Weather Bureau (A en mi2); calibrado hasta ~1 000 km2."""
    Am = A_km2 / 2.59
    return 1 - np.exp(-1.1 * d_h ** 0.25) + np.exp(-1.1 * d_h ** 0.25 - 0.01 * Am)
ESC = pd.DataFrame({"cuenca": ["microcuenca Cottbus", "Chicama hasta El Tambo"], "area_km2": [A, A_ch],
                    "tc_Kirpich_min": [TC_DIS, tc_ch], "FRA_1h": [fra(A, 1.0), fra_ls(A_ch, 1.0)],
                    "FRA_en_tc": [FRA_DIS, fra_ls(A_ch, tc_ch / 60)], "FRA_24h": [fra(A, 24.0), fra_ls(A_ch, 24.0)]})
ESC.round(3).to_csv(OUT / "problemaA_escala.csv", index=False)
print("\nescala:"); print(ESC.round(3).to_string(index=False))

# ---------------------------------------------------------------- 8) bono 2.5.1: minimo costo esperado
def costo_total(Td, Dmax=20.0, r=0.06, n=n_vida):
    Q2 = Qp(TC_DIS, 2, C=C_DIS); Qd = Qp(TC_DIS, Td, C=C_DIS)
    frc = r * (1 + r) ** n / ((1 + r) ** n - 1)
    obra = (Qd / Q2) ** 0.6 * frc                                      # en unidades de C0 por ano
    pp = np.logspace(-6, np.log10(1 / Td), 400)
    Qq = Qp(TC_DIS, 1 / pp, C=C_DIS)
    dano = np.where(Qq > Qd, Dmax * (1 - np.exp(-(Qq - Qd) / (0.5 * Qd))), 0.0)
    dae = np.trapezoid(dano, pp)
    return obra, dae
Tg = np.array([2, 3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 2000, 5000, 10000])
filas = []
for etq, kw in [("base (Dmáx = 20 C0, r = 6 %)", {}), ("Dmáx × 0,5", {"Dmax": 10.0}), ("Dmáx × 2", {"Dmax": 40.0}),
                ("r = 3 %", {"r": 0.03}), ("r = 9 %", {"r": 0.09})]:
    for T in Tg:
        o, d = costo_total(T, **kw); filas.append({"caso": etq, "T": T, "obra_anual": o, "DAE": d, "total": o + d})
CE = pd.DataFrame(filas); CE.round(5).to_csv(OUT / "problemaA_costo_esperado.csv", index=False)
opt = CE.loc[CE.groupby("caso").total.idxmin()][["caso", "T", "total"]]
print("\nT de minimo costo esperado:"); print(opt.round(3).to_string(index=False))

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [0.9, 1.25]})
a = ax[0]
a.barh(range(len(TC)), TC.values, color=[ROJO if k == "Kirpich (1940)" else GRIS for k in TC.index])
a.set_yticks(range(len(TC)), TC.index); a.invert_yaxis(); a.set_xlabel("tc (min)")
for k_, v in enumerate(TC.values):
    a.text(v + 3, k_, f"{v:.0f}", va="center", fontsize=9)
a.set_title("(a) Tiempo de concentración", loc="left", fontsize=10.5)
a = ax[1]
y = np.arange(len(SE))
a.barh(y, SE.D_calc_m, color=[ROJO if c == "diseño" else GRIS for c in SE.caso])
for k_, (dc, dm) in enumerate(zip(SE.D_calc_m, SE.D_comercial_m)):
    a.text(dc + 0.01, k_, f"{dc:.2f} → DN {dm:.2f}", va="center", fontsize=7.5)
a.set_yticks(y, SE.caso, fontsize=8); a.invert_yaxis(); a.set_xlabel("diámetro calculado (m)")
a.set_title("(b) Sensibilidad del diámetro", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_4_problemaA.png", dpi=200); plt.close(fig)

fig, a = plt.subplots(figsize=(7, 4.6))
a.axvspan(2 * NANIOS, Tg.max(), color="#e5e7eb", zorder=0)
a.text(2 * NANIOS * 1.15, 0.06, "extrapolación\n(T > 2 × 30 años)", fontsize=7, color="#4b5563")
for etq, c in [("base (Dmáx = 20 C0, r = 6 %)", "k"), ("Dmáx × 0,5", AZUL), ("Dmáx × 2", ROJO), ("r = 3 %", VERDE), ("r = 9 %", NARANJA)]:
    g = CE[CE.caso == etq]; a.plot(g["T"], g.total, "-", lw=1.5, color=c, label=etq)
    m = g.total.min(); f = g[g.total <= 1.05 * m]
    a.plot(f["T"], f.total, "-", lw=5, color=c, alpha=.35, solid_capstyle="butt")
    a.plot(g.loc[g.total.idxmin(), "T"], m, "o", color=c, ms=5)
a.axvline(T_DIS, color=GRIS, ls=":"); a.text(T_DIS * 0.9, 3.5, f"T por riesgo = {T_DIS}", fontsize=7.5, color=GRIS, ha="right")
a.set_xscale("log"); a.set_yscale("log"); a.set_ylim(0.05, 5)
a.set_xlabel("periodo de retorno de diseño (años)"); a.set_ylabel("costo anual esperado (× C0)")
a.legend(frameon=False, fontsize=7, loc="upper right", ncol=1, title="trazo grueso: dentro de 5 % del mínimo; punto: mínimo", title_fontsize=7)
a.set_title("Bono 2.5.1: costo anual esperado = obra anualizada + daño anual esperado", loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "fig_2_5_bono_costo.png", dpi=200); plt.close(fig)

fig, a = plt.subplots(figsize=(6.5, 4))
a.hist(np.log10(p), bins=60, color=GRIS, alpha=.8)
fr0 = np.mean(p <= 1.01e-9)
a.annotate(f"{fr0:.0%} de las iteraciones:\nel tubo casi nunca se llena\n(p < 10⁻⁹, recortado)", (-9, 1500), xytext=(-8.4, 1250), fontsize=8, arrowprops=dict(arrowstyle="->"))
a.axvline(np.log10(1 / T_DIS), color="k", ls="--", label=f"nominal 1/T = {1/T_DIS:.3f}")
a.axvline(np.log10(p_eff), color=ROJO, lw=2, label=f"efectiva (media) = {p_eff:.3f}")
a.set_xlabel("log₁₀ de la probabilidad anual de falla"); a.set_ylabel("iteraciones")
a.legend(frameon=False, fontsize=9); a.set_title(f"Monte Carlo ({NMC} iteraciones), DN {D_DIS:.2f} m", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_4_problemaA_montecarlo.png", dpi=200); plt.close(fig)
print(f"-> figuras en {FIG.relative_to(RAIZ)}")
