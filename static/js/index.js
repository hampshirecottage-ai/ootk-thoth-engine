// Shared by the start page (draw from a seed) and /pick (pick by hand).
const positionsData = JSON.parse(document.getElementById("positionsData").textContent);
const form = document.getElementById("readingForm");
const $ = id => document.getElementById(id);
const manual = form.elements["draw_mode"].value === "manual";
let activeCardList = [];

// ---------- remembered settings (per browser) ----------
// The draw mode is the page itself, so it is not part of the remembered settings.
// The significator itself is worked out from the sig_* choices; the birth date is never kept.
const SETTING_FIELDS = ["spread_key", "seed", "sig_method", "sig_about", "sig_basis", "sig_rank", "sig_suit",
                        "sig_topic", "sig_any",
                        "mapping_system", "framework"];
const LAST_KEY = "ootk.lastSettings.v1";

function readStore(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || "null") || fallback; } catch (e) { return fallback; }
}
function writeStore(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (e) { return false; }
}

// Only fields on this page: /pick has no significator picker, so it keeps the saved choice.
function getSettings() {
    const fd = new FormData(form), out = {};
    SETTING_FIELDS.forEach(f => { if (form.elements[f]) out[f] = fd.get(f) || ""; });
    return out;
}
function applySettings(s) {
    SETTING_FIELDS.forEach(f => {
        if (!(f in s)) return;
        const els = form.elements[f];
        if (els instanceof RadioNodeList) {
            els.forEach(r => r.checked = r.value === s[f]);
        } else if (els) {
            els.value = s[f];
        }
    });
    updateSpread();
}
// Remember settings for next time, but not the seed: a new visit draws fresh cards.
function rememberSettings() { writeStore(LAST_KEY, Object.assign(readStore(LAST_KEY, {}), getSettings(), { seed: "" })); }

function spreadPositions() { return positionsData[$("spreadSelect").value]; }
function hasSigPosition() { const p = spreadPositions(); return p.length > 0 && /significator/i.test(p[0]); }
function updateSpread() { if (manual) updateSlots(); updateSignificator(); updateMoreSummary(); }

// ---------- More options: a one-line summary of what is folded away ----------
function updateMoreSummary() {
    const short = el => el.options[el.selectedIndex].text.split(" (")[0].replace(/^\d+\.\s*/, "");
    const parts = [short($("mappingSelect")), $("frameworkSelect").value === "auto" ? "" : short($("frameworkSelect"))];
    if (!manual && $("seedInput").value.trim()) parts.unshift(`seed ${$("seedInput").value.trim()}`);
    $("moreSummary").textContent = "· " + parts.filter(Boolean).join(" · ");
}
$("moreOptions").addEventListener("input", updateMoreSummary);
$("moreOptions").addEventListener("change", updateMoreSummary);

// ---------- significator ----------
// Seed mode: Book T description asked as a few questions (who it is about, person or matter,
// temperament or topic for the suit, stage of life for the rank), birth date, or any card.
// Only the resulting card title is sent. On /pick it is the first card placed.
const birthSpans = manual ? [] : JSON.parse($("birthSpans").textContent);
const sigPreviews = manual ? {} : JSON.parse($("sigPreviews").textContent);

function birthCard(isoDate) {
    const [, m, d] = isoDate.split("-").map(Number);
    let card = birthSpans[birthSpans.length - 1][1];     // early January: Queen of Disks
    birthSpans.forEach(([[sm, sd], title]) => { if (m > sm || (m === sm && d >= sd)) card = title; });
    return card;
}

const radioValue = name => form.elements[name] ? form.elements[name].value : "";
function clearRadios(names) { names.forEach(n => form.elements[n].forEach(r => r.checked = false)); }

