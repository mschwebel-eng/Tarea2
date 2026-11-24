"""
03_ajuste_extremos.py - Punto 2.2: distribuciones, metodos, cuantiles, bondad de ajuste, bootstrap y estacionariedad.

Datos: maximos anuales de intensidad (mm/h, con Weiss) de productos/punto2/maximos_anuales_cottbus.csv, anos validos con el
criterio base (>= 80 % del ano y >= 90 % de mayo-septiembre).
  1. 3 distribuciones (Gumbel, GEV, log-Pearson III) x 3 metodos (MOM, LMOM, MLE) x 9 duraciones.
  2. Cuantiles T = 2, 5, 10, 25, 50, 100; graficas de probabilidad con Gringorten (recomendada para Gumbel y GEV).
  3. Bondad de ajuste: Kolmogorov-Smirnov, Anderson-Darling (estadistico) y PPCC; diagrama de razones de L-momentos.
  4. Bootstrap (2000 remuestreos) de la distribucion elegida -> IC 95 % y replicas de parametros (para la IDF y Monte Carlo).
  5. Estacionariedad: Mann-Kendall (Hamed-Rao) y Sen por duracion; Kruskal-Wallis entre las tres epocas de instrumento.
  6. Sensibilidad de los cuantiles a: criterio de anos validos, quitar 2021 (firmware), 2014 con el pluviometro diario.

Salidas: productos/punto2/ajuste_*.csv, bootstrap_*.csv, figuras/fig_2_2_*.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import stats
import pymannkendall as mk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import distribuciones as Dd

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "productos/punto2"
FIG = OUT / "figuras"
DUR = [10, 20, 30, 60, 120, 180, 360, 720, 1440]
TS = [2, 5, 10, 25, 50, 100]
BASE, ESTR, LAXO = "base (80 % año, 90 % may–sep)", "estricto (90 %, 95 %)", "laxo (70 %, 80 %)"
NBOOT = 2000
rng = np.random.default_rng(20261114)
AZUL, ROJO, NARANJA, GRIS, VERDE = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f"
COL = {"Gumbel": GRIS, "GEV": ROJO, "log-Pearson III": AZUL}

MX = pd.read_csv(OUT / "maximos_anuales_cottbus.csv", index_col="anio")
valido = MX[BASE].astype(bool)

# ---------------------------------------------------------------- verificaciones previas
p, s = Dd.verificar_convenciones()
print(f"convencion GEV: cuantil propio (xi=+0.2) {p:.4f} = scipy con c=-0.2 {s:.4f}")
try:
    import lmoments3 as lm
    x60 = MX.loc[valido, "i60_mm_h"].values
    l_prop = Dd.lmom(x60); l_lm = lm.lmom_ratios(x60, nmom=4)
    print(f"L-momentos propios {np.round(l_prop, 4)} | lmoments3 {np.round([l_lm[0], l_lm[1], l_lm[2], l_lm[3]], 4)}")
except Exception as e:
    print(f"no se pudo verificar con lmoments3: {e}")

# ---------------------------------------------------------------- 1-3) ajustes, cuantiles y bondad
filas_q, filas_b, filas_l = [], [], []
for d in DUR:
    x = MX.loc[valido, f"i{d}_mm_h"].dropna().values
    l1, l2, t3, t4 = Dd.lmom(x)
    filas_l.append({"duracion_min": d, "n": len(x), "media": x.mean(), "cv": x.std(ddof=1) / x.mean(), "asimetria": stats.skew(x, bias=False),
                    "L_cv": l2 / l1, "tau3": t3, "tau4": t4})
    for dist, f in Dd.AJUSTES.items():
        for met in Dd.METODOS:
            try:
                aj = f(x, met)
                q = aj["q"](TS)
                filas_q.append({"duracion_min": d, "dist": dist, "metodo": met, **{f"T{T}": v for T, v in zip(TS, q)}, **aj["par"]})
                filas_b.append({"duracion_min": d, "dist": dist, "metodo": met, **Dd.bondad(x, aj)})
            except Exception as e:
                print(f"  FALLO ajuste {dist} {met} {d} min: {e}")
    aj = Dd.glo(x)                                             # contraste sugerido por el diagrama de L-momentos
    filas_q.append({"duracion_min": d, "dist": "GLO (contraste)", "metodo": "LMOM", **{f"T{T}": v for T, v in zip(TS, aj["q"](TS))}, **aj["par"]})
    filas_b.append({"duracion_min": d, "dist": "GLO (contraste)", "metodo": "LMOM", **Dd.bondad(x, aj)})
Q = pd.DataFrame(filas_q); B = pd.DataFrame(filas_b); L = pd.DataFrame(filas_l)
Q.round(4).to_csv(OUT / "ajuste_cuantiles.csv", index=False)
B.round(4).to_csv(OUT / "ajuste_bondad.csv", index=False)
L.round(4).to_csv(OUT / "ajuste_lmomentos.csv", index=False)
print("\nL-momentos por duracion:"); print(L.round(3).to_string(index=False))
print("\nbondad (media de las 9 duraciones):")
print(B.groupby(["dist", "metodo"])[["KS_D", "KS_p", "AD", "PPCC"]].mean().round(3).to_string())
print(f"\nrechazos KS al 5 %: {int((B.KS_p < 0.05).sum())} de {len(B)}")
q60 = Q[Q.duracion_min == 60].set_index(["dist", "metodo"])[[f"T{T}" for T in TS]]
print("\ncuantiles de 60 min (mm/h):"); print(q60.round(1).to_string())
# dispersion entre distribuciones y metodos del cuantil de 100 anos
disp = Q[Q.dist != "GLO (contraste)"].groupby("duracion_min").T100.agg(["min", "max", "median"])
disp["rango_%"] = 100 * (disp["max"] - disp["min"]) / disp["median"]
print("\nrango del cuantil de 100 anos entre las 9 combinaciones (%):", disp["rango_%"].round(0).to_dict())

# ---------------------------------------------------------------- 4) bootstrap de la distribucion elegida (GEV por L-momentos)
ELEGIDA, MET = "GEV", "LMOM"
# Remuestreo de ANOS completos, el mismo para todas las duraciones: un ano humedo lo es en todas las duraciones a la vez,
# y remuestrear cada duracion por separado encoge la incertidumbre de la IDF (que combina duraciones).
anios_v = MX.index[valido].values
idx_boot = [rng.choice(len(anios_v), len(anios_v), replace=True) for _ in range(NBOOT)]
filas_ic, rep = [], []
for d in DUR:
    x = MX.loc[valido, f"i{d}_mm_h"].values; n = len(x)
    qs = []
    for b in range(NBOOT):
        xb = x[idx_boot[b]]
        aj = Dd.gev(xb, MET)
        qs.append(aj["q"](TS)); rep.append({"duracion_min": d, "rep": b, **aj["par"]})
    qs = np.array(qs); base_q = Dd.gev(x, MET)["q"](TS)
    for k, T in enumerate(TS):
        lo, hi = np.percentile(qs[:, k], [2.5, 97.5])
        filas_ic.append({"duracion_min": d, "T": T, "n": n, "T/N": T / n, "q": base_q[k], "lo": lo, "hi": hi,
                         "ancho_rel": (hi - lo) / base_q[k]})
IC = pd.DataFrame(filas_ic); IC.round(4).to_csv(OUT / "bootstrap_ic_gev_lmom.csv", index=False)
pd.DataFrame(rep).round(6).to_csv(OUT / "bootstrap_replicas_gev_lmom.csv.gz", index=False)
print("\nancho relativo del IC 95 % (60 min):", IC[IC.duracion_min == 60].set_index("T").ancho_rel.round(2).to_dict())

# ---------------------------------------------------------------- 5) estacionariedad
filas_e = []
epoca = pd.cut(MX.index, [1990, 2007, 2020, 2026], labels=["NG 200", "PLUVIO", "rain[e]H3"])
for d in DUR:
    y = MX.loc[valido, f"i{d}_mm_h"].dropna()
    hr = mk.hamed_rao_modification_test(y.values)
    pv = hr.p if np.isfinite(hr.p) else mk.original_test(y.values).p
    sen = stats.theilslopes(y.values, y.index.values)[0]
    grupos = [MX.loc[valido & (epoca == e), f"i{d}_mm_h"].dropna().values for e in ["NG 200", "PLUVIO", "rain[e]H3"]]
    kw = stats.kruskal(*[g for g in grupos if len(g) > 2])
    filas_e.append({"duracion_min": d, "sen_%_por_decada": 1000 * sen / y.mean(), "p_MK": pv, "p_KW_epocas": kw.pvalue,
                    **{f"mediana_{e}": np.median(g) for e, g in zip(["NG200", "PLUVIO", "rainH3"], grupos)}})
E = pd.DataFrame(filas_e); E.round(4).to_csv(OUT / "ajuste_estacionariedad.csv", index=False)
print("\nestacionariedad:"); print(E.round(3).to_string(index=False))

# ---------------------------------------------------------------- 6) sensibilidad de los cuantiles
sens = []
casos = {"base": valido, "estricto": MX[ESTR].astype(bool), "laxo": MX[LAXO].astype(bool),
         "base sin 2021": valido & (MX.index != 2021)}
for nom, sel in casos.items():
    for d in [10, 60, 1440]:
        x = MX.loc[sel, f"i{d}_mm_h"].dropna().values
        q = Dd.gev(x, MET)["q"]([10, 100])
        sens.append({"caso": nom, "duracion_min": d, "n": len(x), "T10": q[0], "T100": q[1]})
# 2014 con el pluviometro diario (102.6 mm en vez de 48.6 mm): se escala el maximo de 24 h
x = MX.loc[valido, "i1440_mm_h"].copy(); x.loc[2014] = x.loc[2014] * 102.6 / 48.6
q = Dd.gev(x.values, MET)["q"]([10, 100])
sens.append({"caso": "base, 2014 = pluviómetro diario", "duracion_min": 1440, "n": len(x), "T10": q[0], "T100": q[1]})
S = pd.DataFrame(sens); S.round(3).to_csv(OUT / "ajuste_sensibilidad.csv", index=False)
print("\nsensibilidad (GEV-LMOM):"); print(S.round(2).to_string(index=False))

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(14, 4.3), sharey=False)
for a, d in zip(ax, [10, 60, 1440]):
    x = np.sort(MX.loc[valido, f"i{d}_mm_h"].dropna().values)
    yr = -np.log(-np.log(Dd.gringorten(x)))
    a.scatter(yr, x, color="k", s=16, zorder=5, label="máximos anuales (Gringorten)")
    Tg = np.logspace(np.log10(1.05), np.log10(200), 100); yg = -np.log(-np.log(1 - 1 / Tg))
    for dist, f in Dd.AJUSTES.items():
        for met, ls in [("LMOM", "-"), ("MLE", "--"), ("MOM", ":")]:
            a.plot(yg, f(x, met)["q"](Tg), ls, color=COL[dist], lw=1.3 if met == "LMOM" else 1,
                   label=f"{dist} · {met}" if d == 10 else None)
    ic = IC[IC.duracion_min == d]
    a.fill_between(-np.log(-np.log(1 - 1 / ic["T"])), ic.lo, ic.hi, color=ROJO, alpha=.12, label="IC 95 % GEV-LMOM" if d == 10 else None)
    for T in [2, 10, 50, 100]:
        yv = -np.log(-np.log(1 - 1 / T)); a.axvline(yv, color="#ddd", lw=.8, zorder=0); a.text(yv, a.get_ylim()[0], f" T={T}", fontsize=7, color=GRIS)
    a.set_xlabel("variable reducida de Gumbel"); a.set_ylabel("intensidad (mm/h)")
    a.set_title(f"({'abc'[[10, 60, 1440].index(d)]}) {d} min" if d < 1440 else "(c) 24 h", loc="left", fontsize=10.5)
ax[0].legend(frameon=False, fontsize=6.6, ncol=1, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "fig_2_2_ajustes.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4))
a = ax[0]
t3g = np.linspace(-0.1, 0.5, 200)
for nom, v in Dd.tau4_teorica(t3g).items():
    a.plot(t3g, v, lw=1.2, label=nom)
a.scatter([0.1699], [0.1504], marker="s", color="k", s=40, zorder=5, label="Gumbel")
a.scatter([0], [0.1226], marker="^", color="k", s=40, zorder=5, label="Normal")
sc = a.scatter(L.tau3, L.tau4, c=np.log10(L.duracion_min), cmap="viridis", s=60, edgecolor="k", zorder=6)
for _, r in L.iterrows():
    a.annotate(f"{int(r.duracion_min)}'" if r.duracion_min < 60 else f"{int(r.duracion_min/60)} h", (r.tau3, r.tau4), fontsize=7.5,
               xytext=(4, 3), textcoords="offset points")
t3m, t4m = L.tau3.mean(), L.tau4.mean()
x60 = MX.loc[valido, "i60_mm_h"].dropna().values
t4b = np.array([Dd.lmom(rng.choice(x60, len(x60), replace=True))[3] for _ in range(2000)])
print(f"variabilidad muestral de tau4 (60 min, N = {len(x60)}): desviacion estandar bootstrap = {t4b.std():.3f}")
pd.Series({"tau3_medio": t3m, "tau4_medio": t4m, "tau4_GEV": Dd.tau4_teorica(t3m)["GEV"], "tau4_GLO": Dd.tau4_teorica(t3m)["GLO"],
           "sd_tau4_bootstrap_60min": t4b.std()}).round(4).to_csv(OUT / "ajuste_diagrama_lmom.csv", header=["valor"])
a.scatter([t3m], [t4m], marker="*", s=260, color="w", edgecolor="k", zorder=7, label="promedio de las duraciones")
print(f"promedio tau3 = {t3m:.3f}, tau4 = {t4m:.3f}; curvas en ese tau3: " +
      ", ".join(f"{k} {v:.3f}" for k, v in Dd.tau4_teorica(t3m).items()))
a.set_xlabel("L-asimetría τ₃"); a.set_ylabel("L-curtosis τ₄"); a.set_xlim(-0.1, 0.5); a.set_ylim(0, 0.35)
a.legend(frameon=False, fontsize=7.5, loc="upper left")
a.set_title("(a) Diagrama de razones de L-momentos", loc="left", fontsize=10.5)
a = ax[1]
for d, c in [(10, ROJO), (60, NARANJA), (360, VERDE), (1440, AZUL)]:
    ic = IC[IC.duracion_min == d]
    a.plot(ic["T/N"], 100 * ic.ancho_rel, "o-", color=c, label=f"{d} min" if d < 1440 else "24 h")
a.axvline(2, color=GRIS, ls=":"); a.text(2.05, 32, "T = 2N", fontsize=8, color=GRIS)
a.set_xscale("log"); a.set_xlabel("T / N"); a.set_ylabel("ancho del IC 95 % (% del cuantil)")
a.legend(frameon=False, fontsize=8.5); a.set_title("(b) La incertidumbre crece con T/N", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_2_lmom_bootstrap.png", dpi=200); plt.close(fig)
print(f"-> figuras en {FIG.relative_to(RAIZ)}")
