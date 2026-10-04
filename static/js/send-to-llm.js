// "Copy and open": copies the prompt, then opens the chosen LLM site in a new tab.
// Sites that take a ?q= prompt get it in the link too, but only while the link stays
// short enough to load reliably; longer prompts are pasted from the clipboard.
const LLM_SITES = {
    claude: { name: "Claude", url: "https://claude.ai/new", param: "q" },
    gemini: { name: "Gemini", url: "https://gemini.google.com/app" },
    chatgpt: { name: "ChatGPT", url: "https://chatgpt.com/", param: "q" },
    copilot: { name: "Copilot", url: "https://copilot.microsoft.com/", param: "q" },
    perplexity: { name: "Perplexity", url: "https://www.perplexity.ai/search", param: "q" },
};
const LLM_MAX_URL = 8000;

function llmLink(site, text) {
    if (!site.param) return { href: site.url, filled: false };
    const href = site.url + "?" + site.param + "=" + encodeURIComponent(text);
    return href.length <= LLM_MAX_URL ? { href, filled: true } : { href: site.url, filled: false };
}

document.querySelectorAll("[data-send-llm]").forEach(box => {
    const select = box.querySelector("select");
    const button = box.querySelector("button");
    const note = box.querySelector("[data-send-llm-note]");
    try { const saved = localStorage.getItem("ootk.llmSite"); if (saved in LLM_SITES) select.value = saved; } catch (e) {}
    select.addEventListener("change", () => {
        try { localStorage.setItem("ootk.llmSite", select.value); } catch (e) {}
    });
    button.addEventListener("click", () => {
        const site = LLM_SITES[select.value];
        const text = document.getElementById(box.dataset.sendLlm).textContent;
        const link = llmLink(site, text);
        const copied = ootkCopy(text);
        // Open in the same click, before any await, so pop-up blockers allow it. Without
        // "noopener" window.open tells us when a blocker stopped the tab; opener is cut by hand.
        const tab = window.open(link.href, "_blank");
        // Cross-origin-opener-policy may already have cut it, and then setting it throws.
        if (tab) try { tab.opener = null; } catch (e) {}
        copied.then(ok => {
            note.textContent = "";
            if (!tab) {
                note.append("Your browser blocked the new tab. ");
                const a = document.createElement("a");
                a.href = link.href; a.target = "_blank"; a.rel = "noopener";
                a.textContent = `Open ${site.name}`;
                note.append(a, ". ");
            }
            if (link.filled) {
                note.append(`${tab ? `Opened ${site.name} with` : "The link has"} the prompt filled in.` +
                            (ok ? " It is on your clipboard too." : ""));
            } else if (ok) {
                note.append(`Prompt copied. Paste it into ${site.name} (Ctrl+V, or ⌘V on a Mac).`);
            } else {
                ootkSelect(document.getElementById(box.dataset.sendLlm));
                note.append(`Your browser didn't allow copying, so the prompt is selected: press ` +
                            `Ctrl+C (⌘C on a Mac), then paste it into ${site.name}.`);
            }
        });
    });
});
