"""
17_reforestacion.py - Extension de 1.5: efecto de reforestar la cuenca del Chicama en la ET real, el caudal y el balance de energia.

Modelo de equilibrio anual (el mismo de la diapositiva interactiva p15-refo del sitio):
  1. Budyko-Fu: ET/P = 1 + phi - (1 + phi^w)^(1/w), phi = ETo/P, con w0 = 1.57 calibrado en 1.3 (12_energia_o_agua.py).
  2. w crece linealmente con la cobertura de bosque f: w = w0 + dw (f - f0)/100, f0 = 15 % (CAMELS-PE).
     - Bosque nativo (montano y de quenua): dw tal que pasar de pastizal a bosque multiplique la ET por la razon de las curvas
       de Zhang et al. (2001) a esta aridez (w = 2.0 bosque, 0.5 pastizal).
     - Monocultivo de pino: 1.6 veces ese aumento (Bosch y Hewlett, 1982: ~40 mm de caudal por cada 10 % de coniferas
       frente a ~25 mm de latifoliadas).
  3. Temperatura: dT = beta (f - f0)/100; ETo cambia sT por grado (sensibilidad a HR constante de 10_explicar_diferencias.py).
     beta es incierto (-0.5 a +0.5 C por 100 % de bosque); el caso central usa beta = 0.
  4. Lluvia: P = P0 + rho (ET - ET0) + niebla, con reciclaje rho = 5 % y niebla de 300 mm/a en la franja de la inversion
     (4.3 % de la cuenca, 16_niebla_nubosidad.py).
  5. Energia: calor latente LE = ET lambda; sol absorbido extra = 0.08 (f - f0)/100 Rs (albedo 0.20 -> 0.12);
     calor sensible H = Rn + extra - LE (flujo al suelo ~0 en el ano); razon de Bowen H/LE.
Salidas: productos/punto1/reforestacion_parametros.csv, reforestacion_escenarios.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

RAIZ = Path(__file__).resolve().parents[2]
P1 = RAIZ / "productos/punto1"
K = 2.45e6 / 3.1536e7                                          # 1 mm/a de ET = 0.0777 W/m2 de calor latente

bz = pd.read_csv(P1 / "budyko_resumen.csv", index_col=0).valor
nz = pd.read_csv(P1 / "niebla_resumen.csv", index_col=0).valor
sz = pd.read_csv(P1 / "sensibilidad_anual_pct.csv", index_col=0)
lp = pd.read_csv(P1 / "et_real_largo_plazo.csv", index_col=0).valor
attr = pd.read_csv(RAIZ / "datos/punto1/tarea1/PE_47E0A2A8_atributos.csv", index_col=0).iloc[:, 0]
em = pd.read_csv(P1 / "eto_mensual_cuenca.csv", parse_dates=["fecha"])
anual = em.groupby(em.fecha.dt.year).agg(eto=("eto", "sum"), n=("eto", "size"))
ETo0 = float(anual.loc[anual.n == 12, "eto"].mean())          # ETo media anual FAO-56 (1.1.a)
phi0, w0, f0 = float(bz.phi), float(bz.omega_fu), float(attr.forest_perc)
P0 = ETo0 / phi0; ET0 = P0 * float(bz.ET_P)
sT = float(sz.loc["FAO-56 PM", "T+1_hr"]) / 100
Rs = float(em.rs.sum() / em.dias.sum()) * 1e6 / 86400           # radiacion solar media (W/m2)
Rn = float(lp["Rn_lambda"]) * K                                 # radiacion neta media (W/m2)
FRANJA = float(nz["area_franja_inversion_seca_%"]) / 100
DALB, RHO, NIEBLA = 0.08, 0.05, 300.0

fu = lambda phi, w: 1 + phi - (1 + phi ** w) ** (1 / w)
zh = lambda phi, w: (1 + w * phi) / (1 + w * phi + 1 / phi)     # Zhang et al. (2001)
Rz = zh(phi0, 2.0) / zh(phi0, 0.5)
dw_para = lambda R: brentq(lambda d: fu(phi0, w0 + (1 - f0 / 100) * d) / fu(phi0, w0 - f0 / 100 * d) - R, 0.01, (w0 - 1.001) / (f0 / 100))
DW = {"nativo": dw_para(Rz), "pino": dw_para(1 + 1.6 * (Rz - 1))}


def modelo(f, tipo, beta=0.0, rho=RHO, niebla=NIEBLA):
    dT = beta * (f - f0) / 100
    ETo = ETo0 * (1 + sT * dT)
    w = w0 + DW[tipo] * (f - f0) / 100
    Pn = FRANJA * (f - f0) / 100 * niebla
    P, ET = P0 + Pn, ET0
    for _ in range(40):                                         # punto fijo: la lluvia depende de la ET por el reciclaje
        ET = P * fu(ETo / P, w)
        P = P0 + rho * (ET - ET0) + Pn
    LE = ET * K; extra = DALB * (f - f0) / 100 * Rs; H = Rn + extra - LE
    return {"dT_C": dT, "ETo_mm": ETo, "P_mm": P, "ET_mm": ET, "Q_mm": P - ET, "niebla_mm": Pn,
            "LE_W_m2": LE, "sol_extra_W_m2": extra, "H_W_m2": H, "bowen": H / LE}


pd.Series({"ETo0_mm": ETo0, "P0_mm": P0, "ET0_mm": ET0, "phi0": phi0, "w0": w0, "f0_%": f0, "sT_por_C": sT, "Rs_W_m2": Rs,
           "Rn_W_m2": Rn, "razon_Zhang": Rz, "dw_nativo": DW["nativo"], "dw_pino": DW["pino"], "franja": FRANJA,
           "dalb": DALB, "reciclaje": RHO, "niebla_mm": NIEBLA}).round(5).to_csv(P1 / "reforestacion_parametros.csv", header=["valor"])

filas = []
for etq, f, tipo in [("hoy", f0, "nativo"), ("sin bosque", 0, "nativo"), ("50 % bosque nativo", 50, "nativo"),
                     ("100 % bosque nativo", 100, "nativo"), ("100 % monocultivo de pino", 100, "pino")]:
    c = modelo(f, tipo)
    c["Q_beta_menos05_mm"] = modelo(f, tipo, -0.5)["Q_mm"]; c["Q_beta_mas05_mm"] = modelo(f, tipo, 0.5)["Q_mm"]
    filas.append({"escenario": etq, "bosque_%": f, "tipo": tipo, **c})
ES = pd.DataFrame(filas); ES["dQ_%"] = 100 * (ES.Q_mm / ES.Q_mm.iloc[0] - 1)
ES.round(3).to_csv(P1 / "reforestacion_escenarios.csv", index=False)
q10 = {t: modelo(f0, t, rho=0, niebla=0)["Q_mm"] - modelo(f0 + 10, t, rho=0, niebla=0)["Q_mm"] for t in DW}
print(f"ETo0 = {ETo0:.0f} mm, P0 = {P0:.0f}, ET0 = {ET0:.0f}; razon de Zhang = {Rz:.3f}; dw nativo {DW['nativo']:.3f}, pino {DW['pino']:.3f}")
print(f"comprobacion Bosch-Hewlett: 10 % mas de bosque quita {q10['nativo']:.1f} mm (nativo) y {q10['pino']:.1f} mm (pino)")
print(ES[["escenario", "ET_mm", "Q_mm", "dQ_%", "LE_W_m2", "sol_extra_W_m2", "bowen", "Q_beta_menos05_mm", "Q_beta_mas05_mm"]].round(1).to_string(index=False))
