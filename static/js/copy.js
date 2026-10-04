// ootkCopy(text): puts text on the clipboard. Resolves true when it worked, false when the
// browser refused (no Clipboard API on plain http, permission denied, an old browser), so the
// caller can say so instead of claiming "Copied".
function ootkCopy(text) {
    const fallback = () => {
        const area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        let ok = false;
        try { ok = document.execCommand("copy"); } catch (e) {}
        area.remove();
        return ok;
    };
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text).then(() => true, fallback);
    }
    return Promise.resolve(fallback());
}

// Selects an element's text, so a visitor whose browser refused the copy can press Ctrl+C.
function ootkSelect(el) {
    if (!el) return;
    const folded = el.closest("details");
    if (folded) folded.open = true;          // text in a closed section can't be copied
    const range = document.createRange();
    range.selectNodeContents(el);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
}

// Button feedback: "Copied", or "Press Ctrl+C" with the text selected when copying failed.
function ootkCopyButton(btn, text, sourceEl) {
    const label = btn.dataset.label || (btn.dataset.label = btn.textContent);
    return ootkCopy(text).then(ok => {
        if (!ok) ootkSelect(sourceEl);
        btn.textContent = ok ? "Copied" : (/Mac/.test(navigator.platform) ? "Press ⌘C" : "Press Ctrl+C");
        setTimeout(() => btn.textContent = label, ok ? 1200 : 4000);
        return ok;
    });
}