// Shows each Describe question once the one before it is answered, worded for "me" or
// "someone else". Returns the suit and rank chosen so far.
function updateDescribe() {
    // Settings saved before the questions existed have a rank and suit but no answers here.
    if (!radioValue("sig_about") && (radioValue("sig_rank") || radioValue("sig_suit"))) {
        form.elements["sig_about"].value = "me";
        form.elements["sig_basis"].value = "person";
    }
    const about = radioValue("sig_about"), basis = radioValue("sig_basis");
    const suit = basis === "matter" ? radioValue("sig_topic") : radioValue("sig_suit");
    const show = { about: true, basis: !!about, suit: basis === "person", topic: basis === "matter", rank: !!suit };
    document.querySelectorAll(".sig-q[data-q]").forEach(q => q.hidden = !show[q.dataset.q]);
    document.querySelectorAll("#sigPicker [data-me]").forEach(t => t.textContent = about === "other" ? t.dataset.other : t.dataset.me);
    return { suit, rank: show.rank ? radioValue("sig_rank") : "" };
}

function chosenSignificator() {
    const method = form.elements["sig_method"].value;
    if (method === "describe") {
        const { rank, suit } = updateDescribe();
        return rank && suit ? `${rank} of ${suit}` : "";
    }
    if (method === "birthday") return $("sigBirthday").value ? birthCard($("sigBirthday").value) : "";
    return $("sigAny").value.trim();
}

// Only the sixteen court cards have a preview. The title shown is the page's own, never the
// typed text, and a typed "__proto__" or "toString" finds nothing.
function showPreview(card) {
    const [title, p] = Object.entries(sigPreviews).find(([t]) => t === card) || [];
    $("sigPreview").hidden = !p;
    if (!p) return;
    $("sigPreviewImg").src = p.img;
    $("sigPreviewImg").alt = title;
    $("sigPreviewTitle").textContent = title;
    $("sigPreviewElement").textContent = p.element;
    $("sigPreviewPlace").textContent = p.place;
    $("sigPreviewArt").textContent = p.art;
}

function updateSignificator() {
    const needs = hasSigPosition();
    if (manual) { $("sigNone").hidden = !needs; return; }
    $("sigBox").hidden = !needs;
    const method = form.elements["sig_method"].value;
    document.querySelectorAll("[data-sig]").forEach(el => el.hidden = el.dataset.sig !== method);
    const card = needs ? chosenSignificator() : "";
    $("significatorInput").value = card;
    $("sigResult").textContent = "";
    if (needs) {
        const strong = document.createElement("strong");
        strong.textContent = card || "not chosen yet";
        $("sigResult").append("Significator: ", strong);
        if (card && method === "birthday") $("sigResult").append(" (a birthday on the first or last day of a span may belong to the card next to it)");
    }
    showPreview(card);
    $("sigResult").hidden = !$("sigPreview").hidden;     // the preview names the card itself
}

if (!manual) {
    // Change: back to the first question (Describe) or to the empty field.
    $("sigRestart").addEventListener("click", () => {
        const method = form.elements["sig_method"].value;
        if (method === "describe") clearRadios(["sig_about", "sig_basis", "sig_suit", "sig_topic", "sig_rank"]);
        else if (method === "birthday") $("sigBirthday").value = "";
        else $("sigAny").value = "";
        updateSignificator();
        const first = $("sigPicker").querySelector(`[data-sig="${method}"] input`);
        if (first) first.focus();
    });
    $("sigPicker").addEventListener("input", updateSignificator);
    $("sigPicker").addEventListener("change", updateSignificator);
}

// ---------- start page: draw from a seed ----------
if (!manual) {
    $("randomSeed").addEventListener("click", () => {
        $("seedInput").value = String(100000 + Math.floor(Math.random() * 900000));
        updateMoreSummary();
    });
}

