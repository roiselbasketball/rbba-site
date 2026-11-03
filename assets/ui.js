/* RBBA – réglages d'accessibilité (taille du texte, animations, contraste), mémorisés sur l'appareil. */
(function () {
  "use strict";
  var root = document.documentElement, KEY = "rbba-a11y", prefs = { text: "", motion: "", contrast: "" };
  try { prefs = Object.assign(prefs, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
  function apply() { root.classList.remove("text-lg", "text-xl", "reduce-motion", "contrast"); [prefs.text, prefs.motion, prefs.contrast].forEach(function (c) { if (c) root.classList.add(c); }); }
  apply();
  function boot() {
    var btn = document.querySelector(".a11y-btn"), box = document.getElementById("a11y");
    if (!btn || !box) return;
    ["text", "motion", "contrast"].forEach(function (k) {
      box.querySelectorAll('input[name="a11y-' + k + '"]').forEach(function (r) {
        r.checked = r.value === prefs[k];
        r.addEventListener("change", function () { prefs[k] = r.value; apply(); try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch (e) {} });
      });
    });
    function open(o) { box.hidden = !o; btn.setAttribute("aria-expanded", o); if (o) { var c = box.querySelector("input:checked"); if (c) c.focus(); } else btn.focus(); }
    btn.addEventListener("click", function () { open(box.hidden); });
    box.querySelector(".a11y-close").addEventListener("click", function () { open(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !box.hidden) open(false); });
    document.addEventListener("click", function (e) { if (!box.hidden && !box.contains(e.target) && !btn.contains(e.target)) { box.hidden = true; btn.setAttribute("aria-expanded", "false"); } });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
