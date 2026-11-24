"""
lectura_era5land.py - Lectura de las series horarias de ERA5-Land por celda y agregacion a dias locales.

Convenciones verificadas en el paso 1 del apartado 1.1.a (ver informe):
  * valid_time esta en UTC; Peru esta en UTC-5 y no usa horario de verano.
  * Variables instantaneas (t2m, d2m, u10, v10, sp): el valor es el de ese instante.
    Se asignan al dia local de (valid_time - 5 h): horas locales 00:00 ... 23:00.
  * ssrd es la energia de LA HORA QUE TERMINA en valid_time (J m-2). La hora local que
    termina a las 01:00 es la primera del dia, y la que termina a las 24:00 la ultima, asi
    que se asigna al dia local de (valid_time - 6 h).
  * ssrd trae unos pocos -2 J m-2 a las 19:00 locales (residuo numerico): se ponen en 0.
"""
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DIR_H = RAIZ / "datos/punto1/era5land/horario_puntos"
PESOS = RAIZ / "datos/punto1/tarea1/pesos_era5land_cuenca.csv"


def archivo_celda(lat, lon):
    return DIR_H / f"era5land_ts_lat{lat:+.1f}_lon{lon:+.1f}.zip"


def leer_horario(lat=None, lon=None, ruta=None):
    """Todas las variables horarias de una celda (o de un zip dado en `ruta`) con indice valid_time (UTC)."""
    partes = []
    with zipfile.ZipFile(ruta or archivo_celda(lat, lon)) as z:
        for n in z.namelist():
            d = pd.read_csv(z.open(n), parse_dates=["valid_time"]).drop(columns=["latitude", "longitude"])
            partes.append(d.set_index("valid_time"))
    h = pd.concat(partes, axis=1).sort_index()
    h["ssrd"] = h["ssrd"].clip(lower=0)
    return h


def diario_local(h):
    """Agrega una serie horaria (UTC) a dias locales de Peru. Solo conserva dias con 24 horas."""
    inst = pd.DataFrame({
        "t": h.t2m - 273.15,
        "td": h.d2m - 273.15,
        "u10": np.hypot(h.u10, h.v10),          # magnitud HORARIA, antes de promediar
        "p": h.sp / 1000.0,                      # kPa
    })
    dia_i = (h.index - pd.Timedelta(hours=5)).floor("D")
    g = inst.groupby(dia_i)
    d = pd.DataFrame({
        "tmax": g.t.max(), "tmin": g.t.min(), "tmedia_h": g.t.mean(),
        "td": g.td.mean(), "u10": g.u10.mean(), "p": g.p.mean(), "n_inst": g.t.count(),
    })
    dia_a = (h.index - pd.Timedelta(hours=6)).floor("D")
    ga = h.ssrd.groupby(dia_a)
    d["rs"] = ga.sum() / 1e6                     # MJ m-2 d-1
    d["n_acum"] = ga.count()
    d = d[(d.n_inst == 24) & (d.n_acum == 24)].drop(columns=["n_inst", "n_acum"])
    d.index.name = "fecha"
    return d
