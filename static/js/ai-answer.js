// "Your AI's answer" on the report: paste the AI's interpretation back in and read it next to
// the cards. The answer stays in this browser (localStorage, one entry per report address); it
// is never sent to the site. Card names in it open the card panel (report.js), and a short
// check lists the cards it names that this reading did not draw.

// ---- Card names (pure, so tests can run it with node) ----
// Thoth names first, then the common Waite names an AI may use. Majors are matched with their
// capital letters (so "the art of" or "death of an idea" in lower case is left alone); pips and
// courts in any case. Waite Kings and Pages are left out: which Thoth court they mean depends
// on the system, so linking them could point at the wrong card.
const MAJOR_NAMES = {
    "the fool": ["The Fool"],
    "the magus": ["The Magus", "The Magician"],
    "the priestess": ["The High Priestess", "The Priestess", "High Priestess"],
    "the empress": ["The Empress"],
    "the emperor": ["The Emperor"],
    "the hierophant": ["The Hierophant"],
    "the lovers": ["The Lovers"],
    "the chariot": ["The Chariot"],
    "adjustment": ["Adjustment", "Justice"],
    "the hermit": ["The Hermit"],
    "fortune": ["The Wheel of Fortune", "Wheel of Fortune", "Fortune"],
    "lust": ["Lust"],
    "the hanged man": ["The Hanged Man", "Hanged Man"],
    "death": ["Death"],
    "art": ["Art", "Temperance"],
    "the devil": ["The Devil"],
    "the tower": ["The Tower"],
    "the star": ["The Star"],
    "the moon": ["The Moon"],
    "the sun": ["The Sun"],
    "the aeon": ["The Aeon", "Aeon", "Judgement", "Judgment"],
    "the universe": ["The Universe", "The World"],
};
const RANKS = { ace: "ace", one: "ace", "1": "ace", two: "2", three: "3", four: "4", five: "5", six: "6",
                seven: "7", eight: "8", nine: "9", ten: "10" };
for (let n = 2; n <= 10; n++) RANKS[String(n)] = String(n);
const SUITS = { wands: "wands", cups: "cups", swords: "swords", disks: "disks", discs: "disks",
                pentacles: "disks", coins: "disks" };
const COURTS = ["princess", "prince", "queen", "knight"];

const reEscape = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const anyCase = s => s.replace(/[a-z]/gi, c => `[${c.toLowerCase()}${c.toUpperCase()}]`);
const byLength = (a, b) => b.length - a.length;

const majorAlias = {};
Object.entries(MAJOR_NAMES).forEach(([key, names]) => names.forEach(n => { majorAlias[n] = key; }));
const majorPart = Object.keys(majorAlias).sort(byLength).map(reEscape).join("|");
const rankPart = Object.keys(RANKS).sort(byLength).map(anyCase).join("|");
const suitPart = Object.keys(SUITS).sort(byLength).map(anyCase).join("|");
const courtPart = COURTS.map(anyCase).join("|");
const CARD_RE = new RegExp(
    `\\b(?:(${majorPart})|(${rankPart})\\s+${anyCase("of")}\\s+(?:the\\s+)?(${suitPart})|(${courtPart})\\s+${anyCase("of")}\\s+(?:the\\s+)?(${suitPart}))\\b`,
    "g");

// A deck title as the site stores it ("I - The Magus", "2 of Disks - Change", "Knight of Wands")
// to the key the matcher uses ("the magus", "2 of disks", "knight of wands").
function cardKey(title) {
    return String(title).replace(/^[0IVXL]+ - /, "").replace(/ - .*$/, "").trim().toLowerCase();
}

// Splits text into plain parts and card names: [{text}, {text, key}, ...].
function findCards(text) {
    const parts = [];
    let last = 0;
    for (const m of text.matchAll(CARD_RE)) {
        let key;
        if (m[1]) key = majorAlias[m[1]];
        else if (m[2]) key = `${RANKS[m[2].toLowerCase()]} of ${SUITS[m[3].toLowerCase()]}`;
        else key = `${m[4].toLowerCase()} of ${SUITS[m[5].toLowerCase()]}`;
        if (m.index > last) parts.push({ text: text.slice(last, m.index) });
        parts.push({ text: m[0], key });
        last = m.index + m[0].length;
    }
    if (last < text.length) parts.push({ text: text.slice(last) });
    return parts;
}

