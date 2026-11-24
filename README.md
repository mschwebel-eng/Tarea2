# Tarea 2 de Hidrología (UNAL Medellín, semestre 202602)

Marlin Julie Schwebel · Prof. Carlos David Hoyos

- **Diapositivas con todos los resultados:** https://mschwebel-eng.github.io/Tarea2/ (`index.html`, `img/`, `assets/`).
- **Código:** carpeta `codigo/`.
  - `punto1/`: evapotranspiración en la cuenca del río Chicama hasta El Tambo (scripts `01_` a `17_`, en orden; módulos `fao56.py`, `lectura_era5land.py`, `metodos_etp.py`).
  - `punto2/`: lluvia de 10 min de Cottbus (DWD 00880), extremos, IDF, microcuenca y problemas A y B (scripts `00_` a `08_`; módulo `distribuciones.py`).
  - `sitio/`: genera la página de diapositivas (`construir.py`).
  - `presentacion/`: genera la presentación .pptx (`crear_pptx.py`).

## Cómo correrlo

1. Python 3.12 y los paquetes de `requirements.txt` (`pip install -r requirements.txt`).
2. Los scripts usan rutas relativas a una carpeta raíz con `codigo/`, `datos/` y `productos/`. Los **datos no están en este repositorio**: van en el ZIP de entrega o se descargan con los scripts de descarga (`punto1/01_`, `06_`, `14_`; `punto2/00_`, `01_`).
3. Las descargas de ERA5-Land necesitan una cuenta del Copernicus Climate Data Store y el archivo `~/.cdsapirc`, que **nunca** se sube al repositorio.
