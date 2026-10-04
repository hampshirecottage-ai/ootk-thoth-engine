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
        grid: "The sixteen court cards: the rank gives the first element (Knight Fire, Queen Water, Prince Air, Princess Earth), the suit the second.",
    };
    const order = [...pickEl.options].map(o => o.value).filter(v => v !== "");

    function show(i, push) {
        const n = Number.parseInt(i, 10);   // an index from the menu or a map; anything else shows the whole deck
        const c = Number.isInteger(n) && n >= 0 && n < data.cards.length ? data.cards[n] : null;
        pickEl.value = c ? String(n) : "";
        $("mapTree").innerHTML = A.tree(c, data);
        $("mapCube").innerHTML = A.cube(c, data);
        $("mapRing").innerHTML = A.ring(c, data);
        $("mapSolid").innerHTML = A.solid(c, data);
        $("mapGrid").innerHTML = A.grid(c, data);
        const cap = (key, note, extra) => c ? `${esc(note || "Not placed in this system.")}${extra ? `<span class="muted">${extra}</span>` : ""}` : esc(WHOLE[key]);
        $("capTree").innerHTML = cap("tree", c && c.tree.note);
        $("capCube").innerHTML = cap("cube", c && c.cube.note, c && c.cube.derived ? "Dashed: the card is linked through its sign, not placed on the cube itself." : "");
        $("capRing").innerHTML = cap("ring", c && c.zodiac.note);
        $("capSolid").innerHTML = cap("solid", c && c.solid && `${c.solid.note} Its dual is the ${c.solid.dual.replace(" (Self-Dual)", ", which is its own dual")}.`);
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
