"""
00_disponibilidad_ghcnh_peru.py  -  Punto 2.1: hay lluvia subdiaria cerca de El Tambo?

Cuenta, por anio, cuantos reportes de precipitacion de 1, 3, 6 y 24 h trae la base horaria
GHCNh de NOAA para las estaciones andinas mas cercanas a la cuenca del Chicama.

Entrada : datos/punto2/ghcnh_cache/GHCNh_<ID>_por.psv  (se descargan si faltan; son pesados
          y NO van en el ZIP: son la base completa de cada estacion, ver README)
Salida  : productos/punto2/disponibilidad_ghcnh_peru.csv

Un anio horario completo tiene 8760 horas; uno con reportes de 6 h completos, 1460.
"""
from pathlib import Path
import urllib.request

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CACHE = RAIZ / "datos/punto2/ghcnh_cache"
SALIDA = RAIZ / "productos/punto2/disponibilidad_ghcnh_peru.csv"
URL = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-station/GHCNh_{}_por.psv"

# Estaciones de GHCNh a menos de ~80 km y en la sierra (las de la costa desertica se excluyen:
# otro regimen de lluvia). Distancias aproximadas al punto de cierre (7.574 S, 78.707 O).
ESTACIONES = {
    "PEI0000SPJR": "Cajamarca aeropuerto (2676 m, ~50 km NE)",
    "PEU00084472": "Cajamarca (2621 m, ~50 km NE)",
    "PEM00084479": "San Marcos (2287 m, ~60 km E)",
    "PEA00845050": "Santiago de Chuco (3129 m, ~75 km SE)",
}
COLS = {"precipitation": "p1h", "precipitation_3_hour": "p3h",
        "precipitation_6_hour": "p6h", "precipitation_24_hour": "p24h"}


def asegurar(id_):
    f = CACHE / f"{id_}.psv"
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f"descargando {id_} ...")
        urllib.request.urlretrieve(URL.format(id_), f)      # si falla, el error se ve
    return f


filas = []
for id_, nombre in ESTACIONES.items():
    f = asegurar(id_)
    cab = pd.read_csv(f, sep="|", nrows=0).columns
    usar = ["Year"] + [c for c in COLS if c in cab]
    df = pd.read_csv(f, sep="|", usecols=usar, low_memory=False)
    g = df.groupby("Year")
    res = g.size().rename("registros").to_frame()
    for c in COLS:
        res[COLS[c]] = g[c].count() if c in df else 0
    res = res[(res[list(COLS.values())].sum(axis=1)) > 0]
    res.insert(0, "estacion", nombre)
    res.insert(0, "id", id_)
    filas.append(res.reset_index().rename(columns={"Year": "anio"}))
    print(f"{id_}: {len(res)} anios con algun reporte de lluvia; "
          f"max reportes horarios en un anio = {int(res['p1h'].max()) if len(res) else 0}")

out = pd.concat(filas, ignore_index=True)
out["frac_6h"] = (out["p6h"] / 1460).round(3)           # fraccion de un anio con 4 reportes/dia
SALIDA.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(SALIDA, index=False)
print(f"-> {SALIDA.relative_to(RAIZ)}")
