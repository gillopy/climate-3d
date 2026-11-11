// Terra (EOS AM-1) — figura isométrica de integración, estilo Anatomy.
// Orientación y medidas tomadas del Terra.glb (NASA 3D Resources), 1 unidad = 10 cm.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "./kit/iso-kit.mjs";
import * as L from "./kit/lathe.mjs";
import { kitScript } from "./scripts/inline-kit.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const WIDTH = 940;
const HEIGHT = 600;

// ---------- mundo ----------
const BUS = { x: -13, y: -34, w: 26, d: 68, r: 2.5 };
const BUS_Z = 40;
const BUS_TOP = 75;
const PANEL_X = 13;           // cara +X: panel hexagonal radiador
const BOOM_Z = 57;
const WING = { x: -168, y: -25, w: 84, d: 50, r: 1.5 };
const WING_Z = 56;
const MAST = [-2, 18];        // x,y del mástil de la parabólica
const DISH_Z = 96;

const P = k.fitProjection(
  [
    [-22, -40, 34],
    [24, 40, 80],
    [-16, -36, 0],
    [16, 36, 80],
    [PANEL_X + 2, -30, 74],
    [WING.x, WING.y, WING_Z],
    [WING.x, WING.y + WING.d, WING_Z],
    [MAST[0], MAST[1], DISH_Z + 6],
    [PANEL_X + 1, 30, 74],
  ],
  WIDTH,
  HEIGHT,
  { pad: 6, azimuth: 38, elevation: 30 },
);

const at = (p) => k.iso(p, P);
const S = (paths, style = {}) => k.solidSvg(paths, { crease: "lo", ...style });
const D = (points, style) => k.dotsSvg(points, style);
const LN = (d, style) => k.lineSvg(d, style);
const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));

function member(from, to, size, tone = "mid") {
  const dir = [to[0] - from[0], to[1] - from[1], to[2] - from[2]];
  const len = Math.hypot(...dir);
  const F = L.frameAlong(from, dir.map((v) => v / len));
  const h = size / 2;
  return S(L.prismOf(F, [[-h, -h], [h, -h], [h, h], [-h, h]], 0, len, P), { tone });
}

// ---------- dolly de integración ----------
function dolly() {
  const plate = { x: -42, y: -44, w: 84, d: 88, r: 4 };
  const out = [`<path class="iso-halo" d="${k.haloOf(plate, -16, 16, P)}"/>`];
  for (const [x, y] of byDepth(k.corners(plate, 20))) {
    out.push(S(k.cylinder(x, y, 2.6, -15, 3.4, P, 20), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 3.4, -11, 5, P, 20), { tone: "lo" }));
  }
  out.push(S(k.slabOf(plate, -7, 7, P, 8, 1.2), { tone: "lo" }));
  out.push(LN(k.planOutline(k.insetPlan(plate, 4), 0, P), { tone: "lo" }));
  const screws = k.corners(plate, 9);
  out.push(LN(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5, tone: "lo" }));
  // regla y placa
  const strip = { x: -38, y: plate.y + plate.d - 11, w: 76, d: 5, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.7, P, 3), { tone: "lo", crease: "none" }));
  const ticks = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 4, 5, strip.y + 0.9, 0.7, [2.2, 3.8], P);
  out.push(LN(ticks.minor, { tone: "lo" }), LN(ticks.major, { tone: "mid" }));
  const tag = { x: 10, y: plate.y + 12, w: 24, d: 11, r: 1.2 };
  out.push(S(k.slabOf(tag, 0, 0.8, P, 3), { tone: "lo", crease: "none" }));
  out.push(LN([8, 11].map((dy) => k.lineOnTop([tag.x + 4, tag.y + dy], [tag.x + tag.w - 4, tag.y + dy], 0.8, P)).join(""), { tone: "lo" }));
  // dos caballetes
  for (const y of [-18, 18]) {
    out.push(S(k.slabOf({ x: -20, y: y - 8, w: 40, d: 16, r: 2 }, 0, 6, P, 4, 0.8), { tone: "mid" }));
    out.push(S(k.slabOf({ x: -10, y: y - 5, w: 20, d: 10, r: 2 }, 6, BUS_Z - 12, P, 4, 0.6), { tone: "mid" }));
    out.push(S(k.slabOf({ x: -16, y: y - 7, w: 32, d: 14, r: 3 }, BUS_Z - 6, 6, P, 5, 0.9), { tone: "mid" }));
    out.push(member([-18, y, 2], [0, y, BUS_Z - 12], 1.4));
    out.push(member([18, y, 2], [0, y, BUS_Z - 12], 1.4));
    out.push(D([[-8, y - 4, BUS_Z], [8, y - 4, BUS_Z], [-8, y + 4, BUS_Z], [8, y + 4, BUS_Z]].map(at), { size: 0.5, tone: "lo" }));
  }
  return out.join("");
}

