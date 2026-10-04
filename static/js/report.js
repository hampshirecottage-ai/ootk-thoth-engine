// sourceId: the element holding the text, selected for a manual copy if the browser refuses.
function copyText(text, btn, sourceId) {
    ootkCopyButton(btn, text, sourceId && document.getElementById(sourceId));
}

function openSection(id) {
    const el = document.getElementById(id);
    if (el) el.open = true;
}
if (location.hash) openSection(location.hash.slice(1));

// ---- Aspect filters: one state applied to every drawn line and every table row ----
const filterState = { strongOnly: false, types: new Set() };
document.querySelectorAll(".filters [data-type]").forEach(b => filterState.types.add(b.dataset.type));
const allTypes = new Set(filterState.types);

function applyFilters() {
    let shown = 0, total = 0;
    const perSeg = {};
    document.querySelectorAll("[data-aspect-type]").forEach(el => {
        const ok = filterState.types.has(el.dataset.aspectType) && (!filterState.strongOnly || el.dataset.strong === "1");
        el.classList.toggle("is-hidden", !ok);
        if (el.classList.contains("aspect-row")) {
            total++; if (ok) shown++;
            const seg = el.closest("details.section").id;
            perSeg[seg] = (perSeg[seg] || 0) + (ok ? 1 : 0);
        }
    });
    document.querySelectorAll("[data-count-for]").forEach(el => { el.textContent = perSeg[el.dataset.countFor] || 0; });
    const fc = document.getElementById("filterCount");
    if (fc) fc.textContent = `Showing ${shown} of ${total}`;
    // A report with no aspects has no filter chips; saving there would store an empty
    // filter and hide every line in the next report.
    if (allTypes.size) try { localStorage.setItem("ootk.aspectFilter", JSON.stringify({ strongOnly: filterState.strongOnly, types: [...filterState.types] })); } catch (e) {}
}

function syncChips() {
    document.querySelectorAll(".filters [data-strength]").forEach(b =>
        b.setAttribute("aria-pressed", String((b.dataset.strength === "strong") === filterState.strongOnly)));
    document.querySelectorAll(".filters [data-type]").forEach(b =>
        b.setAttribute("aria-pressed", String(filterState.types.has(b.dataset.type))));
}

document.querySelectorAll(".filters [data-strength]").forEach(b => b.addEventListener("click", () => {
    filterState.strongOnly = b.dataset.strength === "strong";
    syncChips(); applyFilters();
}));
document.querySelectorAll(".filters [data-type]").forEach(b => b.addEventListener("click", ev => {
    const t = b.dataset.type;
    if (ev.altKey || ev.metaKey || ev.shiftKey) {
        // Modifier-click shows only this type.
        filterState.types = new Set([t]);
    } else if (filterState.types.has(t)) {
        filterState.types.delete(t);
    } else {
        filterState.types.add(t);
    }
    syncChips(); applyFilters();
}));
const reset = document.getElementById("filterReset");
if (reset) reset.addEventListener("click", () => { filterState.types = new Set(allTypes); filterState.strongOnly = false; syncChips(); applyFilters(); });

try {
    const saved = JSON.parse(localStorage.getItem("ootk.aspectFilter") || "null");
    const types = saved ? saved.types.filter(t => allTypes.has(t)) : [];
    // An empty saved filter (left by older versions after a report with no aspects) means show all.
    if (types.length) { filterState.strongOnly = !!saved.strongOnly; filterState.types = new Set(types); }
} catch (e) {}
if (document.getElementById("filters")) { syncChips(); applyFilters(); }

// ---- Operation drawings: hover lights a card's links, a tap opens the link inspector ----
const esc = v => String(v).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
const LINKS = {};
document.querySelectorAll('script[id^="links-"]').forEach(s => {
    try { LINKS[s.id.slice(6)] = JSON.parse(s.textContent); } catch (e) {}
});
const selectedIn = {};   // segment id -> selected card index (segment-local)

