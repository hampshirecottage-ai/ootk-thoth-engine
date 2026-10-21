// Question helper under the Question box (templates/_question_helper.html). Shapes a rough
// question into an open one in the terms of a spread's positions, then writes the question,
// spread and framework into the reading form. Nothing here changes which cards are drawn.
(function () {
    const $ = id => document.getElementById(id);
    if (!$("askHelper")) return;

    // What each intent asks for: the spread whose positions answer it best.
    const INTENT_SPREAD = { focus: "1", decide: "2", heading: "3", blocked: "6", manifest: "5",
                            wholelife: "9", spiritual: "7", full: "12" };

    // Per spread: the open question in its position terms, and what the positions answer.
    // Keys match ootk.spreads.SPREADS.
    const SPREAD_QUESTIONS = {
        "1": { q: s => `What is the core thing I need to understand about ${s}`,
               pos: [["Core Theme", "the one thing to understand"]] },
        "2": { q: s => `What is drawing me toward ${s}, and what in me or the situation is resisting it`,
               pos: [["Active Force", "what draws you forward"], ["Resistance", "what in you or the situation holds back"]] },
        "3": { q: s => `Where did ${s} begin, what is active in it now, and where is it heading`,
               pos: [["Past / Root Cause", "where it began"], ["Present", "what is moving now"], ["Future / Result", "where it is heading"]] },
        "4": { q: s => `How is my will around ${s} showing up, as raw impulse, as emotional desire, as focused intent and as practical action`,
               pos: [["Fire of Fire", "your raw impulse"], ["Water of Fire", "what you emotionally want"], ["Air of Fire", "where your focus points"], ["Earth of Fire", "what you actually do"]] },
        "5": { q: s => `How does ${s} move from its first spark, through feeling and planning, into a concrete result`,
               pos: [["Atziluth / Fire", "the creative spark"], ["Briah / Water", "how you hold it in mind and heart"], ["Yetzirah / Air", "how it takes shape"], ["Assiah / Earth", "what it becomes in the world"]] },
        "6": { q: s => `What forces are shaping ${s}: what constrains it, what could expand it, what drives it, what I value and how I think about it, who I am in it, and what lies beneath the surface`,
               pos: [["Saturn", "what constrains it"], ["Jupiter", "what could expand it"], ["Mars", "what drives it"], ["Venus", "what you value in it"], ["Mercury", "how you think about it"], ["Sun", "who you are at its centre"], ["Moon", "what lies beneath the surface"]] },
        "7": { q: s => `How does ${s} unfold from its first spiritual impulse down to how it shows up in my daily life`,
               pos: [["Kether to Binah", "the first impulse, its force and its form"], ["Chesed to Tiphareth", "what expands, what must be cut, your core"], ["Netzach to Yesod", "feeling, thought and the unconscious foundation"], ["Malkuth", "how it shows up in daily life"]] },
        "8": { q: s => `What is the core of ${s}, how will it develop, what outside factors are at play, what lies underneath it, and how does it resolve`,
               pos: [["1. Significator", "the core of the question"], ["2 to 5", "how it develops and its further outcome"], ["6 and 7", "unexpected or outside factors"], ["8 to 11", "its inner and material basis"], ["12 to 15", "karma, counter-balance and resolution"]] },
        "9": { q: s => `Which areas of my life does ${s} touch, from self and money to home, partnerships, career and what is hidden, and what does each need from me`,
               pos: [["Houses 1 to 3", "self, money and values, everyday mind"], ["Houses 4 to 6", "home, creativity, health and work"], ["Houses 7 to 9", "partners, shared resources, beliefs"], ["Houses 10 to 12", "career, allies and hopes, what is hidden"]] },
        "10": { q: s => `How do the qualities of each sign colour ${s}: where should I take initiative, what should I hold steady, and where should I adapt`,
                pos: [["Cardinal signs", "where to begin"], ["Fixed signs", "what to hold steady"], ["Mutable signs", "where to adapt"]] },
        "11": { q: s => `What are the finer turning points of ${s} through the year, decan by decan`,
                pos: [["36 decans", "ten-degree steps through the year, each with its pip card"]] },
        "12": { q: s => `What is the full shape of ${s}: its core and development, the areas of my life it touches, how it unfolds through the year, and its finer turning points`,
                pos: [["Op 1: Heap", "the core and development of the question"], ["Op 2: Houses", "which areas of life it touches"], ["Op 3: Signs", "how it unfolds through the year"], ["Op 4: Decans", "the finer turning points"]] },
    };

    const TIMES = { weeks: [", over the next few weeks", "the next few weeks"],
                    months: [", over the next three months", "the next three months"],
                    year: [", over the coming year", "the coming year"], open: ["", ""] };
    const TOPIC_MAX = Number($("topicInput").getAttribute("maxlength")) || 2000;
    const STEP_COUNT = document.querySelectorAll("[data-ask-step]").length;
    let step = 0;

    const val = id => $(id).value.trim();
    const stripEnd = s => s.replace(/[?.!\s]+$/, "");
    const optionText = (sel, value) => {
        const o = Array.from(sel.options).find(opt => opt.value === value);
        return o ? o.text : value;
    };

    // The spread: from the intent if one is chosen, otherwise whatever the form already has.
    function spreadKey() {
        return INTENT_SPREAD[$("askIntent").value] || $("spreadSelect").value;
    }

    function rawHints(t) {
        const out = [];
        if (!t) return out;
        if (/^(will|should|is|are|does|do|did|can|could|am|would|has|have|was)\b/i.test(t))
            out.push(["warn", "A yes/no question boxes every card into one answer. The reframe asks how or what instead."]);
        if (/\bwhen\b/i.test(t))
            out.push(["warn", "Timing is hard to read. Ask what needs to happen, and set a window in step 5."]);
        if (/\b(he|she|they|him|her|them|his|hers|their)\b/i.test(t) && !/\b(i|me|my|we|us|our)\b/i.test(t))
            out.push(["", "This centres someone else. In step 4, choose \"Mainly about someone else\" and it will ask about your part."]);
        if (/\bor\b/i.test(t)) out.push(["", "Weighing options? \"Help me weigh a decision\" in step 3 suits this."]);
        if (t.split(/\s+/).length < 5) out.push(["", "A short question gives your AI little to tie the cards to. Step 6 lets you add the situation."]);
        return out;
    }

    function compose() {
        const key = spreadKey();
        const sq = SPREAD_QUESTIONS[key] || SPREAD_QUESTIONS["3"];
        const focus = $("askFocus").value, other = val("askOther"), time = TIMES[$("askTime").value];
        let q = sq.q(stripEnd(val("askSubject")) || "this situation");
        if ($("askPath").checked) q += ", as a step on my longer path";
        q += time[0];
        if (focus === "other") q += ", and what is mine to do in it";
        if (focus === "us") q += ", for both of us";
        q = q.charAt(0).toUpperCase() + q.slice(1) + "?";

        const spiritual = $("askIntent").value === "spiritual" || $("askArea").value === "spirit";
        const framework = spiritual ? "light_descent" : $("askPath").checked ? "life_path" : "auto";

        const lines = [q];
        const raw = val("askRaw");
        if (raw) lines.push(`(First asked as: "${raw}")`);
        const ctx = [];
        const area = $("askArea").value;
        if (area && area !== "other") ctx.push(`Area of life: ${optionText($("askArea"), area).toLowerCase()}.`);
        if (focus === "other") ctx.push(`This mainly concerns ${other || "another person"}; I want to understand my part in it.`);
        if (focus === "us") ctx.push(`This is about ${other ? "me and " + other : "a relationship"} together.`);
        if (time[1]) ctx.push(`Timeframe: ${time[1]}.`);
        if (val("askSituation")) ctx.push(`Situation: ${val("askSituation")}`);
        if (val("askTried")) ctx.push(`Already tried or decided: ${val("askTried")}`);
        if (val("askUnsure")) ctx.push(`Most unsure about: ${val("askUnsure")}`);
        if (ctx.length) lines.push("", "Context:", ...ctx.map(c => "- " + c));
        if ($("askCatchAll").checked) lines.push("", "Also tell me: what am I not asking that I should be?");
        return { key, q, sq, framework, spiritual, focus, topic: lines.join("\n") };
    }

    function render() {
        const r = compose();
        $("askHints").replaceChildren(...rawHints(val("askRaw")).map(([cls, text]) => {
            const p = document.createElement("p");
            if (cls) p.className = cls;
            p.textContent = text;
            return p;
        }));
        $("askOtherBox").hidden = r.focus === "me";
        $("askQ").textContent = r.q;

        const sig = r.key === "8" || r.key === "12"
            ? (r.focus === "other" ? "Their court card, not yours" : "Your own court card")
            : "Not needed";
        const fwNote = r.spiritual ? " (or soul_formation for purpose before this life)" : r.framework === "auto" ? " (usually Life Path)" : "";
        const rows = [["Spread", optionText($("spreadSelect"), r.key)],
                      ["Framework", optionText($("frameworkSelect"), r.framework) + fwNote],
                      ["Significator", sig]];
        $("askSet").replaceChildren(...rows.flatMap(([k, v]) => {
            const dt = document.createElement("dt"), dd = document.createElement("dd");
            dt.textContent = k; dd.textContent = v;
            return [dt, dd];
        }));
        $("askPos").replaceChildren(...r.sq.pos.map(([label, what]) => {
            const li = document.createElement("li"), b = document.createElement("b");
            b.textContent = label;
            li.append(b, ": " + what);
            return li;
        }));
        const tooLong = r.topic.length > TOPIC_MAX;
        $("askTooLong").hidden = !tooLong;
        $("askTooLong").textContent = tooLong ? `That's ${r.topic.length} characters; the question box holds ${TOPIC_MAX}. Shorten the context a little.` : "";
        $("askUse").disabled = tooLong;
    }

    function go(i) {
        step = Math.max(0, Math.min(STEP_COUNT - 1, i));
        document.querySelectorAll("[data-ask-step]").forEach(el => el.hidden = Number(el.dataset.askStep) !== step);
        $("askBack").disabled = step === 0;
        $("askNext").disabled = step === STEP_COUNT - 1;
        $("askCount").textContent = `Step ${step + 1} of ${STEP_COUNT}`;
    }

    // Opening the helper starts from whatever is already in the Question box.
    $("askHelper").addEventListener("toggle", () => {
        if ($("askHelper").open && !val("askRaw") && val("topicInput")) $("askRaw").value = $("topicInput").value.trim().slice(0, 300);
        render();
    });
    $("askHelper").addEventListener("input", render);
    $("askHelper").addEventListener("change", render);
    $("askBack").addEventListener("click", () => go(step - 1));
    $("askNext").addEventListener("click", () => go(step + 1));
    // Enter in a one-line box moves on instead of drawing the cards.
    $("askHelper").addEventListener("keydown", e => {
        if (e.key === "Enter" && e.target.tagName === "INPUT" && !e.isComposing) { e.preventDefault(); go(step + 1); }
    });

    $("askUse").addEventListener("click", () => {
        const r = compose();
        $("topicInput").value = r.topic;
        $("spreadSelect").value = r.key;
        $("frameworkSelect").value = r.framework;
        $("spreadSelect").dispatchEvent(new Event("change", { bubbles: true }));
        $("frameworkSelect").dispatchEvent(new Event("change", { bubbles: true }));
        $("askHelper").open = false;
        $("topicInput").focus();
    });

    go(0);
    render();
})();
