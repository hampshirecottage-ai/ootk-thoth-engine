// Start page diagram of the sample Opening of the Key: the 15-card heap of Op 1, the twelve
// signs of Op 3, and the Cube of Space. The same fifteen markers move between the three
// layouts: twelve become the signs (wheel segments, then cube edges) and three the mother
// letters (cube axes). Each marker shows the sample card at that place, coloured by element;
// tapping one opens it in the inspector. It shows where cards fall, never what they mean.
(function () {
    const svg = document.getElementById("journeySvg");
    if (!svg) return;
    const NS = "http://www.w3.org/2000/svg";
    const el = (name, attrs, parent) => {
        const n = document.createElementNS(NS, name);
        Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v));
        if (parent) parent.appendChild(n);
        return n;
    };
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // ---------- Op 1: the heap (SPREAD_DEFAULT_COORDINATES["8"], y up, centred) ----------
    const HEAP = [[0, 0], [-2.25, 0], [-1.75, 0], [1.75, 0], [2.25, 0], [-0.25, 0.75], [0.25, 0.75],
                  [-1.25, -1.5], [-0.75, -1.5], [0.75, -1.5], [1.25, -1.5], [-0.25, 2], [0.25, 2],
                  [0, -0.75], [0, 3]];
    const HEAP_SCALE = 52, HEAP_MID = 0.9;
    const heapXY = ([x, y]) => [x * HEAP_SCALE, -(y - HEAP_MID) * HEAP_SCALE];

    // ---------- the wheel: twelve signs, Aries at 9 o'clock, counter-clockwise ----------
    const SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
                   "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
    const GLYPHS = "♈♉♊♋♌♍♎♏♐♑♒♓".split("").map(g => g + "︎");
    const R_WHEEL = 205;
    const wheelXY = i => {
        const a = (180 + i * 30) * Math.PI / 180;
        return [R_WHEEL * Math.cos(a), -R_WHEEL * Math.sin(a)];
    };

    // ---------- the Cube of Space (x east, y up, z south), isometric ----------
    // Edge and face names as the database's cube positions name them.
    // Turned 45 degrees and tilted 25, so no edge midpoint lands on a face centre.
    const S = 125, YAW = 45 * Math.PI / 180, TILT = 25 * Math.PI / 180;
    const iso = ([x, y, z]) => {
        const xr = x * Math.cos(YAW) - z * Math.sin(YAW), zr = x * Math.sin(YAW) + z * Math.cos(YAW);
        return [xr * S, -(y * Math.cos(TILT) - zr * Math.sin(TILT)) * S];
    };
    const EDGES = {   // sign -> edge midpoint
        "Aries": ["North-East Edge", [1, 0, -1]], "Taurus": ["South-East Edge", [1, 0, 1]],
        "Gemini": ["Upper-East Edge", [1, 1, 0]], "Cancer": ["Lower-East Edge", [1, -1, 0]],
        "Leo": ["North-West Edge", [-1, 0, -1]], "Virgo": ["South-West Edge", [-1, 0, 1]],
        "Libra": ["Upper-West Edge", [-1, 1, 0]], "Scorpio": ["Lower-West Edge", [-1, -1, 0]],
        "Sagittarius": ["Upper-North Edge", [0, 1, -1]], "Capricorn": ["Lower-North Edge", [0, -1, -1]],
        "Aquarius": ["Upper-South Edge", [0, 1, 1]], "Pisces": ["Lower-South Edge", [0, -1, 1]],
    };
    const AXIS_END = 1.4;   // mother markers sit just outside the cube, at the axis ends
    const MOTHERS = [   // letter, element, axis, point on the axis
        ["א", "Aleph, Air", "Vertical Axis", [0, AXIS_END, 0]],
        ["מ", "Mem, Water", "Horizontal Axis (east to west)", [AXIS_END, 0, 0]],
        ["ש", "Shin, Fire", "Longitudinal Axis (north to south)", [0, 0, AXIS_END]],
    ];
    const DOUBLES = [   // planet glyph, planet, face
        ["☿", "Mercury", "Up", [0, 1, 0]], ["☽", "Moon", "Down", [0, -1, 0]],
        ["♀", "Venus", "East", [1, 0, 0]], ["♃", "Jupiter", "West", [-1, 0, 0]],
        ["♂", "Mars", "North", [0, 0, -1]], ["☉", "Sun", "South", [0, 0, 1]],
        ["♄", "Saturn", "Centre", [0, 0, 0]],
    ].map(([g, p, f, pt]) => [g + "︎", p, f, pt]);

    // ---------- the sample reading (cards per place) ----------
    let data = { heap: [], wheel: [], colors: {} };
    try { data = Object.assign(data, JSON.parse(document.getElementById("sampleData").textContent)); } catch (e) {}
    const onCube = data.heap.filter(c => c.place);
    const cardsAt = place => onCube.filter(c => c.place === place);
    const cardsOnAxis = axis => onCube.filter(c => c.place.startsWith(axis.split(" ")[0]));

    const detail = document.getElementById("journeyDetail");
    const caption = document.getElementById("journeyCaption");
    const esc = t => String(t).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
    const signed = n => (n > 0 ? "+" : "") + n;

    // The inspector: one block per card, or a plain line for an empty place.
    function inspect(place, cards) {
        const blocks = cards.map(c => {
            const scores = (c.dignities || []).map(d =>
                `<span class="score ${d.score > 0 ? "pos" : d.score < 0 ? "neg" : "zero"}">${signed(d.score)}</span> with ${esc(d.with)}`).join(" · ");
            return `<div>${c.img ? `<img src="${esc(c.img)}" alt="">` : ""}</div><div>
                <div class="ins-pos">${esc(place)}</div>
                <div class="ins-title">${esc(c.title)}</div>
                <div><span class="dot" style="background:${esc(data.colors[c.element] || "transparent")}"></span>${esc(c.element)} · ${esc(c.attribution)}${c.letter ? " · " + esc(c.letter) : ""}</div>
                ${c.place ? `<div class="ins-pos">Cube of Space: ${esc(c.place)}</div>` : ""}
                ${scores ? `<div class="ins-scores">${scores}</div>` : ""}</div>`;
        });
        detail.innerHTML = blocks.length ? blocks.join("") : `<div><div class="ins-title">${esc(place)}</div><div class="ins-pos">No card from the sample's heap sits here.</div></div>`;
        detail.hidden = false;
    }

    // ---------- static guides, one group per stage ----------
    const guides = {};
    ["heap", "wheel", "cube"].forEach(s => guides[s] = el("g", { class: "guide", "data-stage": s }, svg));
    el("polygon", { points: [[0, 4.1], [-4.6, -2.3], [4.6, -2.3]].map(p => heapXY(p).join(",")).join(" "),
                    class: "frame" }, guides.heap);
    el("circle", { r: R_WHEEL + 32, class: "frame" }, guides.wheel);
    el("circle", { r: R_WHEEL - 32, class: "frame" }, guides.wheel);
    for (let i = 0; i < 12; i++) {
        const a = (195 + i * 30) * Math.PI / 180;
        el("line", { x1: (R_WHEEL - 32) * Math.cos(a), y1: -(R_WHEEL - 32) * Math.sin(a),
                     x2: (R_WHEEL + 32) * Math.cos(a), y2: -(R_WHEEL + 32) * Math.sin(a), class: "frame" },
           guides.wheel);
    }
    const corners = [];
    [-1, 1].forEach(x => [-1, 1].forEach(y => [-1, 1].forEach(z => corners.push([x, y, z]))));
    corners.forEach((a, i) => corners.forEach((b, j) => {
        const diff = a.filter((v, k) => v !== b[k]).length;
        if (j > i && diff === 1) {
            const [x1, y1] = iso(a), [x2, y2] = iso(b);
            el("line", { x1, y1, x2, y2, class: "frame" }, guides.cube);
        }
    }));
    [[0, 1, 0], [1, 0, 0], [0, 0, 1]].forEach(([x, y, z]) => {
        const [x1, y1] = iso([x * -AXIS_END, y * -AXIS_END, z * -AXIS_END]), [x2, y2] = iso([x * AXIS_END, y * AXIS_END, z * AXIS_END]);
        el("line", { x1, y1, x2, y2, class: "frame axis" }, guides.cube);
    });
    const doubles = DOUBLES.map(([glyph, planet, face, pt]) => {
        const [x, y] = iso(pt);
        const place = face === "Centre" ? "Center Core (Holy Temple)" : face === "Up" ? "Up (Zenith)" : face === "Down" ? "Down (Nadir)" : face;
        const cards = cardsAt(place);
        const g = el("g", { class: "double" + (cards.length ? " marked" : ""), transform: `translate(${x},${y})`, tabindex: "0" }, guides.cube);
        el("circle", { r: 13 }, g);
        el("text", { "text-anchor": "middle", dy: "0.35em" }, g).textContent = glyph;
        const label = `${face === "Centre" ? "Centre" : face + " face"} · ${planet}`;
        el("title", {}, g).textContent = label;
        const pick = () => { stopPlaying(); inspect(label, cards); };
        g.addEventListener("click", pick);
        g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
        return { g, cards };
    });

    // ---------- the fifteen moving markers ----------
    // Markers 0-11 become the signs, 12-14 the mother letters. Each stage gives a marker its
    // place, its label and the sample cards it stands for.
    let active = null;
    const nodes = HEAP.map((pos, i) => {
        const g = el("g", { class: "node", tabindex: "0", role: "button" }, svg);
        el("rect", { x: -13, y: -19, width: 26, height: 38, rx: 3, class: "body" }, g);
        const band = el("rect", { x: -11.5, y: -17.5, width: 23, height: 7, rx: 2, class: "band" }, g);
        const t = el("text", { "text-anchor": "middle", dy: "0.55em" }, g);
        const tip = el("title", {}, g);
        let stages;
        if (i < 12) {
            const sign = SIGNS[i], [edge, pt] = EDGES[sign], w = data.wheel[i];
            stages = {
                wheel: { xy: wheelXY(i), label: GLYPHS[i], place: `Op 3, ${sign}`, cards: w ? [w] : [] },
                cube: { xy: iso(pt), label: GLYPHS[i], place: `${edge} · ${sign}`, cards: cardsAt(edge) },
            };
        } else {
            const [letter, name, axis, pt] = MOTHERS[i - 12];
            stages = {
                wheel: { xy: [(i - 13) * 30, 0], label: letter, faint: true, place: `${name}: not on the wheel`, cards: [] },
                cube: { xy: iso(pt), label: letter, place: `${axis} · ${name}`, cards: cardsOnAxis(axis) },
            };
        }
        const h = data.heap[i];
        stages.heap = { xy: heapXY(pos), label: String(i + 1),
                        place: h ? `Op 1, position ${i + 1}: ${h.position}` : `Op 1, position ${i + 1}`,
                        cards: h ? [h] : [] };
        const node = { g, t, band, tip, stages };
        const pick = () => {
            stopPlaying();
            if (active) active.g.classList.remove("active");
            active = node; g.classList.add("active");
            inspect(stages[current].place, stages[current].cards);
        };
        g.addEventListener("click", pick);
        g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
        g.style.transitionDelay = reduceMotion ? "0s" : `${i * 30}ms`;
        return node;
    });

    // ---------- element filter (the bars beside the drawing) ----------
    let element = null;
    const elementButtons = Array.from(document.querySelectorAll("[data-element]"));
    function applyFilter() {
        nodes.forEach(n => {
            const cards = n.stages[current].cards;
            n.g.classList.toggle("dim", !!element && !cards.some(c => c.element === element));
        });
        doubles.forEach(d => d.g.classList.toggle("dim", !!element && !d.cards.some(c => c.element === element)));
        elementButtons.forEach(b => b.setAttribute("aria-pressed", b.dataset.element === element));
    }
    elementButtons.forEach(b => b.addEventListener("click", () => {
        stopPlaying();
        element = element === b.dataset.element ? null : b.dataset.element;
        applyFilter();
    }));

    // ---------- stages ----------
    const CAPTIONS = {
        heap: "Op 1 lays fifteen cards in a heap around the significator. Each pair of neighbouring cards is scored by its elements.",
        wheel: "The next operations deal cards around a wheel: twelve houses, twelve signs, then thirty-six decans. This is Op 3, the signs.",
        cube: "Each sign is also an edge of the Cube of Space, the seven planets are its faces and centre, and the three mother letters are its axes. Outlined: where the heap's cards sit.",
    };
    const buttons = Array.from(document.querySelectorAll("[data-journey]"));
    let current = null;

    function show(stage) {
        current = stage;
        nodes.forEach(n => {
            const s = n.stages[stage];
            n.g.style.transform = `translate(${s.xy[0]}px, ${s.xy[1]}px)`;
            n.g.classList.toggle("faint", !!s.faint);
            n.g.classList.toggle("marked", stage === "cube" && s.cards.length > 0);
            const colour = stage !== "cube" && s.cards.length ? data.colors[s.cards[0].element] : null;
            n.band.style.fill = colour || "transparent";
            n.t.textContent = s.label;
            n.tip.textContent = s.place + (s.cards.length ? ": " + s.cards.map(c => c.short).join(", ") : "");
        });
        Object.entries(guides).forEach(([s, g]) => g.classList.toggle("on", s === stage));
        buttons.forEach(b => b.setAttribute("aria-pressed", b.dataset.journey === stage));
        caption.textContent = CAPTIONS[stage];
        if (active) { active.g.classList.remove("active"); active = null; }
        detail.hidden = true;
        applyFilter();
    }

    // Plays through once when the diagram first comes into view; any click takes over.
    let timer = null;
    const stopPlaying = () => { clearTimeout(timer); timer = null; };
    buttons.forEach(b => b.addEventListener("click", () => { stopPlaying(); show(b.dataset.journey); }));
    show("heap");
    if (!reduceMotion && "IntersectionObserver" in window) {
        const io = new IntersectionObserver(entries => {
            if (!entries.some(e => e.isIntersecting)) return;
            io.disconnect();
            timer = setTimeout(() => {
                show("wheel");
                timer = setTimeout(() => { if (timer) show("cube"); }, 3200);
            }, 2600);
        }, { threshold: 0.5 });
        io.observe(svg);
    }
})();
