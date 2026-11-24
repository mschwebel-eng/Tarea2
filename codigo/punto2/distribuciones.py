"""
distribuciones.py - Ajuste de distribuciones de extremos (punto 2.2) por momentos, L-momentos y maxima verosimilitud.

Convencion de este modulo: forma de la GEV xi > 0 = cola pesada (Frechet), como en la guia.
OJO scipy.stats.genextreme usa c = -xi (verificado en verificar_convenciones()).
Cada ajuste devuelve un dict con la funcion cuantil q(T) y la CDF F(x).
Referencias: Chow et al. (1988), cap. 12; Hosking (1990); Hosking y Wallis (1997); Coles (2001).
"""
import numpy as np
from scipy import stats, special
from scipy.optimize import brentq

EULER = 0.5772156649


# ---------------------------------------------------------------- L-momentos muestrales (PWM no sesgados)
def lmom(x):
    x = np.sort(np.asarray(x, float)); n = len(x); j = np.arange(1, n + 1)
    b0 = x.mean()
    b1 = np.sum((j - 1) / (n - 1) * x) / n
    b2 = np.sum((j - 1) * (j - 2) / ((n - 1) * (n - 2)) * x) / n
    b3 = np.sum((j - 1) * (j - 2) * (j - 3) / ((n - 1) * (n - 2) * (n - 3)) * x) / n
    l1, l2 = b0, 2 * b1 - b0
    l3 = 6 * b2 - 6 * b1 + b0
    l4 = 20 * b3 - 30 * b2 + 12 * b1 - b0
    return l1, l2, l3 / l2, l4 / l2           # lambda1, lambda2, tau3, tau4


def _yT(T):
    return -np.log(-np.log(1 - 1 / np.asarray(T, float)))     # variable reducida de Gumbel


# ---------------------------------------------------------------- Gumbel
def gumbel(x, metodo):
    x = np.asarray(x, float)
    if metodo == "MOM":
        a = np.std(x, ddof=1) * np.sqrt(6) / np.pi; u = x.mean() - EULER * a
    elif metodo == "LMOM":
        l1, l2, _, _ = lmom(x); a = l2 / np.log(2); u = l1 - EULER * a
    else:
        u, a = stats.gumbel_r.fit(x)
    return {"dist": "Gumbel", "metodo": metodo, "par": {"u": u, "alfa": a},
            "q": lambda T: u + a * _yT(T), "F": lambda z: stats.gumbel_r.cdf(z, u, a)}


# ---------------------------------------------------------------- GEV
def _gev_q(mu, sg, xi, T):
    y = -np.log(1 - 1 / np.asarray(T, float))
    return mu + sg / xi * (y ** (-xi) - 1) if abs(xi) > 1e-6 else mu - sg * np.log(y)


def _gev_skew(xi):
    g1, g2, g3 = special.gamma(1 - xi), special.gamma(1 - 2 * xi), special.gamma(1 - 3 * xi)
    return np.sign(xi) * (g3 - 3 * g1 * g2 + 2 * g1 ** 3) / (g2 - g1 ** 2) ** 1.5


def gev(x, metodo):
    x = np.asarray(x, float)
    if metodo == "MOM":
        g = stats.skew(x, bias=False)
        xi = brentq(lambda z: _gev_skew(z) - g, -0.99, 0.3329) if abs(g - 1.1396) > 1e-3 else 1e-7
        g1, g2 = special.gamma(1 - xi), special.gamma(1 - 2 * xi)
        sg = np.std(x, ddof=1) * abs(xi) / np.sqrt(g2 - g1 ** 2)
        mu = x.mean() - sg * (g1 - 1) / xi
    elif metodo == "LMOM":                                   # Hosking et al. (1985); k = -xi
        l1, l2, t3, _ = lmom(x)
        c = 2 / (3 + t3) - np.log(2) / np.log(3)
        k = 7.8590 * c + 2.9554 * c ** 2
        sg = l2 * k / ((1 - 2 ** (-k)) * special.gamma(1 + k))
        mu = l1 - sg * (1 - special.gamma(1 + k)) / k
        xi = -k
    else:
        cs, mu, sg = stats.genextreme.fit(x)                 # scipy: c = -xi
        xi = -cs
    return {"dist": "GEV", "metodo": metodo, "par": {"mu": mu, "sigma": sg, "xi": xi},
            "q": lambda T: _gev_q(mu, sg, xi, T), "F": lambda z: stats.genextreme.cdf(z, -xi, mu, sg)}


# ---------------------------------------------------------------- log-Pearson III (Pearson III sobre log10 x)
def _pe3_lmom(l1, l2, t3):
    """Hosking y Wallis (1997), aproximacion racional: devuelve (mu, sigma, gamma) de Pearson III."""
    a3 = abs(t3)
    if a3 < 1e-6:
        return l1, l2 * np.sqrt(np.pi), 0.0
    if a3 < 1 / 3:
        z = 3 * np.pi * t3 ** 2
        alfa = (1 + 0.2906 * z) / (z + 0.1882 * z ** 2 + 0.0442 * z ** 3)
    else:
        z = 1 - a3
        alfa = (0.36067 * z - 0.59567 * z ** 2 + 0.25361 * z ** 3) / (1 - 2.78861 * z + 2.56096 * z ** 2 - 0.77045 * z ** 3)
    gam = 2 / np.sqrt(alfa) * np.sign(t3)
    sg = l2 * np.sqrt(np.pi) * np.sqrt(alfa) * np.exp(special.gammaln(alfa) - special.gammaln(alfa + 0.5))   # estable
    return l1, sg, gam


