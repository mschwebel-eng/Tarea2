"""
fao56.py - Ecuaciones de FAO-56 (Allen et al., 1998) usadas en el punto 1.

Cada funcion indica la ecuacion de FAO-56 que implementa. Unidades de FAO-56:
temperaturas en grados C, presiones en kPa, radiacion en MJ m-2 d-1, viento en m s-1,
ETo en mm d-1. Todas las funciones aceptan escalares, arreglos de numpy o series de pandas.
"""
import numpy as np

SIGMA = 4.903e-9      # constante de Stefan-Boltzmann, MJ K-4 m-2 d-1
GSC = 0.0820          # constante solar, MJ m-2 min-1
LAMBDA = 2.45         # calor latente de vaporizacion, MJ kg-1 (FAO-56 lo fija en 20 C)
ALBEDO_REF = 0.23     # albedo del pasto de referencia


def presion_desde_z(z):
    """Ec. 7: presion atmosferica (kPa) a la elevacion z (m)."""
    return 101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26


def z_desde_presion(p):
    """Inversa de la ec. 7: elevacion (m) que corresponde a una presion p (kPa)."""
    return 293.0 / 0.0065 * (1.0 - (p / 101.3) ** (1 / 5.26))


def gamma(p):
    """Ec. 8: constante psicrometrica (kPa C-1) para la presion p (kPa)."""
    return 0.665e-3 * p


def e0(t):
    """Ec. 11: presion de vapor de saturacion (kPa) a la temperatura t (C)."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def es_diaria(tmax, tmin):
    """Ec. 12: presion de vapor de saturacion media diaria (kPa)."""
    return 0.5 * (e0(tmax) + e0(tmin))


def delta(t):
    """Ec. 13: pendiente de la curva de saturacion (kPa C-1) a la temperatura t (C)."""
    return 4098.0 * e0(t) / (t + 237.3) ** 2


def u2_desde_uz(uz, z=10.0):
    """Ec. 47: viento a 2 m a partir del viento medido a z m (perfil logaritmico del pasto)."""
    return uz * 4.87 / np.log(67.8 * z - 5.42)


def ra(lat_grados, dia_juliano):
    """Ecs. 21-25: radiacion extraterrestre diaria (MJ m-2 d-1)."""
    phi = np.radians(lat_grados)
    j = np.asarray(dia_juliano, dtype=float)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)              # ec. 23
    dec = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)          # ec. 24
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))  # ec. 25
    return 24 * 60 / np.pi * GSC * dr * (ws * np.sin(phi) * np.sin(dec)
                                         + np.cos(phi) * np.cos(dec) * np.sin(ws))


def rso(ra_, z):
    """Ec. 37: radiacion solar de cielo despejado (MJ m-2 d-1)."""
    return (0.75 + 2e-5 * z) * ra_


def rnl(tmax, tmin, ea, rs, rso_):
    """Ec. 39: radiacion neta de onda larga que pierde la superficie (MJ m-2 d-1)."""
    rel = np.clip(rs / rso_, 0.0, 1.0)                        # Rs/Rso <= 1
    tk4 = 0.5 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4)
    return SIGMA * tk4 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * rel - 0.35)


def eto_desde_diario(d, lat, z, p):
    """ETo diaria y todos sus terminos a partir de un DataFrame diario con columnas
    tmax, tmin, td, u10 (magnitud media del viento a 10 m) y rs (MJ m-2 d-1), indice de fechas.
    z: elevacion para Rso (m); p: presion para gamma (kPa, escalar o serie). G = 0 (ec. 42)."""
    t = (d.tmax + d.tmin) / 2
    es = es_diaria(d.tmax, d.tmin)
    ea = e0(d.td)
    u2 = u2_desde_uz(d.u10)
    ra_ = ra(lat, d.index.day_of_year)
    rso_ = rso(ra_, z)
    rns = (1 - ALBEDO_REF) * d.rs
    rnl_ = rnl(d.tmax, d.tmin, ea, d.rs, rso_)
    rn = rns - rnl_
    eto, rad, aero = eto_pm(t, u2, es, ea, rn, 0.0, p)
    return d.assign(t=t, es=es, ea=ea, vpd=es - ea, u2=u2, ra=ra_, rso=rso_, rns=rns, rnl=rnl_, rn=rn,
                    eto=eto, eto_rad=rad, eto_aero=aero)


def eto_pm(t, u2, es, ea, rn, g, p):
    """Ec. 6: ETo Penman-Monteith FAO-56 (mm d-1).

    Devuelve (eto, termino_radiativo, termino_aerodinamico), cuya suma es eto.
    t: temperatura media (C); rn y g en MJ m-2 d-1; es, ea, p en kPa; u2 en m s-1.
    """
    d, gm = delta(t), gamma(p)
    den = d + gm * (1 + 0.34 * u2)
    rad = 0.408 * d * (rn - g) / den
    aero = gm * 900.0 / (t + 273.0) * u2 * (es - ea) / den
    return rad + aero, rad, aero
