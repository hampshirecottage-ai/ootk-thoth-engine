const positionsData = JSON.parse(document.getElementById("positionsData").textContent);
const form = document.getElementById("readingForm");
let activeCardList = [];

// ---------- presets & remembered settings (per browser) ----------
const SETTING_FIELDS = ["spread_key", "draw_mode", "seed", "significator", "mapping_system", "framework", "output_format"];
const BUILTIN_PRESETS = {
    "Full OOTK · Golden Dawn": { spread_key: "12", draw_mode: "seed", seed: "", mapping_system: "golden_dawn", framework: "auto", output_format: "visual" },
    "Full OOTK · French/Egyptian": { spread_key: "12", draw_mode: "seed", seed: "", mapping_system: "french_egyptian", framework: "auto", output_format: "visual" },
    "Daily card": { spread_key: "1", draw_mode: "seed", seed: "", mapping_system: "golden_dawn", framework: "auto", output_format: "visual" },
};
const PRESET_KEY = "ootk.presets.v1", LAST_KEY = "ootk.lastSettings.v1";

function readStore(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || "null") || fallback; } catch (e) { return fallback; }
}
function writeStore(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (e) { return false; }
}

function getSettings() {
    const fd = new FormData(form), out = {};
    SETTING_FIELDS.forEach(f => out[f] = fd.get(f) || "");
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
    updateMode();
    updateSlots();
}

function renderPresets(selected) {
    const sel = document.getElementById("presetSelect");
    const user = readStore(PRESET_KEY, {});
    sel.innerHTML = '<option value="">Choose a preset…</option>';
    const add = (group, names, prefix) => {
        if (!names.length) return;
        const og = document.createElement("optgroup"); og.label = group;
        names.forEach(n => { const o = document.createElement("option"); o.value = prefix + n; o.textContent = n; og.appendChild(o); });
        sel.appendChild(og);
    };
    add("Built in", Object.keys(BUILTIN_PRESETS), "b:");
    add("Saved", Object.keys(user).sort(), "u:");
    sel.value = selected || "";
    document.getElementById("deletePreset").disabled = !sel.value.startsWith("u:");
}

document.getElementById("presetSelect").addEventListener("change", e => {
    const v = e.target.value;
    if (!v) return;
    const preset = v.startsWith("b:") ? BUILTIN_PRESETS[v.slice(2)] : readStore(PRESET_KEY, {})[v.slice(2)];
    if (preset) applySettings(preset);
    document.getElementById("deletePreset").disabled = !v.startsWith("u:");
});
document.getElementById("savePreset").addEventListener("click", () => {
    const name = (prompt("Name this preset (a blank seed draws a new one each time):") || "").trim();
    if (!name) return;
    const user = readStore(PRESET_KEY, {});
    user[name] = getSettings();
    if (!writeStore(PRESET_KEY, user)) { alert("This browser is not letting the page save presets."); return; }
    renderPresets("u:" + name);
});
document.getElementById("deletePreset").addEventListener("click", () => {
    const v = document.getElementById("presetSelect").value;
    if (!v.startsWith("u:")) return;
    const user = readStore(PRESET_KEY, {});
    delete user[v.slice(2)];
    writeStore(PRESET_KEY, user);
    renderPresets("");
});

// ---------- draw mode ----------
function drawMode() { return form.elements["draw_mode"].value; }

function updateMode() {
    const seedMode = drawMode() === "seed";
    document.getElementById("seedRow").style.display = seedMode ? "" : "none";
    document.getElementById("manualBoard").style.display = seedMode ? "none" : "";
    document.getElementById("seedNote").style.display = seedMode ? "" : "none";
    document.getElementById("deckPanel").classList.toggle("disabled", seedMode);
    document.getElementById("catalogHint").style.display = seedMode ? "" : "none";
    document.body.classList.toggle("manual", !seedMode);
    updateSeedNote();
}
function updateSeedNote() {
    const key = document.getElementById("spreadSelect").value;
    const seed = document.getElementById("seedInput").value.trim();
    const n = positionsData[key].length;
    document.getElementById("seedNote").innerHTML = seed
        ? `${n} card${n === 1 ? "" : "s"} will be drawn from seed <strong>${seed.replace(/</g, "&lt;")}</strong>. The same seed and settings always give the same reading.`
        : `${n} card${n === 1 ? "" : "s"} will be drawn from a new seed. The report shows the seed so you can repeat the reading.`;
}

form.querySelectorAll('input[name="draw_mode"]').forEach(r => r.addEventListener("change", updateMode));
document.getElementById("seedInput").addEventListener("input", updateSeedNote);
document.getElementById("randomSeed").addEventListener("click", () => {
    document.getElementById("seedInput").value = String(100000 + Math.floor(Math.random() * 900000));
    updateSeedNote();
});

// ---------- manual board ----------
function updateSlots() {
    const key = document.getElementById("spreadSelect").value;
    const positions = positionsData[key];
    const slotsContainer = document.getElementById("spreadSlots");
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
    updateSeedNote();
}

function selectCard(cardTitle) {
    if (drawMode() !== "manual") return;
    const positions = positionsData[document.getElementById("spreadSelect").value];
    if (activeCardList.includes(cardTitle)) return;
    if (activeCardList.length >= positions.length) { alert("All spread slots are filled."); return; }
    activeCardList.push(cardTitle);
    updateSlots();
}

function syncHiddenInput() {
    const positions = positionsData[document.getElementById("spreadSelect").value];
    document.getElementById("selectedCardsInput").value = activeCardList.join(",");
    document.getElementById("slotCount").textContent = drawMode() === "manual"
        ? `${activeCardList.length} / ${positions.length}` : `${positions.length} card${positions.length === 1 ? "" : "s"}`;
    document.querySelectorAll(".card-item").forEach(el => el.classList.toggle("used", activeCardList.includes(el.dataset.title)));
    document.getElementById("pickCount").textContent = `${activeCardList.length} / ${positions.length}`;
    const n = activeCardList.length;
    document.getElementById("pickLast").textContent = n ? `${activeCardList[n - 1]} → ${positions[n - 1]}` : "Tap cards in order";
}

document.getElementById("cardGrid").addEventListener("click", e => {
    const item = e.target.closest(".card-item");
    if (item) selectCard(item.dataset.title);
});
document.querySelectorAll("#undoCard, #pickUndo").forEach(b => b.addEventListener("click", () => { activeCardList.pop(); updateSlots(); }));
document.getElementById("clearCards").addEventListener("click", () => { activeCardList = []; updateSlots(); });
document.getElementById("spreadSelect").addEventListener("change", updateSlots);
document.getElementById("search").addEventListener("input", () => {
    const query = document.getElementById("search").value.toLowerCase();
    document.querySelectorAll(".card-item").forEach(item => {
        item.style.display = item.dataset.title.toLowerCase().includes(query) ? "flex" : "none";
    });
});

form.addEventListener("submit", e => {
    if (drawMode() === "manual") {
        const n = positionsData[document.getElementById("spreadSelect").value].length;
        if (activeCardList.length !== n) { e.preventDefault(); alert(`Pick ${n} cards first (${activeCardList.length} chosen).`); return; }
    }
    // Remember settings for next time, but not the seed: a new visit draws fresh cards.
    writeStore(LAST_KEY, Object.assign(getSettings(), { seed: "" }));
});

document.getElementById("themeToggle").addEventListener("click", () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
    try { localStorage.setItem("ootk.theme", root.dataset.theme); } catch (e) {}
});

renderPresets("");
applySettings(readStore(LAST_KEY, {}));
