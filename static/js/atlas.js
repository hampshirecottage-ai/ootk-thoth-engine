// Card maps: draws where a card sits on the Tree of Life, the Cube of Space, the zodiac's
// decans, the five Platonic solids, their dual pairs and the elemental grid. The data comes from ootk.atlas
// (one card's atlas, and optionally the whole deck for labels and tap targets). Every
// drawing returns an SVG or HTML string. Positions only: nothing here interprets a card.
(function () {
    const esc = t => String(t ?? "").replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
    const f1 = n => Math.round(n * 10) / 10;
    const hebrew = t => (String(t || "").match(/[א-ת]/) || [""])[0];
    const tip = t => `<title>${esc(t)}</title>`;
    // Tap target for card `i`: indexes come from the page's JSON, so they are forced to integers.
    const pick = (i, label) => Number.isInteger(i) ? ` data-pick="${Number(i)}" tabindex="0" role="button" aria-label="${esc(label)}"` : "";

    // ---------- Tree of Life ----------
    const SEPH = [[0, 0], [1, 1], [-1, 1], [1, 2.5], [-1, 2.5], [0, 3.3], [1, 4.6], [-1, 4.6], [0, 5.5], [0, 6.6]];
    const SEPH_NAMES = ["Kether", "Chokmah", "Binah", "Chesed", "Geburah", "Tiphareth", "Netzach", "Hod", "Yesod", "Malkuth"];
    const PATHS = { 11: [1, 2], 12: [1, 3], 13: [1, 6], 14: [2, 3], 15: [2, 6], 16: [2, 4], 17: [3, 6], 18: [3, 5],
                    19: [4, 5], 20: [4, 6], 21: [4, 7], 22: [5, 6], 23: [5, 8], 24: [6, 7], 25: [6, 9], 26: [6, 8],
                    27: [7, 8], 28: [7, 9], 29: [7, 10], 30: [8, 9], 31: [8, 10], 32: [9, 10] };
    const PATH_GLYPHS = "אבגדהוזחטיכלמנסעפצקרשת";
    const LABEL_AT = { 27: 0.3, 19: 0.3, 14: 0.3, 29: 0.62, 31: 0.62 };   // keep crossing labels apart

    function tree(sel, deck, opts = {}) {
        const k = opts.compact ? 46 : 64, ox = opts.compact ? 70 : 150, oy = 26;
        const P = n => [ox + SEPH[n - 1][0] * k * 1.25, oy + SEPH[n - 1][1] * k];
        const W = ox * 2, H = oy * 2 + 6.6 * k;
        const hlPath = sel && sel.tree.path, hlSeph = sel ? sel.tree.sephira : [];
        let s = `<svg class="atlas-svg" viewBox="0 0 ${W} ${f1(H)}" role="img" aria-label="Tree of Life${sel ? ": " + esc(sel.tree.note) : ""}">`;
        Object.entries(PATHS).forEach(([p, [a, b]]) => {
            const [x1, y1] = P(a), [x2, y2] = P(b);
            s += `<line class="${+p === hlPath ? "a-hl-line" : "a-frame"}" x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}"/>`;
        });
        if (!opts.compact) Object.entries(PATHS).forEach(([p, [a, b]]) => {
            const [x1, y1] = P(a), [x2, y2] = P(b), t = LABEL_AT[p] || 0.5;
            const x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t;
            const info = deck && deck.paths[p];
            const names = info ? info.cards.map(i => deck.cards[i].short) : [];
            const major = info ? info.cards.find(i => deck.cards[i].kind === "Major") : null;
            const on = +p === hlPath;
            s += `<g class="a-node${on ? " on" : ""}"${pick(major, `Path ${p}`)} transform="translate(${f1(x)},${f1(y)})">${tip(`Path ${p}, ${info ? info.letter : ""}${names.length ? ": " + names.join(", ") : ""}`)}<circle r="10"/><text dy="0.35em">${PATH_GLYPHS[p - 11]}</text></g>`;
        });
        SEPH.forEach((_, i) => {
            const [x, y] = P(i + 1), on = hlSeph.includes(i + 1), r = opts.compact ? 11 : 16;
            s += `<g class="a-seph${on ? " on" : ""}" transform="translate(${f1(x)},${f1(y)})">${tip(`${i + 1}. ${SEPH_NAMES[i]}`)}<circle r="${r}"/><text dy="0.35em">${i + 1}</text>`;
            if (!opts.compact) s += `<text class="a-small" x="${SEPH[i][0] < 0 ? -r - 4 : r + 4}" dy="0.35em" text-anchor="${SEPH[i][0] < 0 ? "end" : "start"}">${SEPH_NAMES[i]}</text>`;
            s += `</g>`;
        });
        return s + `</svg>`;
    }

    // ---------- Cube of Space (x east, y up, z south), as on the start page ----------
    const YAW = 45 * Math.PI / 180, TILT = 25 * Math.PI / 180;
    const PLACES = {
        "North-East Edge": [1, 0, -1], "South-East Edge": [1, 0, 1], "Upper-East Edge": [1, 1, 0], "Lower-East Edge": [1, -1, 0],
        "North-West Edge": [-1, 0, -1], "South-West Edge": [-1, 0, 1], "Upper-West Edge": [-1, 1, 0], "Lower-West Edge": [-1, -1, 0],
        "Upper-North Edge": [0, 1, -1], "Lower-North Edge": [0, -1, -1], "Upper-South Edge": [0, 1, 1], "Lower-South Edge": [0, -1, 1],
        "Up (Zenith)": [0, 1, 0], "Down (Nadir)": [0, -1, 0], "East": [1, 0, 0], "West": [-1, 0, 0],
        "North": [0, 0, -1], "South": [0, 0, 1], "Center Core (Holy Temple)": [0, 0, 0],
    };
    const AXES = { "Vertical": [0, 1, 0], "Horizontal": [1, 0, 0], "Longitudinal": [0, 0, 1] };
    const AXIS_END = 1.42;
    const axisOf = place => Object.keys(AXES).find(a => String(place).startsWith(a));

    function cube(sel, deck, opts = {}) {
        const S = opts.compact ? 64 : 122, R = opts.compact ? 120 : 220;
        const iso = ([x, y, z]) => {
            const xr = x * Math.cos(YAW) - z * Math.sin(YAW), zr = x * Math.sin(YAW) + z * Math.cos(YAW);
            return [f1(xr * S), f1(-(y * Math.cos(TILT) - zr * Math.sin(TILT)) * S)];
        };
        const place = sel && sel.cube.place, derived = sel && sel.cube.derived;
        const hlCls = derived ? "a-hl-line dashed" : "a-hl-line";
        let s = `<svg class="atlas-svg" viewBox="${-R} ${-R} ${R * 2} ${R * 2}" role="img" aria-label="Cube of Space${sel && sel.cube.note ? ": " + esc(sel.cube.note) : ""}">`;
        // highlighted face first, under the frame
        if (place && PLACES[place] && PLACES[place].filter(v => v).length === 1) {
            const n = PLACES[place], axis = n.findIndex(v => v), others = [0, 1, 2].filter(i => i !== axis);
            const pts = [[-1, -1], [-1, 1], [1, 1], [1, -1]].map(([a, b]) => {
                const p = [0, 0, 0]; p[axis] = n[axis]; p[others[0]] = a; p[others[1]] = b; return iso(p).join(",");
            });
            s += `<polygon class="a-hl-face${derived ? " dashed" : ""}" points="${pts.join(" ")}"/>`;
        }
        const corners = [];
        [-1, 1].forEach(x => [-1, 1].forEach(y => [-1, 1].forEach(z => corners.push([x, y, z]))));
        corners.forEach((a, i) => corners.forEach((b, j) => {
            if (j > i && a.filter((v, q) => v !== b[q]).length === 1) {
                const [x1, y1] = iso(a), [x2, y2] = iso(b);
                s += `<line class="a-frame" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
            }
        }));
        Object.entries(AXES).forEach(([name, d]) => {
            const [x1, y1] = iso(d.map(v => -v * AXIS_END)), [x2, y2] = iso(d.map(v => v * AXIS_END));
            s += `<line class="${axisOf(place) === name ? hlCls : "a-frame axis"}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
        });
        // highlighted edge
        if (place && PLACES[place] && PLACES[place].filter(v => v).length === 2) {
            const m = PLACES[place], free = m.findIndex(v => v === 0);
            const a = [...m], b = [...m]; a[free] = -1; b[free] = 1;
            const [x1, y1] = iso(a), [x2, y2] = iso(b);
            s += `<line class="${hlCls}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
        }
        if (!opts.compact) {
            [["N", [0, 0, -1.78]], ["S", [0, 0, 1.78]], ["E", [1.78, 0, 0]], ["W", [-1.78, 0, 0]], ["Above", [0, 1.7, 0]], ["Below", [0, -1.7, 0]]]
                .forEach(([t, p]) => { const [x, y] = iso(p); s += `<text class="a-small a-compass" x="${x}" y="${y}" dy="0.35em">${t}</text>`; });
            // a marker per place, carrying its letter; axes get theirs at the positive end
            const at = {};
            (deck ? deck.cards : []).forEach((c, i) => { if (c.kind === "Major" && c.cube.place) (at[c.cube.place] = at[c.cube.place] || []).push(i); });
            Object.entries(at).forEach(([pl, ids]) => {
                const axis = axisOf(pl);
                const pt = axis ? AXES[axis].map(v => v * AXIS_END) : PLACES[pl];
                if (!pt) return;
                const [x, y] = iso(pt), c = deck.cards[ids[0]];
                const on = pl === place || (axis && axis === axisOf(place));
                const courts = deck.cards.filter(o => o.kind === "Court" && o.cube.place === pl).map(o => o.short);
                s += `<g class="a-node${on ? " on" : ""}${PLACES[pl] && PLACES[pl].filter(v => v).length === 1 ? " face" : ""}"${pick(ids[0], pl)} transform="translate(${x},${y})">${tip(`${pl}: ${c.letter} · ${c.short}${courts.length ? ", " + courts.join(", ") : ""}`)}<circle r="11"/><text dy="0.35em">${esc(hebrew(c.letter))}</text></g>`;
            });
        } else if (place) {
            const axis = axisOf(place);
            const pt = axis ? AXES[axis].map(v => v * AXIS_END) : PLACES[place];
            if (pt) { const [x, y] = iso(pt); s += `<g class="a-node on"><circle cx="${x}" cy="${y}" r="7"/></g>`; }
        }
        return s + `</svg>`;
    }

    // ---------- Zodiac, decans and court spans (Aries at 9 o'clock, counter-clockwise) ----------
    const SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
    const SIGN_GLYPHS = "♈♉♊♋♌♍♎♏♐♑♒♓".split("").map(g => g + "︎");
    const CHALDEAN = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"];
    const PLANET_GLYPHS = { Mars: "♂", Sun: "☉", Venus: "♀", Mercury: "☿", Moon: "☽", Saturn: "♄", Jupiter: "♃" };
    const pt = (r, deg) => { const a = (180 + deg) * Math.PI / 180; return [f1(r * Math.cos(a)), f1(-r * Math.sin(a))]; };
    const sector = (r1, r2, a0, a1) => {
        const [x1, y1] = pt(r2, a0), [x2, y2] = pt(r2, a1), [x3, y3] = pt(r1, a1), [x4, y4] = pt(r1, a0);
        const big = a1 - a0 > 180 ? 1 : 0;
        return `M${x1},${y1} A${r2},${r2} 0 ${big} 0 ${x2},${y2} L${x3},${y3} A${r1},${r1} 0 ${big} 1 ${x4},${y4} Z`;
    };

    function ring(sel, deck, opts = {}) {
        const c = opts.compact;
        const R = c ? { sign: [92, 112], dec: [66, 92], court: [48, 66], pss: [30, 48], hl: [113, 120], box: 124 }
                    : { sign: [160, 192], dec: [118, 160], court: [86, 118], pss: [52, 86], hl: [194, 204], box: 210 };
        const decans = new Set(sel ? sel.zodiac.decans : []);
        let s = `<svg class="atlas-svg" viewBox="${-R.box} ${-R.box} ${R.box * 2} ${R.box * 2}" role="img" aria-label="Zodiac and decans${sel && sel.zodiac.note ? ": " + esc(sel.zodiac.note) : ""}">`;
        for (let i = 0; i < 12; i++) {
            s += `<path class="a-band${sel && sel.zodiac.arcs.some(([a, b]) => a <= i * 30 && b >= i * 30 + 30) ? " on" : ""}" d="${sector(R.sign[0], R.sign[1], i * 30, i * 30 + 30)}">${tip(SIGNS[i])}</path>`;
            { const [x, y] = pt((R.sign[0] + R.sign[1]) / 2, i * 30 + 15); s += `<text class="a-glyph${c ? " sm" : ""}" x="${x}" y="${y}" dy="0.35em">${SIGN_GLYPHS[i]}</text>`; }
        }
        for (let i = 0; i < 36; i++) {
            const d = deck && deck.decans[i], ruler = d ? d.ruler : CHALDEAN[i % 7];
            const label = `${SIGNS[Math.floor(i / 3)]} ${i % 3 * 10}°–${i % 3 * 10 + 10}°: ${ruler}${d ? ", " + d.card : ""}`;
            s += `<g class="a-dec${decans.has(i) ? " on" : ""}"${c ? "" : pick(d && d.index, label)}><path d="${sector(R.dec[0], R.dec[1], i * 10, i * 10 + 10)}"/>${tip(label)}`;
            if (!c) { const [x, y] = pt((R.dec[0] + R.dec[1]) / 2, i * 10 + 5); s += `<text class="a-glyph sm" x="${x}" y="${y}" dy="0.35em">${esc(PLANET_GLYPHS[ruler] || "")}︎</text>`; }
            s += `</g>`;
        }
        // court spans: Knights, Queens and Princes tile the circle from 20° of each sign;
        // the Princesses rule quadrants
        const courts = deck ? deck.cards.map((cd, i) => [cd, i]).filter(([cd]) => cd.kind === "Court" && cd.zodiac.arcs.length) : [];
        courts.forEach(([cd, i]) => {
            const [a, b] = cd.zodiac.arcs[0], pss = b - a === 90, band = pss ? R.pss : R.court;
            const on = sel && sel.title === cd.title;
            const [rank, , suit] = cd.short.split(" ");
            s += `<g class="a-court${on ? " on" : ""}"${pick(i, cd.short)}><path d="${sector(band[0], band[1], a, b)}"/>${tip(`${cd.short}: ${cd.zodiac.note}`)}`;
            if (!c) { const [x, y] = pt((band[0] + band[1]) / 2, (a + b) / 2); s += `<text class="a-small" x="${x}" y="${y}" dy="0.35em">${esc(pss ? "Princess" : rank[0] === "P" ? "Pr" : rank.slice(0, rank[0] === "K" ? 2 : 1))} ${esc(suit[0])}</text>`; }
            s += `</g>`;
        });
        if (sel && !deck && sel.kind === "Court" && sel.zodiac.arcs.length) {
            const [a, b] = sel.zodiac.arcs[0], band = b - a === 90 ? R.pss : R.court;
            s += `<path class="a-court on" d="${sector(band[0], band[1], a, b)}"/>`;
        }
        (sel ? sel.zodiac.arcs : []).forEach(([a, b]) => { s += `<path class="a-hl-fill" d="${sector(R.hl[0], R.hl[1], a, b)}"/>`; });
        return s + `</svg>`;
    }

    // ---------- Platonic solids ----------
    const PHI = (1 + Math.sqrt(5)) / 2;
    const cyc = ([a, b, c]) => [[a, b, c], [b, c, a], [c, a, b]];
    const signs3 = (v) => { const out = []; [1, -1].forEach(i => [1, -1].forEach(j => [1, -1].forEach(k => out.push([v[0] * i, v[1] * j, v[2] * k])))); return out; };
    const uniq = pts => pts.filter((p, i) => pts.findIndex(q => q.every((v, k) => Math.abs(v - p[k]) < 1e-9)) === i);
    const SOLIDS = {
        "Tetrahedron": [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]],
        "Hexahedron (Cube)": signs3([1, 1, 1]),
        "Octahedron": uniq([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]),
        "Icosahedron": uniq(signs3([0, 1, PHI]).flatMap(cyc)),
        "Dodecahedron": uniq([...signs3([1, 1, 1]), ...signs3([0, 1 / PHI, PHI]).flatMap(cyc)]),
    };
    const SOLID_ELEMENT = { "Tetrahedron": "Fire", "Hexahedron (Cube)": "Earth", "Octahedron": "Air", "Icosahedron": "Water", "Dodecahedron": "Spirit" };
    const SOLID_SHORT = { "Hexahedron (Cube)": "Cube" };
    const edgesOf = (pts) => {
        let min = Infinity; const d = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
        pts.forEach((a, i) => pts.forEach((b, j) => { if (j > i) min = Math.min(min, d(a, b)); }));
        const out = [];
        pts.forEach((a, i) => pts.forEach((b, j) => { if (j > i && d(a, b) < min * 1.001) out.push([a, b]); }));
        return out;
    };

    // `flip` draws the solid turned inside out (every corner through the centre): the
    // tetrahedron's dual is the same solid pointing the other way.
    function solidSvg(name, size, on, spin = 0.5, flip = false) {
        const pts = flip ? SOLIDS[name].map(p => p.map(v => -v)) : SOLIDS[name];
        const r = Math.max(...pts.map(p => Math.hypot(...p)));
        const ay = spin, ax = 0.42;
        const rot = ([x, y, z]) => {
            const x1 = x * Math.cos(ay) + z * Math.sin(ay), z1 = -x * Math.sin(ay) + z * Math.cos(ay);
            const y1 = y * Math.cos(ax) - z1 * Math.sin(ax), z2 = y * Math.sin(ax) + z1 * Math.cos(ax);
            return [x1 / r * size * 0.42, -y1 / r * size * 0.42, z2];
        };
        const lines = edgesOf(pts).map(([a, b]) => { const p = rot(a), q = rot(b); return [p, q, (p[2] + q[2]) / 2]; })
            .sort((u, v) => u[2] - v[2]);
        let s = "";
        lines.forEach(([p, q, z]) => { s += `<line class="${z < -0.01 ? "back" : "front"}" x1="${f1(p[0])}" y1="${f1(p[1])}" x2="${f1(q[0])}" y2="${f1(q[1])}"/>`; });
        return `<g class="a-solid${on ? " on" : ""}">${s}</g>`;
    }

    function solid(sel, deck, opts = {}) {
        const name = sel && sel.solid ? sel.solid.name : null;
        const W = opts.compact ? 200 : 400, big = opts.compact ? 150 : 230;
        let s = `<svg class="atlas-svg" viewBox="0 0 ${W} ${opts.compact ? big + 10 : name ? big + 120 : 150}" role="img" aria-label="Platonic solid${name ? ": " + esc(name) : "s"}">`;
        if (name) {
            const so = sel.solid;
            s += `<g transform="translate(${W / 2},${big / 2 + 4})">${solidSvg(name, big, true)}</g>`;
            if (!opts.compact) s += `<text class="a-text" x="${W / 2}" y="${big + 18}">${esc(so.faces)} faces · ${esc(so.vertices)} vertices · ${esc(so.edges)} edges</text>`;
        }
        if (!opts.compact) {
            const names = Object.keys(SOLIDS), step = W / names.length, y = name ? big + 76 : big / 2 + 30;
            const count = n => deck ? deck.cards.filter(c => c.solid && c.solid.name === n).length : null;
            names.forEach((n, i) => {
                const x = step * i + step / 2, sz = name ? 58 : 76;
                s += `<g transform="translate(${f1(x)},${y})">${tip(`${n}: ${SOLID_ELEMENT[n]}${deck ? ", " + count(n) + " cards" : ""}`)}${solidSvg(n, sz, n === name, 0.5 + i * 0.15)}<text class="a-small" y="${sz / 2 + 10}">${SOLID_SHORT[n] || n}</text><text class="a-small a-muted" y="${sz / 2 + 22}">${SOLID_ELEMENT[n]}${deck ? " · " + count(n) : ""}</text></g>`;
            });
        }
        return s + `</svg>`;
    }

    // ---------- Dual inversions ----------
    // Put a corner at the centre of each face of a solid and the corners make its dual. The
    // Cube of Space's dual is an octahedron whose six corners are the centres of its six faces:
    // the six directions the Sefer Yetzirah gives to six double letters.
    const DUALS = [["Hexahedron (Cube)", "Octahedron"], ["Dodecahedron", "Icosahedron"], ["Tetrahedron", "Tetrahedron"]];
    const DIRECTIONS = ["Up (Zenith)", "Down (Nadir)", "East", "West", "North", "South"];
    const dualOf = name => { const d = DUALS.find(p => p.includes(name)); return d ? (d[0] === name ? d[1] : d[0]) : null; };
    const pairLabel = (a, b) => a === b ? `${a}, its own dual` : `${SOLID_SHORT[a] || a} \u21c4 ${SOLID_SHORT[b] || b}`;

    function pairSvg(a, b, size, on) {
        const gap = size * 0.5;
        return `<g transform="translate(${f1(-size / 2 - gap / 2)},0)">${solidSvg(a, size, on, 0.5)}</g>` +
            `<text class="a-text" dy="0.35em">\u21c4</text>` +
            `<g transform="translate(${f1(size / 2 + gap / 2)},0)">${solidSvg(b, size, on, 0.5, a === b)}</g>`;
    }

    function dual(sel, deck, opts = {}) {
        const name = sel && sel.solid ? sel.solid.name : null;
        if (opts.compact) {
            const W = 200, H = 110, other = name && dualOf(name);
            let s = `<svg class="atlas-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Dual inversion${other ? ": " + esc(pairLabel(name, other)) : ""}">`;
            if (other) s += `<g transform="translate(${W / 2},${H / 2})">${pairSvg(name, other, 70, true)}</g>`;
            return s + `</svg>`;
        }
        const S = 100, top = 150, W = 440;
        const iso = ([x, y, z]) => {
            const xr = x * Math.cos(YAW) - z * Math.sin(YAW), zr = x * Math.sin(YAW) + z * Math.cos(YAW);
            return [f1(W / 2 + xr * S), f1(top - (y * Math.cos(TILT) - zr * Math.sin(TILT)) * S),
                    zr * Math.cos(TILT) + y * Math.sin(TILT)];   // last: nearness to the viewer
        };
        const place = sel && sel.cube.place;
        const cubeOn = name === "Hexahedron (Cube)", octaOn = name === "Octahedron";
        let s = `<svg class="atlas-svg" viewBox="0 0 ${W} ${top + 290}" role="img" aria-label="Dual inversions: the Cube of Space and its dual octahedron, then the three dual pairs">`;
        const corners = [];
        [-1, 1].forEach(x => [-1, 1].forEach(y => [-1, 1].forEach(z => corners.push([x, y, z]))));
        corners.forEach((a, i) => corners.forEach((b, j) => {
            if (j > i && a.filter((v, q) => v !== b[q]).length === 1) {
                const [x1, y1] = iso(a), [x2, y2] = iso(b);
                s += `<line class="a-frame${cubeOn ? " on" : ""}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
            }
        }));
        // the octahedron: each face centre joins the four that are not opposite it
        const centres = DIRECTIONS.map(d => PLACES[d]);
        s += `<g class="a-octa${octaOn ? " on" : ""}">`;
        centres.forEach((a, i) => centres.forEach((b, j) => {
            if (j > i && a.some((v, q) => v !== -b[q])) {
                const p = iso(a), q = iso(b);
                s += `<line class="${(p[2] + q[2]) / 2 < -0.01 ? "back" : "front"}" x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}"/>`;
            }
        }));
        s += `</g>`;
        // the six directions (and the centre both solids share), with their letters
        const letterAt = pl => { const i = deck ? deck.cards.findIndex(c => c.kind === "Major" && c.cube.place === pl) : -1; return i < 0 ? null : i; };
        [...DIRECTIONS, "Center Core (Holy Temple)"].forEach(pl => {
            const [x, y] = iso(PLACES[pl]), i = letterAt(pl), c = i === null ? null : deck.cards[i];
            const on = pl === place, centre = pl.startsWith("Center");
            s += `<g class="a-node${on ? " on" : ""}${centre ? "" : " face"}"${c ? pick(i, pl) : ""} transform="translate(${x},${y})">${tip(c ? `${pl}: ${c.letter} · ${c.short}` : pl)}<circle r="${c ? 11 : 4}"/>${c ? `<text dy="0.35em">${esc(hebrew(c.letter))}</text>` : ""}</g>`;
        });
        s += `<text class="a-small a-muted" x="${W / 2}" y="${top + 178}">Cube of Space (grey) and its dual octahedron, cornered on the six faces</text>`;
        // the three dual pairs
        const step = W / 3, y = top + 230;
        DUALS.forEach(([a, b], i) => {
            const on = name && (a === name || b === name), x = step * i + step / 2;
            const count = n => deck ? deck.cards.filter(c => c.solid && c.solid.name === n).length : null;
            const counts = deck ? (a === b ? ` · ${count(a)}` : ` · ${count(a)} and ${count(b)}`) : "";
            s += `<g transform="translate(${f1(x)},${y})">${tip(`${pairLabel(a, b)}: ${SOLID_ELEMENT[a]}${a === b ? "" : " and " + SOLID_ELEMENT[b]}`)}${pairSvg(a, b, 50, on)}` +
                `<text class="a-small" y="38">${esc(pairLabel(a, b))}</text>` +
                `<text class="a-small a-muted" y="50">${SOLID_ELEMENT[a]}${a === b ? "" : " \u21c4 " + SOLID_ELEMENT[b]}${counts}</text></g>`;
        });
        return s + `</svg>`;
    }

    // ---------- Elemental grid: suit (row) by rank (column) ----------
    const ELEMENTS = ["Fire", "Water", "Air", "Earth"];
    const SUITS = { Fire: "Wands", Water: "Cups", Air: "Swords", Earth: "Disks" };
    const RANKS = { Fire: "Knight", Water: "Queen", Air: "Prince", Earth: "Princess" };

    function grid(sel, deck) {
        const g = sel ? sel.grid : { row: null, col: null };
        const index = {};
        (deck ? deck.cards : []).forEach((c, i) => { index[c.short] = i; });
        let s = `<table class="atlas-grid"><caption class="sr-only">Court cards by suit and rank</caption><thead><tr><th></th>`;
        ELEMENTS.forEach(e => { s += `<th scope="col" class="${g.col === e ? "on" : ""}">${RANKS[e]}<br><span class="a-muted">${e}</span></th>`; });
        s += `</tr></thead><tbody>`;
        ELEMENTS.forEach(row => {
            s += `<tr class="${g.row === row && !g.col ? "on" : ""}"><th scope="row" class="${g.row === row ? "on" : ""}">${SUITS[row]}<br><span class="a-muted">${row}</span></th>`;
            ELEMENTS.forEach(col => {
                const name = `${RANKS[col]} of ${SUITS[row]}`, on = g.row === row && g.col === col;
                s += `<td class="${on ? "on" : ""}"${pick(index[name], name)}><span>${col} of ${row}</span></td>`;
            });
            s += `</tr>`;
        });
        return s + `</tbody></table>`;
    }

    const solidName = n => SOLID_SHORT[n] || n;
    window.Atlas = { tree, cube, ring, solid, dual, dualOf, solidName, grid, esc };
})();
