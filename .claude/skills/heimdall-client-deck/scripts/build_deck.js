// Ragnar Races — Data Science Insights — Genomic Digital, September 2026
// Builds docs/ragnar_deck/Ragnar_Races_Data_Science_Insights_Sept2026.pptx from
// content.json (all copy + per-category insights) and charts/ (rendered PNGs).
// Form: the Fluid client-deliverable grammar (objective → methodology → segment →
// correlation categories as Big Data Analysis / Key Insight pairs → persona → path forward),
// in the Genomic Digital brand (black / off-white, condensed uppercase, single amber accent).
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const DECK = process.argv[2] || __dirname;
const C = JSON.parse(fs.readFileSync(path.join(DECK, "content.json"), "utf8"));
const IMG = (n) => path.join(DECK, "img", n);
const CH = (n) => path.join(DECK, "charts", n);

const INK = "111111", PAPER = "F4F3F0", WHITE = "FFFFFF", MUTE = "7A7A7A", AMBER = "E0A100", LINE = "D9D7D2", DARK = "1B1B1B";
const HEAD = "Arial Narrow", BODY = "Calibri";   // Arial Narrow = the condensed uppercase look; Calibri = safe body

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.333 x 7.5
pres.author = "Genomic Digital"; pres.company = "Genomic Digital"; pres.title = C.title;
const W = 13.333, H = 7.5;