def lp3(x, metodo):
    y = np.log10(np.asarray(x, float))
    if metodo == "MOM":
        mu, sg, gam = y.mean(), np.std(y, ddof=1), stats.skew(y, bias=False)
    elif metodo == "LMOM":
        l1, l2, t3, _ = lmom(y); mu, sg, gam = _pe3_lmom(l1, l2, t3)
    else:
        gam, mu, sg = stats.pearson3.fit(y)
    return {"dist": "log-Pearson III", "metodo": metodo, "par": {"mu_log": mu, "sigma_log": sg, "gamma_log": gam},
            "q": lambda T: 10 ** stats.pearson3.ppf(1 - 1 / np.asarray(T, float), gam, mu, sg),
            "F": lambda z: stats.pearson3.cdf(np.log10(z), gam, mu, sg)}


def glo(x, metodo="LMOM"):
    """Logistica generalizada (Hosking y Wallis, 1997), solo por L-momentos: k = -tau3.
    x(F) = xi + alfa [1 - ((1 - F)/F)^k] / k. Se usa como contraste porque el diagrama de L-momentos la sugiere."""
    l1, l2, t3, _ = lmom(x)
    k = -t3
    a = l2 * np.sin(k * np.pi) / (k * np.pi)
    xi = l1 - a * (1 / k - np.pi / np.sin(k * np.pi))
    q = lambda T: xi + a * (1 - ((1 / np.asarray(T, float)) / (1 - 1 / np.asarray(T, float))) ** k) / k

    def F(z):
        y = -np.log(np.clip(1 - k * (np.asarray(z, float) - xi) / a, 1e-12, None)) / k
        return 1 / (1 + np.exp(-y))
    return {"dist": "GLO", "metodo": "LMOM", "par": {"xi_loc": xi, "alfa": a, "k": k}, "q": q, "F": F}


AJUSTES = {"Gumbel": gumbel, "GEV": gev, "log-Pearson III": lp3}
METODOS = ["MOM", "LMOM", "MLE"]


# ---------------------------------------------------------------- posiciones de graficacion y bondad de ajuste
def gringorten(x):
    """Probabilidad de NO excedencia de cada dato ordenado de menor a mayor (Gringorten, a = 0.44)."""
    n = len(x); m = np.arange(n, 0, -1)                     # rango de mayor a menor
    return 1 - (m - 0.44) / (n + 0.12)


def bondad(x, aj):
    x = np.sort(np.asarray(x, float)); n = len(x)
    F = np.clip(aj["F"](x), 1e-10, 1 - 1e-10)
    ks = stats.kstest(x, aj["F"])
    i = np.arange(1, n + 1)
    ad = -n - np.sum((2 * i - 1) / n * (np.log(F) + np.log(1 - F[::-1])))
    p = gringorten(x)
    ppcc = np.corrcoef(x, aj["q"](1 / (1 - p)))[0, 1]
    return {"KS_D": ks.statistic, "KS_p": ks.pvalue, "AD": ad, "PPCC": ppcc}


# ---------------------------------------------------------------- curvas teoricas del diagrama de L-momentos
def tau4_teorica(t3):
    """Hosking y Wallis (1997), aproximaciones polinomicas de tau4(tau3)."""
    return {
        "GEV": 0.10701 + 0.11090 * t3 + 0.84838 * t3 ** 2 - 0.06669 * t3 ** 3 + 0.00567 * t3 ** 4 - 0.04208 * t3 ** 5 + 0.03763 * t3 ** 6,
        "GLO": 0.16667 + 0.83333 * t3 ** 2,
        "GNO (lognormal 3p)": 0.12282 + 0.77518 * t3 ** 2 + 0.12279 * t3 ** 4 - 0.13638 * t3 ** 6 + 0.11368 * t3 ** 8,
        "PE3": 0.12240 + 0.30115 * t3 ** 2 + 0.95812 * t3 ** 4 - 0.57488 * t3 ** 6 + 0.19383 * t3 ** 8,
        "GPA": 0.20196 * t3 + 0.95924 * t3 ** 2 - 0.20096 * t3 ** 3 + 0.04061 * t3 ** 4,
    }


def verificar_convenciones():
    """Caso conocido: GEV con xi = +0.2 (cola pesada). scipy debe recibir c = -0.2 y dar el mismo cuantil."""
    mu, sg, xi, T = 10.0, 3.0, 0.2, 100
    propio = _gev_q(mu, sg, xi, T)
    sc = stats.genextreme.ppf(1 - 1 / T, -xi, mu, sg)
    return propio, sc