// Light the lines (aspects or element pairs, whichever is drawn) touching card i, and fade
// the cards it has no link to.
function lightUp(svg, i) {
    i = String(i);
    svg.classList.add("focus");
    const pairs = svg.classList.contains("mode-pairs");
    const linked = new Set([i]);
    svg.querySelectorAll(pairs ? ".pair-link, .pair-badge" : ".aspect-line").forEach(l => {
        const on = l.dataset.a === i || l.dataset.b === i;
        l.classList.toggle("lit", on);
        if (on && !l.classList.contains("is-hidden")) { linked.add(l.dataset.a); linked.add(l.dataset.b); }
    });
    svg.querySelectorAll(".card-slot").forEach(s => s.classList.toggle("unlinked", !linked.has(s.dataset.idx)));
}
function unlight(svg) {
    svg.classList.remove("focus");
    svg.querySelectorAll(".unlinked").forEach(s => s.classList.remove("unlinked"));
}
function restore(svg) {
    const sel = selectedIn[svg.dataset.seg];
    if (sel === undefined) unlight(svg); else lightUp(svg, sel);
}

const signedText = n => (n > 0 ? "+" : "") + n;
const scoreChip = (n, text) => `<span class="score ${n > 0 ? "pos" : n < 0 ? "neg" : ""}">${esc(text || signedText(n))}</span>`;

function inspect(seg, i) {
    const data = LINKS[seg], box = document.getElementById(`inspect-${seg}`);
    if (!data || !box) return;
    const svg = document.querySelector(`svg[data-seg="${seg}"]`);
    selectedIn[seg] = i;
    if (svg) {
        svg.querySelectorAll(".card-slot").forEach(s => s.classList.toggle("selected", s.dataset.idx === String(i)));
        lightUp(svg, i);
    }
    const c = data.cards[i];
    const who = j => {
        const o = data.cards[j];
        return `<button type="button" data-pick="${j}">${esc(o.title)}</button> <span class="why">(${esc(o.where)}, <i class="dot" style="background:${o.color}"></i>${esc(o.element)})</span>`;
    };
    const other = l => (l.a === i ? l.b : l.a);
    const pairs = data.pairs.filter(p => p.a === i || p.b === i);
    const aspects = data.aspects.filter(a => a.a === i || a.b === i);
    const img = c.image
        ? `<img src="${esc(c.image)}" alt="${esc(c.title)}" style="border-color:${c.color}" decoding="async">`
        : `<div class="noimg" style="border-color:${c.color}">${esc(c.title)}</div>`;
    let html = `<div class="li-head">${img}<div>
        <div class="li-pos">${esc(c.position_name)}</div>
        <div class="li-title">${esc(c.title)}</div>
        ${c.art ? `<div class="li-pos">${esc(c.art)}</div>` : ""}
        <div><i class="dot" style="background:${c.color}"></i>${esc(c.element)}${c.attribution ? " · " + esc(c.attribution) : ""}</div>
        <div class="li-pos">${pairs.length} element pair${pairs.length === 1 ? "" : "s"}${data.aspects.length ? ` · ${aspects.length} aspect link${aspects.length === 1 ? "" : "s"}` : ""}</div>
        </div></div>`;
    if (pairs.length) {
        html += `<h4>Element pairs (its neighbours)</h4><ul>` + pairs.map(p =>
            `<li>${scoreChip(p.score)} with ${who(other(p))}<br><span class="why">${esc(p.why)}</span></li>`).join("") + `</ul>`;
    }
    if (aspects.length) {
        html += `<h4>Aspects</h4><ul>` + aspects.map(a =>
            `<li><i class="dot" style="background:${a.color}"></i><strong>${esc(a.type)}</strong> ${scoreChip(a.score, a.score_text)} with ${who(other(a))}` +
            `<br><span class="why">${esc(a.apart)}${a.cards ? ". Cards: " + esc(a.cards) : ""}</span></li>`).join("") + `</ul>`;
    }
    const n = data.cards.length;
    html += `<div class="more"><button class="chip" type="button" data-pick="${(i + n - 1) % n}" aria-label="Previous card">‹ Prev</button> <button class="chip" type="button" data-pick="${(i + 1) % n}" aria-label="Next card">Next ›</button> <button class="chip" type="button" data-more="${c.gindex}">All card details</button> <button class="chip" type="button" data-clear="${seg}">Clear</button></div>`;
    box.innerHTML = html;
}
function clearInspect(seg) {
    delete selectedIn[seg];
    const svg = document.querySelector(`svg[data-seg="${seg}"]`);
    if (svg) { svg.querySelectorAll(".card-slot.selected").forEach(s => s.classList.remove("selected")); unlight(svg); }
    const box = document.getElementById(`inspect-${seg}`);
    if (box && box.dataset.intro) box.innerHTML = box.dataset.intro;
}
document.querySelectorAll(".link-inspector").forEach(box => { box.dataset.intro = box.innerHTML; });