let n = 0;
function chrome(s, dark = false) {
  n += 1;
  s.addText("GENOMIC DIGITAL", { x: 0.5, y: 0.28, w: 3, h: 0.3, fontFace: HEAD, fontSize: 11, bold: true, charSpacing: 4,
    color: dark ? WHITE : INK, margin: 0, isTextBox: true });
  s.addText("genomicdigital.com", { x: W - 3.5, y: 0.28, w: 2.5, h: 0.3, fontFace: BODY, fontSize: 9, color: dark ? "AAAAAA" : MUTE,
    align: "right", margin: 0, isTextBox: true });
  s.addText(String(n), { x: W - 0.9, y: 0.28, w: 0.4, h: 0.3, fontFace: BODY, fontSize: 9, color: dark ? "AAAAAA" : MUTE, align: "right", margin: 0, isTextBox: true });
}
function bg(s, color) { s.background = { color }; }
function cover(imgName, kicker, title, sub, foot) {
  const s = pres.addSlide(); bg(s, DARK);
  s.addImage({ path: IMG(imgName), x: 0, y: 0, w: W, h: H, sizing: { type: "cover", w: W, h: H }, transparency: 35 });
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: "000000", transparency: 45 }, line: { color: "000000", transparency: 100 } });
  s.addText("GENOMIC DIGITAL", { x: 0.7, y: 0.6, w: 6, h: 0.4, fontFace: HEAD, fontSize: 14, bold: true, charSpacing: 6, color: WHITE, margin: 0, isTextBox: true });
  if (kicker) s.addText(kicker, { x: 0.7, y: 2.55, w: 9, h: 0.45, fontFace: BODY, fontSize: 16, color: AMBER, bold: true, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText(title, { x: 0.7, y: 3.0, w: 10.5, h: 1.6, fontFace: HEAD, fontSize: 60, bold: true, color: WHITE, margin: 0, isTextBox: true, valign: "top" });
  if (sub) s.addText(sub, { x: 0.7, y: 4.65, w: 9, h: 0.9, fontFace: BODY, fontSize: 20, color: "E6E6E6", margin: 0, isTextBox: true, valign: "top" });
  if (foot) s.addText(foot, { x: 0.7, y: H - 1.0, w: 9, h: 0.4, fontFace: BODY, fontSize: 11, color: "BBBBBB", margin: 0, isTextBox: true });
  n += 1;
  return s;
}
function section(imgName, num, title, blurb) {
  const s = pres.addSlide(); bg(s, DARK);
  s.addImage({ path: IMG(imgName), x: 6.4, y: 0, w: W - 6.4, h: H, sizing: { type: "cover", w: W - 6.4, h: H } });
  chrome(s, true);
  s.addText(num, { x: 0.7, y: 2.2, w: 3, h: 0.6, fontFace: HEAD, fontSize: 22, color: AMBER, bold: true, charSpacing: 3, margin: 0, isTextBox: true });
  s.addText(title, { x: 0.7, y: 2.8, w: 5.4, h: 1.9, fontFace: HEAD, fontSize: 48, bold: true, color: WHITE, margin: 0, isTextBox: true, valign: "top" });
  s.addText(blurb, { x: 0.7, y: 4.8, w: 5.2, h: 1.6, fontFace: BODY, fontSize: 14, color: "CFCFCF", margin: 0, isTextBox: true, valign: "top" });
  return s;
}
function kickerTitle(s, kicker, title, x = 0.7, y = 0.95, w = 5.2, size = 34) {
  s.addText(kicker, { x, y, w, h: 0.35, fontFace: BODY, fontSize: 13, color: MUTE, margin: 0, isTextBox: true });
  s.addText(title, { x, y: y + 0.38, w, h: 1.5, fontFace: HEAD, fontSize: size, bold: true, color: INK, margin: 0, isTextBox: true, valign: "top" });
}
function para(s, text, x, y, w, h, size = 13, color = "333333") {
  s.addText(text, { x, y, w, h, fontFace: BODY, fontSize: size, color, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 6 });
}
function bullets(s, items, x, y, w, h, size = 12.5) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 12 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })),
    { x, y, w, h, fontFace: BODY, fontSize: size, color: "333333", margin: 0, isTextBox: true, valign: "top" });
}
function stat(s, x, y, w, big, label) {
  s.addText(big, { x, y, w, h: 0.9, fontFace: HEAD, fontSize: 44, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText(label, { x, y: y + 0.9, w, h: 0.7, fontFace: BODY, fontSize: 11.5, color: MUTE, margin: 0, isTextBox: true, valign: "top" });
}
function rule(s, x, y, w) { s.addShape(pres.ShapeType.line, { x, y, w, h: 0, line: { color: LINE, width: 0.75 } }); }

// ───────────────────────────── 1 · cover
cover("cover.png", "DATA SCIENCE INSIGHTS  ·  SEPTEMBER 2026", C.title, C.subtitle, C.prepared);

// ───────────────────────────── 2 · objective
{
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  s.addImage({ path: IMG("van.png"), x: 7.6, y: 0, w: W - 7.6, h: H, sizing: { type: "cover", w: W - 7.6, h: H } });
  kickerTitle(s, "THE ENGAGEMENT", "PROJECT\nOBJECTIVE", 0.7, 0.95, 6.2, 40);
  para(s, C.objective, 0.7, 3.0, 6.3, 3.8, 13.5);
}
// ───────────────────────────── 3 · agenda
{
  const s = pres.addSlide(); bg(s, PAPER); chrome(s);
  kickerTitle(s, "WHAT IS IN THIS DOCUMENT", "CONTENTS", 0.7, 0.95, 5, 40);
  let y = 1.15;
  C.agenda.forEach(([t, d], i) => {
    s.addText(String(i + 1).padStart(2, "0"), { x: 6.2, y, w: 0.7, h: 0.5, fontFace: HEAD, fontSize: 22, bold: true, color: AMBER, margin: 0, isTextBox: true });
    s.addText(t, { x: 7.0, y, w: 5.6, h: 0.45, fontFace: HEAD, fontSize: 20, bold: true, color: INK, margin: 0, isTextBox: true });
    s.addText(d, { x: 7.0, y: y + 0.45, w: 5.6, h: 0.5, fontFace: BODY, fontSize: 11.5, color: MUTE, margin: 0, isTextBox: true, valign: "top" });
    y += 1.02;
  });
}
// ───────────────────────────── 4 · methodology (4 steps)
{
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  kickerTitle(s, "HOW HEIMDALL WORKS", "METHODOLOGY", 0.7, 0.95, 6, 40);
  const cols = C.method_steps; const cw = (W - 1.4 - 0.3 * 3) / 4;
  cols.forEach((c, i) => {
    const x = 0.7 + i * (cw + 0.3);
    s.addText(`STEP ${i + 1}`, { x, y: 2.75, w: cw, h: 0.3, fontFace: BODY, fontSize: 10.5, color: AMBER, bold: true, charSpacing: 2, margin: 0, isTextBox: true });
    s.addText(c[0], { x, y: 3.05, w: cw, h: 0.85, fontFace: HEAD, fontSize: 22, bold: true, color: INK, margin: 0, isTextBox: true, valign: "top" });
    rule(s, x, 3.98, cw);
    para(s, c[1], x, 4.1, cw, 2.7, 11.5, "444444");
  });
}
// ───────────────────────────── 5 · the corpus in numbers
{
  const s = pres.addSlide(); bg(s, DARK); chrome(s, true);
  s.addText("STEP 3", { x: 0.7, y: 0.95, w: 3, h: 0.3, fontFace: BODY, fontSize: 12, color: AMBER, bold: true, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText("RUN BILLIONS\nOF CORRELATIONS", { x: 0.7, y: 1.3, w: 6, h: 1.7, fontFace: HEAD, fontSize: 40, bold: true, color: WHITE, margin: 0, isTextBox: true, valign: "top" });
  para(s, C.corpus_blurb, 0.7, 3.15, 5.4, 2.5, 13, "D0D0D0");
  const stats = C.corpus_stats; const sw = 2.9;
  stats.forEach((st, i) => {
    const x = 6.7 + (i % 2) * (sw + 0.35), y = 1.25 + Math.floor(i / 2) * 2.05;
    s.addText(st[0], { x, y, w: sw, h: 0.9, fontFace: HEAD, fontSize: 40, bold: true, color: AMBER, margin: 0, isTextBox: true });
    s.addText(st[1], { x, y: y + 0.9, w: sw, h: 0.9, fontFace: BODY, fontSize: 11.5, color: "C9C9C9", margin: 0, isTextBox: true, valign: "top" });
  });
}
// ───────────────────────────── 6 · one word, four populations
{
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  kickerTitle(s, "STEP 1 — WHY THE SEGMENT DEFINITION MATTERS", "ONE WORD,\nFOUR POPULATIONS", 0.7, 0.95, 5.3, 34);
  para(s, C.senses_blurb, 0.7, 3.05, 5.1, 3.9, 12.5);
  const rows = [[{ text: "SENSE", options: { bold: true, color: MUTE } }, { text: "EXAMPLE SEARCH", options: { bold: true, color: MUTE } }, { text: "US SEARCHES / MO", options: { bold: true, color: MUTE, align: "right" } }]]
    .concat(C.senses.map(r => [r[0], r[1], { text: r[2], options: { align: "right" } }]));
  s.addTable(rows, { x: 6.5, y: 1.1, w: 6.2, colW: [1.9, 2.7, 1.6], fontFace: BODY, fontSize: 11.5, color: INK, border: { type: "solid", color: LINE, pt: 0.5 }, fill: { color: WHITE }, rowH: 0.42, margin: 0.06 });
  para(s, C.senses_note, 6.5, 4.85, 6.2, 2.0, 11.5, "444444");
}
// ───────────────────────────── 7 · disambiguation measured (only when the client has a sense collision)
if (fs.existsSync(CH("disambiguation.png"))) {
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  kickerTitle(s, "Big Data Analysis", "THE FIX,\nMEASURED", 0.7, 0.95, 3.6, 34);
  para(s, C.disamb_blurb, 0.7, 3.0, 3.5, 4, 11.5);
  s.addImage({ path: CH("disambiguation.png"), x: 4.5, y: 1.0, w: 8.3, h: 5.19 });
}
// ───────────────────────────── 8 · strengths / limitations
{
  const s = pres.addSlide(); bg(s, PAPER); chrome(s);
  s.addText("STRENGTHS", { x: 0.7, y: 1.0, w: 5.6, h: 0.7, fontFace: HEAD, fontSize: 34, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("LIMITATIONS", { x: 7.0, y: 1.0, w: 5.6, h: 0.7, fontFace: HEAD, fontSize: 34, bold: true, color: INK, margin: 0, isTextBox: true });
  let y = 1.95;
  C.strengths.forEach(([t, d]) => {
    s.addText(t, { x: 0.7, y, w: 5.6, h: 0.35, fontFace: BODY, fontSize: 13, bold: true, color: AMBER, margin: 0, isTextBox: true });
    para(s, d, 0.7, y + 0.36, 5.6, 1.1, 11.5, "444444"); y += 1.55;
  });
  y = 1.95;
  C.limitations.forEach(([t, d]) => {
    s.addText(t, { x: 7.0, y, w: 5.6, h: 0.35, fontFace: BODY, fontSize: 13, bold: true, color: "8A1C1C", margin: 0, isTextBox: true });
    para(s, d, 7.0, y + 0.36, 5.6, 1.1, 11.5, "444444"); y += 1.55;
  });
}
// ───────────────────────────── 9 · section: the segment
section("night_road.png", "01", "THE RAGNAR\nRELAY SEGMENT", C.segment_section_blurb);
// ───────────────────────────── 10 · segment definition
{
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  kickerTitle(s, "Ragnar relay participant", "SEGMENT\nDEFINITION", 0.7, 0.95, 4.6, 40);
  para(s, C.segment_def_blurb, 0.7, 3.1, 4.5, 3.8, 12);
  s.addShape(pres.ShapeType.rect, { x: 5.7, y: 1.0, w: 7.0, h: 5.4, fill: { color: "1B1B1B" }, line: { color: "1B1B1B" } });
  s.addText(C.segment_formula.map((l, i) => ({ text: l.text, options: { color: l.neg ? AMBER : (l.dim ? "8C8C8C" : "F0F0F0"), breakLine: i < C.segment_formula.length - 1 } })),
    { x: 6.0, y: 1.2, w: 6.5, h: 5.0, fontFace: "Courier New", fontSize: 12.5, margin: 0, isTextBox: true, valign: "top", paraSpaceAfter: 2 });
}
// ───────────────────────────── 11 · categories
{
  const s = pres.addSlide(); bg(s, PAPER); chrome(s);
  kickerTitle(s, "Ragnar relay participant", `${C.categories.length} CORRELATION\nCATEGORIES`, 0.7, 0.95, 4.6, 40);
  para(s, C.categories_blurb, 0.7, 3.4, 4.4, 3.2, 12);
  C.categories.forEach((c, i) => {
    const col = Math.floor(i / 7), x = 5.9 + col * 3.6, y = 1.15 + (i % 7) * 0.8;
    s.addText(String(i + 1), { x, y, w: 0.6, h: 0.6, fontFace: HEAD, fontSize: 26, bold: true, color: AMBER, margin: 0, isTextBox: true });
    s.addText(c.toUpperCase(), { x: x + 0.65, y: y + 0.06, w: 2.9, h: 0.5, fontFace: HEAD, fontSize: 19, bold: true, color: INK, margin: 0, isTextBox: true });
  });
}
// ───────────────────────────── 12+ · geography pair
{
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  kickerTitle(s, "Big Data Analysis", "GEOGRAPHIC\nFOOTPRINT", 0.7, 0.95, 3.4, 34);
  para(s, C.geo_blurb, 0.7, 3.0, 3.3, 4, 11.5);
  s.addImage({ path: CH("geography.png"), x: 4.3, y: 1.05, w: 8.5, h: 4.6 });
}
{
  const s = pres.addSlide(); bg(s, PAPER); chrome(s);
  s.addImage({ path: IMG("trail.png"), x: 7.9, y: 0, w: W - 7.9, h: H, sizing: { type: "cover", w: W - 7.9, h: H } });
  kickerTitle(s, "Key Insight", C.geo_insight_title, 0.7, 0.95, 6.6, 34);
  para(s, C.geo_insight, 0.7, 3.0, 6.6, 4, 12.5);
}
// ───────────────────────────── category pairs
for (const cat of C.category_pages) {
  const f = CH(cat.chart);
  if (!fs.existsSync(f)) { console.log("no chart for", cat.name); continue; }
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  kickerTitle(s, "Big Data Analysis", cat.name.toUpperCase().replace(" & ", " &\n").replace(" AND ", " &\n"), 0.7, 0.95, 3.4, 34);
  para(s, cat.chart_note, 0.7, 3.2, 3.3, 3.8, 11, "555555");
  s.addImage({ path: f, x: 4.3, y: 0.95, w: 8.5, h: 5.3 });
  const k = pres.addSlide(); bg(k, PAPER); chrome(k);
  kickerTitle(k, "Key Insight", cat.insight_title, 0.7, 0.95, 6.4, 34);
  para(k, cat.insight, 0.7, 3.1, 6.4, 3.9, 12.5);
  // named-entity callouts on the right: top 5 with values
  const top = (cat.callouts || []).slice(0, 6);
  let y = 1.15;
  k.addText(cat.callout_label || "STRONGEST SIGNALS", { x: 7.8, y: 0.85, w: 4.8, h: 0.3, fontFace: BODY, fontSize: 10.5, color: MUTE, charSpacing: 2, margin: 0, isTextBox: true });
  top.forEach(([label, val]) => {
    k.addText(label, { x: 7.8, y, w: 3.6, h: 0.45, fontFace: HEAD, fontSize: 20, bold: true, color: INK, margin: 0, isTextBox: true });
    k.addText(val, { x: 11.4, y, w: 1.3, h: 0.45, fontFace: BODY, fontSize: 13, color: val.startsWith("-") ? "8A1C1C" : AMBER, bold: true, align: "right", margin: 0, isTextBox: true });
    rule(k, 7.8, y + 0.48, 4.9); y += 0.6;
  });
  if (cat.negatives && cat.negatives.length) {
    y += 0.15;
    k.addText("NOT THIS AUDIENCE", { x: 7.8, y, w: 4.8, h: 0.3, fontFace: BODY, fontSize: 10.5, color: MUTE, charSpacing: 2, margin: 0, isTextBox: true }); y += 0.34;
    cat.negatives.slice(0, 3).forEach(([label, val]) => {
      k.addText(label, { x: 7.8, y, w: 3.6, h: 0.36, fontFace: HEAD, fontSize: 16, bold: true, color: "555555", margin: 0, isTextBox: true });
      k.addText(val, { x: 11.4, y, w: 1.3, h: 0.36, fontFace: BODY, fontSize: 12, color: "8A1C1C", bold: true, align: "right", margin: 0, isTextBox: true });
      y += 0.44;
    });
  }
}
// ───────────────────────────── personas
section("finish.png", "02", "WHO WE ARE\nTALKING TO", C.persona_section_blurb);
for (const p of C.personas) {
  const s = pres.addSlide(); bg(s, WHITE); chrome(s);
  s.addImage({ path: IMG(p.img), x: 0, y: 0, w: 5.0, h: H, sizing: { type: "cover", w: 5.0, h: H } });
  s.addText(p.kicker, { x: 5.6, y: 1.0, w: 7, h: 0.35, fontFace: BODY, fontSize: 13, color: MUTE, margin: 0, isTextBox: true });
  s.addText(p.name, { x: 5.6, y: 1.35, w: 7, h: 0.9, fontFace: HEAD, fontSize: 42, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText(p.tag, { x: 5.6, y: 2.25, w: 7, h: 0.5, fontFace: BODY, fontSize: 14, italic: true, color: AMBER, margin: 0, isTextBox: true });
  bullets(s, p.points, 5.6, 2.95, 7.0, 3.6, 12);
  s.addText(p.caveat, { x: 5.6, y: 6.6, w: 7, h: 0.5, fontFace: BODY, fontSize: 9.5, color: MUTE, margin: 0, isTextBox: true, valign: "top" });
}
// ───────────────────────────── path forward
section("trail.png", "03", "PATH\nFORWARD", C.path_section_blurb);
for (const pg of C.strategy_pages) {
  const s = pres.addSlide(); bg(s, pg.dark ? DARK : WHITE); chrome(s, !!pg.dark);
  const ink = pg.dark ? WHITE : INK, body = pg.dark ? "D6D6D6" : "333333";
  s.addText(pg.kicker, { x: 0.7, y: 0.95, w: 5, h: 0.35, fontFace: BODY, fontSize: 13, color: pg.dark ? "AAAAAA" : MUTE, margin: 0, isTextBox: true });
  s.addText(pg.title, { x: 0.7, y: 1.33, w: 5.2, h: 1.6, fontFace: HEAD, fontSize: 36, bold: true, color: ink, margin: 0, isTextBox: true, valign: "top" });
  para(s, pg.lead, 0.7, 3.1, 4.9, 3.7, 12.5, body);
  const many = pg.cards.length > 4;
  const cols = many ? 3 : 2, cw = many ? 2.15 : 3.2, ch = many ? 2.55 : 2.5, gap = many ? 0.2 : 0.3, x0 = many ? 5.75 : 6.1;
  pg.cards.forEach((c, i) => {
    const cx = x0 + (i % cols) * (cw + gap), cy = 1.1 + Math.floor(i / cols) * (ch + 0.25);
    s.addShape(pres.ShapeType.rect, { x: cx, y: cy, w: cw, h: ch, fill: { color: pg.dark ? "2A2A2A" : PAPER }, line: { color: pg.dark ? "2A2A2A" : PAPER } });
    s.addText(c[0], { x: cx + 0.22, y: cy + 0.18, w: cw - 0.44, h: many ? 0.75 : 0.6, fontFace: HEAD, fontSize: many ? 16 : 18, bold: true, color: ink, margin: 0, isTextBox: true, valign: "top" });
    para(s, c[1], cx + 0.22, cy + (many ? 0.95 : 0.85), cw - 0.44, ch - 1.1, many ? 10 : 10.5, body);
  });
}
// ───────────────────────────── appendix + close
{
  const s = pres.addSlide(); bg(s, PAPER); chrome(s);
  kickerTitle(s, "Appendix", "HOW TO READ\nTHE CHARTS", 0.7, 0.95, 5, 36);
  bullets(s, C.appendix_reading, 0.7, 3.1, 5.4, 3.8, 11.5);
  s.addText("PROVENANCE", { x: 6.8, y: 1.05, w: 6, h: 0.3, fontFace: BODY, fontSize: 10.5, color: MUTE, charSpacing: 2, margin: 0, isTextBox: true });
  bullets(s, C.appendix_provenance, 6.8, 1.45, 5.9, 5.4, 10.5);
}
cover("night_road.png", null, "THANK YOU.", C.closing, "Genomic Digital  ·  Ben Fife, Founder  ·  genomicdigital.com");

const out = path.join(DECK, C.filename);
pres.writeFile({ fileName: out }).then(() => console.log("wrote", out, "slides:", n));
