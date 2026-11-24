"""
07_prueba_estacion_cajamarca.py - Apartado 1.1.b, prueba 1: ETo con una estacion meteorologica.

Estacion: Cajamarca aeropuerto (WMO 84472, GSOD 84472099999), 7.139 S, 78.489 O, 2676 m, ~50 km al NE
del cierre de El Tambo, en un valle interandino de la misma cordillera.
Fuente: NOAA Global Summary of the Day (GSOD), resumenes diarios de los mensajes sinopticos:
TEMP, DEWP (F), MAX, MIN (F; 24 h), WDSP (nudos), STP (hPa). Se descargan a datos/punto1/estacion_cajamarca_gsod/.

Por que GSOD y no GHCNh horario: el aeropuerto solo reporta de 04:00 a 18:00 hora local (09-23 UTC), asi que
el horario no ve la noche y no da Tmin. En GSOD la bandera '*' indica que el extremo se derivo de las
observaciones horarias: se acepta para MAX (el maximo cae en horas de reporte) y se descarta para MIN.
Limitacion: WDSP es el promedio de observaciones diurnas, cuando el viento es mas fuerte (sesgo alto).

ETo de la estacion con FAO-56: Rs con la ec. 50 (kRs = 0.16, interior; FAO-56 cap. 3), P con la ec. 7 a 2676 m,
ea = e0(Tdew), u2 con la ec. 47 (anemometro a 10 m). Se compara DIA A DIA con ERA5-Land en el mismo punto,
y se atribuye la diferencia a cada variable cambiando una a la vez (estacion -> reanalisis).

Salidas: productos/punto1/prueba_estacion_cajamarca_*.csv, figuras/fig_1_1b_estacion.png
"""
from pathlib import Path
import sys
import urllib.request

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fao56 as F
from lectura_era5land import leer_horario, diario_local, RAIZ

LAT, LON, Z_EST = -7.139, -78.489, 2676.0
DIR = RAIZ / "datos/punto1/estacion_cajamarca_gsod"
OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
KRS = 0.16
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475"
f2c = lambda x: (x - 32) * 5 / 9

# ---------------------------------------------------------------- 1) GSOD
DIR.mkdir(parents=True, exist_ok=True)
partes = []
for anio in range(1981, 2026):
    f = DIR / f"84472099999_{anio}.csv"
    if not f.exists():
        try:
            urllib.request.urlretrieve(f"https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{anio}/84472099999.csv", f)
        except Exception as e:
            print(f"  sin archivo GSOD {anio}: {e}")
            continue
    partes.append(pd.read_csv(f, dtype=str))
g = pd.concat(partes, ignore_index=True)
g.index = pd.to_datetime(g.DATE)
g = g[~g.index.duplicated()]
num = lambda c, malo: pd.to_numeric(g[c].str.strip(), errors="coerce").where(lambda s: s < malo)
est = pd.DataFrame({
    "tmax": f2c(num("MAX", 9999)), "tmin": f2c(num("MIN", 9999)),
    "tmax_flag": g.MAX_ATTRIBUTES.str.strip(), "tmin_flag": g.MIN_ATTRIBUTES.str.strip(),
    "td": f2c(num("DEWP", 9999)), "n_td": pd.to_numeric(g.DEWP_ATTRIBUTES, errors="coerce"),
    "u10": num("WDSP", 999) * 0.514444, "n_obs": pd.to_numeric(g.TEMP_ATTRIBUTES, errors="coerce"),
}).sort_index()
n0 = len(est)
# Tmax con bandera '*' se acepta: el maximo (~13 h local) cae dentro de las horas de reporte (04-18 h local).
# Tmin con '*' NO: la minima ocurre de madrugada, fuera de esas horas, y saldria demasiado alta.
ok = (est.tmin_flag != "*") & est[["tmax", "tmin", "td", "u10"]].notna().all(axis=1) \
     & (est.tmax > est.tmin) & (est.n_td >= 4)
est = est[ok]
print(f"GSOD Cajamarca: {n0} dias con algun dato; {len(est)} dias validos para ETo "
      f"({est.index.min().date()} a {est.index.max().date()})")

# ---------------------------------------------------------------- 2) ERA5-Land en el punto
era = diario_local(leer_horario(ruta=RAIZ / "datos/punto1/era5land/estacion_cajamarca/era5land_ts_cajamarca_SPJR.zip"))
z_mod = float(F.z_desde_presion(era.p.mean()))
print(f"ERA5-Land en el punto: presion media {era.p.mean():.1f} kPa -> elevacion del modelo ~{z_mod:.0f} m (estacion {Z_EST:.0f} m)")

comun = est.index.intersection(era.index)
e, r = est.loc[comun].copy(), era.loc[comun].copy()
print(f"dias comunes estacion-ERA5-Land: {len(comun)}")

P_EST = F.presion_desde_z(Z_EST)


def eto(d, rs_modo):
    """ETo de un DataFrame diario (tmax, tmin, td, u10 y, si rs_modo == 'medida', rs)."""
    ra = F.ra(LAT, d.index.day_of_year)
    rs = d.rs if rs_modo == "medida" else KRS * np.sqrt(d.tmax - d.tmin) * ra       # ec. 50
    dd = d.assign(rs=np.minimum(rs, F.rso(ra, Z_EST)))
    return F.eto_desde_diario(dd, LAT, Z_EST, P_EST)


E = eto(e, "ec50")
R = eto(r, "medida")
# variante: reanalisis llevado a la elevacion de la estacion con los gradientes del paso 5 (script 05)
GRAD = {"tmax": -5.42e-3, "tmin": -5.08e-3, "td": -5.32e-3}
rc = r.copy()
for v, gz in GRAD.items():
    rc[v] = r[v] + gz * (Z_EST - z_mod)