// ---------- bus: módulos MLI a lo largo de Y ----------
function bus() {
  const out = [];
  const modules = [
    { x: -11, y: -32, w: 22, d: 18, z: 40, h: 33, r: 1.5 },
    { x: -10, y: -12, w: 20, d: 14, z: 44, h: 29, r: 1.5 },
    { x: -11, y: 3, w: 22, d: 15, z: 40, h: 33, r: 1.5 },
    { x: -9, y: 19, w: 18, d: 14, z: 46, h: 27, r: 1.5 },
    { x: -8, y: 32, w: 16, d: 4, z: 44, h: 23, r: 1.5 },
  ];
  for (const m of modules) {
    out.push(S(k.slabOf(m, m.z, m.h, P, 3, 1.1), { tone: "hi" }));
    out.push(LN([m.z + 5, m.z + m.h - 5].map((z) => k.sideSeam(m, z, P)).join(""), { tone: "lo" }));
  }
  // panel hexagonal (radiador) en la cara +X, con esferas, pernos y lamas
  const hex = [];
  for (let i = 0; i < 8; i++) {
    const a = (Math.PI / 4) * i + Math.PI / 8;
    hex.push([Math.cos(a) * 27, Math.sin(a) * 14]);
  }
  const F = L.frameAlong([PANEL_X, 0, 57], [1, 0, 0]);
  out.push(S(L.prismOf(F, hex, 0, 1.2, P), { tone: "mid" }));
  out.push(LN(L.arcOf(L.frameOf([PANEL_X + 1.2, 0, 57], [1, 0, 0], [0, 1, 0], [0, 0, 1]), 0, 27, P, { steps: 8 }), { tone: "lo" }));
  for (let i = 0; i < 8; i++) {
    const a = (Math.PI / 4) * i + Math.PI / 8;
    out.push(S(L.sphereOf([PANEL_X + 1.4, Math.cos(a) * 24.5, 57 + Math.sin(a) * 12], 1.4, P, { steps: 16 }), { tone: "mid" }));
  }
  const bolts = [];
  for (let i = 0; i < 8; i++) {
    const a = (Math.PI / 4) * i + Math.PI / 8;
    bolts.push(at([PANEL_X + 1.25, Math.cos(a) * 20, 57 + Math.sin(a) * 9.5]));
  }
  out.push(D(bolts, { size: 0.5, tone: "lo" }));
  const lv = [];
  for (let i = 0; i < 6; i++) lv.push(k.segment([PANEL_X + 1.25, -24, 47 + i * 4], [PANEL_X + 1.25, 24, 47 + i * 4], P));
  out.push(LN(lv.join(""), { tone: "lo" }));
  // cajitas y barral sobre el panel
  out.push(S(k.slabOf({ x: PANEL_X + 1.2, y: -6, w: 1.4, d: 8, r: 0.4 }, 62, 4, P, 2), { tone: "mid" }));
  out.push(S(k.slabOf({ x: PANEL_X + 1.2, y: 6, w: 1.4, d: 6, r: 0.4 }, 48, 3, P, 2), { tone: "mid" }));
  // toberas bajo el panel
  for (const [yy, zz, r] of [[-8, 44, 2.4], [-2, 42, 2], [4, 44, 2.4]]) {
    const N = L.frameAlong([PANEL_X + 1.6, yy, zz], [0.6, 0, -0.8]);
    out.push(S(L.lathe([[0, r * 0.6], [1.1, r * 0.85], [2.6, r], [3.8, r * 1.2], [4.2, r]], N, P, { steps: 26 }), { tone: "lo" }));
  }
  // placa de identificación en el módulo de cola
  out.push(S(k.slabOf({ x: -11.5, y: -34, w: 9, d: 0.9, r: 0.4 }, 58, 3.2, P, 2), { tone: "mid" }));
  out.push(LN([61, 63].map((z) => k.segment([-10.2, -34.05, z], [-4.2, -34.05, z], P)).join(""), { tone: "lo" }));
  return out.join("");
}

