// Start page: shows the reading form one step at a time (question, spread, significator,
// options, then a review with the Draw button). Runs after index.js and uses its
// hasSigPosition() and positionsData. Without this script every field shows at once.
// The guided answers (the g_* radios, outside the form so never sent) only set the real
// fields: the question box, and the spread, mapping and framework selects.
(function () {
    const form = document.getElementById("readingForm");
    const el = id => document.getElementById(id);
    if (!form || !el("wizRail")) return;

    const allSteps = Array.from(form.querySelectorAll(".wiz-step"));
    let current = 0;

    // The significator step only counts when the chosen spread has a significator position.
    function activeSteps() {
        return allSteps.filter(s => s.dataset.step !== "significator" || hasSigPosition());
    }
    function stepIndex(name) { return activeSteps().findIndex(s => s.dataset.step === name); }

    function selectedText(select) {
        const o = select.options[select.selectedIndex];
        return o ? o.text : "";
    }

    // ---------- guided answers ----------
    const radios = name => Array.from(document.querySelectorAll(`input[name="${name}"]`));
    const picked = name => { const r = radios(name).find(r => r.checked); return r ? r.value : ""; };
    const setPicked = (name, value) => radios(name).forEach(r => r.checked = r.value === value);
    // The plain answer, without its small print.
    const answerText = (name, value) => {
        const r = radios(name).find(r => r.value === value);
        return r ? r.nextElementSibling.firstChild.textContent.trim() : "";
    };
    const smallText = (name, value) => {
        const r = radios(name).find(r => r.value === value), s = r && r.nextElementSibling.querySelector("small");
        return s ? s.firstChild.textContent.trim() : "";
    };

    // Question: "Help me" opens the helper, "No question" sets the box aside (disabled, so it
    // is not sent, but kept in case they change their mind).
    function syncAsk() {
        const how = picked("g_ask");
        el("topicInput").disabled = how === "none";
        // Until one is chosen only the three answers show.
        form.querySelector(".ask-own").hidden = how !== "own";
        el("askHelper").hidden = how !== "help";
        if (how === "help" && !el("askHelper").open) el("askHelper").open = true;
    }
    function startAsk() {
        if (el("topicInput").value.trim()) setPicked("g_ask", "own");
        syncAsk();
    }
    radios("g_ask").forEach(r => r.addEventListener("change", () => {
        if (picked("g_ask") === "own") el("askHelper").open = false;
        syncAsk();
    }));
    // "Use this question" shows the finished question in the box, to read or edit.
    el("askHelper").addEventListener("ask:used", () => { setPicked("g_ask", "own"); syncAsk(); });

    // Spread: how deep, then the spreads at that depth. Follows the select, which saved
    // settings, links and the question helper may have set; a new depth starts on its first spread.
    function syncSpreadGuide() {
        const key = el("spreadSelect").value;
        const opt = radios("g_spread").find(r => r.value === key);
        const depth = opt ? opt.closest("label").dataset.depth : "";
        setPicked("g_depth", depth);
        setPicked("g_spread", key);
        form.querySelector('[data-g="spread"]').hidden = !depth;
        radios("g_spread").forEach(r => {
            const label = r.closest("label");
            label.hidden = label.dataset.depth !== depth;
            label.querySelector(".g-suggested").hidden = r.value !== el("spreadSelect").dataset.suggested;
        });
    }
    radios("g_depth").forEach(r => r.addEventListener("change", () => {
        const first = radios("g_spread").find(s => s.closest("label").dataset.depth === r.value);
        if (first) setSelect("spreadSelect", first.value);
    }));
    radios("g_spread").forEach(r => r.addEventListener("change", () => setSelect("spreadSelect", r.value)));

    function setSelect(id, value) {
        el(id).value = value;
        el(id).dispatchEvent(new Event("change", { bubbles: true }));
    }

    // Options: the seed box shows only for a repeat; mapping and framework follow their selects.
    function syncOptions() {
        if (!picked("g_seed")) setPicked("g_seed", el("seedInput").value.trim() ? "repeat" : "new");
        form.querySelector(".seed-box").hidden = picked("g_seed") !== "repeat";
        setPicked("g_mapping", el("mappingSelect").value);
        setPicked("g_framework", el("frameworkSelect").value);
    }
    radios("g_seed").forEach(r => r.addEventListener("change", () => {
        if (picked("g_seed") === "new") el("seedInput").value = "";
        syncOptions();
        if (picked("g_seed") === "repeat") el("seedInput").focus({ preventScroll: true });
    }));
    radios("g_mapping").forEach(r => r.addEventListener("change", () => setSelect("mappingSelect", r.value)));
    radios("g_framework").forEach(r => r.addEventListener("change", () => setSelect("frameworkSelect", r.value)));

    function renderSpreadPreview() {
        const positions = positionsData[el("spreadSelect").value] || [];
        const names = positions.slice(0, 6).map(p => p.replace(/^\[Op \d+\]\s*/, "").replace(/^\d+\.\s*/, "").split(" (")[0]);
        const more = positions.length > 6 ? `, and ${positions.length - 6} more` : "";
        el("spreadPreview").textContent = positions.length ? `Positions: ${names.join(", ")}${more}.` : "";
    }

    function renderReview() {
        const key = el("spreadSelect").value, n = (positionsData[key] || []).length;
        const fw = el("frameworkSelect").value, seed = el("seedInput").value.trim();
        const rows = [
            ["Question", (!el("topicInput").disabled && el("topicInput").value.trim()) || "None: a general reading", "question"],
            ["Spread", `${smallText("g_spread", key).split(" · ")[0]}, ${n} card${n === 1 ? "" : "s"}`, "spread"],
        ];
        if (hasSigPosition()) rows.push(["Significator", el("significatorInput").value || "Not chosen yet", "significator"]);
        rows.push(["Tradition", answerText("g_mapping", el("mappingSelect").value), "options"],
                  ["Story", answerText("g_framework", fw) + (fw === "auto" ? " (Auto)" : ` (${smallText("g_framework", fw).split(":")[0]})`), "options"],
                  ["Cards", seed ? `Repeat seed ${seed}` : "New cards", "options"]);
        el("wizReview").replaceChildren(...rows.flatMap(([label, value, step]) => {
            const dt = document.createElement("dt"), dd = document.createElement("dd");
            const edit = document.createElement("button");
            dt.textContent = label;
            dd.textContent = value;
            if (step === "question") dd.className = "q";
            edit.type = "button";
            edit.textContent = "Edit";
            edit.setAttribute("aria-label", `Edit ${label.toLowerCase()}`);
            edit.addEventListener("click", () => go(stepIndex(step)));
            return [dt, dd, edit];
        }));
    }

    // Blocks leaving a step that isn't complete; only the significator can be.
    function stepError(step) {
        if (step.dataset.step === "significator" && hasSigPosition() && !el("significatorInput").value)
            return "This spread needs a significator. Choose one to continue.";
        return "";
    }
    function showError(msg) {
        el("wizError").textContent = msg;
        el("wizError").hidden = !msg;
    }

    function render() {
        const steps = activeSteps();
        current = Math.max(0, Math.min(current, steps.length - 1));
        const step = steps[current], last = current === steps.length - 1;
        allSteps.forEach(s => s.toggleAttribute("data-hidden", s !== step));
        form.classList.toggle("wiz-not-last", !last);
        el("wizBack").disabled = current === 0;
        el("wizCount").textContent = `Step ${current + 1} of ${steps.length}`;
        el("wizRail").replaceChildren(...steps.map((s, i) => {
            const li = document.createElement("li"), b = document.createElement("button"), n = document.createElement("span");
            b.type = "button";
            n.textContent = i + 1;
            b.append(n, s.dataset.title);
            if (i === current) b.setAttribute("aria-current", "step");
            if (i < current) b.className = "done";
            b.addEventListener("click", () => go(i));
            li.append(b);
            return li;
        }));
        if (step.dataset.step === "question") syncAsk();
        if (step.dataset.step === "spread") { syncSpreadGuide(); renderSpreadPreview(); }
        if (step.dataset.step === "options") syncOptions();
        if (last) renderReview();
    }

    function go(i) {
        // Moving forward past an incomplete step stops on that step instead.
        const steps = activeSteps();
        for (let k = current; k < i && k < steps.length; k++) {
            const msg = stepError(steps[k]);
            if (msg) { current = k; render(); showError(msg); return; }
        }
        showError("");
        current = i;
        render();
        const field = activeSteps()[current].querySelector("textarea, select, input:not([type=hidden])");
        // Not on touch screens, where focusing a field pops up the keyboard.
        if (field && !field.closest("[hidden]") && matchMedia("(pointer: fine)").matches) field.focus({ preventScroll: true });
        form.scrollIntoView({ block: "nearest" });
    }

    // Turn the wizard on: the review step was hidden for visitors without JavaScript.
    form.classList.add("wizard");
    el("wizRail").hidden = false;
    el("wizNav").hidden = false;
    form.querySelector('.wiz-step[data-step="review"]').hidden = false;
    el("moreOptions").open = true;

    el("wizBack").addEventListener("click", () => go(current - 1));
    el("wizNext").addEventListener("click", () => go(current + 1));
    el("spreadSelect").addEventListener("change", () => { renderSpreadPreview(); render(); });
    el("mappingSelect").addEventListener("change", syncOptions);
    el("frameworkSelect").addEventListener("change", syncOptions);
    el("sigPicker").addEventListener("change", () => showError(""));

    // Enter in the question box, or in a one-line field, moves on until the last step,
    // where it draws as before. Runs before index.js's own submit handler.
    document.addEventListener("submit", e => {
        if (e.target !== form) return;
        const steps = activeSteps();
        if (current < steps.length - 1) {
            e.preventDefault();
            e.stopImmediatePropagation();
            go(current + 1);
            return;
        }
        const missing = steps.find(stepError);
        if (missing) {
            e.preventDefault();
            e.stopImmediatePropagation();
            go(steps.indexOf(missing));
            showError(stepError(missing));
        }
    }, true);

    startAsk();
    render();
})();
