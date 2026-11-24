"""
metodos_etp.py - Metodos simples de demanda evaporativa (apartado 1.1.c), con las versiones de las notas del curso
(Hoyos, 2026, seccion 7, diapositivas #s62-#s65 y #s34). Todas devuelven mm d-1 salvo Thornthwaite (mm/mes).

Entradas en unidades de FAO-56: T en C, Ra y Rs y Rn en MJ m-2 d-1, presiones en kPa, viento en m s-1.
"""
import numpy as np
import pandas as pd

import fao56 as F


def duracion_dia(lat_grados, dia_juliano):
    """FAO-56 ec. 34: horas de luz N = 24/pi * omega_s."""
    phi = np.radians(lat_grados)
    dec = 0.409 * np.sin(2 * np.pi * np.asarray(dia_juliano, float) / 365 - 1.39)
    return 24 / np.pi * np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))


# ---------------------------------------------------------------- familia: temperatura
def thornthwaite_mensual(t_mes, lat, I=None, a=None):
    """Thornthwaite (1948), notas #s62. t_mes: serie MENSUAL de T media (C) con indice de fechas (inicio de mes).
    ETP = 16 (L/12)(N/30)(10 T/I)^a mm/mes; I con la climatologia de los 12 meses; T>26.5 C con la forma cuadratica.
    I y a pueden fijarse (experimentos de sensibilidad: el indice de calor es una constante del sitio)."""
    if I is None:
        clim = t_mes.groupby(t_mes.index.month).mean()
        I = ((clim.clip(lower=0) / 5) ** 1.514).sum()
        a = 6.75e-7 * I ** 3 - 7.71e-5 * I ** 2 + 0.01792 * I + 0.49239
    t = t_mes.clip(lower=0)
    sin_aj = np.where(t > 26.5, -415.85 + 32.24 * t - 0.43 * t ** 2, 16 * (10 * t / I) ** a)
    dias = t_mes.index.days_in_month
    j_medio = (t_mes.index + pd.to_timedelta(dias / 2 - 0.5, unit="D")).day_of_year
    L = duracion_dia(lat, j_medio)
    return pd.Series(sin_aj * (L / 12) * (dias / 30), index=t_mes.index), I, a


def hamon(t, lat, dia_juliano):
    """Hamon (1961), forma de Lu et al. (2005), notas #s63: ETP = 29.8 D es(T)/(T + 273.2) mm/d, D en horas."""
    D = duracion_dia(lat, dia_juliano)
    return 29.8 * D * F.e0(t) / (t + 273.2)


# ---------------------------------------------------------------- familia: temperatura y radiacion extraterrestre
def hargreaves(tmax, tmin, ra):
    """Hargreaves y Samani (1985), FAO-56 ec. 52, notas #s63: 0.0023 * 0.408 Ra (T + 17.8) sqrt(Tmax - Tmin)."""
    t = (tmax + tmin) / 2
    return 0.0023 * 0.408 * ra * (t + 17.8) * np.sqrt(np.clip(tmax - tmin, 0, None))


def oudin(t, ra):
    """Oudin et al. (2005), notas #s63: 0.408 Ra (T + 5)/100 si T > -5 C, si no 0."""
    return np.where(t > -5, 0.408 * ra * (t + 5) / 100, 0.0)


# ---------------------------------------------------------------- familia: radiacion
def priestley_taylor(t, rn, p, alfa=1.26, g=0.0):
    """Priestley y Taylor (1972), notas #s33 y #s64: alfa Delta/(Delta+gamma) (Rn - G)/lambda."""
    d, gm = F.delta(t), F.gamma(p)
    return alfa * d / (d + gm) * (rn - g) / F.LAMBDA


def makkink(t, rs, p):
    """Makkink (1957), forma original, notas #s64: 0.61 Delta/(Delta+gamma) Rs/lambda - 0.12 (mm/d)."""
    d, gm = F.delta(t), F.gamma(p)
    return np.clip(0.61 * d / (d + gm) * rs / F.LAMBDA - 0.12, 0, None)


# ---------------------------------------------------------------- familia: transferencia de masa
def dalton_fao24(es, ea, u2):
    """Dalton con la funcion de viento de Penman/FAO-24 (notas #s34 y #s65):
    E = 0.27 (1 + U/100) (es - ea), con U el recorrido del viento a 2 m en km/d y (es - ea) en hPa (mbar)."""
    return 0.27 * (1 + u2 * 86.4 / 100) * (es - ea) * 10.0


def meyer(es, ea, u10, C=15.0):
    """Meyer (1915), notas #s34: E = C (es - ea)(1 + u/10), E en pulgadas/mes, (es - ea) en pulgadas de Hg,
    u en millas/h a ~9 m (se usa u10). C = 15 (cuerpos pequenos y someros). Se convierte a mm/d.
    Ojo: Meyer usa es a la temperatura del AGUA; aqui se usa la del aire (simplificacion declarada)."""
    de_inhg = (es - ea) / 3.38639
    u_mph = u10 * 2.23694
    return C * de_inhg * (1 + u_mph / 10) * 25.4 / 30.4375


# ---------------------------------------------------------------- metodo nuevo con humedad: Linacre
def linacre(t, td, z, lat):
    """Linacre (1977), notas #s63: E = [500 Tm/(100 - |lat|) + 15 (T - Td)]/(80 - T), Tm = T + 0.006 z.
    Simplificacion de Penman con temperatura, punto de rocio y altitud (constante 500: vegetacion bien regada)."""
    tm = t + 0.006 * z
    return np.clip((500 * tm / (100 - abs(lat)) + 15 * (t - td)) / (80 - t), 0, None)