const hoverable = matchMedia("(hover: hover)").matches;
document.querySelectorAll("svg[data-seg]").forEach(svg => {
    svg.querySelectorAll(".card-slot").forEach(slot => {
        slot.addEventListener("mouseenter", () => { if (hoverable) lightUp(svg, slot.dataset.idx); });
        slot.addEventListener("mouseleave", () => { if (hoverable) restore(svg); });
    });
});

// Aspect lines or element pairs, per drawing.
document.querySelectorAll("[data-link-mode]").forEach(b => b.addEventListener("click", () => {
    const seg = b.dataset.for, svg = document.querySelector(`svg[data-seg="${seg}"]`);
    svg.classList.toggle("mode-pairs", b.dataset.linkMode === "pairs");
    document.querySelectorAll(`[data-link-mode][data-for="${seg}"]`).forEach(o => o.setAttribute("aria-pressed", String(o === b)));
    restore(svg);
}));

// ---- Theme ----
document.getElementById("themeToggle").addEventListener("click", () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
    try { localStorage.setItem("ootk.theme", root.dataset.theme); } catch (e) {}
});

// ---- Card detail panel ----
const CARDS = JSON.parse(document.getElementById("cardDetails").textContent);
const panel = document.getElementById("detailPanel");

// Small maps of where the card sits (static/js/atlas.js); /maps has the full-size ones.
function maps(c) {
    const a = c.atlas, A = window.Atlas;
    if (!a || !A) return "";
    const fig = (title, svg, note) => `<figure>${svg}<figcaption><b>${title}</b>${esc(note || "Not placed in this system.")}</figcaption></figure>`;
    const solid = a.solid ? `${a.solid.name}: ${a.solid.faces} faces, ${a.solid.vertices} vertices, ${a.solid.edges} edges.` : "";
    const system = ["thoth", "golden_dawn", "french_egyptian"].find(k => k === panel.dataset.system) || "thoth";
    const href = `/maps?card=${encodeURIComponent(a.title)}&system=${system}`;
    return `<h3>Where it sits</h3><div class="maps-mini">` +
        fig("Tree of Life", A.tree(a, null, { compact: true }), a.tree.note) +
        fig("Cube of Space", A.cube(a, null, { compact: true }), a.cube.note) +
        fig("Zodiac and decans", A.ring(a, null, { compact: true }), a.zodiac.note) +
        fig("Platonic solid", A.solid(a, null, { compact: true }), solid) +
        `</div><p style="margin:0 0 12px;font-size:0.85em"><a href="${esc(href)}">Open the card maps</a></p>`;
}

