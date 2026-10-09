// The sections on /start fold away under their headings. A link to one of them, or to
// anything inside one (/start#sample, /start#stagesTitle), opens it and scrolls to it.
const openFromHash = () => {
    const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!target) return;
    for (let el = target; el; el = el.parentElement) if (el.tagName === "DETAILS") el.open = true;
    target.scrollIntoView();
};
openFromHash();
window.addEventListener("hashchange", openFromHash);
