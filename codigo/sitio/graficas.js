/* ───────── navegación (misma lógica del sitio de Hidroituango) ───────── */
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

function oscuro() {
  const d = document.documentElement;
  return (d.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
}
function etiquetaTema() { $("#themeTg .tlbl").textContent = oscuro() ? "Modo claro" : "Modo oscuro"; }
$("#themeTg").addEventListener("click", () => {
  document.documentElement.dataset.theme = oscuro() ? "light" : "dark";
  try { localStorage.setItem("theme", document.documentElement.dataset.theme); } catch (e) {}
  etiquetaTema(); redibujar();
});
etiquetaTema();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { etiquetaTema(); redibujar(); });

const slides = $$(".slide"), dots = $("#dots"), main = $("#main");
let cur = 0;
slides.forEach((s, i) => {
  const b = document.createElement("button"); b.className = "g" + (s.dataset.g || "");
  b.setAttribute("aria-label", "Diapositiva " + (i + 1) + ": " + ((s.querySelector("h1,h2") || {}).textContent || ""));
  b.onclick = () => go(i); dots.appendChild(b);
});
function go(i) {
  cur = clamp(i, 0, slides.length - 1);
  slides.forEach((s, k) => s.classList.toggle("on", k === cur));
  [...dots.children].forEach((d, k) => d.classList.toggle("on", k === cur));
  $("#counter").textContent = (cur + 1) + " / " + slides.length;
  $("#secLabel").innerHTML = "<b>" + slides[cur].dataset.sec + "</b>";
  $$("nav.series .mod").forEach(m => {
    const t = document.getElementById(m.dataset.go);
    m.classList.toggle("on", !!t && t.dataset.sec === slides[cur].dataset.sec);
  });
  $("#prev").disabled = cur === 0; $("#next").disabled = cur === slides.length - 1;
  main.scrollTop = 0;
  dibujar(slides[cur].id);
  try { history.replaceState(null, "", "#" + slides[cur].id); } catch (e) {}
}
$("#prev").onclick = () => go(cur - 1); $("#next").onclick = () => go(cur + 1);
document.addEventListener("click", e => {
  const b = e.target.closest("[data-go]"); if (!b) return;
  const v = b.dataset.go; go(isNaN(+v) ? slides.indexOf(document.getElementById(v)) : +v);
});
document.addEventListener("keydown", e => {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
  if (["ArrowRight", "PageDown"].includes(e.key)) { e.preventDefault(); go(cur + 1); }
  if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); go(cur - 1); }
  if (e.key === "Home") go(0); if (e.key === "End") go(slides.length - 1);
});
let tx = null, ty = null;
main.addEventListener("touchstart", e => { tx = e.touches[0].clientX; ty = e.touches[0].clientY; }, { passive: true });
main.addEventListener("touchend", e => {
  if (tx === null) return;
  const dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty;
  if (Math.abs(dx) > 70 && Math.abs(dx) > 2 * Math.abs(dy)) go(cur + (dx < 0 ? 1 : -1)); tx = null;
});

