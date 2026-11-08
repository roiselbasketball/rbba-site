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

/* RBBA – bouton « Installer l'appli » : toujours visible (sauf appli déjà installée).
   Android/Chrome : fenêtre officielle d'installation. iPhone et autres : mode d'emploi. */
(function () {
  "use strict";
  var standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  var ua = navigator.userAgent;
  var ios = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var deferred = null;
  addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferred = e; });
  function boot() {
    var btn = document.querySelector(".install-btn"), help = document.getElementById("install-help");
    if (!btn) return;
    if (standalone) { btn.hidden = true; return; }
    addEventListener("appinstalled", function () { btn.hidden = true; if (help) help.hidden = true; });
    if (help) {
      help.querySelector(".ih-ios").hidden = !ios;
      help.querySelector(".ih-android").hidden = ios;
    }
    function open(o) { help.hidden = !o; btn.setAttribute("aria-expanded", o); if (o) help.querySelector(".ih-close").focus(); else btn.focus(); }
    btn.addEventListener("click", function () {
      if (deferred) { deferred.prompt(); deferred.userChoice.then(function (c) { deferred = null; if (c && c.outcome === "accepted") btn.hidden = true; }); return; }
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

/* Alertes de match (OneSignal) : bouton « Recevoir les alertes » */
(function () {
  function boot() {
    var btn = document.getElementById("alerts-btn"); if (!btn) return;
    var status = document.querySelector(".alerts-status"), iosNote = document.querySelector(".alerts-ios");
    var ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    var standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
    var OS = null;
    function say(t) { if (status) status.textContent = t; }
    function optedIn() { try { return !!(OS && OS.User.PushSubscription.optedIn); } catch (e) { return false; } }
    function refresh() {
      if (!("Notification" in window)) return;
      if (Notification.permission === "denied") { btn.textContent = "Alertes bloquées"; say("Les notifications sont bloquées pour ce site. Sur iPhone : Réglages > Notifications > RBBA. Sur Android : appui long sur l'appli > Infos > Notifications."); return; }
      var on = Notification.permission === "granted" && (OS ? optedIn() : true);
      btn.textContent = on ? "Alertes activées" : "Recevoir les alertes";
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      say(on ? "C'est bon : vous recevrez les alertes du RBBA." : "");
    }
    if (ios && !standalone) {
      if (iosNote) iosNote.hidden = false;
      btn.textContent = "Installer l'appli d'abord";
      btn.addEventListener("click", function () { var b = document.querySelector(".install-btn"); if (b) b.click(); else location.href = "appli.html"; });
      return;
    }
    if (!("Notification" in window) || !("serviceWorker" in navigator)) { btn.disabled = true; say("Ce navigateur ne gère pas les notifications. Sur iPhone, il faut iOS 16.4 ou plus récent et l'appli installée."); return; }
    refresh();
    btn.addEventListener("click", function () {
      if (optedIn()) { say("Pour couper les alertes : réglages de notifications du téléphone."); return; }
      say("Demande en cours…");
      // Demande native immédiate (iPhone exige qu'elle parte directement du toucher)
      var ask = Notification.permission === "default" ? Notification.requestPermission() : Promise.resolve(Notification.permission);
      Promise.resolve(ask).then(function (perm) {
        if (perm !== "granted") { refresh(); if (perm !== "denied") say("Alertes non activées."); return; }
        say("Activation…");
        var tries = 0;
        (function finish() {
          if (OS) { Promise.resolve(OS.User.PushSubscription.optIn()).catch(function () {}).then(function () { setTimeout(refresh, 800); }); return; }
          if (++tries > 20) { say("Autorisation enregistrée. L'abonnement se finalisera à la prochaine ouverture de l'appli."); return; }
          setTimeout(finish, 500);
        })();
      }).catch(function () { say("Activation impossible pour le moment. Réessayez dans un instant."); });
    });
    window.OneSignalDeferred = window.OneSignalDeferred || [];
    OneSignalDeferred.push(function (O) {
      OS = O; refresh();
      try { O.User.PushSubscription.addEventListener("change", refresh); } catch (e) {}
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
