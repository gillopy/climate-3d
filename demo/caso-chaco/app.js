(function () {
  "use strict";

  var D = window.DEMO;
  if (!D) return;
  var T = window.TECNICO || null;
  var E = window.ESTE || null;

  var nf = new Intl.NumberFormat("es-PY", { maximumFractionDigits: 1 });
  var nf0 = new Intl.NumberFormat("es-PY", { maximumFractionDigits: 0 });
  var nf2 = new Intl.NumberFormat("es-PY", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var nf4 = new Intl.NumberFormat("es-PY", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

  function ha(v) { return nf.format(v) + " ha"; }
  function pct(a, b) { return nf.format(100 * a / b) + " %"; }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /* ---------- slider ---------- */

  function montarSlider(boxId, afterId, dividerId, rangeId) {
    var box = document.getElementById(boxId);
    var after = document.getElementById(afterId);
    var divider = document.getElementById(dividerId);
    var range = document.getElementById(rangeId);
    if (!box || !after || !divider || !range) return;

    function set(p) {
      p = Math.max(0, Math.min(100, p));
      after.style.clipPath = "inset(0 0 0 " + p + "%)";
      divider.style.left = p + "%";
      range.value = String(p);
    }

    function desdeEvento(ev) {
      var r = box.getBoundingClientRect();
      return ((ev.clientX - r.left) / r.width) * 100;
    }

    var arrastrando = false;

    box.addEventListener("pointerdown", function (ev) {
      arrastrando = true;
      box.setPointerCapture(ev.pointerId);
      set(desdeEvento(ev));
    });
    box.addEventListener("pointermove", function (ev) {
      if (arrastrando) set(desdeEvento(ev));
    });
    box.addEventListener("pointerup", function (ev) {
      arrastrando = false;
      if (box.hasPointerCapture(ev.pointerId)) box.releasePointerCapture(ev.pointerId);
    });
    box.addEventListener("pointercancel", function () { arrastrando = false; });
    range.addEventListener("input", function () { set(parseFloat(range.value)); });

    set(50);
  }

  montarSlider("slider", "sliderAfter", "sliderDivider", "sliderRange");
  montarSlider("esteSlider", "esteSliderAfter", "esteSliderDivider", "esteSliderRange");
  montarSlider("s2Slider", "s2SliderAfter", "s2SliderDivider", "s2SliderRange");
  montarSlider("resSlider", "resSliderAfter", "resSliderDivider", "resSliderRange");
  montarSlider("resNisarSlider", "resNisarSliderAfter", "resNisarSliderDivider", "resNisarSliderRange");

  /* ---------- cifras destacadas ---------- */

  (function () {
    var host = document.getElementById("stats");
    if (!host) return;

    var chaco = T ? nf0.format(T.caso.mmu.ha_con_mmu) : "—";
    var este = E ? nf0.format(E.caso.mmu.ha_con_mmu) : "—";
    var control = (T && E)
      ? nf.format(Math.max(T.control.mmu.ha_con_mmu, E.control.mmu.ha_con_mmu))
      : "—";

    var items = [
      { num: chaco, unit: " ha", label: "Chaco, con unidad mínima de 0,5 ha" },
      { num: este, unit: " ha", label: "Este, con unidad mínima de 0,5 ha" },
      { num: control, unit: " ha", label: "de cambio coherente en los dos controles" }
    ];

    items.forEach(function (it) {
      var s = el("div", "stat");
      var n = el("span", "stat__num");
      n.textContent = it.num;
      if (it.unit) n.appendChild(el("small", null, it.unit));
      s.appendChild(n);
      s.appendChild(el("span", "stat__label", it.label));
      host.appendChild(s);
    });
  })();

  /* ---------- mapa ---------- */

  (function () {
    var host = document.getElementById("mapa");
    if (!host) return;

    var KM_LON = 111.32;
    var KM_LAT = 110.574;
    var c = D.caso, k = D.control;

    function centro(poly) {
      var x = 0, y = 0, n = poly.length - 1;
      for (var i = 0; i < n; i++) { x += poly[i][0]; y += poly[i][1]; }
      return [x / n, y / n];
    }

    var cc = centro(c.poligono);
    var kc = centro(k.poligono);

    var lons = c.poligono.concat(k.poligono).map(function (p) { return p[0]; });
    var lats = c.poligono.concat(k.poligono).map(function (p) { return p[1]; });

    var padLon = (Math.max.apply(null, lons) - Math.min.apply(null, lons)) * 0.16;
    var padLat = (Math.max.apply(null, lats) - Math.min.apply(null, lats)) * 0.16;

    var w = Math.min.apply(null, lons) - padLon;
    var e = Math.max.apply(null, lons) + padLon;
    var s = Math.min.apply(null, lats) - padLat;
    var n = Math.max.apply(null, lats) + padLat;

    var midLat = (n + s) / 2;
    var kmx = KM_LON * Math.cos(midLat * Math.PI / 180);
    var kmy = KM_LAT;

    var Wkm = (e - w) * kmx;
    var Hkm = (n - s) * kmy;
    var H = 865;
    var scale = Math.min(1000 / Wkm, H / Hkm);
    var ox = (1000 - Wkm * scale) / 2;
    var oy = (H - Hkm * scale) / 2;

    function px(lon) { return ox + (lon - w) * kmx * scale; }
    function py(lat) { return oy + (n - lat) * kmy * scale; }

    function path(poly) {
      return poly.map(function (p, i) {
        return (i === 0 ? "M" : "L") + px(p[0]).toFixed(1) + " " + py(p[1]).toFixed(1);
      }).join(" ") + " Z";
    }

    var paso = 5 * kmx * scale;
    var grid = "";
    for (var gx = paso; gx < 1000; gx += paso) {
      grid += '<line x1="' + gx.toFixed(0) + '" y1="0" x2="' + gx.toFixed(0) + '" y2="' + H + '" stroke="#1b1b22" stroke-width="1"/>';
    }
    for (var gy = paso; gy < H; gy += paso) {
      grid += '<line x1="0" y1="' + gy.toFixed(0) + '" x2="1000" y2="' + gy.toFixed(0) + '" stroke="#1b1b22" stroke-width="1"/>';
    }

    var dx = (cc[0] - kc[0]) * kmx;
    var dy = (cc[1] - kc[1]) * kmy;
    var dist = Math.sqrt(dx * dx + dy * dy);
    var bar = 5 * kmx * scale;

    var svg =
      '<svg viewBox="0 0 1000 ' + H + '" role="img" aria-label="Mapa esquemático del área de estudio y del polígono de control">' +
      '<rect width="1000" height="' + H + '" fill="#0c0c10"/>' + grid +
      '<line x1="' + px(kc[0]) + '" y1="' + py(kc[1]) + '" x2="' + px(cc[0]) + '" y2="' + py(cc[1]) +
        '" stroke="#5e6ad2" stroke-width="1.5" stroke-dasharray="3 6" opacity="0.7"/>' +
      '<path d="' + path(k.poligono) + '" fill="rgba(155,155,170,0.07)" stroke="#7a7a88" stroke-width="2.5" stroke-dasharray="10 8"/>' +
      '<path d="' + path(c.poligono) + '" fill="rgba(255,107,74,0.18)" stroke="#ff6b4a" stroke-width="3"/>' +
      '<text x="' + px(kc[0]) + '" y="' + (py(kc[1]) + 8) + '" fill="#c9c9d4" font-size="26" font-family="system-ui, sans-serif" text-anchor="middle">control</text>' +
      '<text x="' + px(cc[0]) + '" y="' + (py(cc[1]) + 8) + '" fill="#ffb3a0" font-size="26" font-family="system-ui, sans-serif" text-anchor="middle">desmonte</text>' +
      '<text x="' + ((px(kc[0]) + px(cc[0])) / 2) + '" y="' + ((py(kc[1]) + py(cc[1])) / 2 - 10) +
        '" fill="#9b9baa" font-size="20" font-family="system-ui, sans-serif" text-anchor="middle">' +
        nf.format(dist) + " km</text>" +
      '<line x1="36" y1="' + (H - 40) + '" x2="' + (36 + bar) + '" y2="' + (H - 40) + '" stroke="#ececf1" stroke-width="4"/>' +
      '<line x1="36" y1="' + (H - 50) + '" x2="36" y2="' + (H - 30) + '" stroke="#ececf1" stroke-width="3"/>' +
      '<line x1="' + (36 + bar) + '" y1="' + (H - 50) + '" x2="' + (36 + bar) + '" y2="' + (H - 30) + '" stroke="#ececf1" stroke-width="3"/>' +
      '<text x="36" y="' + (H - 14) + '" fill="#9b9baa" font-size="20" font-family="system-ui, sans-serif">5 km</text>' +
      "</svg>";

    host.innerHTML = svg;
  })();

  /* ---------- barras por par ---------- */

  (function () {
    var host = document.getElementById("chart");
    if (!host) return;

    var max = 0;
    D.pasos.forEach(function (p) { max = Math.max(max, p.perdida); });
    if (!max) max = 1;

    D.pasos.forEach(function (p) {
      var step = el("div", "step");
      var bars = el("div", "step__bars");

      var loss = el("div", "bar bar--loss");
      loss.style.height = Math.max(2, (p.perdida / max) * 100) + "%";
      loss.title = p.perdida + " ha de pérdida";

      var ctrl = el("div", "bar bar--ctrl");
      ctrl.style.height = Math.max(2, (p.control_perdida / max) * 100) + "%";
      ctrl.title = p.control_perdida + " ha de pérdida en el control";

      bars.appendChild(loss);
      bars.appendChild(ctrl);

      var val = el("div", "step__value", nf0.format(p.perdida) + " ha");
      if (p.ganancia > 0) val.appendChild(el("span", null, "  +" + nf0.format(p.ganancia)));

      step.appendChild(bars);
      step.appendChild(val);
      step.appendChild(el("div", "step__label", p.desde + " → " + p.hasta));
      host.appendChild(step);
    });
  })();

  /* ---------- tabla de pares ---------- */

  (function () {
    var t = document.getElementById("tablaPasos");
    if (!t) return;

    var head = "<thead><tr><th>Par de 12 días</th><th>Pérdida</th><th>Ganancia</th><th>Control pérdida</th><th>Control ganancia</th></tr></thead>";

    var body = "<tbody>" + D.pasos.map(function (p) {
      return "<tr>" +
        "<td>" + p.desde + " → " + p.hasta + "</td>" +
        '<td class="' + (p.perdida ? "is-loss" : "is-zero") + '">' + nf.format(p.perdida) + " ha</td>" +
        '<td class="' + (p.ganancia ? "is-gain" : "is-zero") + '">' + nf.format(p.ganancia) + " ha</td>" +
        '<td class="' + (p.control_perdida ? "" : "is-zero") + '">' + nf.format(p.control_perdida) + " ha</td>" +
        '<td class="' + (p.control_ganancia ? "is-gain" : "is-zero") + '">' + nf.format(p.control_ganancia) + " ha</td>" +
        "</tr>";
    }).join("") + "</tbody>";

    var sumL = D.pasos.reduce(function (a, p) { return a + p.perdida; }, 0);
    var sumG = D.pasos.reduce(function (a, p) { return a + p.ganancia; }, 0);
    var sumCL = D.pasos.reduce(function (a, p) { return a + p.control_perdida; }, 0);
    var sumCG = D.pasos.reduce(function (a, p) { return a + p.control_ganancia; }, 0);

    var foot = "<tfoot>" +
      "<tr><td>Suma de los pares</td>" +
      '<td class="is-loss">' + nf.format(sumL) + " ha</td>" +
      '<td class="is-gain">' + nf.format(sumG) + " ha</td>" +
      "<td>" + nf.format(sumCL) + " ha</td>" +
      "<td>" + nf.format(sumCG) + " ha</td></tr>" +
      "<tr><td>Acumulado 20 ene → 21 mar</td>" +
      '<td class="is-loss">' + nf.format(D.caso.perdida_ha) + " ha</td>" +
      '<td class="is-gain">' + nf.format(D.caso.ganancia_ha) + " ha</td>" +
      "<td>" + nf.format(D.control.perdida_ha) + " ha</td>" +
      "<td>" + nf.format(D.control.ganancia_ha) + " ha</td></tr>" +
      "</tfoot>";

    t.innerHTML = head + body + foot;
  })();

  /* ---------- veredicto ---------- */

  (function () {
    var host = document.getElementById("verdict");
    if (!host) return;

    var d = D.caso, k = D.control;
    var ratio = d.perdida_ha / k.perdida_ha;
    var porMilCaso = (d.perdida_ha / d.area_ha) * 1000;
    var porMilCtrl = (k.perdida_ha / k.area_ha) * 1000;

    host.innerHTML =
      "<h3>El control fija la escala del error</h3>" +
      '<p><span class="ratio">' + Math.round(ratio) + ":1</span></p>" +
      "<p>El desmonte pierde " + ha(d.perdida_ha) + " y el bosque intacto " + ha(k.perdida_ha) +
      " con las mismas imágenes y el mismo umbral. Normalizado por superficie, " +
      "<strong>" + nf.format(porMilCaso) + " ha por cada 1.000 ha</strong> en el desmonte " +
      "frente a <strong>" + nf.format(porMilCtrl) + " ha por cada 1.000 ha</strong> en el control.</p>";
  })();

  /* ---------- ventanas ---------- */

  (function () {
    var host = document.getElementById("cards");
    if (!host) return;

    D.ventanas.forEach(function (v) {
      var card = el("article", "card card--" + v.estado);
      card.appendChild(el("span", "card__tag", v.etiqueta));
      card.appendChild(el("h3", "card__title", v.estado === "valida" ? "Par adyacente" : "Comparación larga"));
      card.appendChild(el("p", "card__dates", v.detalle));

      var nums = el("div", "card__nums");
      var l = el("div", "card__num card__num--loss");
      l.innerHTML = nf0.format(v.perdida) + " ha<small>pérdida</small>";
      var g = el("div", "card__num card__num--gain");
      g.innerHTML = nf0.format(v.ganancia) + " ha<small>ganancia</small>";
      nums.appendChild(l);
      nums.appendChild(g);

      card.appendChild(nums);
      card.appendChild(el("p", "card__read", v.lectura));
      host.appendChild(card);
    });
  })();

  /* ---------- método ---------- */

  (function () {
    var host = document.getElementById("pasosMetodo");
    if (!host) return;

    var pasos = [
      ["Escena.", " NISAR L2 GCOV, banda L, doble polarización HH y HV. Recorte sobre la grilla geocodificada del producto."],
      ["Píxel.", " 20 m × 20 m en el Chaco y 10 m × 10 m en el Este. Un píxel de 20 m equivale a 400 m²; uno de 10 m, a 100 m²."],
      ["Validez.", " Se descarta todo píxel que la máscara del producto no marque como dato."],
      ["Bosque.", " <code>HV_antes &gt; −15,5 dB</code>. Es un umbral de dosel, no un mapa de cobertura forestal."],
      ["Cambio.", " <code>ΔHV = HV_después − HV_antes</code>, por píxel y en dB."],
      ["Máscara.", " <code>ΔHV &lt; −3 dB</code>."],
      ["Coherencia espacial.", " Voto de mayoría 3×3: el píxel se conserva si al menos 5 de sus 9 vecinos también cumplen la condición."],
      ["Mapeo.", " Componentes conexas de 8 vecinos. Se descarta toda mancha menor a 0,5 ha: 12,5 píxeles a 20 m y 50 píxeles a 10 m."],
      ["Área.", " Píxeles conservados × superficie del píxel ÷ 10.000."]
    ];

    pasos.forEach(function (p) {
      var li = document.createElement("li");
      li.appendChild(el("strong", null, p[0]));
      if (p[1].indexOf("<code>") >= 0) li.insertAdjacentHTML("beforeend", p[1]);
      else li.appendChild(document.createTextNode(p[1]));
      host.appendChild(li);
    });
  })();

  (function () {
    var host = document.getElementById("formula");
    if (!host) return;
    host.innerHTML =
      "ΔHV(dB) = 10 · log10( P_después / P_antes )<span>      // P en potencia lineal, nunca en dB</span><br>" +
      "1 píxel = 400 m² (Chaco) | 100 m² (Este)<span>      25 px = 1 ha a 20 m</span><br>" +
      "MMU = 0,5 ha = 12,5 px a 20 m | 50 px a 10 m<span>   superficie = Σ bloques ≥ MMU × m² / 10.000</span>";
  })();

  /* ---------- barrido de umbral (reutilizable) ---------- */

  function tablaUmbral(host, X) {
    if (!host || !X) return;

    var head = "<thead><tr><th>Umbral</th><th>Desmonte</th><th>Control</th><th>Relación</th></tr></thead>";
    var rows = X.caso.sensibilidad.map(function (s, i) {
      var c = X.control.sensibilidad[i];
      var ratio = c.px > 0 ? nf0.format(s.px / c.px) + " : 1" : "∞";
      var activo = Math.abs(s.db - X.parametros.umbral_db) < 0.01;
      return "<tr>" +
        "<td>" + nf.format(s.db) + " dB" + (activo ? " ●" : "") + "</td>" +
        '<td class="is-loss">' + nf.format(s.ha) + " ha</td>" +
        "<td>" + nf.format(c.ha) + " ha</td>" +
        "<td>" + ratio + "</td>" +
        "</tr>";
    }).join("");

    host.innerHTML = head + "<tbody>" + rows + "</tbody>";
  }

  tablaUmbral(document.getElementById("tablaUmbral"), T);
  tablaUmbral(document.getElementById("tablaUmbralEste"), E);

  /* ---------- mmu y corrección ---------- */

  (function () {
    var host = document.getElementById("mmuStats");
    if (!host || !T) return;
    var m = T.caso.mmu;
    var retenido = m.ha_sin_mmu ? (100 * m.ha_con_mmu / m.ha_sin_mmu) : 0;

    var filas = [
      ["Componentes conexas", nf0.format(m.componentes), ""],
      ["Superan 0,5 ha", nf0.format(m.componentes_validos), "is-ok"],
      ["Superficie retenida", nf.format(m.ha_con_mmu) + " ha", "is-ok"],
      ["Retenido del total", nf.format(retenido) + " %", ""],
      ["Componente mayor", nf.format(m.componente_mayor_ha) + " ha", ""],
      ["Componente mediana", nf2.format(m.componente_mediana_ha) + " ha", ""]
    ];

    filas.forEach(function (f) {
      var d = document.createElement("div");
      d.appendChild(el("dt", null, f[0]));
      d.appendChild(el("dd", f[2] || null, f[1]));
      host.appendChild(d);
    });
  })();

  (function () {
    var host = document.getElementById("corrStats");
    if (!host || !T) return;
    var c = T.correccion;

    var filas = [
      ["Tasa de pérdida del control", nf4.format(c.tasa_control_pct) + " %", ""],
      ["Falsos positivos esperados", nf.format(c.fp_esperados_ha) + " ha", ""],
      ["Superficie sin corregir", nf.format(T.caso.perdida_ha) + " ha", "is-loss"],
      ["Superficie corregida", nf.format(c.perdida_corregida_ha) + " ha", "is-ok"]
    ];

    filas.forEach(function (f) {
      var d = document.createElement("div");
      d.appendChild(el("dt", null, f[0]));
      d.appendChild(el("dd", f[2] || null, f[1]));
      host.appendChild(d);
    });
  })();

  /* ---------- firma polarimétrica ---------- */

  (function () {
    var t = document.getElementById("tablaFirma");
    if (!t || !T) return;

    function fila(nombre, dhv, dhh, pix) {
      var ratio = dhv - dhh;
      return "<tr>" +
        "<td>" + nombre + "</td>" +
        '<td class="' + (dhv < 0 ? "is-loss" : "") + '">' + nf.format(dhv) + " dB</td>" +
        '<td class="' + (dhh < 0 ? "is-loss" : "") + '">' + nf.format(dhh) + " dB</td>" +
        "<td>" + (ratio > 0 ? "+" : "") + nf.format(ratio) + " dB</td>" +
        "<td>" + (pix != null ? nf0.format(pix) : "—") + "</td>" +
        "</tr>";
    }

    var c = T.caso, k = T.control;

    t.innerHTML =
      "<thead><tr><th>Conjunto</th><th>ΔHV</th><th>ΔHH</th><th>Δ(HV−HH)</th><th>Píxeles</th></tr></thead>" +
      "<tbody>" +
      fila("Desmonte, píxeles de pérdida", c.firma.delta_hv_db, c.firma.delta_hh_db, c.firma.pixeles) +
      fila("Desmonte, caja completa", c.delta_hv_medio_db, c.delta_hh_medio_db, c.px_bosque) +
      fila("Control, caja completa", k.delta_hv_medio_db, k.delta_hh_medio_db, k.px_bosque) +
      "</tbody>";

    var lectura = document.getElementById("lecturaFirma");
    if (lectura) {
      lectura.innerHTML =
        "Sobre la caja completa, HV y HH caen casi lo mismo (" + nf.format(c.delta_hv_medio_db) +
        " y " + nf.format(c.delta_hh_medio_db) + " dB): ese comportamiento corresponde a humedad. " +
        "En los píxeles clasificados como pérdida, HV cae <strong>" +
        nf.format(Math.abs(c.firma.delta_ratio_db)) + " dB más que HH</strong>, lo que es compatible " +
        "con pérdida de dispersión de volumen. El control no muestra ninguna de las dos cosas.";
    }
  })();

  /* ---------- histograma (reutilizable) ---------- */

  function dibujarHistograma(host, X) {
    if (!host || !X) return;

    var bins = X.bins.slice(0, -1);
    var caso = X.caso.hist;
    var ctrl = X.control.hist;
    var n = caso.length;

    var max = 0;
    for (var i = 0; i < n; i++) max = Math.max(max, caso[i], ctrl[i]);
    if (!max) return;

    var ml = 58, mr = 18, mt = 18, mb = 46;
    var W = 1000, H = 340;

    function x(i) { return ml + ((i + 0.5) / n) * (W - ml - mr); }
    function y(v) { return H - mb - (v / max) * (H - mt - mb); }

    function linea(datos, color, ancho) {
      var d = datos.map(function (v, i) {
        return (i === 0 ? "M" : "L") + x(i).toFixed(1) + " " + y(v).toFixed(1);
      }).join(" ");
      return '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="' + ancho +
        '" stroke-linejoin="round" stroke-linecap="round"/>';
    }

    function area(datos, color) {
      var d = datos.map(function (v, i) {
        return (i === 0 ? "M" : "L") + x(i).toFixed(1) + " " + y(v).toFixed(1);
      }).join(" ") + " L" + x(n - 1).toFixed(1) + " " + y(0) + " L" + x(0).toFixed(1) + " " + y(0) + " Z";
      return '<path d="' + d + '" fill="' + color + '" opacity="0.14" stroke="none"/>';
    }

    var ticks = [-12, -8, -4, 0, 4];
    var ejeX = ticks.map(function (v) {
      var i = (v - bins[0]) / 0.5;
      return '<text x="' + x(i).toFixed(1) + '" y="' + (H - 20) + '" fill="#6c6c7a" font-size="20" ' +
        'font-family="system-ui, sans-serif" text-anchor="middle">' + v + "</text>";
    }).join("");

    var grid = "";
    for (var g = 0; g <= 4; g++) {
      var v = (max * g) / 4;
      var yy = y(v);
      grid += '<line x1="' + ml + '" y1="' + yy.toFixed(1) + '" x2="' + (W - mr) + '" y2="' + yy.toFixed(1) +
        '" stroke="#1b1b22" stroke-width="1"/>';
      grid += '<text x="' + (ml - 8) + '" y="' + (yy + 6).toFixed(1) + '" fill="#6c6c7a" font-size="18" ' +
        'font-family="system-ui, sans-serif" text-anchor="end">' +
        (v * 100).toFixed(1).replace(".", ",") + "</text>";
    }

    var iU = (-3 - bins[0]) / 0.5;
    var xU = x(iU);

    host.innerHTML =
      '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Distribución de delta HV en el desmonte y en el control">' +
      '<rect width="' + W + '" height="' + H + '" fill="#0c0c10"/>' +
      grid +
      '<line x1="' + xU.toFixed(1) + '" y1="' + mt + '" x2="' + xU.toFixed(1) + '" y2="' + (H - mb) +
        '" stroke="#ff6b4a" stroke-width="2" stroke-dasharray="7 6" opacity="0.85"/>' +
      '<text x="' + (xU + 8).toFixed(1) + '" y="' + (mt + 20) + '" fill="#ff8a6e" font-size="18" ' +
        'font-family="system-ui, sans-serif">−3 dB</text>' +
      area(caso, "#ff6b4a") + area(ctrl, "#9b9baa") +
      linea(ctrl, "#9b9baa", 2.5) + linea(caso, "#ff6b4a", 3) +
      ejeX +
      '<text x="' + (W - mr) + '" y="' + (H - 2) + '" fill="#6c6c7a" font-size="18" ' +
        'font-family="system-ui, sans-serif" text-anchor="end">ΔHV (dB)</text>' +
      '<text x="' + (W - mr) + '" y="' + (mt + 2) + '" fill="#6c6c7a" font-size="18" ' +
        'font-family="system-ui, sans-serif" text-anchor="end">% de píxeles de bosque por intervalo</text>' +
      "</svg>";
  }

  dibujarHistograma(document.getElementById("histograma"), T);
  dibujarHistograma(document.getElementById("histogramaEste"), E);

  /* ---------- comparación de las dos escenas ---------- */

  (function () {
    var t = document.getElementById("tablaCasos");
    if (!t || !T || !E) return;

    var c = T.caso, k = T.control, e = E.caso, ek = E.control;

    var filas = [
      ["Ventana", "60 días", "48 días"],
      ["Resolución", c.mpp + " m/px", e.mpp + " m/px"],
      ["Área de la caja", ha(c.area_ha), ha(e.area_ha)],
      ["Bosque", ha(c.bosque_ha) + " (" + pct(c.bosque_ha, c.area_ha) + ")",
        ha(e.bosque_ha) + " (" + pct(e.bosque_ha, e.area_ha) + ")"],
      ["Pérdida a 3 dB", ha(c.perdida_ha), ha(e.perdida_ha)],
      ["Componentes conexas", nf0.format(c.mmu.componentes), nf0.format(e.mmu.componentes)],
      ["Superan 0,5 ha",
        ha(c.mmu.ha_con_mmu) + " (" + pct(c.mmu.ha_con_mmu, c.mmu.ha_sin_mmu) + ")",
        ha(e.mmu.ha_con_mmu) + " (" + pct(e.mmu.ha_con_mmu, e.perdida_ha) + ")"],
      ["Control, superan 0,5 ha", ha(k.mmu.ha_con_mmu), ha(ek.mmu.ha_con_mmu)],
      ["Firma ΔHV − ΔHH", nf.format(c.firma.delta_ratio_db) + " dB", nf.format(e.firma.delta_ratio_db) + " dB"]
    ];

    t.innerHTML = "<thead><tr><th></th><th>Chaco</th><th>Este</th></tr></thead><tbody>" +
      filas.map(function (f) {
        return "<tr><td>" + f[0] + "</td><td>" + f[1] + "</td><td>" + f[2] + "</td></tr>";
      }).join("") + "</tbody>";

    var lectura = document.getElementById("lecturaEste");
    if (lectura) {
      lectura.innerHTML =
        "En el Este, " + nf0.format(e.mmu.componentes) + " componentes se reducen a " +
        nf0.format(e.mmu.componentes_validos) + " al exigir 0,5 ha, y la superficie cae de " +
        ha(e.perdida_ha) + " a " + ha(e.mmu.ha_con_mmu) + ". El control, con " +
        nf0.format(ek.mmu.componentes) + " fragmentos, no produce ningún bloque que supere ese " +
        "mínimo: su componente mayor mide " + nf2.format(ek.mmu.componente_mayor_ha) + " ha.";
    }
  })();

  /* ---------- distribución por tamaño ---------- */

  (function () {
    var t = document.getElementById("tablaDistribucion");
    if (!t || !T || !E) return;

    var rc = T.caso.mmu.distribucion || [];
    var re = E.caso.mmu.distribucion || [];

    var head = "<thead><tr><th>Tamaño</th><th>Chaco n</th><th>Chaco ha</th><th>Este n</th><th>Este ha</th></tr></thead>";
    var body = rc.map(function (f, i) {
      var g = re[i] || { componentes: 0, ha: 0 };
      return "<tr>" +
        "<td>" + f.rango + " ha</td>" +
        "<td>" + nf0.format(f.componentes) + "</td>" +
        '<td class="is-loss">' + nf.format(f.ha) + "</td>" +
        "<td>" + nf0.format(g.componentes) + "</td>" +
        '<td class="is-loss">' + nf.format(g.ha) + "</td>" +
        "</tr>";
    }).join("");

    t.innerHTML = head + "<tbody>" + body + "</tbody>";

    var nota = document.getElementById("escalaNota");
    if (nota) {
      var caida = 100 * (1 - D.escala.este_20m_ha / E.caso.perdida_ha);
      nota.innerHTML =
        "Al remuestrear la misma escena del Este de 10 a 20 m, el conteo directo cae de " +
        ha(E.caso.perdida_ha) + " a " + ha(D.escala.este_20m_ha) + ", un " +
        nf0.format(caida) + " % menos, sin que cambie el terreno. El conteo de píxeles sobre " +
        "un umbral no es estable frente a la escala. El área de componentes coherentes depende " +
        "menos, porque exige una mancha mínima, pero tampoco es invariante. Ambas cifras se " +
        "informan como rango y no como valor único.";
    }
  })();

  /* ---------- tabla de la reserva ---------- */

  (function () {
    var t = document.getElementById("tablaReserva");
    if (!t || !D.reserva) return;

    var r = D.reserva;
    var filas = [
      ["Sensor", "Sentinel-2 L2A"],
      ["Ventana", r.antes + " → " + r.despues],
      ["Área de la caja", ha(r.area_ha)],
      ["Dentro de la reserva", ha(r.dentro_reserva_ha)],
      ["Pérdida bruta", ha(r.perdida_ha)],
      ["Con unidad mínima de 0,5 ha", ha(r.mmu_ha) + " en " + r.parcelas + " parcelas"],
      ["Parcela mayor", ha(r.mayor_ha)],
      ["Control", ha(r.control_ha)],
      ["NDVI medio del bosque", nf.format(r.ndvi_antes) + " → " + nf.format(r.ndvi_despues)]
    ];

    t.innerHTML = "<thead><tr><th>Métrica</th><th>Valor</th></tr></thead><tbody>" +
      filas.map(function (f) {
        return "<tr><td>" + f[0] + "</td><td>" + f[1] + "</td></tr>";
      }).join("") + "</tbody>";
  })();

  /* ---------- límites ---------- */

  (function () {
    var host = document.getElementById("limits");
    if (!host) return;

    var items = [
      ["Producto provisional.", " NISAR L2 GCOV PROVISIONAL V1. La colección puede reprocesarse y los valores cambiar entre versiones."],
      ["El cambio es de cobertura, no de biomasa.", " Sentinel-2 muestra la pérdida de dosel y el suelo desnudo, pero cuantificar cuánta biomasa se perdió requiere inventario de campo."],
      ["NISAR mide estructura, no biomasa.", " Convertir retrodispersión en biomasa o volumen exige calibración con inventario forestal de campo."],
      ["El umbral de 3 dB no está calibrado contra verdad de campo.", " El barrido muestra que la conclusión se sostiene entre 2 y 4 dB, pero eso no reemplaza un inventario en terreno."],
      ["La ganancia de 102 ha no fue rebrote.", " El control registró 26,6 ha en la misma ventana: el aumento es de la escena completa."],
      ["Sin corrección por ángulo de incidencia local.", " El detector aplica voto de mayoría 3×3 y componentes conexas, pero no normaliza el ángulo de incidencia ni filtra speckle multitemporal."],
      ["La firma polarimétrica es indicativa, no concluyente.", " La diferencia de 1,52 dB entre HV y HH es compatible con pérdida de dispersión de volumen, pero una sola diferencia polarimétrica no demuestra el mecanismo."],
      ["La validación óptica con estas mismas fechas está pendiente.", " Falta Sentinel-2 del 20 de enero y del 21 de marzo para la matriz de confusión definitiva."],
      ["La superficie depende del criterio.", " Suma de pares de 12 días: 126 ha. Umbral acumulado: 263 ha. Con unidad mínima de 0,5 ha: 245 ha. Corregida por el control: 262 ha. Se informan las cuatro."],
      ["El control del Este se eligió sobre la máscara, no en terreno.", " Es una caja de 1.892 ha con 94 % de bosque, pero su condición de bosque intacto no fue verificada en campo."]
    ];

    items.forEach(function (it) {
      var li = document.createElement("li");
      li.appendChild(el("strong", null, it[0]));
      li.appendChild(document.createTextNode(it[1]));
      host.appendChild(li);
    });
  })();

  /* ---------- ficha ---------- */

  (function () {
    var host = document.getElementById("specs");
    if (!host) return;

    var m = D.meta;
    var filas = [
      ["Sensor", m.sensor],
      ["Colección", m.coleccion],
      ["Track / frame", m.track + " / " + m.frame],
      ["Polarización", m.polarizacion],
      ["Banda usada", m.banda],
      ["Resolución Chaco", m.mpp + " m/px"],
      ["Resolución Este", (E ? E.caso.mpp : "—") + " m/px"],
      ["Proyección", "EPSG:" + m.epsg],
      ["Umbral", m.umbral_db + " dB"],
      ["HV mínimo", m.hv_min_db + " dB"],
      ["Área Chaco", nf.format(D.caso.area_ha) + " ha"],
      ["Área control Chaco", nf.format(D.control.area_ha) + " ha"],
      ["Ventana Chaco", D.caso.desde + " → " + D.caso.hasta]
    ];

    filas.forEach(function (r) {
      var d = document.createElement("div");
      d.appendChild(el("dt", null, r[0]));
      d.appendChild(el("dd", null, r[1]));
      host.appendChild(d);
    });
  })();

  /* ---------- números de las figuras ---------- */

  (function () {
    var d = document.getElementById("numDesmonte");
    var c = document.getElementById("numControl");
    if (d) d.textContent = nf.format(D.caso.perdida_ha) + " ha";
    if (c) c.textContent = nf.format(D.control.perdida_ha) + " ha";
  })();
})();
