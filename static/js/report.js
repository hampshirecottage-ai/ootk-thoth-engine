function copyText(text, btn) {
    const done = () => { const t = btn.textContent; btn.textContent = "Copied"; setTimeout(() => btn.textContent = t, 1200); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => {});
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

// ---- Hover (or tap, on a touch screen) a card to light up its aspect lines ----
function lightUp(svg, slot) {
    const i = slot.dataset.idx;
    document.querySelectorAll("svg.focus").forEach(o => o.classList.remove("focus"));
    svg.classList.add("focus");
    svg.querySelectorAll(".aspect-line").forEach(l => l.classList.toggle("lit", l.dataset.a === i || l.dataset.b === i));
}
const hoverable = matchMedia("(hover: hover)").matches;
document.querySelectorAll("svg[data-seg]").forEach(svg => {
    svg.querySelectorAll(".card-slot").forEach(slot => {
        slot.addEventListener("mouseenter", () => { if (hoverable) lightUp(svg, slot); });
        slot.addEventListener("mouseleave", () => { if (hoverable) svg.classList.remove("focus"); });
        // A tap has no hover, so it keeps the card's lines lit until the details close.
        // On a phone the details open as a bottom sheet, so bring the drawing up above it.
        slot.addEventListener("click", () => {
            if (hoverable) return;
            lightUp(svg, slot);
            if (matchMedia("(max-width: 640px)").matches) svg.scrollIntoView({ block: "start", behavior: "smooth" });
        });
    });
});

// ---- Theme ----
document.getElementById("themeToggle").addEventListener("click", () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
    try { localStorage.setItem("ootk.theme", root.dataset.theme); } catch (e) {}
});

// ---- Card detail panel ----
const CARDS = JSON.parse(document.getElementById("cardDetails").textContent);
const panel = document.getElementById("detailPanel");
const esc = v => String(v).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

function openCard(i) {
    const c = CARDS[i];
    if (!c) return;
    document.getElementById("dPos").textContent = `Position ${c.number} · ${c.position}`;
    document.getElementById("dTitle").textContent = c.title;
    const img = c.image
        ? `<img src="${esc(c.image)}" alt="${esc(c.title)}" decoding="async" style="border-color:${c.color}">`
        : `<div class="noimg" style="border-color:${c.color}">${esc(c.title)}</div>`;
    const fields = [["Element", c.element], ["Dignified", c.dignified ? "yes" : "no (neighbouring dignities sum below zero)"], ...c.fields]
        .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
    const list = (title, items) => items.length
        ? `<h3>${title} (${items.length})</h3><ul>${items.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : "";
    document.getElementById("dBody").innerHTML = img + `<dl>${fields}</dl>` + list("Aspects", c.aspects) + list("Elemental dignities", c.dignities);
    document.querySelectorAll("[data-card]").forEach(el => el.classList.toggle("selected", el.dataset.card === String(i)));
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
}
function closeCard() {
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    document.querySelectorAll("[data-card].selected").forEach(el => el.classList.remove("selected"));
    if (!hoverable) document.querySelectorAll("svg.focus").forEach(o => o.classList.remove("focus"));
}
document.addEventListener("click", e => {
    const el = e.target.closest("[data-card]");
    if (el) openCard(Number(el.dataset.card));
    // A tap outside the open panel closes it (on a phone it covers the lower part of the screen).
    else if (panel.classList.contains("open") && !panel.contains(e.target)) closeCard();
});
document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeCard();
    const el = e.target.closest && e.target.closest("[data-card]");
    if (el && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); openCard(Number(el.dataset.card)); }
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
const READING = JSON.parse(document.getElementById("readingData").textContent);
const fileStem = `ootk_reading_${READING.session_id || "latest"}`;
document.querySelectorAll("[data-download-json]").forEach(btn => btn.addEventListener("click", () =>
    download(`${fileStem}.json`, "application/json", JSON.stringify(READING, null, 2))));
// The prompt is already on the page, so the download needs no new request (and saves no
// second copy of the session).
document.querySelectorAll("[data-download-md]").forEach(btn => btn.addEventListener("click", () =>
    download(`ootk_report_${READING.session_id || "latest"}.md`, "text/markdown",
             document.getElementById("promptText").textContent)));

document.querySelectorAll("[data-svg-download]").forEach(btn => btn.addEventListener("click", () => {
    const svg = document.querySelector(`svg[data-seg="${btn.dataset.svgDownload}"]`);
    const clone = svg.cloneNode(true);
    clone.classList.remove("focus");
    // Standalone file: absolute image links and the current theme's colours baked in.
    clone.querySelectorAll("image").forEach(img => img.setAttribute("href", new URL(img.getAttribute("href"), location.href).href));
    clone.querySelectorAll(".is-hidden").forEach(el => el.remove());
    const cs = getComputedStyle(svg);
    const v = name => cs.getPropertyValue(name).trim();
    const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
    style.textContent = `text{fill:${v("--text")};font-family:sans-serif}.card-border{fill:none;stroke-width:2.5}
.aspect-line{stroke-linecap:round}.aspect-line.unaspected{stroke-dasharray:5 5}.card-base{fill:${v("--card-base")}}
.w-face{fill:${v("--svg-face")};stroke:${v("--svg-rule")}}.w-hole{fill:${v("--svg-hole")};stroke:${v("--svg-rule")}}
.w-rule{fill:none;stroke:${v("--svg-rule")}}.w-sector{stroke:${v("--svg-sector")}}.badge{fill:${v("--badge")}}`;
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
