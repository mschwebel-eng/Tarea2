"""
06_descarga_pruebas_1_1b.py - Datos para poner a prueba la ETo (apartado 1.1.b).

  A) TerraClimate (Abatzoglou et al., 2018), mensual ~4 km, por OPeNDAP (sin registro):
     pet (ETo Penman-Monteith de referencia), tmax, tmin, vpd, ws, srad, aet, ppt.
     Recorte: 7.3-8.1 S, 78.9-78.1 O, 1981-2024.
  B) ERA5-Land horario en el punto de la estacion GHCNh de Cajamarca (aeropuerto SPJR, 7.139 S,
     78.489 O, 2676 m) para comparar reanalisis y estacion en el mismo lugar.

Los fallos se imprimen y se registran; nada se reemplaza en silencio.
"""
from pathlib import Path
import datetime as dt

import xarray as xr

RAIZ = Path(__file__).resolve().parents[2]
TC = RAIZ / "datos/punto1/terraclimate"
ERA = RAIZ / "datos/punto1/era5land/estacion_cajamarca"
LOG = RAIZ / "datos/punto1/log_descargas_1_1b.txt"
URLS = ["http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_terraclimate_{v}_1950_CurrentYear_GLOBE.nc",
        "http://thredds.northwestknowledge.net:8080/thredds/dodsC/agg_terraclimate_{v}_1958_CurrentYear_GLOBE.nc"]
VARS_TC = ["pet", "tmax", "tmin", "vpd", "ws", "srad", "aet", "ppt"]


def registrar(msg):
    linea = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def terraclimate():
    TC.mkdir(parents=True, exist_ok=True)
    for v in VARS_TC:
        destino = TC / f"terraclimate_{v}_chicama_1981_2024.nc"
        if destino.exists():
            registrar(f"ya existe {destino.name}"); continue
        for u in URLS:
            try:
                ds = xr.open_dataset(u.format(v=v))
                sub = ds[v].sel(lat=slice(-7.3, -8.1), lon=slice(-78.9, -78.1), time=slice("1981-01-01", "2024-12-31")).load()
                sub.to_netcdf(destino)
                registrar(f"OK {destino.name} {dict(sub.sizes)} desde {u.format(v=v)}")
                break
            except Exception as e:
                registrar(f"FALLO {v} con {u.format(v=v)}: {e}")


def era5land_cajamarca():
    import cdsapi
    ERA.mkdir(parents=True, exist_ok=True)
    destino = ERA / "era5land_ts_cajamarca_SPJR.zip"
    if destino.exists():
        registrar(f"ya existe {destino.name}"); return
    try:
        cdsapi.Client().retrieve("reanalysis-era5-land-timeseries", {
            "variable": ["2m_temperature", "2m_dewpoint_temperature", "10m_u_component_of_wind",
                         "10m_v_component_of_wind", "surface_solar_radiation_downwards", "surface_pressure"],
            "location": {"longitude": -78.489, "latitude": -7.139},
            "date": ["1981-01-01/2025-12-31"], "data_format": "csv"}, str(destino))
        registrar(f"OK {destino.name}")
    except Exception as e:
        registrar(f"FALLO ERA5-Land Cajamarca: {e}")


if __name__ == "__main__":
    terraclimate()
    era5land_cajamarca()
