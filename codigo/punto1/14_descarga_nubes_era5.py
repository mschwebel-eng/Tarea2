"""
14_descarga_nubes_era5.py - Datos para el apartado 1.5.c (niebla y nubosidad persistente bajo la inversion).

ERA5 (Hersbach et al., 2020), medias mensuales de niveles unicos, en un recuadro que incluye el mar, la costa y la cuenca
(6.5-8.5 S, 80-77.5 O, malla de 0.25 grados):
  A) monthly_averaged_reanalysis 1981-2024: nubosidad baja, media y total, altura de la capa limite.
  B) monthly_averaged_reanalysis_by_hour_of_day 2005-2024, cada 3 h: nubosidad baja y altura de la capa limite,
     para ver el ciclo dia-noche (estabilidad).
Los fallos quedan registrados; nada se reemplaza en silencio.
"""
from pathlib import Path
import datetime as dt

import cdsapi

RAIZ = Path(__file__).resolve().parents[2]
DEST = RAIZ / "datos/punto1/era5_nubes"
LOG = DEST / "log_descargas.txt"
AREA = [-6.5, -80.0, -8.5, -77.5]
DEST.mkdir(parents=True, exist_ok=True)          # la carpeta debe existir antes de la primera descarga


def registrar(msg):
    DEST.mkdir(parents=True, exist_ok=True)
    linea = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def pedir(nombre, req):
    destino = DEST / nombre
    if destino.exists():
        registrar(f"ya existe {nombre}"); return
    try:
        cdsapi.Client().retrieve("reanalysis-era5-single-levels-monthly-means", req, str(destino))
        registrar(f"OK {nombre}")
    except Exception as e:
        registrar(f"FALLO {nombre}: {e}")


meses = [f"{m:02d}" for m in range(1, 13)]
pedir("era5_nubes_mensual_1981_2024.nc", {
    "product_type": ["monthly_averaged_reanalysis"],
    "variable": ["low_cloud_cover", "medium_cloud_cover", "total_cloud_cover", "boundary_layer_height"],
    "year": [str(a) for a in range(1981, 2025)], "month": meses, "time": ["00:00"],
    "area": AREA, "data_format": "netcdf", "download_format": "unarchived"})
pedir("era5_nubes_por_hora_2005_2024.nc", {
    "product_type": ["monthly_averaged_reanalysis_by_hour_of_day"],
    "variable": ["low_cloud_cover", "boundary_layer_height"],
    "year": [str(a) for a in range(2005, 2025)], "month": meses,
    "time": [f"{h:02d}:00" for h in range(0, 24, 3)],
    "area": AREA, "data_format": "netcdf", "download_format": "unarchived"})
