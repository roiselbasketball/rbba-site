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

/* RBBA – bouton « Installer l'appli » : invite native sur Android, mode d'emploi sur iPhone. */
(function () {
  "use strict";
  var standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  if (standalone) return; // déjà installée : rien à proposer
  var ua = navigator.userAgent;
  var ios = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var deferred = null;
  function boot() {
    var btn = document.querySelector(".install-btn"), help = document.getElementById("install-help");
    if (!btn) return;
    if (ios && help) btn.hidden = false; // Safari iPhone : mode d'emploi
    addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferred = e; btn.hidden = false; }); // Android / Chrome
    addEventListener("appinstalled", function () { btn.hidden = true; });
    function open(o) { help.hidden = !o; btn.setAttribute("aria-expanded", o); if (o) help.querySelector(".ih-close").focus(); else btn.focus(); }
    btn.addEventListener("click", function () {
      if (deferred) { deferred.prompt(); deferred.userChoice.then(function () { deferred = null; btn.hidden = true; }); return; }
      if (help) open(help.hidden);
    });
    if (help) {
      help.querySelector(".ih-close").addEventListener("click", function () { open(false); });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !help.hidden) open(false); });
      document.addEventListener("click", function (e) { if (!help.hidden && !help.contains(e.target) && !btn.contains(e.target)) open(false); });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