// ---------- /pick: spread board and card catalog ----------
function updateSlots() {
    const positions = spreadPositions();
    const slotsContainer = $("spreadSlots");
    slotsContainer.innerHTML = "";
    activeCardList = activeCardList.slice(0, positions.length);
    positions.forEach((pos, idx) => {
        const div = document.createElement("div");
        div.className = "slot";
        const name = document.createElement("span"); name.className = "pos-name"; name.textContent = pos;
        const card = document.createElement("span"); card.className = "card-selected"; card.id = `slot-${idx}`;
        card.textContent = activeCardList[idx] || "[ Empty ]";
        div.append(name, card);
        slotsContainer.appendChild(div);
    });
    syncHiddenInput();
}

// The full Opening of the Key reshuffles for each operation, so a card may fall again in a
// later operation but only once within the operation being filled.
function opOf(pos) { const m = /^\[Op (\d+)\]/.exec(pos || ""); return m ? Number(m[1]) : 1; }
function usedInCurrentOp() {
    const positions = spreadPositions();
    const op = opOf(positions[Math.min(activeCardList.length, positions.length - 1)]);
    return activeCardList.filter((_, i) => opOf(positions[i]) === op);
}

function selectCard(cardTitle) {
    const positions = spreadPositions();
    if (usedInCurrentOp().includes(cardTitle)) return;
    if (activeCardList.length >= positions.length) { alert("All spread slots are filled."); return; }
    activeCardList.push(cardTitle);
    updateSlots();
}

function syncHiddenInput() {
    const positions = spreadPositions();
    $("selectedCardsInput").value = activeCardList.join(",");
    $("slotCount").textContent = `${activeCardList.length} / ${positions.length}`;
    const used = usedInCurrentOp();
    document.querySelectorAll(".card-item").forEach(el => el.classList.toggle("used", used.includes(el.dataset.title)));
    $("pickCount").textContent = `${activeCardList.length} / ${positions.length}`;
    const n = activeCardList.length;
    $("pickLast").textContent = n ? `${activeCardList[n - 1]} → ${positions[n - 1]}` : "Tap cards in order";
}

if (manual) {
    $("cardGrid").addEventListener("click", e => {
        const item = e.target.closest(".card-item");
        if (item) selectCard(item.dataset.title);
    });
    document.querySelectorAll("#undoCard, #pickUndo").forEach(b => b.addEventListener("click", () => { activeCardList.pop(); updateSlots(); }));
    $("clearCards").addEventListener("click", () => { activeCardList = []; updateSlots(); });
    $("search").addEventListener("input", () => {
        const query = $("search").value.toLowerCase();
        document.querySelectorAll(".card-item").forEach(item => {
            item.style.display = item.dataset.title.toLowerCase().includes(query) ? "flex" : "none";
        });
    });
}

// ---------- both pages ----------
$("spreadSelect").addEventListener("change", updateSpread);
// Carry the current settings over when switching between the two pages.
$("modeSwitch").addEventListener("click", rememberSettings);

form.addEventListener("submit", e => {
    if (manual) {
        const n = spreadPositions().length;
        if (activeCardList.length !== n) { e.preventDefault(); alert(`Pick ${n} cards first (${activeCardList.length} chosen).`); return; }
    } else if (hasSigPosition() && !$("significatorInput").value) {
        e.preventDefault();
        alert("This spread needs a significator. Choose one under Significator.");
        $("sigBox").scrollIntoView({ block: "center" });
        return;
    }
    rememberSettings();
});

$("themeToggle").addEventListener("click", () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
    try { localStorage.setItem("ootk.theme", root.dataset.theme); } catch (e) {}
});

// A link such as /?spread=3#readingForm (from the Start here page) picks that spread.
const linkedSpread = new URLSearchParams(location.search).get("spread");
applySettings(Object.assign(readStore(LAST_KEY, {}),
                            linkedSpread in positionsData ? { spread_key: linkedSpread } : {}));

// The question box wraps onto two lines, but Enter still draws the cards (Shift+Enter for a new line).
$("topicInput").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        e.target.form.requestSubmit();
    }
});
