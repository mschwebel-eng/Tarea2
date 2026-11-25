"""
10_reforestacion_cottbus.py - Extension: que pasaria si la microcuenca del problema A (Cottbus) se reforesta.

Tres escenarios para la microcuenca de 0.44 km2 (hoy: 83 % pastizal, 17 % bosque, WorldCover):
  * bosque nativo: la vegetacion natural potencial de la llanura humeda del Spree, robledal de roble pedunculado con carpe
    (Quercus robur, Carpinus betulus) y alisedas de aliso negro (Alnus glutinosa) en los suelos mas humedos (Hofmann y Pommer, 2005);
  * monocultivo de pino silvestre (Pinus sylvestris), el bosque plantado dominante en Brandeburgo.
Balance de agua anual: Zhang et al. (2001), ET/P = (1 + w phi)/(1 + w phi + 1/phi), con w = 0.5 (pastizal) y 2.0 (bosque);
el pino toma 1.6 veces el aumento de ET del bosque nativo (Bosch y Hewlett, 1982: ~40 mm de caudal por cada 10 % de coniferas
frente a ~25 mm de latifoliadas). phi = ETo/P con la lluvia y la ETo FAO-56 de la estacion DWD 00880 (datos diarios KL, 1991-2025;
radiacion solar por la ecuacion de Angstrom con las horas de sol, FAO-56 ec. 35; e_a de la presion de vapor medida).
Balance de energia: calor latente LE = ET lambda; sol absorbido extra por el menor albedo (pastizal 0.22, latifoliado 0.16,
pino 0.10; Oke, 1987); calor sensible H = Rn - LE; razon de Bowen H/LE.
Diseno: C(T = 25) de bosque en zonas planas (Chow et al., 1988, tabla 15.1.1) en vez del ponderado actual -> caudal y diametro
de la alcantarilla del problema A (el tc de Kirpich solo depende del cauce), y riesgo de inundacion: periodo de retorno que
aguanta el tubo instalado y su riesgo en 30 anos, con C(T) de pastizal y de bosque.
Salidas: productos/punto2/reforestacion_cottbus_parametros.csv, reforestacion_cottbus_escenarios.csv
"""
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "codigo/punto1"))
import fao56 as F
sys.path.insert(0, str(RAIZ / "codigo/punto2"))
import distribuciones as Dd
from scipy.optimize import brentq

OUT = RAIZ / "productos/punto2"
LAT, Z = 51.7759, 69.0                                       # estacion 00880
K = 2.45e6 / 3.1536e7                                        # 1 mm/a de ET = 0.0777 W/m2
ALB = {"pastizal": 0.22, "nativo": 0.16, "pino": 0.10}
C_BOSQUE_T25 = 0.31                                          # Chow, tabla 15.1.1, bosque, pendiente 0-2 %, T = 25

zf = zipfile.ZipFile(RAIZ / "datos/punto2/dwd_diario/tageswerte_KL_00880_18870101_20251231_hist.zip")
d = pd.read_csv(zf.open([n for n in zf.namelist() if n.startswith("produkt")][0]), sep=";", na_values=-999, skipinitialspace=True)
d.columns = d.columns.str.strip()
d.index = pd.to_datetime(d.MESS_DATUM.astype(str)); d = d.loc["1991-01-01":"2025-12-31"]


def eto_dia(tmax, tmin, ea, sdk, fm, pm, idx):
    ra = F.ra(LAT, idx.day_of_year)
    phi = np.radians(LAT); dec = 0.409 * np.sin(2 * np.pi * idx.day_of_year / 365 - 1.39)
    N = 24 / np.pi * np.arccos(-np.tan(phi) * np.tan(dec))   # duracion del dia (h), ec. 34
    rs = (0.25 + 0.50 * np.clip(sdk / N, 0, 1)) * ra         # Angstrom, ec. 35
    rn = (1 - 0.23) * rs - F.rnl(tmax, tmin, ea, rs, F.rso(ra, Z))
    eto, _, _ = F.eto_pm((tmax + tmin) / 2, F.u2_desde_uz(fm), F.es_diaria(tmax, tmin), ea, rn, 0.0, pm / 10)
    return eto, rs, rn


v = d[["RSK", "TXK", "TNK", "VPM", "SDK", "FM", "PM"]].dropna()
ea = v.VPM / 10
eto, rs, rn = eto_dia(v.TXK, v.TNK, ea, v.SDK, v.FM, v.PM, v.index)
# sensibilidad de la ETo a +1 C con humedad relativa constante
f_ea = F.e0((v.TXK + v.TNK) / 2 + 1) / F.e0((v.TXK + v.TNK) / 2)
eto1, _, _ = eto_dia(v.TXK + 1, v.TNK + 1, ea * f_ea, v.SDK, v.FM, v.PM, v.index)
anual = pd.DataFrame({"P": d.RSK.groupby(d.index.year).sum(min_count=330), "n": v.groupby(v.index.year).size(),
                      "ETo": eto.groupby(v.index.year).sum()})
anual = anual[anual.n >= 330]
P = float(anual.P.mean()); ETo = float((anual.ETo * 365.25 / anual.n).mean()); phi = ETo / P
sT = float(eto1.sum() / eto.sum() - 1)
Rs = float(rs.mean()) * 1e6 / 86400; Rn = float(rn.mean()) * 1e6 / 86400

