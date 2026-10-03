// Start page diagram: the 15-card heap of Op 1, the 12-part wheel of the later operations,
// and the Cube of Space. The same fifteen markers move between the three layouts: twelve
// become the signs (wheel segments, then cube edges) and three the mother letters (cube axes).
// A schematic of the layouts, not a reading: it shows where things go, not what they mean.
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

    // Cards from the sample reading that sit on the cube: their edge or face is marked.
    let samplePlaces = [];
    try { samplePlaces = JSON.parse(document.getElementById("sampleCube").textContent); } catch (e) {}
    const sampleAt = place => samplePlaces.filter(c => c.place === place).map(c => c.title);

    let heapNames = [];
    try { heapNames = JSON.parse(document.getElementById("positionsData").textContent)["8"] || []; } catch (e) {}
    const detail = document.getElementById("journeyDetail");
    const inspect = text => { detail.textContent = text; detail.hidden = false; };

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
    DOUBLES.forEach(([glyph, planet, face, pt]) => {
        const [x, y] = iso(pt);
        const marked = sampleAt(face).length > 0;
        const g = el("g", { class: "double" + (marked ? " marked" : ""), transform: `translate(${x},${y})`, tabindex: "0" }, guides.cube);
        el("circle", { r: 13 }, g);
        const t = el("text", { "text-anchor": "middle", dy: "0.35em" }, g);
        t.textContent = glyph;
        const tip = `${face === "Centre" ? "Centre" : face + " face"}: ${planet}` + (marked ? ` (sample: ${sampleAt(face).join(", ")})` : "");
        el("title", {}, g).textContent = tip;
        g.addEventListener("click", () => { stopPlaying(); inspect(tip); });
    });

    // ---------- the fifteen moving markers ----------
    // Markers 0-11 become the signs, 12-14 the mother letters.
    const nodes = HEAP.map((pos, i) => {
        const g = el("g", { class: "node", tabindex: "0" }, svg);
        el("rect", { x: -12, y: -18, width: 24, height: 36, rx: 3 }, g);
        const t = el("text", { "text-anchor": "middle", dy: "0.35em" }, g);
        const tip = el("title", {}, g);
        let stages;
        if (i < 12) {
            const sign = SIGNS[i], [edge, pt] = EDGES[sign], marked = sampleAt(edge);
            stages = {
                wheel: { xy: wheelXY(i), label: GLYPHS[i], tip: sign },
                cube: { xy: iso(pt), label: GLYPHS[i], marked: marked.length > 0,
                        tip: `${edge}: ${sign}` + (marked.length ? ` (sample: ${marked.join(", ")})` : "") },
            };
        } else {
            const [letter, name, axis, pt] = MOTHERS[i - 12];
            stages = {
                wheel: { xy: [(i - 13) * 30, 0], label: letter, faint: true, tip: `${name}: outside the wheel` },
                cube: { xy: iso(pt), label: letter, tip: `${axis}: ${name}` },
            };
        }
        stages.heap = { xy: heapXY(pos), label: String(i + 1),
                        tip: heapNames[i] ? `Op 1, position ${heapNames[i].replace(/^(\d+)\.\s*/, "$1: ")}` : `Op 1, position ${i + 1}` };
        const pick = () => { stopPlaying(); inspect(stages[current].tip); };
        g.addEventListener("click", pick);
        g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
        g.style.transitionDelay = reduceMotion ? "0s" : `${i * 30}ms`;
        return { g, t, tip, stages };
    });

    // ---------- stages ----------
    const CAPTIONS = {
        heap: "Op 1 lays fifteen cards in a heap around your significator. Each pair of cards is scored by its elements.",
        wheel: "The next operations deal cards around a wheel: twelve houses, twelve signs, then thirty-six decans. Cards are related by the aspects between their places.",
        cube: "Each sign is also an edge of the Cube of Space, the seven planets are its faces and centre, and the three mother letters are its axes. The report places every card that has a Hebrew letter here.",
    };
    const buttons = Array.from(document.querySelectorAll("[data-journey]"));
    const caption = document.getElementById("journeyCaption");
    let current = null;

    function show(stage) {
        current = stage;
        svg.dataset.stage = stage;
        nodes.forEach(n => {
            const s = n.stages[stage];
            n.g.style.transform = `translate(${s.xy[0]}px, ${s.xy[1]}px)`;
            n.g.classList.toggle("faint", !!s.faint);
            n.g.classList.toggle("marked", !!s.marked);
            n.t.textContent = s.label;
            n.tip.textContent = s.tip;
        });
        Object.entries(guides).forEach(([s, g]) => g.classList.toggle("on", s === stage));
        buttons.forEach(b => b.setAttribute("aria-pressed", b.dataset.journey === stage));
        let text = CAPTIONS[stage];
        if (stage === "cube" && samplePlaces.length) {
            text += " Marked: " + samplePlaces.map(c => `${c.title} (${c.place.toLowerCase()})`).join(" and ")
                  + ", from the sample reading below.";
        }
        caption.textContent = text;
        detail.hidden = true;
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
            }, 2200);
        }, { threshold: 0.5 });
        io.observe(svg);
    }
})();