// ---------- instrumentos en la cara nadir (-Z) ----------
function barrel(cx, cy, profile, plate, lit = false) {
  const out = [];
  out.push(S(k.slabOf({ x: cx - plate / 2, y: cy - plate / 2, w: plate, d: plate, r: 1 }, BUS_Z - 1.4, 2, P, 3, 0.4), { tone: "mid" }));
  const F = L.frameAlong([cx, cy, BUS_Z - 1.4], [0, 0, -1]);
  out.push(S(L.lathe(profile, F, P, { steps: 36, smooth: "auto" }), { tone: "hi", lit }));
  return out.join("");
}

function instruments() {
  const out = [];
  out.push(barrel(-6, -22, [[0, 0], [0.6, 4], [1.8, 4.4], [5.6, 4.4], [6.2, 5], [7.2, 5], [7.6, 4.2], [7.6, 3.6]], 13));
  out.push(barrel(-4, -8, [[0, 0], [0.5, 2.3], [3.8, 2.4], [4.4, 2.9], [5.2, 2.9], [5.4, 2.1], [5.4, 0]], 8));
  for (const cy of [2, 8]) {
    out.push(barrel(-3, cy, [[0, 0], [0.4, 1.5], [2.8, 1.6], [3.2, 2], [3.6, 2], [3.6, 0]], 4.4));
    for (const d of [-1.2, 0, 1.2]) {
      const F = L.frameOf([-3 + d, cy, BUS_Z - 5], [0, 0, -1], [1, 0, 0], [0, 1, 0]);
      out.push(LN(L.arcOf(F, 0, 0.5, P, { steps: 12 }), { tone: "lo" }));
    }
  }
  // MISR: una carcasa con nueve cámaras
  out.push(barrel(3, -14, [[0, 0], [0.4, 3.2], [4.2, 3.3], [4.6, 3.7], [5, 3.7], [5, 0]], 16));
  for (const dx of [-2, 0, 2]) {
    for (const dz of [-2, 0, 2]) {
      const F = L.frameOf([3 + dx, -14 + dz, BUS_Z - 6.4], [0, 0, -1], [1, 0, 0], [0, 1, 0]);
      out.push(LN(L.arcOf(F, 0, 0.5, P, { steps: 12 }), { tone: "lo" }));
    }
  }
  out.push(barrel(3, 16, [[0, 0], [0.5, 2.6], [3.8, 2.7], [4.4, 3.2], [5, 3.2], [5.2, 2.4], [5.2, 0]], 8));
  return out.join("");
}

