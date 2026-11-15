// The site's two themes, shared by every page. Loaded in <head> without defer, so the saved
// choice is set before anything is drawn (no flash of the wrong theme). The ◐ Theme button in
// the OOTK bar (_site_bar.html) switches between them and remembers the choice.
(function () {
    const root = document.documentElement;
    let saved = null;
    try { saved = localStorage.getItem("ootk.theme"); } catch (e) {}
    root.dataset.theme = saved || "light";   // the green theme unless dark was chosen

    document.addEventListener("DOMContentLoaded", () => {
        const button = document.getElementById("themeToggle");
        if (!button) return;
        button.addEventListener("click", () => {
            root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
            try { localStorage.setItem("ootk.theme", root.dataset.theme); } catch (e) {}
        });
    });
})();
