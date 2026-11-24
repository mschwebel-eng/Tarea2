"""
03_eto_diaria_cuenca.py - Apartado 1.1.a, paso 3: ETo FAO-56 diaria 1981-2025 en la cuenca.

Para cada una de las 30 celdas de ERA5-Land (pesos de la Tarea 1):
  horario (UTC) -> dia local (UTC-5) -> ETo diaria con la ec. 6 (G = 0, ec. 42)
y luego promedio de la cuenca ponderado por el area de cada celda dentro de la divisoria.

Decisiones (justificar en el informe):
  * La ETo se calcula en cada celda y despues se promedia (la ecuacion no es lineal; promediar
    primero las variables y despues calcular es otra version del error por promediar, que tambien
    se reporta como sensibilidad).
  * gamma y Rso con la elevacion media de la cuenca, 2557 m (CAMELS-PE), como pide la guia.
    Sensibilidad: gamma con la presion diaria del modelo en cada celda.
  * u2 con la ec. 47 a partir de la magnitud HORARIA del viento a 10 m.

Salidas (productos/punto1/):
  forzantes_diarios_celdas.csv.gz   variables diarias por celda (cache para los scripts siguientes)
  eto_diaria_cuenca.csv             ETo y forzantes diarios de la cuenca
  eto_mensual_cuenca.csv            sumas y medias mensuales
  eto_climatologia_mensual.csv      ciclo anual (1981-2025)
  figuras/fig_1_1a_*.png
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
from lectura_era5land import leer_horario, diario_local, PESOS, RAIZ

Z_CUENCA = 2557.0
P_CUENCA = F.presion_desde_z(Z_CUENCA)
OUT = RAIZ / "productos/punto1"
FIG = OUT / "figuras"
FIG.mkdir(parents=True, exist_ok=True)
CACHE = OUT / "forzantes_diarios_celdas.csv.gz"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
AZUL, ROJO, NARANJA, GRIS = "#1d4ed8", "#c2452a", "#b07a0c", "#5b6475"


def eto_celda(d, lat):
    """ETo diaria y sus terminos para un DataFrame diario de una celda."""
    d = F.eto_desde_diario(d, lat, Z_CUENCA, P_CUENCA)
    eto_pc, _, _ = F.eto_pm(d.t, d.u2, d.es, d.ea, d.rn, 0.0, d.p)   # sensibilidad: presion de la celda
    return d.assign(eto_pcelda=eto_pc)


# ---------------------------------------------------------------- 1) diario por celda (con cache)
pesos = pd.read_csv(PESOS)
if CACHE.exists():
    todo = pd.read_csv(CACHE, parse_dates=["fecha"])
    print(f"leido el cache {CACHE.name}")
else:
    partes = []
    for k, r in pesos.iterrows():
        d = diario_local(leer_horario(r.lat, r.lon))
        d["lat"], d["lon"] = r.lat, r.lon
        partes.append(d.reset_index())
        print(f"  celda {k+1:2d}/30  lat {r.lat} lon {r.lon}: {len(d)} dias")
    todo = pd.concat(partes, ignore_index=True)
    todo.round(4).to_csv(CACHE, index=False)

celdas = []
for (lat, lon), d in todo.groupby(["lat", "lon"]):
    d = eto_celda(d.set_index("fecha").sort_index(), lat)
    w = pesos.loc[(pesos.lat.round(1) == round(lat, 1)) & (pesos.lon.round(1) == round(lon, 1)), "area_en_cuenca_km2"].iloc[0]
    celdas.append(d.assign(w=w))
cel = pd.concat(celdas)

# verificacion contra el caso a mano (script 02)
chk = cel[(cel.lat == -7.6) & (cel.lon == -78.5)].loc["1981-01-15", "eto"]
print(f"verificacion: celda central 1981-01-15 ETo = {chk:.3f} mm/d (script 02: 3.494)")
assert abs(chk - 3.494) < 0.001, "no coincide con el calculo a mano"

# ---------------------------------------------------------------- 2) promedio ponderado de la cuenca
vars_ = ["tmax", "tmin", "t", "td", "es", "ea", "vpd", "u10", "u2", "p", "rs", "ra", "rso", "rns", "rnl", "rn",
         "eto", "eto_rad", "eto_aero", "eto_pcelda"]
cel_w = cel[vars_].multiply(cel.w, axis=0)
cuenca = cel_w.groupby(level=0).sum().div(cel.w.groupby(level=0).sum(), axis=0)
cuenca.index.name = "fecha"
cuenca.round(4).to_csv(OUT / "eto_diaria_cuenca.csv")

# variante: promediar primero las variables y calcular despues (error por promediar en el espacio)
c = cuenca
eto_var1, _, _ = F.eto_pm(c.t, c.u2, c.es, c.ea, c.rn, 0.0, P_CUENCA)

# ---------------------------------------------------------------- 3) mensual y anual
suma = ["eto", "eto_rad", "eto_aero", "eto_pcelda", "rs", "rn", "ra"]
mes = cuenca[suma].resample("MS").sum()
mes = mes.join(cuenca.drop(columns=suma).resample("MS").mean())
mes["dias"] = cuenca.eto.resample("MS").count()
mes["eto_var_primero"] = eto_var1.resample("MS").sum()
mes = mes[mes.dias >= 28]
mes.round(3).to_csv(OUT / "eto_mensual_cuenca.csv")

cam = pd.read_csv(RAIZ / "datos/punto1/tarea1/PE_47E0A2A8.csv", parse_dates=["date"], index_col="date")
p_mes = cam.prec.resample("MS").sum().reindex(mes.index)
clim = mes.groupby(mes.index.month).mean()
clim["eto_p10"] = mes.groupby(mes.index.month).eto.quantile(0.1)
clim["eto_p90"] = mes.groupby(mes.index.month).eto.quantile(0.9)
clim["p_camels"] = p_mes.groupby(p_mes.index.month).mean()
clim["frac_rad"] = clim.eto_rad / clim.eto
clim.index.name = "mes"
clim.round(3).to_csv(OUT / "eto_climatologia_mensual.csv")

anual = mes.eto.resample("YS").sum()[mes.dias.resample("YS").count() == 12]
print(f"\nETo media anual de la cuenca 1981-2025: {anual.mean():.0f} mm/a (min {anual.min():.0f}, max {anual.max():.0f})")
print(f"  termino radiativo {100*clim.eto_rad.sum()/clim.eto.sum():.0f} % ; aerodinamico {100*clim.eto_aero.sum()/clim.eto.sum():.0f} %")
print(f"  sensibilidad gamma con presion de cada celda: {100*(mes.eto_pcelda.sum()/mes.eto.sum()-1):+.1f} %")
print(f"  sensibilidad 'promediar variables primero': {100*(mes.eto_var_primero.sum()/mes.eto.sum()-1):+.2f} %")
print(f"  P media anual CAMELS-PE 1981-2025: {p_mes.resample('YS').sum().loc[anual.index].mean():.0f} mm/a")
print(clim[["eto", "eto_rad", "eto_aero", "p_camels", "rs", "rn", "t", "vpd", "u2"]].round(2).to_string())

# por celda: ETo anual media vs elevacion del modelo (presion -> ec. 7 inversa)
pc = cel.groupby(["lat", "lon"]).agg(eto=("eto", "mean"), p=("p", "mean"), t=("t", "mean"), w=("w", "first"))
pc["eto_anual"] = pc.eto * 365.25
pc["z_modelo"] = F.z_desde_presion(pc.p)
pc.round(3).to_csv(OUT / "eto_por_celda.csv")

# ---------------------------------------------------------------- 4) figuras
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
x = np.arange(1, 13)

fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
a = ax[0]
a.bar(x, clim.eto_rad, color=NARANJA, label="término radiativo")
a.bar(x, clim.eto_aero, bottom=clim.eto_rad, color=GRIS, label="término aerodinámico")
a.errorbar(x, clim.eto, yerr=[clim.eto - clim.eto_p10, clim.eto_p90 - clim.eto], fmt="none", ecolor="k", capsize=3,
           lw=1, label="P10–P90 entre años")
a.plot(x, clim.p_camels, "o-", color=AZUL, label="lluvia $P_L$ (CAMELS-PE)")
a.set_xticks(x, MESES); a.set_ylabel("mm/mes"); a.legend(frameon=False, fontsize=8.5)
a.set_title("(a) ETo FAO-56 de la cuenca y lluvia, 1981–2025", loc="left", fontsize=10.5)
a = ax[1]
a.plot(x, clim.ra / clim.dias, "--", color=GRIS, label="$R_a$ (tope de la atmósfera)")
a.plot(x, clim.rs / clim.dias, "-o", color=NARANJA, label="$R_s$ (llega al suelo)")
a.plot(x, clim.rn / clim.dias, "-s", color=ROJO, label="$R_n$ del pasto de referencia")
a.set_xticks(x, MESES); a.set_ylabel("MJ m$^{-2}$ d$^{-1}$"); a.legend(frameon=False, fontsize=8.5)
a.set_title("(b) Radiación diaria media", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1a_ciclo_anual.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
ax[0].fill_between(x, clim.tmin, clim.tmax, color=ROJO, alpha=.15, label="Tmín–Tmáx")
ax[0].plot(x, clim.t, "o-", color=ROJO, label="T media"); ax[0].plot(x, clim.td, "o-", color=AZUL, label="T rocío")
ax[0].set_ylabel("°C"); ax[0].set_title("(a) Temperatura y rocío", loc="left", fontsize=10.5)
ax[1].plot(x, clim.vpd, "o-", color=ROJO); ax[1].set_ylabel("kPa")
ax[1].set_title("(b) Déficit de vapor $e_s-e_a$", loc="left", fontsize=10.5)
ax[2].plot(x, clim.u2, "o-", color=GRIS); ax[2].set_ylabel("m s$^{-1}$")
ax[2].set_title("(c) Viento a 2 m, $u_2$", loc="left", fontsize=10.5)
for a in ax: a.set_xticks(x, [m[0] for m in MESES])
ax[0].legend(frameon=False, fontsize=8.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1a_forzantes.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(12, 3.4))
ax.plot(mes.index, mes.eto, color=NARANJA, lw=.8, label="ETo mensual")
ax.plot(mes.eto.rolling(12, center=True).mean().index, mes.eto.rolling(12, center=True).mean(), color="k", lw=1.6,
        label="media móvil 12 meses")
ax.set_ylabel("mm/mes"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
ax.set_title("ETo FAO-56 mensual de la cuenca del Chicama hasta El Tambo (ERA5-Land, 30 celdas ponderadas)", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1a_serie_mensual.png", dpi=200); plt.close(fig)

fig, ax = plt.subplots(figsize=(5.5, 4.2))
sc = ax.scatter(pc.z_modelo, pc.eto_anual, s=20 + pc.w / 1.5, c=pc.t, cmap="coolwarm", edgecolor="k", lw=.4)
fig.colorbar(sc, label="T media (°C)")
ax.set_xlabel("elevación de la celda en el modelo (m, desde la presión)"); ax.set_ylabel("ETo media (mm/año)")
ax.set_title("ETo por celda (tamaño: área dentro de la cuenca)", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "fig_1_1a_eto_elevacion.png", dpi=200); plt.close(fig)
print(f"\nfiguras en {FIG.relative_to(RAIZ)}")
