// The /maps page: draws the picked card on each map (static/js/atlas.js) and keeps the
// address in step, so a link opens the same card.
(function () {
    const A = window.Atlas, data = JSON.parse(document.getElementById("atlasData").textContent);
    const pickEl = document.getElementById("cardPick");
    const $ = id => document.getElementById(id);
    const esc = A.esc;
    const WHOLE = {
        tree: "The ten sephiroth and the 22 paths between them. Each path carries a Hebrew letter and one Major; the small cards sit on the sephiroth by number.",
        cube: "Twelve edges for the twelve signs' letters, six faces and the centre for the seven planets' letters, three axes for the mother letters. Dashed circles are faces.",
        ring: "Outer ring: the twelve signs, counter-clockwise from 0° Aries on the left. Middle: the 36 decans with their ruling planets (one small card each). Inner rings: the court cards' thirty-degree spans, then the Princesses' quadrants.",
        solid: "The five solids and how many cards take each. A card's solid follows its element; the planetary Majors keep the Dodecahedron.",
        dual: "Put a corner at the centre of each face of a solid and the corners make its dual. The Cube of Space's dual is an octahedron whose six corners are the centres of the cube's six faces: the six directions, each held by a double letter, with Tav at the centre both share. Below, the three dual pairs and how many cards take each solid. The report notes neighbouring cards whose solids are duals.",
        grid: "The sixteen court cards: the rank gives the first element (Knight Fire, Queen Water, Prince Air, Princess Earth), the suit the second.",
    };
    // One card's caption: its solid and dual, and its corner of the octahedron if it has one.
    const FACES = ["Up (Zenith)", "Down (Nadir)", "East", "West", "North", "South"];
    function dualNote(c) {
        if (!c.solid) return "";
        const other = A.dualOf(c.solid.name), own = A.solidName(c.solid.name);
        let t = other === c.solid.name
            ? `The ${own} is its own dual: turned through its centre it makes another ${own}.`
            : `The ${own}'s dual is the ${A.solidName(other)}; in a reading, a neighbouring card with that solid makes a dual pair.`;
        if (FACES.includes(c.cube.place) && !c.cube.derived) t += ` The card's letter holds the ${c.cube.place} face, one corner of the cube's dual octahedron.`;
        return t;
    }
    const order = [...pickEl.options].map(o => o.value).filter(v => v !== "");

    // ---------- Decan tour: the "Play" button under the zodiac walks a hand round all 36
    // decans from 0° Aries, counter-clockwise, lighting each decan, its sign and its small card.
    // It starts only when pressed; with reduced motion the hand jumps instead of sweeping.
    const STEP_MS = 1600, SVG_NS = "http://www.w3.org/2000/svg";
    const playBtn = $("ringPlay"), stepEl = $("ringStep");
    let tour = null, resumeAt = 0;   // tour is { i, timer, turn } while playing
    function tourFrame() {
        const svg = $("mapRing").querySelector("svg"), i = tour.i;
        const decs = svg.querySelectorAll(".a-dec"), bands = svg.querySelectorAll(".a-band");
        decs.forEach((g, k) => g.classList.toggle("on", k === i));
        bands.forEach((b, k) => b.classList.toggle("on", k === Math.floor(i / 3)));
        let hand = svg.querySelector(".a-hand");
        if (!hand) {
            const r = 118;   // to the inner edge of the decan ring (atlas.js ring, full size)
            hand = document.createElementNS(SVG_NS, "g");
            hand.setAttribute("class", "a-hand");
            hand.innerHTML = `<line x1="0" y1="0" x2="-${r}" y2="0"/><circle r="5"/>`;
            svg.appendChild(hand);
            hand.getBoundingClientRect();   // lay out once, so the first turn sweeps from 0°
        }
        // counter-clockwise from 9 o'clock, as the wheel is drawn; the angle only grows, so the
        // hand carries on past Pisces into Aries instead of swinging back
        tour.turn = tour.turn === null ? i * 10 + 5 : tour.turn + 10;
        hand.style.transform = `rotate(${-tour.turn}deg)`;
        const d = data.decans[i], card = Number.isInteger(d.index) ? data.cards[d.index] : null;
        stepEl.textContent = `${d.sign} ${i % 3 * 10}°–${i % 3 * 10 + 10}°, ruled by ${d.ruler}: ${card ? card.title : d.card} (${i + 1} of 36 from 0° Aries)`;
    }
    function stopTour() {
        if (!tour) return;
        clearInterval(tour.timer);
        resumeAt = (tour.i + 1) % 36;
        tour = null;
        playBtn.setAttribute("aria-pressed", "false");
        playBtn.innerHTML = "&#9654; Play the 36 decans";
        stepEl.textContent = "";
    }
    function startTour() {
        $("mapRing").innerHTML = A.ring(null, data);   // whole wheel, nothing marked, while it plays
        $("capRing").innerHTML = esc(WHOLE.ring);
        tour = { i: resumeAt, turn: null };
        playBtn.setAttribute("aria-pressed", "true");
        playBtn.innerHTML = "&#10074;&#10074; Pause";
        tourFrame();
        tour.timer = setInterval(() => { tour.i = (tour.i + 1) % 36; tourFrame(); }, STEP_MS);
    }
    playBtn.addEventListener("click", () => {
        if (tour) show(pickEl.value, false); else startTour();   // show() pauses the tour
    });

    function show(i, push) {
        stopTour();
        const n = Number.parseInt(i, 10);   // an index from the menu or a map; anything else shows the whole deck
        const c = Number.isInteger(n) && n >= 0 && n < data.cards.length ? data.cards[n] : null;
        pickEl.value = c ? String(n) : "";
        $("mapTree").innerHTML = A.tree(c, data);
        $("mapCube").innerHTML = A.cube(c, data);
        $("mapRing").innerHTML = A.ring(c, data);
        $("mapSolid").innerHTML = A.solid(c, data);
        $("mapDual").innerHTML = A.dual(c, data);
        $("mapGrid").innerHTML = A.grid(c, data);
        const cap = (key, note, extra) => c ? `${esc(note || "Not placed in this system.")}${extra ? `<span class="muted">${extra}</span>` : ""}` : esc(WHOLE[key]);
        $("capTree").innerHTML = cap("tree", c && c.tree.note);
        $("capCube").innerHTML = cap("cube", c && c.cube.note, c && c.cube.derived ? "Dashed: the card is linked through its sign, not placed on the cube itself." : "");
        $("capRing").innerHTML = cap("ring", c && c.zodiac.note);
        $("capSolid").innerHTML = cap("solid", c && c.solid && `${c.solid.note} Its dual is the ${c.solid.dual.replace(" (Self-Dual)", ", which is its own dual")}.`);
        $("capDual").innerHTML = cap("dual", c && dualNote(c));
        $("capGrid").innerHTML = cap("grid", c && c.grid.note);
        $("mapSummary").innerHTML = c
            ? `<strong>${esc(c.title)}</strong><span>${esc(c.attribution)}${c.letter ? " · " + esc(c.letter) : ""} · ${esc(c.element)}</span>` +
              (c.colour && c.colour.startsWith("#") ? `<span><span class="swatch" style="background:${esc(c.colour)}"></span>King Scale: ${esc(c.colour_name)}</span>` : "")
            : `<span class="muted">Whole deck: every place labelled, nothing marked.</span>`;
        $("systemCard").value = c ? c.title : "";
        if (push) {
            const u = new URL(location.href);
            if (c) u.searchParams.set("card", c.title); else u.searchParams.delete("card");
            history.replaceState(null, "", u);
        }
    }
    const step = d => {
        const at = order.indexOf(pickEl.value);
        show(order[(at + d + order.length + (at < 0 && d > 0 ? 1 : 0)) % order.length], true);
    };
    pickEl.addEventListener("change", () => show(pickEl.value, true));
    $("prevCard").addEventListener("click", () => step(-1));
    $("nextCard").addEventListener("click", () => step(1));
    $("systemPick").addEventListener("change", () => $("systemForm").submit());
    const jump = el => { show(el.dataset.pick, true); if (el.closest("table.matrix")) $("pickTitle").scrollIntoView({ behavior: "smooth" }); };
    document.addEventListener("click", e => { const el = e.target.closest("[data-pick]"); if (el) jump(el); });
    document.addEventListener("keydown", e => {
        const el = e.target.closest && e.target.closest("[data-pick]");
        if (el && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); jump(el); }
    });
    show(pickEl.value, false);
})();