zh = lambda phi_, w: (1 + w * phi_) / (1 + w * phi_ + 1 / phi_)
desc = pd.read_csv(OUT / "microcuenca_dgm_descripcion.csv", index_col=0).iloc[:, 0]
fb0 = float(desc["cobertura_bosque_%"]) / 100; fp0 = 1 - fb0
ra_ = pd.read_csv(OUT / "problemaA_resumen.csv", index_col=0).valor
DN = np.array([0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.20, 1.40, 1.60, 1.80, 2.00])
Dcalc = lambda Q: (0.013 * Q / (0.312 * 0.005 ** 0.5)) ** (3 / 8)


# riesgo de inundacion: periodo de retorno que aguanta el tubo instalado (DN 1.00 m) con C(T) de Chow (tabla 15.1.1)
ip = pd.read_csv(OUT / "idf_parametros.csv").set_index("parametro").valor
TS = np.array([2, 5, 10, 25, 50, 100])
C_PAST = np.array([0.25, 0.28, 0.30, 0.34, 0.37, 0.41]); C_BOS = np.array([0.22, 0.25, 0.28, 0.31, 0.35, 0.39])
i_tc = lambda T: Dd._gev_q(ip.gev_mu, ip.gev_sigma, ip.gev_xi, T) / (ra_.tc_min / 60 + ip.theta_h) ** ip.eta


def T_tubo(f_bosque):
    """T cuya lluvia de duracion tc llena el tubo (Qcap), con C(T) ponderado por cobertura (el C de tabla se mantiene sobre T = 100)."""
    C = lambda T: (1 - f_bosque) * np.interp(T, TS, C_PAST) + f_bosque * np.interp(T, TS, C_BOS)
    g = lambda lt: C(10 ** lt) * i_tc(10 ** lt) * desc.area_km2 * ra_.FRA / 3.6 - ra_.Qcap_m3_s
    return 10 ** brentq(g, np.log10(2.0), 5.0)


def escenario(f_bosque, tipo, beta=0.0):
    """f_bosque: fraccion de bosque (0-1); tipo: 'nativo' o 'pino' para el bosque NUEVO (el 17 % actual se toma como nativo)."""
    phi_ = ETo * (1 + sT * beta * (f_bosque - fb0)) / P
    et_p, et_b = P * zh(phi_, 0.5), P * zh(phi_, 2.0)
    et_nuevo = et_b if tipo == "nativo" else et_p + 1.6 * (et_b - et_p)
    extra = max(f_bosque - fb0, 0)
    ET = (1 - f_bosque) * et_p + min(f_bosque, fb0) * et_b + extra * et_nuevo
    alb = (1 - f_bosque) * ALB["pastizal"] + min(f_bosque, fb0) * ALB["nativo"] + extra * ALB[tipo]
    alb0 = fp0 * ALB["pastizal"] + fb0 * ALB["nativo"]
    sol = (alb0 - alb) * Rs; LE = ET * K; H = Rn + sol - LE
    C = ((1 - f_bosque) * 0.34 + f_bosque * C_BOSQUE_T25)    # Chow T = 25: pastizal 0.34, bosque 0.31
    Q = ra_.Q_m3_s * C / ra_.C
    return {"ET_mm": ET, "Q_mm": P - ET, "Q_m3_anio": (P - ET) / 1000 * desc.area_km2 * 1e6, "LE_W_m2": LE, "sol_extra_W_m2": sol,
            "H_W_m2": H, "bowen": H / LE, "C_T25": C, "Qp_m3_s": Q, "D_calc_m": Dcalc(Q), "DN_m": DN[np.searchsorted(DN, Dcalc(Q))],
            "T_tubo_anios": T_tubo(f_bosque), "riesgo_30a_%": 100 * (1 - (1 - 1 / T_tubo(f_bosque)) ** 30)}


pd.Series({"P_mm": P, "ETo_mm": ETo, "phi": phi, "sT_por_C": sT, "Rs_W_m2": Rs, "Rn_W_m2": Rn, "bosque_hoy": fb0,
           "albedo_pastizal": ALB["pastizal"], "albedo_nativo": ALB["nativo"], "albedo_pino": ALB["pino"],
           "C_hoy": ra_.C, "C_bosque": C_BOSQUE_T25, "Qp_hoy_m3_s": ra_.Q_m3_s, "anios": len(anual)}).round(5).to_csv(
    OUT / "reforestacion_cottbus_parametros.csv", header=["valor"])
filas = [{"escenario": e, "bosque_%": 100 * f, "tipo": t, **escenario(f, t)}
         for e, f, t in [("hoy", fb0, "nativo"), ("sin bosque", 0.0, "nativo"), ("100 % bosque nativo", 1.0, "nativo"),
                         ("100 % monocultivo de pino", 1.0, "pino")]]
ES = pd.DataFrame(filas); ES["dQ_%"] = 100 * (ES.Q_mm / ES.Q_mm.iloc[0] - 1)
ES.round(4).to_csv(OUT / "reforestacion_cottbus_escenarios.csv", index=False)
print(f"Cottbus {anual.index.min()}-{anual.index.max()} ({len(anual)} anos): P = {P:.0f} mm, ETo = {ETo:.0f} mm, phi = {phi:.2f}, "
      f"ETo +{100*sT:.1f} %/C, Rs = {Rs:.0f} W/m2, Rn = {Rn:.0f} W/m2")
print(ES[["escenario", "ET_mm", "Q_mm", "dQ_%", "LE_W_m2", "sol_extra_W_m2", "bowen", "C_T25", "Qp_m3_s", "DN_m", "T_tubo_anios", "riesgo_30a_%"]].round(2).to_string(index=False))