/* ───────── gráficas Plotly estáticas (valores al pasar el cursor, sin zoom) ───────── */
const CFG = { displayModeBar: false, responsive: true, scrollZoom: false };
function base(extra = {}) {
  const fg = css("--fg"), mu = css("--muted"), ln = css("--line");
  const ax = { gridcolor: ln, linecolor: ln, zeroline: false, fixedrange: true, color: mu, tickfont: { family: "Geist Mono", size: 12 } };
  return Object.assign({
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", dragmode: false,
    font: { family: "Geist, system-ui, sans-serif", color: fg, size: 13 }, margin: { l: 56, r: 16, t: 30, b: 44 },
    xaxis: Object.assign({}, ax), yaxis: Object.assign({}, ax),
    legend: { orientation: "h", y: 1.12, x: 0, font: { size: 12 } }, hoverlabel: { font: { family: "Geist Mono" } }
  }, extra);
}
const AZUL = () => css("--neg"), ROJO = () => css("--pos");
function rgba(hex, a) {
  const h = hex.replace("#", ""), n = parseInt(h.length === 3 ? h.split("").map(c => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a.toFixed(2)})`;
}

const e0 = t => 0.6108 * Math.exp(17.27 * t / (t + 237.3));   // FAO-56 ec. 11

const G = {
  "p26-refo": () => {
    const r = D.refoc, el = id => document.getElementById(id), K = 2.45e6 / 3.1536e7;
    const zh = (p, w) => (1 + w * p) / (1 + w * p + 1 / p);
    const DN = [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0], Dc = Q => Math.pow(0.013 * Q / (0.312 * Math.sqrt(0.005)), 3 / 8);
    const nf = (v, d = 0) => Math.abs(v).toFixed(d).replace(".", ","), sg = (v, d = 0) => (+Math.abs(v).toFixed(d) === 0 ? "±" : v > 0 ? "+" : "−") + nf(v, d);
    function modelo(fb, tipo, beta) {
      const fb0 = r.bosque_hoy, phi = r.ETo_mm * (1 + r.sT_por_C * beta * (fb - fb0)) / r.P_mm;
      const etp = r.P_mm * zh(phi, 0.5), etb = r.P_mm * zh(phi, 2.0), etn = tipo === "nativo" ? etb : etp + 1.6 * (etb - etp);
      const extra = Math.max(fb - fb0, 0), base = Math.min(fb, fb0);
      const ET = (1 - fb) * etp + base * etb + extra * etn;
      const alb = (1 - fb) * r.albedo_pastizal + base * r.albedo_nativo + extra * (tipo === "nativo" ? r.albedo_nativo : r.albedo_pino);
      const alb0 = (1 - fb0) * r.albedo_pastizal + fb0 * r.albedo_nativo, sol = (alb0 - alb) * r.Rs_W_m2, LE = ET * K, H = r.Rn_W_m2 + sol - LE;
      const C = (1 - fb) * 0.34 + fb * r.C_bosque, Q = r.Qp_hoy_m3_s * C / r.C_hoy, D = Dc(Q);
      return { ET, Q: r.P_mm - ET, LE, sol, H, C, Qp: Q, D, DN: DN.find(x => x >= D), dT: beta * (fb - fb0) };
    }
    function act() {
      let fb = +el("rc-f").value / 100; const tipo = el("rc-tipo").value, beta = +el("rc-beta").value;
      if (Math.abs(fb - r.bosque_hoy) < 0.006) fb = r.bosque_hoy;
      el("rc-fo").textContent = Math.round(100 * fb) + " %"; el("rc-betao").textContent = sg(beta, 1) + " °C";
      const m = modelo(fb, tipo, beta), b = modelo(r.bosque_hoy, tipo, beta);
      el("rc-out").innerHTML =
        `<div><span>ET real</span><b class='c-data'>${nf(m.ET)} mm</b></div>` +
        `<div><span>Recarga y zanjas</span><b class='c-lw'>${nf(m.Q)} mm</b></div>` +
        `<div><span>Frente a hoy</span><b class='c-lw'>${sg(100 * (m.Q / b.Q - 1))} %</b></div>` +
        `<div><span>Temperatura</span><b class='c-arch'>${sg(m.dT, 2)} °C</b></div>` +
        `<div><span>Δ calor latente</span><b class='c-data'>${sg(m.LE - b.LE, 1)} W/m²</b></div>` +
        `<div><span>Δ sol absorbido</span><b class='c-sw'>${sg(m.sol - b.sol, 1)} W/m²</b></div>` +
        `<div><span>Razón de Bowen</span><b>${nf(m.H / m.LE, 2)}</b></div>` +
        `<div><span>Alcantarilla</span><b>${nf(m.Qp, 2)} m³/s → DN ${nf(m.DN, 2)}</b></div>`;
      el("rc-txt").innerHTML = `<b>Balance de energía:</b> el bosque evapora más y gasta ${sg(m.LE - b.LE, 1)} W/m² en calor latente, pero por su menor albedo ` +
        `absorbe ${sg(m.sol - b.sol, 1)} W/m² más de sol. ${Math.abs(m.sol - b.sol) < 0.5 ? "Mueve el control de bosque para ver qué gana." : m.sol - b.sol > m.LE - b.LE ? "Gana el sol extra: sube el calor sensible y el aire puede calentarse." : "La evaporación alcanza a gastar el sol extra: el aire tiende a enfriarse."}`;
      const F = [], ETs = [], Qs = [];
      for (let x = 0; x <= 100; x += 2) { const z = modelo(x / 100, tipo, beta); F.push(x); ETs.push(z.ET); Qs.push(z.Q); }
      Plotly.react("g-refoc", [
        { x: F, y: ETs, name: "ET real", mode: "lines", line: { color: css("--data"), width: 2 }, hovertemplate: "%{x} % · ET %{y:.0f} mm<extra></extra>" },
        { x: F, y: Qs, name: "recarga y zanjas", mode: "lines", line: { color: css("--lw"), width: 2 }, hovertemplate: "%{x} % · %{y:.0f} mm<extra></extra>" },
        { x: [100 * fb, 100 * fb], y: [m.ET, m.Q], mode: "markers", marker: { size: 10, color: [css("--data"), css("--lw")] }, showlegend: false, hoverinfo: "skip" }
      ], base({ margin: { l: 52, r: 12, t: 30, b: 44 },
        xaxis: Object.assign(base().xaxis, { title: "cobertura de bosque (%)", range: [0, 100] }),
        yaxis: Object.assign(base().yaxis, { title: "mm/año", rangemode: "tozero" }),
        shapes: [{ type: "line", x0: 100 * r.bosque_hoy, x1: 100 * r.bosque_hoy, yref: "paper", y0: 0, y1: 1, line: { color: css("--muted"), dash: "dot" } }],
        annotations: [{ x: 100 * r.bosque_hoy, y: 0.02, yref: "paper", text: " hoy", showarrow: false, yanchor: "bottom", xanchor: "left", font: { size: 11, color: css("--muted") } },
          { x: 1, xref: "paper", y: 1.12, yref: "paper", xanchor: "right", yanchor: "bottom", showarrow: false, font: { size: 11, color: css("--muted") },
            text: tipo === "nativo" ? "bosque nativo · Zhang et al. (2001)" : "pino · ×1,6 (Bosch y Hewlett, 1982)" }] }), CFG);
    }
    if (!el("rc-f").dataset.ok) { ["rc-f", "rc-tipo", "rc-beta"].forEach(i => el(i).addEventListener("input", act)); el("rc-f").dataset.ok = 1; }
    act();
  },
  "p1-dia": () => {
    const d = D.dia, nar = css("--sw"), gris = css("--muted");
    // 1) cascada de energia
    Plotly.react("g-dia-energia", [{
      type: "waterfall", orientation: "v",
      measure: ["absolute", "relative", "total", "relative", "total", "relative", "relative", "total"],
      x: ["R<sub>a</sub><br>tope", "atmósfera<br>despejada", "R<sub>so</sub>", "nubes", "R<sub>s</sub><br>suelo", "albedo<br>0,23", "onda<br>larga", "R<sub>n</sub>"],
      y: [d.ra, -(d.ra - d.rso), 0, -(d.rso - d.rs), 0, -(d.rs - d.rns), -d.rnl, 0],
      text: [d.ra, -(d.ra - d.rso), d.rso, -(d.rso - d.rs), d.rs, -(d.rs - d.rns), -d.rnl, d.rn].map(v => v.toFixed(1)),
      textposition: "outside", cliponaxis: false,
      decreasing: { marker: { color: rgba(ROJO(), .75) } }, totals: { marker: { color: nar } },
      increasing: { marker: { color: gris } }, connector: { line: { color: css("--line") } },
      hovertemplate: "%{x}: %{text} MJ m⁻² d⁻¹<extra></extra>"
    }], base({ margin: { l: 44, r: 8, t: 14, b: 50 }, showlegend: false,
      yaxis: Object.assign(base().yaxis, { title: "MJ m⁻² d⁻¹", range: [0, d.ra * 1.15] }),
      xaxis: Object.assign(base().xaxis, { tickfont: { size: 11 } }) }), CFG);
    // 2) curva de saturacion
    const T = [], E = [];
    for (let t = 4; t <= 28; t += 0.25) { T.push(t); E.push(e0(t)); }
    const az = AZUL(), ro = ROJO();
    Plotly.react("g-dia-sat", [
      { x: T, y: E, mode: "lines", line: { color: css("--fg"), width: 2 }, name: "e°(T)", hoverinfo: "skip" },
      { x: [d.tmin, d.tmax], y: [d.e_tmin, d.e_tmax], mode: "lines+markers", line: { color: ro, dash: "dot" },
        marker: { color: ro, size: 9 }, name: "e°(Tmín) y e°(Tmáx)",
        hovertemplate: "T = %{x:.1f} °C · e° = %{y:.2f} kPa<extra></extra>" },
      { x: [d.t], y: [d.es], mode: "markers", marker: { color: ro, size: 12, symbol: "diamond" }, name: "e<sub>s</sub> (FAO-56)",
        hovertemplate: "e<sub>s</sub> = %{y:.2f} kPa<extra></extra>" },
      { x: [d.t], y: [d.e_tmedia], mode: "markers", marker: { color: gris, size: 9, symbol: "x" }, name: "e°(T media)",
        hovertemplate: "e°(T media) = %{y:.2f} kPa<extra></extra>" },
      { x: [d.td], y: [d.ea], mode: "markers", marker: { color: az, size: 11 }, name: "e<sub>a</sub> = e°(T<sub>rocío</sub>)",
        hovertemplate: "T rocío = %{x:.1f} °C · e<sub>a</sub> = %{y:.2f} kPa<extra></extra>" },
      { x: [d.t, d.t], y: [d.ea, d.es], mode: "lines", line: { color: az, width: 4 }, name: "déficit e<sub>s</sub> − e<sub>a</sub>",
        hovertemplate: "déficit = " + (d.es - d.ea).toFixed(2) + " kPa<extra></extra>" },
      { x: [d.td, d.t], y: [d.ea, d.ea], mode: "lines", line: { color: az, width: 1, dash: "dot" }, showlegend: false, hoverinfo: "skip" }
    ], base({ margin: { l: 48, r: 8, t: 10, b: 44 }, legend: { x: 0.01, y: 0.99, font: { size: 11 }, bgcolor: "rgba(0,0,0,0)" },
      xaxis: Object.assign(base().xaxis, { title: "temperatura (°C)" }),
      yaxis: Object.assign(base().yaxis, { title: "presión de vapor (kPa)" }) }), CFG);
    // 3) resultado
    Plotly.react("g-dia-eto", [
      { type: "bar", orientation: "h", y: ["ETo"], x: [d.rad], name: "radiativo", marker: { color: nar },
        text: ["radiativo " + d.rad.toFixed(2)], textposition: "inside", hovertemplate: "término radiativo: %{x:.2f} mm/d<extra></extra>" },
      { type: "bar", orientation: "h", y: ["ETo"], x: [d.aero], name: "aerodinámico", marker: { color: gris },
        text: [d.aero.toFixed(2)], textposition: "outside", hovertemplate: "término aerodinámico: %{x:.2f} mm/d<extra></extra>" }
    ], base({ barmode: "stack", showlegend: false, margin: { l: 44, r: 20, t: 24, b: 36 },
      xaxis: Object.assign(base().xaxis, { title: "mm/d", range: [0, d.eto * 1.25] }),
      shapes: [{ type: "line", x0: d.eeq, x1: d.eeq, yref: "paper", y0: 0, y1: 1, line: { color: css("--fg"), dash: "dash" } }],
      annotations: [{ x: d.eeq, y: 1.0, yref: "paper", text: "E<sub>eq</sub> = " + d.eeq.toFixed(2), showarrow: false,
        yanchor: "bottom", font: { size: 11, color: css("--fg") } }] }), CFG);
  },
  "p1-cuenca": () => {
    const c = D.celdas, tr = [];
    const h = 0.05;
    c.lon.forEach((lo, i) => {
      const la = c.lat[i], fr = c.fraccion_celda[i];
      tr.push({ type: "scatter", mode: "lines", fill: "toself", hoverinfo: "text",
        x: [lo - h, lo + h, lo + h, lo - h, lo - h], y: [la - h, la - h, la + h, la + h, la - h],
        line: { color: css("--line"), width: 1 },
        fillcolor: rgba(AZUL(), 0.08 + 0.72 * fr),
        text: `celda ${la.toFixed(1)}°, ${lo.toFixed(1)}°<br>área en cuenca ${c.area_en_cuenca_km2[i].toFixed(1)} km²<br>fracción ${(100 * fr).toFixed(0)} %`,
        showlegend: false });
    });
    D.cuenca.forEach(r => tr.push({ type: "scatter", mode: "lines", x: r.map(p => p[0]), y: r.map(p => p[1]),
      line: { color: css("--fg"), width: 2 }, hoverinfo: "skip", showlegend: false }));
    Plotly.react("g-celdas", tr, base({
      margin: { l: 56, r: 10, t: 10, b: 40 },
      xaxis: Object.assign(base().xaxis, { title: "longitud (°)", dtick: 0.1, range: [-78.9, -78.1], constrain: "domain" }),
      yaxis: Object.assign(base().yaxis, { title: "latitud (°)", dtick: 0.1, range: [-8.1, -7.3], scaleanchor: "x", scaleratio: 1, constrain: "domain" })
    }), CFG);
  },
  "p2-peru": () => {
    const c = D.caj;
    Plotly.react("g-caj", [
      { type: "bar", x: c.anio, y: c.p6h, name: "reportes de 6 h", marker: { color: AZUL() },
        hovertemplate: "%{x}: %{y} reportes de 6 h<extra></extra>" },
      { type: "bar", x: c.anio, y: c.p1h, name: "reportes horarios", marker: { color: ROJO() },
        hovertemplate: "%{x}: %{y} reportes horarios<extra></extra>" }
    ], base({ barmode: "overlay", yaxis: Object.assign(base().yaxis, { title: "reportes por año", range: [0, 1600] }),
      title: { text: "Cajamarca aeropuerto (SPJR) · lluvia en GHCNh", font: { size: 14 }, x: 0 },
      shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 1460, y1: 1460, line: { color: css("--muted"), dash: "dot" } }] }), CFG);
  },
  "p2-cottbus": () => {
    const c = D.comp, gris = css("--muted");
    Plotly.react("g-comp", [
      { type: "bar", x: c.anio, y: c.pct_anio, name: "% del año", marker: { color: c.valido.map(v => v ? AZUL() : gris) },
        hovertemplate: "%{x}: %{y:.1f} % del año<extra></extra>" },
      { type: "scatter", mode: "markers", x: c.anio, y: c.pct_may_sep, name: "% may–sep", marker: { color: ROJO(), size: 7, symbol: "diamond" },
        hovertemplate: "%{x}: %{y:.1f} % en may–sep<extra></extra>" }
    ], base({ yaxis: Object.assign(base().yaxis, { title: "% de datos", range: [0, 104] }),
      margin: { l: 56, r: 16, t: 34, b: 64 }, legend: { orientation: "h", y: -0.28, x: 0, font: { size: 12 } },
      title: { text: "Completitud de la serie de 10 min (gris: año descartado)", font: { size: 14 }, x: 0 },
      shapes: [80, 90].map(y => ({ type: "line", xref: "paper", x0: 0, x1: 1, y0: y, y1: y, line: { color: gris, dash: "dot", width: 1 } })) }), CFG);
    Plotly.react("g-max", [
      { type: "bar", x: c.anio, y: c.max_10min_mm, marker: { color: c.valido.map(v => v ? AZUL() : gris) },
        hovertemplate: "%{x}: %{y:.1f} mm en 10 min<extra></extra>", showlegend: false }
    ], base({ margin: { l: 56, r: 16, t: 10, b: 40 }, yaxis: Object.assign(base().yaxis, { title: "mm en 10 min" }) }), CFG);
  }
};
const dibujados = new Set();
function dibujar(id) { if (G[id] && window.Plotly) { G[id](); dibujados.add(id); } }
function redibujar() { dibujados.forEach(id => G[id]()); }
window.addEventListener("resize", () => { if (window.Plotly) $$(".slide.on .js-plotly-plot").forEach(el => Plotly.Plots.resize(el)); });

const ini = slides.findIndex(s => "#" + s.id === location.hash);
go(ini >= 0 ? ini : 0);
