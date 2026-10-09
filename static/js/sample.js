// The sample Opening of the Key on /start (templates/_sample_reading.html).
const $ = id => document.getElementById(id);
// The sample starts folded away; a link to /start#sample opens it.
const openSampleFromHash = () => { if (location.hash === "#sample") $("sample").open = true; };
openSampleFromHash();
window.addEventListener("hashchange", openSampleFromHash);
// The prompt is about 72 KB, so it is fetched when the sample is first opened rather than
// sent with every visit to /start.
let samplePrompt = null;
const loadSamplePrompt = () => {
    const pre = $("samplePrompt");
    samplePrompt = samplePrompt || fetch(pre.dataset.src)
        .then(r => { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(text => { pre.textContent = text; pre.removeAttribute("aria-busy"); return text; })
        .catch(() => {
            samplePrompt = null;   // let the next open or click try again
            pre.textContent = "The prompt couldn't be loaded. Open the full report instead.";
            pre.removeAttribute("aria-busy");
            return null;
        });
    return samplePrompt;
};
$("sample").addEventListener("toggle", () => { if ($("sample").open) loadSamplePrompt(); });
if ($("sample").open) loadSamplePrompt();
$("copySample").addEventListener("click", e => {
    const btn = e.currentTarget;
    loadSamplePrompt().then(text => {
        if (text) ootkCopyButton(btn, text, $("samplePrompt"));
    });
});
$("mechToggle").addEventListener("click", e => {
    const open = $("mechanics").hidden;
    $("mechanics").hidden = !open;
    e.currentTarget.setAttribute("aria-expanded", open);
    e.currentTarget.textContent = (open ? "Hide" : "Show") + " Hermetic / Cabbalistic mechanics";
});
$("expandSample").addEventListener("click", e => {
    const open = $("samplePromptBox").classList.toggle("open");
    e.currentTarget.setAttribute("aria-expanded", open);
    e.currentTarget.textContent = open ? "Show less" : "Show the whole prompt";
});