// What the answer names, against the cards drawn: which drawn cards it mentions, which it
// doesn't, and which cards it names that were not drawn (keys, in order of first mention).
function checkAnswer(text, drawnKeys) {
    const drawn = new Set(drawnKeys);
    const named = [];
    findCards(text).forEach(p => { if (p.key && !named.includes(p.key)) named.push(p.key); });
    return {
        mentioned: [...drawn].filter(k => named.includes(k)),
        missing: [...drawn].filter(k => !named.includes(k)),
        notDrawn: named.filter(k => !drawn.has(k)),
    };
}

// The card's name to show for a key: the first name in MAJOR_NAMES, or "2 of Disks".
function keyLabel(key) {
    if (MAJOR_NAMES[key]) return MAJOR_NAMES[key][0];
    return key.replace(/\b[a-z]/g, c => c.toUpperCase()).replace(/ Of /, " of ");
}

if (typeof module !== "undefined") module.exports = { findCards, checkAnswer, cardKey, keyLabel };

// ---- Page ----
(function () {
    if (typeof document === "undefined") return;
    const box = document.getElementById("aiAnswer");
    if (!box) return;
    const MAX = 200000;
    const input = document.getElementById("answerInput");
    const view = document.getElementById("answerView");
    const body = document.getElementById("answerBody");
    const check = document.getElementById("answerCheck");
    const editor = document.getElementById("answerEditor");
    const status = document.getElementById("answerStatus");
    // Kept per report address: a saved report's /report/<link>, or a shared /reading?seed=...
    // A report shown straight after a failed save has no address of its own, so nothing is kept.
    const keepable = location.pathname !== "/generate_report";
    const storeKey = `ootk.answer:${location.pathname}${location.search}`;

    // The reading's cards, by key, to the first position that holds each (for the card panel).
    const cards = JSON.parse(document.getElementById("cardDetails").textContent);
    const firstIndex = {};
    cards.forEach((c, i) => { const k = cardKey(c.title); if (!(k in firstIndex)) firstIndex[k] = i; });

    function load() {
        try { const v = JSON.parse(localStorage.getItem(storeKey) || "null"); return v && typeof v.text === "string" ? v : null; }
        catch (e) { return null; }
    }
    function store(text) {
        if (!keepable) return false;
        try {
            if (text) localStorage.setItem(storeKey, JSON.stringify({ text, saved: new Date().toISOString() }));
            else localStorage.removeItem(storeKey);
            return true;
        } catch (e) { return false; }
    }

    // Inline text: **bold** and card names. Built with DOM nodes only, never innerHTML, so
    // nothing in a pasted answer can run as code on the page.
    function inline(parent, text) {
        text.split(/(\*\*[^*]+\*\*|__[^_]+__)/).forEach(chunk => {
            if (!chunk) return;
            let target = parent;
            if (/^(\*\*|__).+(\*\*|__)$/.test(chunk)) {
                target = parent.appendChild(document.createElement("strong"));
                chunk = chunk.slice(2, -2);
            }
            findCards(chunk.replace(/(^|\s)[*_](\S)/g, "$1$2").replace(/(\S)[*_](?=\s|$|[.,;:!?])/g, "$1")).forEach(p => {
                if (p.key && p.key in firstIndex) {
                    const b = document.createElement("button");
                    Object.assign(b, { type: "button", className: "card-ref", textContent: p.text, title: `Open ${cards[firstIndex[p.key]].title}` });
                    b.dataset.card = firstIndex[p.key];
                    target.appendChild(b);
                } else if (p.key) {
                    const s = document.createElement("span");
                    Object.assign(s, { className: "card-ref not-drawn", textContent: p.text, title: "Not drawn in this reading" });
                    target.appendChild(s);
                } else target.appendChild(document.createTextNode(p.text));
            });
        });
    }

    // A light reading of the Markdown AIs write: headings, lists, tables, rules, paragraphs.
    function render(text) {
        body.replaceChildren();
        const lines = text.replace(/\r\n?/g, "\n").split("\n");
        let para = [], list = null, table = null;
        const flushPara = () => {
            if (!para.length) return;
            const p = body.appendChild(document.createElement("p"));
            para.forEach((l, i) => { if (i) p.appendChild(document.createElement("br")); inline(p, l); });
            para = [];
        };
        const flushAll = () => { flushPara(); list = null; table = null; };
        for (const raw of lines) {
            const line = raw.trimEnd();
            let m;
            if (!line.trim()) { flushAll(); continue; }
            if (/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { flushAll(); body.appendChild(document.createElement("hr")); continue; }
            if ((m = line.match(/^\s*(#{1,6})\s+(.*)$/))) {
                flushAll();
                inline(body.appendChild(document.createElement(m[1].length <= 2 ? "h3" : "h4")), m[2].replace(/#+\s*$/, ""));
                continue;
            }
            if (/^\s*\|.*\|\s*$/.test(line)) {
                flushPara(); list = null;
                const cells = line.trim().slice(1, -1).split("|").map(c => c.trim());
                if (cells.every(c => /^:?-{2,}:?$/.test(c))) continue;     // the header rule
                if (!table) table = body.appendChild(document.createElement("div")).appendChild(document.createElement("table"));
                table.parentNode.className = "answer-table";
                const tr = table.appendChild(document.createElement("tr"));
                cells.forEach(c => inline(tr.appendChild(document.createElement(table.rows.length === 1 ? "th" : "td")), c));
                continue;
            }
            if ((m = line.match(/^\s*(?:([-*+])|(\d+)[.)])\s+(.*)$/))) {
                flushPara(); table = null;
                const tag = m[1] ? "ul" : "ol";
                if (!list || list.tagName.toLowerCase() !== tag) list = body.appendChild(document.createElement(tag));
                inline(list.appendChild(document.createElement("li")), m[3]);
                continue;
            }
            if ((m = line.match(/^\s*>\s?(.*)$/))) {
                flushAll();
                inline(body.appendChild(document.createElement("blockquote")), m[1]);
                continue;
            }
            list = null; table = null;
            para.push(line.trim());
        }
        flushAll();
    }

    function listOf(keys) {
        return keys.map(keyLabel).join(", ");
    }

    function showCheck(text) {
        const r = checkAnswer(text, Object.keys(firstIndex));
        const total = Object.keys(firstIndex).length;
        const lines = [];
        let line = `It names ${r.mentioned.length} of the ${total} card${total === 1 ? "" : "s"} drawn.`;
        if (r.missing.length && r.missing.length <= 12) line += ` Not named: ${listOf(r.missing)}.`;
        lines.push(line);
        if (r.notDrawn.length) {
            lines.push(`It also names ${r.notDrawn.length === 1 ? "a card" : "cards"} not drawn here: ${listOf(r.notDrawn)}. ` +
                "That can be fine, since the prompt also mentions ruling cards, decan cards and birth cards. " +
                "Check it hasn't put one of them in a position of this reading.");
        }
        check.replaceChildren(...lines.map(t => Object.assign(document.createElement("p"), { textContent: t })));
        check.classList.toggle("warn", r.notDrawn.length > 0);
    }

    let current = "";
    function show(saved) {
        const text = saved && saved.text;
        current = text || "";
        box.classList.toggle("no-print", !text);
        view.hidden = !text;
        editor.hidden = !!text;
        if (!text) { status.textContent = ""; return; }
        render(text);
        showCheck(text);
        status.textContent = keepable
            ? "Kept in this browser only. It isn't sent to the site, and the share link doesn't carry it."
            : "This reading has no link of its own, so the answer goes when you leave the page.";
    }

    document.getElementById("answerSave").addEventListener("click", () => {
        const text = input.value.trim().slice(0, MAX);
        if (!text) { input.focus(); return; }
        const kept = store(text);
        show({ text });
        if (keepable && !kept) status.textContent = "This browser wouldn't keep it (private window or full storage). It goes when you leave the page.";
        box.scrollIntoView({ block: "start", behavior: "smooth" });
    });
    document.getElementById("answerEdit").addEventListener("click", () => {
        input.value = current;
        view.hidden = true;
        editor.hidden = false;
        input.focus();
    });
    document.getElementById("answerRemove").addEventListener("click", () => {
        if (!confirm("Remove the AI's answer from this page?")) return;
        store("");
        input.value = "";
        show(null);
    });
    document.getElementById("answerCopy").addEventListener("click", e => {
        if (current && typeof copyText === "function") copyText(current, e.currentTarget);
    });

    show(load());
})();
