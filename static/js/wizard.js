// Start page: shows the reading form one step at a time (question, spread, significator,
// options, then a review with the Draw button). Runs after index.js and uses its
// hasSigPosition() and positionsData. Without this script every field shows at once.
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

    function renderSpreadPreview() {
        const positions = positionsData[el("spreadSelect").value] || [];
        const names = positions.slice(0, 6).map(p => p.replace(/^\[Op \d+\]\s*/, "").replace(/^\d+\.\s*/, "").split(" (")[0]);
        const more = positions.length > 6 ? `, and ${positions.length - 6} more` : "";
        el("spreadPreview").textContent = positions.length ? `Positions: ${names.join(", ")}${more}.` : "";
    }

    function renderReview() {
        const rows = [
            ["Question", el("topicInput").value.trim() || "None: a general reading", "question"],
            ["Spread", selectedText(el("spreadSelect")), "spread"],
        ];
        if (hasSigPosition()) rows.push(["Significator", el("significatorInput").value || "Not chosen yet", "significator"]);
        rows.push(["Mapping", selectedText(el("mappingSelect")).split(" (")[0], "options"],
                  ["Framework", selectedText(el("frameworkSelect")), "options"],
                  ["Seed", el("seedInput").value.trim() || "New random seed", "options"]);
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
        if (step.dataset.step === "spread") renderSpreadPreview();
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

    render();
})();