// ---------- boom de celosía + tambor (eje X, z bajo como el modelo) ----------
function boom() {
  const out = [];
  const x0 = BUS.x;
  const x1 = WING.x + WING.w;
  const zTop = BOOM_Z + 2.4;
  const zBot = BOOM_Z - 2.4;
  const ys = [-3.2, 3.2];
  for (const y of ys) {
    out.push(S(k.slabOf({ x: x1, y: y - 1, w: x0 - x1, d: 2, r: 0.4 }, zTop - 0.7, 1.4, P, 3), { tone: "mid" }));
    out.push(S(k.slabOf({ x: x1, y: y - 1, w: x0 - x1, d: 2, r: 0.4 }, zBot - 0.7, 1.4, P, 3), { tone: "mid" }));
  }
  const stations = [];
  for (let x = x0 - 8; x > x1; x -= 12) stations.push(x);
  for (const x of stations) {
    for (const y of ys) out.push(S(k.slabOf({ x: x - 0.6, y: y - 3.2, w: 1.2, d: 6.4, r: 0.2 }, zBot, zTop - zBot, P, 2), { tone: "mid" }));
  }
  for (let i = 0; i < stations.length - 1; i++) {
    const a = stations[i];
    const b = stations[i + 1];
    out.push(member([a, ys[0], zTop], [b, ys[0], zBot], 0.9));
    out.push(member([a, ys[1], zBot], [b, ys[1], zTop], 0.9));
  }
  // collar en la raíz y tambor en la punta
  out.push(S(L.lathe([[0, 0], [0.5, 5], [1.2, 5.8], [4, 5.8], [4.6, 5], [4.6, 0]], L.frameAlong([x0, 0, BOOM_Z], [-1, 0, 0]), P, { steps: 36 }), { tone: "mid" }));
  const drum = L.frameAlong([x1, 0, BOOM_Z], [-1, 0, 0]);
  out.push(S(L.lathe([[0, 0], [0.6, 6.4], [1.6, 7], [7, 7], [8, 6.4], [8, 4.2], [8, 0]], drum, P, { steps: 48, smooth: "auto" }), { tone: "mid" }));
  out.push(S(L.lathe([[0, 0], [0.4, 3], [1.2, 3], [1.2, 0]], L.frameAlong([x1 - 8, 0, BOOM_Z], [-1, 0, 0]), P, { steps: 28 }), { tone: "lit", lit: true }));
  return out.join("");
}

// ---------- ala solar ----------
function wing() {
  const out = [];
  out.push(S(k.slabOf(WING, WING_Z, 2, P, 4, 0.5), { tone: "mid" }));
  const y0 = WING.y;
  const y1 = WING.y + WING.d;
  out.push(S(k.slabOf({ x: WING.x - 1, y: y0 - 1, w: WING.w + 2, d: 3, r: 0.4 }, WING_Z + 2, 1.6, P, 3), { tone: "mid" }));
  out.push(S(k.slabOf({ x: WING.x - 1, y: y1 - 2, w: WING.w + 2, d: 3, r: 0.4 }, WING_Z + 2, 1.6, P, 3), { tone: "mid" }));
  const seams = [];
  for (let i = 1; i < 9; i++) {
    const x = WING.x + (WING.w / 9) * i;
    seams.push(k.lineOnTop([x, y0 + 2], [x, y1 - 2], WING_Z + 2, P));
  }
  out.push(LN(seams.join(""), { tone: "mid" }));
  const cells = [];
  // espina central de celosía
  for (let x = WING.x + 6; x < WING.x + WING.w - 4; x += 8) {
    cells.push(k.lineOnTop([x, -2.6], [x + 8, 2.6], WING_Z + 2.4, P));
    cells.push(k.lineOnTop([x, 2.6], [x + 8, -2.6], WING_Z + 2.4, P));
  }
  out.push(LN(cells.join(""), { tone: "mid" }));
  out.push(S(k.slabOf({ x: WING.x + WING.w - 3, y: -3.4, w: 3, d: 6.8, r: 0.8 }, WING_Z + 2, 2.6, P, 2), { tone: "mid" }));
  const cells2 = [];
  for (const f of [0.25, 0.75]) cells2.push(k.lineOnTop([WING.x + 2, y0 + WING.d * f], [WING.x + WING.w - 2, y0 + WING.d * f], WING_Z + 2, P));
  out.push(LN(cells2.join(""), { tone: "lo" }));
  for (let i = 0; i < 7; i++) {
    const x = WING.x + 8 + i * 12;
    out.push(S(k.slabOf({ x: x - 1.2, y: y0 - 1.6, w: 2.4, d: 1.6, r: 0.3 }, WING_Z + 2, 1.6, P, 2), { tone: "mid" }));
    out.push(D([at([x, y0 - 0.8, WING_Z + 3.6])], { size: 0.4, tone: "lo" }));
  }
  out.push(S(k.slabOf({ x: WING.x + WING.w, y: -6, w: 6, d: 12, r: 1 }, WING_Z, 3, P, 3), { tone: "mid" }));
  return out.join("");
}