Rc = eto(rc, "medida")
print(f"ERA5-Land corregido a {Z_EST:.0f} m: Tmax {rc.tmax.mean():.2f}  Tmin {rc.tmin.mean():.2f}  ETo {Rc.eto.mean():.2f} mm/d")
R50 = eto(r, "ec50")                         # reanalisis con la misma Rs de la ec. 50: aisla el metodo de Rs
pd.DataFrame({"eto_estacion": E.eto, "eto_era5land": R.eto, "tmax_est": e.tmax, "tmin_est": e.tmin}).round(4).to_csv(
    OUT / "prueba_estacion_cajamarca_diaria.csv")                     # para las tendencias de 1.4

# atribucion: se reemplaza en la ETo del reanalisis una variable a la vez por la de la estacion
atrib = {}
for v, cols in [("temperatura (Tmax, Tmin)", ["tmax", "tmin"]), ("rocio (ea)", ["td"]), ("viento", ["u10"])]:
    rr = r.copy(); rr[cols] = e[cols]
    atrib[v] = (eto(rr, "medida").eto - R.eto).mean()
rr = r.copy(); rr["rs"] = KRS * np.sqrt(e.tmax - e.tmin) * F.ra(LAT, rr.index.day_of_year)
atrib["radiacion (Rs ec. 50 de la estacion)"] = (eto(rr, "medida").eto - R.eto).mean()

res = pd.DataFrame({
    "variable": ["Tmax (C)", "Tmin (C)", "Tdew (C)", "Tmin - Tdew (C)", "u10 (m/s)", "Rs (MJ m-2 d-1)", "ETo (mm/d)"],
    "estacion": [e.tmax.mean(), e.tmin.mean(), e.td.mean(), (e.tmin - e.td).mean(), e.u10.mean(), E.rs.mean(), E.eto.mean()],
    "era5land": [r.tmax.mean(), r.tmin.mean(), r.td.mean(), (r.tmin - r.td).mean(), r.u10.mean(), R.rs.mean(), R.eto.mean()],
})
res["diferencia"] = res.estacion - res.era5land
res.round(3).to_csv(OUT / "prueba_estacion_cajamarca_resumen.csv", index=False)
print(res.round(2).to_string(index=False))
print(f"\nETo ERA5-Land con Rs de la ec. 50 (sus propios Tmax-Tmin): {R50.eto.mean():.2f} mm/d "
      f"(con Rs del modelo: {R.eto.mean():.2f})")
print("atribucion de ETo_estacion - ETo_ERA5 (cambiando una variable a la vez, mm/d):")
for k, v in atrib.items():
    print(f"   {k:40s} {v:+.2f}")
print(f"   suma {sum(atrib.values()):+.2f}  vs diferencia total {E.eto.mean() - R.eto.mean():+.2f}")
pd.Series(atrib).rename("mm_d").to_csv(OUT / "prueba_estacion_cajamarca_atribucion.csv")

# ciclo anual pareado (mm/mes)
cic = pd.DataFrame({"estacion": E.eto, "era5land": R.eto, "era5land_rs_ec50": R50.eto,
                    "est_tmin_td": e.tmin - e.td, "era_tmin_td": r.tmin - r.td})
cm = cic.groupby(cic.index.month).mean()
dias_mes = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
for c in ["estacion", "era5land", "era5land_rs_ec50"]:
    cm[c + "_mm_mes"] = cm[c] * dias_mes
cm["n_dias"] = cic.groupby(cic.index.month).estacion.count()
cm.index.name = "mes"
cm.round(3).to_csv(OUT / "prueba_estacion_cajamarca_ciclo.csv")

# ---------------------------------------------------------------- figura
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
x = np.arange(1, 13)
fig, ax = plt.subplots(1, 3, figsize=(13, 3.9), gridspec_kw={"width_ratios": [1.2, 1, 1]})
a = ax[0]
a.plot(x, cm.estacion_mm_mes, "o-", color="k", label="estación (GSOD), $R_s$ ec. 50")
a.plot(x, cm.era5land_mm_mes, "s-", color=NARANJA, label="ERA5-Land, $R_s$ del modelo")
a.plot(x, cm.era5land_rs_ec50_mm_mes, "^--", color=NARANJA, alpha=.6, label="ERA5-Land, $R_s$ ec. 50")
a.set_xticks(x, [m[0] for m in MESES]); a.set_ylabel("ETo (mm/mes)"); a.legend(frameon=False, fontsize=8)
a.set_title(f"(a) Cajamarca, {len(comun)} días pareados", loc="left", fontsize=10.5)
a = ax[1]
k = list(atrib.keys()); v = list(atrib.values())
a.barh(range(len(k)), v, color=[ROJO if t > 0 else AZUL for t in v]); a.axvline(0, color="k", lw=.8)
a.set_yticks(range(len(k)), [s.split(" (")[0] for s in k]); a.set_xlabel("efecto sobre ETo (mm/d)")
a.set_title("(b) Qué variable explica la diferencia", loc="left", fontsize=10.5)
a = ax[2]
a.plot(x, cm.est_tmin_td, "o-", color="k", label="estación")
a.plot(x, cm.era_tmin_td, "s-", color=NARANJA, label="ERA5-Land")
a.axhline(2, color=ROJO, ls=":", label="umbral de aridez (Allen, 1996)")
a.set_xticks(x, [m[0] for m in MESES]); a.set_ylabel("Tmín − T rocío (°C)"); a.legend(frameon=False, fontsize=8)
a.set_title("(c) ¿La estación está «regada»?", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1b_estacion.png", dpi=200); plt.close(fig)
print(f"-> {FIG.relative_to(RAIZ) / 'fig_1_1b_estacion.png'}")
