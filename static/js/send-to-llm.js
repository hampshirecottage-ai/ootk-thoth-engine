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
        if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
        // Open in the same click, before any await, so pop-up blockers allow it.
        window.open(link.href, "_blank", "noopener");
        note.textContent = link.filled
            ? `Opened ${site.name} with the prompt filled in. It is on your clipboard too.`
            : `Prompt copied. Paste it into ${site.name} (Ctrl+V, or ⌘V on a Mac).`;
    });
});