// ---------- parabólica + monopolo ----------
function dish() {
  const out = [];
  out.push(S(k.cylinder(MAST[0], MAST[1], 1.3, BUS_TOP, DISH_Z - BUS_TOP - 2.4, P, 20), { tone: "mid" }));
  out.push(S(L.sphereOf([MAST[0], MAST[1], DISH_Z - 1.2], 2, P, { steps: 28 }), { tone: "mid" }));
  out.push(S(k.slabOf({ x: MAST[0] - 1.4, y: MAST[1] - 6, w: 2.8, d: 3, r: 0.5 }, DISH_Z + 2.2, 8, P, 3), { tone: "mid" }));
  out.push(S(k.slabOf({ x: MAST[0] - 1.4, y: MAST[1] + 3, w: 2.8, d: 3, r: 0.5 }, DISH_Z + 2.2, 8, P, 3), { tone: "mid" }));
  out.push(S(k.slabOf({ x: MAST[0] - 1.4, y: MAST[1] - 6, w: 2.8, d: 12, r: 0.5 }, DISH_Z + 10.2, 2.2, P, 3), { tone: "mid" }));
  const D0 = L.frameAlong([MAST[0], MAST[1], DISH_Z + 5.4], [0, 0, 1]);
  out.push(S(L.lathe([[0, 0], [0.9, 1.3], [2.1, 3.8, 1], [3.5, 6.2, 1], [4.7, 8.1, 1], [5.4, 9, 1]], D0, P, { steps: 64, smooth: "auto" }), { tone: "hi" }));
  for (const r of [3, 5.4, 7.4]) {
    out.push(LN(L.arcOf(L.frameOf([MAST[0], MAST[1], DISH_Z + 5.4 + (r === 3 ? 1 : r === 5.4 ? 1.7 : 2.5)], [0, 0, 1], [1, 0, 0], [0, 1, 0]), 0, r, P, { steps: 40 }), { tone: "lo" }));
  }
  out.push(S(k.cylinder(MAST[0], MAST[1], 1.2, DISH_Z + 14.4, 3.2, P, 16), { tone: "mid" }));
  out.push(member([MAST[0], MAST[1] + 8.4, DISH_Z + 9], [MAST[0], MAST[1], DISH_Z + 16], 0.7));
  for (const a of [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2]) {
    out.push(LN(k.segment([MAST[0], MAST[1], DISH_Z + 5.4], [MAST[0] + Math.cos(a) * 8.8, MAST[1] + Math.sin(a) * 8.8, DISH_Z + 5.4], P), { tone: "lo" }));
  }

  out.push(S(k.cylinder(3, 30, 0.55, BUS_TOP, 13, P, 12), { tone: "mid" }));
  out.push(S(L.sphereOf([3, 30, BUS_TOP + 13.4], 0.9, P, { steps: 18 }), { tone: "mid" }));
  return out.join("");
}

// ---------- escena con despiece ----------
const parts = [`<path class="iso-halo" d="${k.haloOf({ x: -20, y: -34, w: 46, d: 68, r: 4 }, BUS_Z - 2, 0.1, P)}" style="filter:blur(6px)"/>`];
function group(name, index, apart, content) {
  const [dx, dy] = k.axisVector(P, apart);
  parts.push(`<g class="part" data-part="${name}" style="--apart:translate(${dx}px, ${dy}px);--i:${index}">${content}</g>`);
}

group("bus", 1, [0, 0, 8], bus());
group("instruments", 2, [-6, -52, 4], instruments());
group("boom", 3, [-14, 0, 0], boom());
group("wing", 4, [-34, 0, 6], wing());
group("dish", 5, [0, 0, 14], dish());

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label: "Terra (EOS AM-1) sobre su caballete de integración, despiezado en cinco conjuntos",
  body: parts.join(""),
});