function openCard(i) {
    const c = CARDS[Number.parseInt(i, 10)];
    if (!c) return;
    document.getElementById("dPos").textContent = `Position ${c.number} · ${c.position}`;
    document.getElementById("dTitle").textContent = c.title;
    const img = c.image
        ? `<img src="${esc(c.image)}" alt="${esc(c.title)}" decoding="async" style="border-color:${esc(c.color)}">`
        : `<div class="noimg" style="border-color:${esc(c.color)}">${esc(c.title)}</div>`;
    const fields = [["Element", c.element], ["Dignified", c.dignified ? "yes" : "no (neighbouring dignities sum below zero)"], ...c.fields]
        .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
    const list = (title, items) => items.length
        ? `<h3>${title} (${items.length})</h3><ul>${items.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : "";
    const art = c.art ? `<p class="art-note">${esc(c.art)}</p>` : "";
    document.getElementById("dBody").innerHTML = img + art + `<dl>${fields}</dl>` + maps(c) + list("Aspects", c.aspects) + list("Elemental dignities", c.dignities);
    document.querySelectorAll("[data-card]").forEach(el => el.classList.toggle("selected", el.dataset.card === String(i)));
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
}
function closeCard() {
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    document.querySelectorAll("[data-card].selected").forEach(el => { if (!el.matches(".card-slot")) el.classList.remove("selected"); });
}
document.addEventListener("click", e => {
    const pick = e.target.closest("[data-pick]"), more = e.target.closest("[data-more]"), clear = e.target.closest("[data-clear]");
    if (pick) { inspect(pick.closest(".link-inspector").dataset.seg, Number(pick.dataset.pick)); return; }
    if (more) { openCard(Number(more.dataset.more)); return; }
    if (clear) { clearInspect(clear.dataset.clear); return; }
    const el = e.target.closest("[data-card]");
    // A card in an operation drawing opens that operation's link inspector, below the drawing.
    const slot = el && el.matches(".card-slot") && el.closest("svg[data-seg]");
    if (slot && document.getElementById(`inspect-${slot.dataset.seg}`)) {
        if (panel.classList.contains("open")) closeCard();
        inspect(slot.dataset.seg, Number(el.dataset.idx));
        const box = document.getElementById(`inspect-${slot.dataset.seg}`);
        if (box.getBoundingClientRect().top > innerHeight - 120) box.scrollIntoView({ block: "nearest", behavior: "smooth" });
        return;
    }
    if (el) openCard(Number(el.dataset.card));
    // A tap outside the open panel closes it (on a phone it covers the lower part of the screen).
    else if (panel.classList.contains("open") && !panel.contains(e.target)) closeCard();
});
document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeCard();
    const el = e.target.closest && e.target.closest("[data-card]");
    if (el && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); el.dispatchEvent(new MouseEvent("click", { bubbles: true })); }
});
document.getElementById("dClose").addEventListener("click", closeCard);

// ---- Report search ----
const searchBox = document.getElementById("reportSearch");
function applySearch() {
    const q = searchBox.value.trim().toLowerCase();
    let hits = 0;
    const segHits = new Set();
    document.querySelectorAll("tr[data-search], figure[data-search]").forEach(el => {
        const ok = !q || el.dataset.search.includes(q);
        el.classList.toggle("search-hidden", !ok);
    });
    document.querySelectorAll("svg .card-slot[data-search], .card-row[data-search]").forEach(el => {
        const ok = !q || el.dataset.search.includes(q);
        if (el.matches(".card-slot")) el.classList.toggle("dimmed", !ok);
        if (q && ok && el.matches(".card-slot, figure")) { hits++; segHits.add(el.closest("details.section").id); }
    });
    if (q) segHits.forEach(id => openSection(id));
    document.getElementById("searchCount").textContent = q ? `${hits} card${hits === 1 ? "" : "s"} match` : "";
}
searchBox.addEventListener("input", applySearch);

// ---- Exports ----
function download(name, type, text) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const fileStem = "ootk_reading";
// A report with its own address downloads the JSON from the server; it is too big to carry
// in every page. A report without one (a database too old to save links) has it embedded.
document.querySelectorAll("[data-download-json]").forEach(btn => btn.addEventListener("click", () => {
    if (btn.dataset.jsonUrl) {
        const a = Object.assign(document.createElement("a"), { href: btn.dataset.jsonUrl, download: `${fileStem}.json` });
        document.body.appendChild(a); a.click(); a.remove();
        return;
    }
    const reading = JSON.parse(document.getElementById("readingData").textContent);
    download(`${fileStem}.json`, "application/json", JSON.stringify(reading, null, 2));
}));
// The prompt is already on the page, so the download needs no new request (and saves no
// second copy of the session).
document.querySelectorAll("[data-download-md]").forEach(btn => btn.addEventListener("click", () =>
    download("ootk_report.md", "text/markdown",
             document.getElementById("promptText").textContent)));

document.querySelectorAll("[data-svg-download]").forEach(btn => btn.addEventListener("click", () => {
    const svg = document.querySelector(`svg[data-seg="${btn.dataset.svgDownload}"]`);
    const clone = svg.cloneNode(true);
    clone.classList.remove("focus");
    clone.querySelectorAll(".unlinked, .selected, .lit").forEach(el => el.classList.remove("unlinked", "selected", "lit"));
    // Keep only the links drawn now: aspect lines or element pairs.
    clone.querySelectorAll(svg.classList.contains("mode-pairs") ? ".lines" : ".pair-links, .pair-badges").forEach(el => el.remove());
    // Standalone file: absolute image links and the current theme's colours baked in.
    clone.querySelectorAll("image").forEach(img => img.setAttribute("href", new URL(img.getAttribute("href"), location.href).href));
    clone.querySelectorAll(".is-hidden").forEach(el => el.remove());
    const cs = getComputedStyle(svg);
    const v = name => cs.getPropertyValue(name).trim();
    const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
    style.textContent = `text{fill:${v("--text")};font-family:sans-serif}.card-border{fill:none;stroke-width:2.5}
.aspect-line{stroke-linecap:round}.aspect-line.unaspected{stroke-dasharray:5 5}.card-base{fill:${v("--card-base")}}
.w-face{fill:${v("--svg-face")};stroke:${v("--svg-rule")}}.w-hole{fill:${v("--svg-hole")};stroke:${v("--svg-rule")}}
.w-rule{fill:none;stroke:${v("--svg-rule")}}.pair-link{fill:none;stroke-linecap:round}.pair-badge text{fill:#0d2617}.w-sector{stroke:${v("--svg-sector")}}.badge{fill:${v("--badge")}}`;
    // Paint the panel colour behind the drawing so the light labels stay readable in any viewer.
    const [vx, vy, vw, vh] = svg.getAttribute("viewBox").split(/[\s,]+/);
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    Object.entries({x: vx, y: vy, width: vw, height: vh, fill: v("--drawing-bg")}).forEach(([k, val]) => bg.setAttribute(k, val));
    clone.insertBefore(bg, clone.firstChild);
    clone.insertBefore(style, clone.firstChild);
    clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
    download(`${fileStem}_${btn.dataset.svgDownload}.svg`, "image/svg+xml",
             '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone));
}));

// Print / PDF: open every section so nothing collapsed is left out.
let reopened = [];
window.addEventListener("beforeprint", () => {
    reopened = [...document.querySelectorAll("details:not([open])")];
    reopened.forEach(d => d.open = true);
});
window.addEventListener("afterprint", () => { reopened.forEach(d => d.open = false); reopened = []; });

// Save menu: close it after a choice or a click elsewhere.
document.addEventListener("click", e => {
    document.querySelectorAll("details.menu[open]").forEach(m => {
        if (!m.contains(e.target) || e.target.closest(".menu-list button")) m.open = false;
    });
});
