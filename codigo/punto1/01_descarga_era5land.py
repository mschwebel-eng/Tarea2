"""
01_descarga_era5land.py  -  Punto 1.1.a (ETo FAO-56), cuenca del rio Chicama en El Tambo

Descarga dos conjuntos de ERA5-Land del CDS de Copernicus:

  A) reanalysis-era5-land-timeseries  (series HORARIAS en puntos)
     Una solicitud por cada celda de 0.1 deg que toca la cuenca. Las celdas y sus
     pesos (area dentro de la cuenca) salen de la Tarea 1:
     datos/punto1/tarea1/pesos_era5land_cuenca.csv  -> misma ponderacion espacial.
     Se usan para el calculo DIARIO de ETo: Tmax y Tmin de las 24 h, viento como
     magnitud horaria sqrt(u^2+v^2) promediada despues, Td, Rs y presion.

  B) reanalysis-era5-land-monthly-means  (medias MENSUALES por area)
     Para la ETo "con medias mensuales" (error por promediar, 1.1.a), la radiacion
     neta real (1.2.3), la evaporacion total (1.2.4) y la humedad del suelo (1.3.2).
     Ojo: las variables acumuladas vienen en m/d o J m-2 d-1 (multiplicar por dias
     del mes) y la evaporacion es negativa por convencion. ECMWF advierte un error
     en estas medias entre 2022-09 y 2024-02 (revisarlo en 02_...).

Requisitos: archivo ~/.cdsapirc con la clave del CDS (NO va en el ZIP de entrega) y
haber aceptado la licencia de ambos conjuntos en la web del CDS.

Uso (desde la carpeta tarea2):
    .venv\\Scripts\\python.exe codigo\\punto1\\01_descarga_era5land.py

Si una descarga falla, el error se imprime y se registra en el log; no se
reemplaza nada en silencio. Al volver a ejecutar, los archivos ya bajados se omiten.
"""
from pathlib import Path
import csv
import datetime as dt

import cdsapi

RAIZ = Path(__file__).resolve().parents[2]          # carpeta tarea2/
PESOS = RAIZ / "datos/punto1/tarea1/pesos_era5land_cuenca.csv"
SALIDA_H = RAIZ / "datos/punto1/era5land/horario_puntos"
SALIDA_M = RAIZ / "datos/punto1/era5land/mensual"
LOG = RAIZ / "datos/punto1/era5land/log_descargas.txt"

PERIODO = "1981-01-01/2025-12-31"     # 1981-2025: el registro largo hace falta para 1.4
ANIOS = [str(a) for a in range(1981, 2026)]

# --- A) Variables horarias para FAO-56 (todas en hora UTC) -------------------------
VARS_HORARIAS = [
    "2m_temperature",                       # T  -> Tmax, Tmin, Tmedia diarias (K)
    "2m_dewpoint_temperature",              # Td -> ea = e0(Td) (K)
    "10m_u_component_of_wind",              # u10 (m/s)
    "10m_v_component_of_wind",              # v10 (m/s)
    "surface_solar_radiation_downwards",    # Rs (J m-2; verificar acumulacion)
    "surface_thermal_radiation_downwards",  # onda larga incidente (diagnostico Rnl)
    "surface_pressure",                     # P (Pa) -> gamma
    "total_precipitation",                  # para controles y apartado 1.6
]

# --- B) Variables mensuales por area ------------------------------------------------
VARS_MENSUALES = [
    "2m_temperature", "2m_dewpoint_temperature",
    "10m_u_component_of_wind", "10m_v_component_of_wind",
    "surface_pressure",
    "surface_solar_radiation_downwards", "surface_thermal_radiation_downwards",
    "surface_net_solar_radiation", "surface_net_thermal_radiation",   # Rn real (1.2.3)
    "surface_latent_heat_flux", "surface_sensible_heat_flux",
    "total_evaporation", "potential_evaporation",                     # ET real; pev (NO es ETo)
    "evaporation_from_vegetation_transpiration",
    "volumetric_soil_water_layer_1", "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",                                  # humedad del suelo (1.3.2)
    "total_precipitation",
]
# Recuadro [Norte, Oeste, Sur, Este] = centros de las celdas de la Tarea 1
AREA = [-7.4, -78.8, -8.0, -78.2]


def registrar(msg: str) -> None:
    linea = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linea)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def leer_celdas():
    with open(PESOS, newline="", encoding="utf-8") as f:
        return [(float(r["lon"]), float(r["lat"]), float(r["area_en_cuenca_km2"]))
                for r in csv.DictReader(f)]


def descargar_horario(c: cdsapi.Client) -> None:
    SALIDA_H.mkdir(parents=True, exist_ok=True)
    celdas = leer_celdas()
    registrar(f"{len(celdas)} celdas, area total en cuenca = "
              f"{sum(a for *_, a in celdas):.1f} km2")
    for lon, lat, area in celdas:
        destino = SALIDA_H / f"era5land_ts_lat{lat:+.1f}_lon{lon:+.1f}.zip"
        if destino.exists():
            registrar(f"ya existe, se omite: {destino.name}")
            continue
        try:
            c.retrieve("reanalysis-era5-land-timeseries", {
                "variable": VARS_HORARIAS,
                "location": {"longitude": lon, "latitude": lat},
                "date": [PERIODO],
                "data_format": "csv",
            }, str(destino))
            registrar(f"OK {destino.name} (peso {area:.1f} km2)")
        except Exception as e:                       # el fallo queda visible
            registrar(f"FALLO punto lat={lat} lon={lon}: {e}")


def descargar_mensual(c: cdsapi.Client) -> None:
    SALIDA_M.mkdir(parents=True, exist_ok=True)
    destino = SALIDA_M / "era5land_mensual_1981_2025_chicama.nc"
    if destino.exists():
        registrar(f"ya existe, se omite: {destino.name}")
        return
    try:
        c.retrieve("reanalysis-era5-land-monthly-means", {
            "product_type": ["monthly_averaged_reanalysis"],
            "variable": VARS_MENSUALES,
            "year": ANIOS,
            "month": [f"{m:02d}" for m in range(1, 13)],
            "time": ["00:00"],
            "area": AREA,
            "data_format": "netcdf",
            "download_format": "unarchived",
        }, str(destino))
        registrar(f"OK {destino.name}")
    except Exception as e:
        registrar(f"FALLO mensual: {e}")


if __name__ == "__main__":
    LOG.parent.mkdir(parents=True, exist_ok=True)
    cliente = cdsapi.Client()
    descargar_mensual(cliente)     # una sola solicitud: empezar por aqui
    descargar_horario(cliente)     # 30 solicitudes, una por celda
