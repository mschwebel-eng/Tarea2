"""
01_completitud_dwd_cottbus.py  -  Punto 2.1: completitud anual de la lluvia de 10 min en Cottbus

Fuente : DWD Climate Data Center, precipitacion de 10 minutos, estacion 00880 (Cottbus),
         https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/precipitation/historical/
Entrada: datos/punto2/dwd_00880/10minutenwerte_nieder_00880_*_hist.zip (se descargan si faltan)
Salida : productos/punto2/completitud_anual_cottbus_00880.csv

Criterio de anio valido (propuesta inicial, a discutir en el grupo y a probar en sensibilidad):
  >= 80 % de los intervalos de 10 min con dato en el anio  Y
  >= 90 % en mayo-septiembre (temporada de tormentas convectivas en Brandeburgo).
Faltante en el DWD: RWS_10 = -999. Se cuenta como dato todo valor distinto de -999.
"""
from pathlib import Path
import calendar
import urllib.request
import zipfile

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / "datos/punto2/dwd_00880"
SALIDA = RAIZ / "productos/punto2/completitud_anual_cottbus_00880.csv"
BASE = ("https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/"
        "10_minutes/precipitation/historical/")
TRAMOS = ["19911031_19991231", "20000101_20091231", "20100101_20191231", "20200101_20251231"]
UMBRAL_ANIO, UMBRAL_VERANO = 80.0, 90.0


def leer_tramo(tramo):
    z = DIR / f"10minutenwerte_nieder_00880_{tramo}_hist.zip"
    if not z.exists():
        DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(BASE + z.name, z)          # si falla, el error se ve
    with zipfile.ZipFile(z) as zf:
        nombre = [n for n in zf.namelist() if n.startswith("produkt")][0]
        with zf.open(nombre) as fh:
            df = pd.read_csv(fh, sep=";", skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df["t"] = pd.to_datetime(df["MESS_DATUM"].astype(str), format="%Y%m%d%H%M")
    return df[["t", "RWS_10"]]


d = pd.concat([leer_tramo(t) for t in TRAMOS], ignore_index=True)
d = d.drop_duplicates("t").sort_values("t")
d["valido"] = d["RWS_10"] > -998
d["anio"], d["mes"] = d.t.dt.year, d.t.dt.month
d["verano"] = d.mes.between(5, 9)

filas = []
for anio, g in d.groupby("anio"):
    esperado = (366 if calendar.isleap(anio) else 365) * 144
    esperado_v = 153 * 144                                  # 1 may - 30 sep
    v = g[g.valido]
    filas.append({
        "anio": anio,
        "pct_anio": round(100 * len(v) / esperado, 1),
        "pct_may_sep": round(100 * v.verano.sum() / esperado_v, 1),
        "max_10min_mm": v.RWS_10.max() if len(v) else np.nan,
        "total_mm": round(v.RWS_10.sum(), 0),
    })
t = pd.DataFrame(filas)
t["valido"] = (t.pct_anio >= UMBRAL_ANIO) & (t.pct_may_sep >= UMBRAL_VERANO)
SALIDA.parent.mkdir(parents=True, exist_ok=True)
t.to_csv(SALIDA, index=False)
print(t.to_string(index=False))
print(f"\nanios validos ({UMBRAL_ANIO}% anio y {UMBRAL_VERANO}% may-sep): {int(t.valido.sum())}"
      f"  ->  {SALIDA.relative_to(RAIZ)}")