const live = `
const stage = document.querySelector('.iso-stage');
const btn = document.querySelector('.iso-apart');
const readout = document.querySelector('[data-readout]');
const set = (on) => {
  document.body.classList.toggle('is-apart', on);
  btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  readout.textContent = on ? 'despiezado · 5 conjuntos' : 'armado · 5 instrumentos';
};
btn.addEventListener('click', () => set(!document.body.classList.contains('is-apart')));
stage.addEventListener('keydown', (event) => {
  if (event.key === 'd' || event.key === 'D') { event.preventDefault(); set(!document.body.classList.contains('is-apart')); }
});
`;

const body = k.plateHtml({
  fig: "Fig 1",
  title: "Terra · EOS AM-1",
  hint: "Botón o tecla D para despiezar",
  readout: "armado · 5 instrumentos",
  keys: [
    { mark: "lit", label: "Tambor de accionamiento del ala" },
    { mark: "raised", label: "Bus de módulos MLI y panel hexagonal" },
  ],
  caption:
    "Terra, en la orientación del modelo de la NASA: bus de 6,8 m con módulos MLI, panel radiador hexagonal en la cara +X con las toberas, ala de 9 × 5 m sobre el mástil por −X y parabólica sobre el mástil cenital. Los cinco instrumentos van en la cara nadir, que el despiece deja a la vista.",
  body: `<div class="iso-stage" tabindex="0" role="group" aria-label="Terra: botón Despiezar o tecla D para separar los conjuntos">${svg}</div>`,
});

const tools =
  '<div class="iso-tools"><button class="iso-apart" type="button" aria-pressed="false">Despiezar</button>' +
  '<span class="iso-tools-note">Separa los cinco conjuntos para ver cómo se monta</span></div>';

const tokens =
  '`.iso[data-theme="light"]{--anatomy-page:#f2f2ef;--anatomy-card:#fbfbfa;--anatomy-text:#57575a;--anatomy-strong:#18181a;--anatomy-muted:#8c8c90;--anatomy-paper:#fbfbfa;--anatomy-face:#ffffff;--anatomy-top:#ffffff;--anatomy-shade-0:#c9cac6;--anatomy-shade-1:#d8d8d4;--anatomy-shade-2:#e6e6e1;--anatomy-shade-3:#f1f1ec;--anatomy-lit-top:#ffffff;--anatomy-lit-shade:#e9e9e4;--anatomy-hi:#1c1e21;--anatomy-mid:#54575b;--anatomy-lo:#8f9296;--anatomy-faint:#c2c4c6;--anatomy-lit:#000000;--anatomy-halo:#8a8a80;--anatomy-halo-opacity:.28;--anatomy-dot:#2c2e31}`';

const css = tokens + ` + \`
.iso-tools{display:flex;align-items:center;justify-content:flex-end;gap:12px;margin:0 0 10px}
.iso-tools-note{font:400 12px/1.4 ui-sans-serif,system-ui,sans-serif;color:var(--anatomy-muted)}
.iso-apart{font:600 12px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--anatomy-strong);background:transparent;border:1px solid var(--anatomy-lo);border-radius:999px;padding:9px 16px;cursor:pointer}
.iso-apart:hover{border-color:var(--anatomy-mid)}
.iso-apart:active{transform:scale(.96)}
.iso-apart[aria-pressed="true"]{background:var(--anatomy-face);border-color:var(--anatomy-hi)}
.iso-stage{outline:none}
.part{transform:translate(0,0);transition:transform .9s cubic-bezier(.23,1,.32,1) calc(var(--i)*45ms)}
body.is-apart .part{transform:var(--apart)}
@media (prefers-reduced-motion:reduce){.part{transition-duration:.01ms!important;transition-delay:0ms!important}}
\``;

const page = k
  .pageHtml({ title: "Terra · EOS AM-1", theme: "light", body: body + tools, script: kitScript() + live, width: 1000 })
  .replace("</style>", css + "</style>");

writeFileSync(join(HERE, "terra.html"), page);
console.log("escrito terra.html");
