"""
02_eto_un_dia_a_mano.py - Apartado 1.1.a, paso 2: ETo FAO-56 de UN dia, termino por termino.

Celda central de la cuenca (7.6 S, 78.5 O, enteramente dentro de la divisoria), 15 de enero de 1981.
Sirve como caso de verificacion: el script 03 debe dar exactamente este valor para esta celda y dia,
y la libreria pyet (implementacion independiente) tambien.

Salida: productos/punto1/verificacion_eto_un_dia.txt
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fao56 as F
from lectura_era5land import leer_horario, diario_local, RAIZ

LAT, LON, DIA = -7.6, -78.5, "1981-01-15"
Z_CUENCA = 2557.0          # elevacion media de la cuenca (CAMELS-PE, atributo elev_mean), m
SALIDA = RAIZ / "productos/punto1/verificacion_eto_un_dia.txt"

lineas = []
def p(s=""):
    print(s); lineas.append(s)

h = leer_horario(LAT, LON)
d = diario_local(h).loc[DIA]
J = pd.Timestamp(DIA).day_of_year

p(f"ETo FAO-56 a mano - celda {LAT} {LON} - dia local {DIA} (dia juliano {J})")
p("=" * 78)
p("1) Datos del dia (agregados de 24 valores horarios de ERA5-Land, hora local UTC-5)")
p(f"   Tmax = {d.tmax:.2f} C   Tmin = {d.tmin:.2f} C   Tmedia=(Tmax+Tmin)/2 = {(d.tmax+d.tmin)/2:.2f} C")
p(f"   (media de las 24 h = {d.tmedia_h:.2f} C; FAO-56 usa (Tmax+Tmin)/2)")
p(f"   Td media = {d.td:.2f} C   u10 media (magnitud horaria) = {d.u10:.2f} m/s   Rs = {d.rs:.2f} MJ m-2 d-1")
p(f"   presion del modelo en la celda = {d.p:.2f} kPa  -> elevacion equivalente (ec.7 inversa) = {F.z_desde_presion(d.p):.0f} m")
T = (d.tmax + d.tmin) / 2

p("\n2) Presion y constante psicrometrica (ecs. 7 y 8), con la elevacion media de la cuenca")
P = F.presion_desde_z(Z_CUENCA); gm = F.gamma(P)
p(f"   P = 101.3((293-0.0065*{Z_CUENCA:.0f})/293)^5.26 = {P:.2f} kPa")
p(f"   gamma = 0.665e-3 * P = {gm:.4f} kPa/C")

p("\n3) Vapor de agua (ecs. 11-14)")
e_max, e_min = F.e0(d.tmax), F.e0(d.tmin)
es = (e_max + e_min) / 2; ea = F.e0(d.td)
p(f"   e0(Tmax) = 0.6108 exp(17.27*{d.tmax:.2f}/({d.tmax:.2f}+237.3)) = {e_max:.3f} kPa")
p(f"   e0(Tmin) = {e_min:.3f} kPa   ->  es = {es:.3f} kPa")
p(f"   e0(Tmedia) = {F.e0(T):.3f} kPa  (menor que es: la curva de saturacion es convexa)")
p(f"   ea = e0(Td) = {ea:.3f} kPa   ->  deficit de vapor es - ea = {es-ea:.3f} kPa   (HR media ~ {100*ea/es:.0f} %)")
D = F.delta(T)
p(f"   Delta = 4098 e0(T)/(T+237.3)^2 = {D:.4f} kPa/C")

p("\n4) Viento a 2 m (ec. 47)")
u2 = F.u2_desde_uz(d.u10)
p(f"   u2 = u10 * 4.87/ln(67.8*10-5.42) = {d.u10:.2f} * {4.87/np.log(67.8*10-5.42):.3f} = {u2:.2f} m/s")

p("\n5) Radiacion (ecs. 21, 37, 38, 39)")
Ra = F.ra(LAT, J); Rso = F.rso(Ra, Z_CUENCA)
Rns = (1 - F.ALBEDO_REF) * d.rs; Rnl = F.rnl(d.tmax, d.tmin, ea, d.rs, Rso); Rn = Rns - Rnl
p(f"   Ra (extraterrestre) = {Ra:.2f} MJ m-2 d-1      Rso (cielo despejado) = {Rso:.2f}")
p(f"   Rs/Rso = {d.rs/Rso:.2f}  (fraccion de la radiacion de cielo despejado que llego: nubosidad)")
p(f"   Rns = 0.77*Rs = {Rns:.2f}    Rnl = {Rnl:.2f}    Rn = Rns - Rnl = {Rn:.2f} MJ m-2 d-1")
p(f"   Rn en energia: {Rn:.2f} MJ m-2 d-1 = {Rn*1e6/86400:.0f} W m-2;  como lamina Rn/lambda = {Rn/F.LAMBDA:.2f} mm/d")

p("\n6) ETo (ec. 6), G = 0 en escala diaria (ec. 42)")
eto, rad, aero = F.eto_pm(T, u2, es, ea, Rn, 0.0, P)
p(f"   denominador Delta + gamma(1+0.34 u2) = {D + gm*(1+0.34*u2):.4f}")
p(f"   termino radiativo     0.408 Delta Rn / den              = {rad:.3f} mm/d  ({100*rad/eto:.0f} %)")
p(f"   termino aerodinamico  gamma 900/(T+273) u2 (es-ea) / den = {aero:.3f} mm/d  ({100*aero/eto:.0f} %)")
p(f"   ETo = {eto:.3f} mm/d   (= {eto*28.4:.0f} W m-2 de calor latente; regla de la guia: 1 mm/d ~ 28 W m-2)")
Eeq = D / (D + gm) * Rn / F.LAMBDA
p(f"   E_eq = Delta/(Delta+gamma) Rn/lambda = {Eeq:.3f} mm/d   ->  alfa* = ETo/E_eq = {eto/Eeq:.2f}")

p("\n7) Verificacion independiente con pyet.pm_fao56")
try:
    import pyet
    idx = pd.DatetimeIndex([DIA])
    s = lambda v: pd.Series([v], index=idx)
    e_pyet = pyet.pm_fao56(tmean=s(T), wind=s(u2), rn=s(Rn), g=0, tmax=s(d.tmax), tmin=s(d.tmin),
                           ea=s(ea), pressure=s(P), elevation=Z_CUENCA, lat=np.radians(LAT)).iloc[0]
    p(f"   pyet (misma Rn, mismo u2): ETo = {e_pyet:.3f} mm/d   diferencia = {eto - e_pyet:+.4f} mm/d")
    e_pyet2 = pyet.pm_fao56(tmean=s(T), wind=s(u2), rs=s(d.rs), tmax=s(d.tmax), tmin=s(d.tmin),
                            ea=s(ea), pressure=s(P), elevation=Z_CUENCA, lat=np.radians(LAT)).iloc[0]
    p(f"   pyet calculando Rn por su cuenta desde Rs: ETo = {e_pyet2:.3f} mm/d   diferencia = {eto - e_pyet2:+.4f} mm/d")
except Exception as e:                       # el fallo queda visible
    p(f"   FALLO la verificacion con pyet: {e}")

SALIDA.parent.mkdir(parents=True, exist_ok=True)
SALIDA.write_text("\n".join(lineas), encoding="utf-8")
# los mismos valores en JSON, para las graficas del sitio
import json
valores = dict(dia=DIA, lat=LAT, lon=LON, tmax=d.tmax, tmin=d.tmin, t=T, td=d.td, u10=d.u10, u2=u2, rs=d.rs, ra=Ra, rso=Rso,
               rns=Rns, rnl=Rnl, rn=Rn, es=es, ea=ea, e_tmax=e_max, e_tmin=e_min, e_tmedia=F.e0(T), delta=D, gamma=gm, p=P,
               eto=eto, rad=rad, aero=aero, eeq=Eeq, alfa=eto / Eeq,
               eto_pyet=float(e_pyet) if "e_pyet" in dir() else None)
(SALIDA.with_suffix(".json")).write_text(json.dumps({k: (round(float(v), 4) if not isinstance(v, str) and v is not None else v)
                                                     for k, v in valores.items()}, indent=1), encoding="utf-8")
print(f"\n-> {SALIDA.relative_to(RAIZ)} (+ .json)")
