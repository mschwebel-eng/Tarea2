"""
08_problema_B.py - Punto 2.4, problema B: tanque de detencion para la microcuenca urbanizada (Chow et al., 1988, sec. 15.4).

Antes (problema A): C(25) ponderado pastizal/bosque, tc Kirpich. Caudal maximo permitido O_max = C_pre i(tc_pre, T) A / 3.6 (sin FRA:
el problema B se plantea con el racional puro; con FRA ~ 0.98 los volumenes cambian ~2 %).
Despues (escenario del grupo): 50 % impermeable (mitad vias de asfalto, mitad techos/concreto) y 50 % prados urbanos (tabla 15.1.1);
tc = 0.4 x Kirpich (ajuste de Kirpich para flujo sobre asfalto/concreto, Chow tabla 15.1.2) y, como contraste, flujo en cunetas y
tuberias a 1 m/s + 10 min de entrada.
  1. Hidrogramas trapezoidales del racional modificado para d >= tc_post.
  2. Hietograma de bloques alternos (dt = 10 min, dentro del rango de la IDF) de 6 h, con el pico al inicio, al centro y al final;
     hidrograma con el racional de tiempo-area: Q(t) = C A / 3.6 * intensidad media de los tc minutos anteriores.
  3. Transito de piscina nivelada (indicacion de almacenamiento, Chow cap. 8.2) con tanque prismatico S = As h y orificio libre
     O = Cd Ao sqrt(2 g h), Cd = 0.6. Con S lineal y O ~ sqrt(h) cada paso tiene solucion cerrada (cuadratica en sqrt(h)).
  4. Diseno: profundidad maxima h_max (decision del grupo, 1.5 m; nivel freatico somero en la llanura del Spree) fija el orificio
     (O(h_max) = O_max); para cada hidrograma se busca por biseccion el area As que hace max h = h_max. Volumen = As h_max.
Salidas: productos/punto2/problemaB_*.csv, figuras/fig_2_4_problemaB*.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import distribuciones as Dd

RAIZ = Path(__file__).resolve().parents[2]
OUT = RAIZ / "productos/punto2"
FIG = OUT / "figuras"
AZUL, ROJO, NARANJA, GRIS, VERDE, MORADO = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475", "#2f7d4f", "#6d28d9"
TS = np.array([2, 5, 10, 25, 50, 100])
T = 25
G, CD = 9.81, 0.6

mc = pd.read_csv(OUT / "microcuenca_dgm_descripcion.csv", index_col=0).iloc[:, 0]
A, L, S = mc.area_km2, mc.L_cauce_principal_m, mc.S_global
fp, fb = mc["cobertura_pastizal_%"] / 100, mc["cobertura_bosque_%"] / 100
ip = pd.read_csv(OUT / "idf_parametros.csv").set_index("parametro").valor
aT = lambda TT: Dd._gev_q(ip.gev_mu, ip.gev_sigma, ip.gev_xi, TT)
idf = lambda d_min, TT=T: aT(TT) / (np.asarray(d_min, float) / 60 + ip.theta_h) ** ip.eta     # mm/h
cT = lambda fila: np.interp(T, TS, fila)

# ---------------------------------------------------------------- antes y despues
C_pre = fp * cT([0.25, 0.28, 0.30, 0.34, 0.37, 0.41]) + fb * cT([0.22, 0.25, 0.28, 0.31, 0.35, 0.39])
tc_pre = 0.0195 * L ** 0.77 * S ** -0.385
C_post = (0.25 * cT([0.73, 0.77, 0.81, 0.86, 0.90, 0.95]) + 0.25 * cT([0.75, 0.80, 0.83, 0.88, 0.92, 0.97])
          + 0.50 * cT([0.21, 0.23, 0.25, 0.29, 0.32, 0.36]))
tc_post = 0.4 * tc_pre
tc_post_v = L / 1.0 / 60 + 10                                      # contraste: cunetas/tuberias a 1 m/s + 10 min de entrada
Qr = lambda C, i: C * i * A / 3.6
O_max = Qr(C_pre, idf(tc_pre))
Q_post = Qr(C_post, idf(tc_post))
print(f"antes:   C = {C_pre:.3f}, tc = {tc_pre:.0f} min, i = {idf(tc_pre):.1f} mm/h -> Qp = O_max = {O_max:.3f} m3/s")
print(f"despues: C = {C_post:.3f}, tc = {tc_post:.0f} min (contraste {tc_post_v:.0f} min), i = {idf(tc_post):.1f} mm/h -> Qp = {Q_post:.3f} m3/s "
      f"({Q_post/O_max:.1f} veces)")

DT = 60.0                                                          # paso de transito (s)

def trapecio(d, tc, C):
    """Racional modificado: sube en tc hasta C i(d) A/3.6, se mantiene d - tc y baja en tc (minutos -> serie cada DT)."""
    qp = Qr(C, idf(d)); t = np.arange(0, (d + tc) * 60 + 6 * 3600, DT) / 60
    q = np.interp(t, [0, tc, d, d + tc], [0, qp, qp, 0], right=0.0)
    return t, q

def bloques(D_min, pos, dtb=10):
    """Hietograma de bloques alternos (mm/h por bloque de dtb min). pos: 'inicio', 'centro' o 'final'."""
    n = int(D_min // dtb); dur = dtb * np.arange(1, n + 1)
    P = idf(dur) * dur / 60                                        # profundidad acumulada (mm) para cada duracion
    inc = np.diff(np.r_[0, P])                                     # incrementos ordenados de mayor a menor
    if pos == "inicio":
        orden = inc
    elif pos == "final":
        orden = inc[::-1]
    else:
        orden = np.zeros(n); c = (n - 1) // 2
        for k, v in enumerate(inc):                                # alterna derecha/izquierda del centro
            j = c + ((k + 1) // 2) * (1 if k % 2 else -1) if k else c
            j = min(max(j, 0), n - 1)
            while orden[j] != 0:
                j = j + 1 if j < n - 1 else 0
            orden[j] = v
    return orden / (dtb / 60), dtb                                 # intensidad mm/h por bloque

def tiempo_area(i_blq, dtb, tc, C, cola_h=6):
    """Q(t) = C A/3.6 * intensidad media en los tc minutos anteriores a t (lluvia constante por bloque, resolucion DT)."""
    t = np.arange(0, len(i_blq) * dtb * 60 + cola_h * 3600, DT) / 60
    i_t = np.where(t < len(i_blq) * dtb, i_blq[np.minimum((t // dtb).astype(int), len(i_blq) - 1)], 0.0)
    cum = np.r_[0, np.cumsum(i_t[:-1]) * DT / 60]                 # integral de i (mm/h * min) hasta t
    cum_tc = np.interp(t - tc, t, cum, left=0.0)
    return t, Qr(C, (cum - cum_tc) / tc)

def transitar(q, As, Ao):
    """Piscina nivelada por indicacion de almacenamiento: 2S/dt + O = I1 + I2 + 2S1/dt - O1, S = As h, O = k sqrt(h)."""
    k = CD * Ao * np.sqrt(2 * G); a = 2 * As / DT
    h = np.zeros_like(q); o = np.zeros_like(q)
    for j in range(1, len(q)):
        rhs = q[j - 1] + q[j] + a * h[j - 1] - o[j - 1]
        x = (-k + np.sqrt(k * k + 4 * a * max(rhs, 0))) / (2 * a)
        h[j] = x * x; o[j] = k * x
    return h, o

def area_requerida(q, Ao, h_max):
    lo, hi = 1.0, 1e6
    for _ in range(60):
        m = np.sqrt(lo * hi)
        if transitar(q, m, Ao)[0].max() > h_max:
            lo = m
        else:
            hi = m
    return hi

H_MAX = 1.5
Ao = O_max / (CD * np.sqrt(2 * G * H_MAX)); D_or = np.sqrt(4 * Ao / np.pi)
print(f"orificio para h_max = {H_MAX} m: Ao = {Ao:.4f} m2 (D = {100*D_or:.1f} cm)")

# ---------------------------------------------------------------- 1) trapezoides
DUR = np.array([round(tc_post), 50, 60, 75, 90, 105, 120, 150, 180, 240, 300, 360, 480, 600, 720, 960, 1440])
filas = []
for d in DUR:
    t, q = trapecio(d, tc_post, C_post); As = area_requerida(q, Ao, H_MAX)
    filas.append({"d_min": d, "i_mm_h": idf(d), "Qp_m3_s": q.max(), "V_entrada_m3": q.sum() * DT, "As_m2": As, "V_tanque_m3": As * H_MAX})
TR = pd.DataFrame(filas); TR.loc[TR.Qp_m3_s <= O_max, ["As_m2", "V_tanque_m3"]] = 0.0   # el pico no supera O_max: no hace falta tanque
TR.round(3).to_csv(OUT / "problemaB_trapecios.csv", index=False)
dcrit = TR.loc[TR.V_tanque_m3.idxmax()]
print("\ntrapezoides:"); print(TR.round(1).to_string(index=False))
# volumen aproximado de Chow 15.4 (salida que crece linealmente hasta O_max): V = max_d [Qp(d) d - O_max (d + tc)/2] * 60
V_aprox = max(Qr(C_post, idf(d)) * d * 60 - O_max * (d + tc_post) * 60 / 2 for d in np.arange(tc_post, 1440, 1.0))
print(f"duracion critica (trapecios): {dcrit.d_min:.0f} min -> V = {dcrit.V_tanque_m3:.0f} m3 (aprox. sin transito {V_aprox:.0f} m3)")

# ---------------------------------------------------------------- 2) bloques alternos
D_HIET = 360
HG, filas = {}, []
for pos in ["inicio", "centro", "final"]:
    ib, dtb = bloques(D_HIET, pos); t, q = tiempo_area(ib, dtb, tc_post, C_post)
    As = area_requerida(q, Ao, H_MAX); h, o = transitar(q, As, Ao)
    HG[pos] = (ib, t, q, h, o, As)
    tpk_q = t[q.argmax()]; v_hasta_pico = q[t <= tpk_q].sum() * DT
    fin = D_HIET + tc_post; vac = t[(t > fin) & (h < 0.01 * H_MAX)]
    t_vac = (vac[0] - fin) / 60 if len(vac) else np.nan
    filas.append({"posicion": pos, "P_total_mm": (ib * dtb / 60).sum(), "Qp_m3_s": q.max(), "t_pico_min": tpk_q,
                  "V_entrada_m3": q.sum() * DT, "V_entrada_antes_del_pico_m3": v_hasta_pico,
                  "As_m2": As, "V_tanque_m3": As * H_MAX, "O_max_m3_s": o.max(), "t_pico_h_min": t[h.argmax()],
                  "vaciado_tras_escorrentia_h": t_vac})
BA = pd.DataFrame(filas); BA.round(3).to_csv(OUT / "problemaB_bloques.csv", index=False)
print("\nbloques alternos (6 h):"); print(BA.round(2).to_string(index=False))
# verificacion: antes de urbanizar, el hietograma por tiempo-area debe dar el pico del racional
ib, dtb = bloques(D_HIET, "centro"); qpre = tiempo_area(ib, dtb, tc_pre, C_pre)[1].max()
print(f"verificacion: pico pre-urbanizacion con bloques y tiempo-area {qpre:.3f} frente a O_max {O_max:.3f} m3/s")

# ---------------------------------------------------------------- 3) sensibilidades
filas = []
for etq, kw in [("base", {}), ("h_max = 1.0 m", {"h": 1.0}), ("h_max = 2.0 m", {"h": 2.0}),
                (f"tc_post = {0.2*tc_pre:.0f} min (Kirpich × 0,2: canales de concreto)", {"tc": 0.2 * tc_pre}),
                ("tc_post = 60 min (urbanización menos eficiente)", {"tc": 60.0}),
                ("C_post − 20 %", {"C": 0.8 * C_post}), ("C_post + 20 %", {"C": 1.2 * C_post})]:
    h_ = kw.get("h", H_MAX); tc_ = kw.get("tc", tc_post); C_ = kw.get("C", C_post)
    Ao_ = O_max / (CD * np.sqrt(2 * G * h_))
    vt = max(area_requerida(trapecio(d, tc_, C_)[1], Ao_, h_) * h_ for d in DUR[DUR >= tc_ - 1])
    vb = {p: area_requerida(tiempo_area(*bloques(D_HIET, p), tc_, C_)[1], Ao_, h_) * h_ for p in ["inicio", "centro", "final"]}
    filas.append({"caso": etq, "V_trapecio_critico_m3": vt, **{f"V_bloques_{p}_m3": v for p, v in vb.items()}})
for Dh in [120, 180, 240, 720]:
    vb = {p: area_requerida(tiempo_area(*bloques(Dh, p), tc_post, C_post)[1], Ao, H_MAX) * H_MAX for p in ["inicio", "centro", "final"]}
    filas.append({"caso": f"hietograma de {Dh // 60} h", "V_trapecio_critico_m3": np.nan, **{f"V_bloques_{p}_m3": v for p, v in vb.items()}})
SB = pd.DataFrame(filas); SB.round(0).to_csv(OUT / "problemaB_sensibilidad.csv", index=False)
print("\nsensibilidad:"); print(SB.round(0).to_string(index=False))

pd.Series({"C_pre": C_pre, "tc_pre_min": tc_pre, "i_pre_mm_h": idf(tc_pre), "i_post_mm_h": idf(tc_post), "O_max_m3_s": O_max, "C_post": C_post, "tc_post_min": tc_post, "tc_post_contraste_min": tc_post_v,
           "Qp_post_m3_s": Q_post, "h_max_m": H_MAX, "Cd": CD, "Ao_m2": Ao, "D_orificio_m": D_or, "d_critica_trapecio_min": dcrit.d_min,
           "V_trapecio_m3": dcrit.V_tanque_m3, "V_aprox_sin_transito_m3": V_aprox, "V_bloques_max_m3": BA.V_tanque_m3.max(),
           "pico_pre_verificacion_m3_s": qpre}).round(4).to_csv(OUT / "problemaB_resumen.csv", header=["valor"])

# ---------------------------------------------------------------- figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw={"width_ratios": [1.1, 1.1, 0.9]})
a = ax[0]
for d, c in [(round(tc_post), ROJO), (90, NARANJA), (int(dcrit.d_min), "k"), (360, AZUL)]:
    t, q = trapecio(d, tc_post, C_post); m = t <= d + tc_post + 30
    a.plot(t[m], q[m], color=c, lw=2 if d == dcrit.d_min else 1.3, label=f"d = {d} min" + (" (crítica)" if d == dcrit.d_min else ""))
a.axhline(O_max, color=VERDE, ls="--", label=f"O_max = pico previo = {O_max:.2f} m³/s")
a.set_xlabel("tiempo (min)"); a.set_ylabel("caudal de entrada (m³/s)"); a.legend(frameon=False, fontsize=8)
a.set_title("(a) Racional modificado (trapecios), T = 25", loc="left", fontsize=10.5)
a = ax[1]
cols = {"inicio": AZUL, "centro": "k", "final": ROJO}
for pos, (ib, t, q, h, o, As) in HG.items():
    m = t <= 640
    a.plot(t[m], q[m], color=cols[pos], lw=1.3, label=f"entrada, pico al {pos}")
    a.plot(t[m], o[m], color=cols[pos], lw=1.3, ls=":")
a.axhline(O_max, color=VERDE, ls="--")
a.set_xlabel("tiempo (min)"); a.set_ylabel("caudal (m³/s)"); a.legend(frameon=False, fontsize=8, title="punteado: salida del tanque", title_fontsize=8)
a.set_title("(b) Bloques alternos de 6 h y tiempo–área", loc="left", fontsize=10.5)
a = ax[2]
a.plot(TR.d_min, TR.V_tanque_m3, "-o", ms=3, color="k", label="trapecios (según d)")
for pos in ["inicio", "centro", "final"]:
    a.axhline(BA.set_index("posicion").loc[pos, "V_tanque_m3"], color=cols[pos], ls="--", lw=1.2, label=f"bloques, pico al {pos}")
a.set_xscale("log"); a.set_xlabel("duración de la lluvia d (min)"); a.set_ylabel("volumen del tanque (m³)")
a.legend(frameon=False, fontsize=8); a.set_title(f"(c) Volumen requerido (h_max = {H_MAX} m)", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_4_problemaB.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(1, 3, figsize=(15, 3.4), sharey=True)
for a, pos in zip(ax, ["inicio", "centro", "final"]):
    ib = HG[pos][0]
    a.bar(np.arange(len(ib)) * 10 + 5, ib, width=9.5, color=cols[pos])
    a.set_title(f"Pico al {pos}", loc="left", fontsize=10.5); a.set_xlabel("tiempo (min)")
ax[0].set_ylabel("intensidad (mm/h)")
fig.suptitle(f"Hietogramas de bloques alternos, T = 25 años, 6 h, Δt = 10 min ({(HG['centro'][0] * 10 / 60).sum():.0f} mm)", x=0.01, ha="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_2_4_problemaB_hietogramas.png", dpi=200); plt.close(fig)
print(f"-> figuras en {FIG.relative_to(RAIZ)}")
