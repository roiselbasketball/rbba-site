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

/* Alertes de match (OneSignal) : bouton « Recevoir les alertes » + proposition à l'ouverture de l'appli installée */
(function () {
  var OS = null, listeners = [];
  var ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  var supported = ("Notification" in window) && ("serviceWorker" in navigator);
  function optedIn() { try { return !!(OS && OS.User.PushSubscription.optedIn); } catch (e) { return false; } }
  function state() {
    if (!supported) return "unsupported";
    if (Notification.permission === "denied") return "denied";
    if (Notification.permission === "granted" && optedIn()) return "on";
    return "off";
  }
  function notify() { var st = state(); if (st === "on") bienvenue(); listeners.forEach(function (f) { f(st); }); }
  // Bienvenue : on note l'heure d'abonnement (étiquette OneSignal) ; le robot du site envoie
  // 10 à 15 minutes plus tard une notification avec le prochain match (une seule fois par téléphone).
  function bienvenue() {
    if (!OS) return;
    try { if (localStorage.getItem("rbba-bienvenue")) return; } catch (e) {}
    try {
      OS.User.addTag("abonne_le", String(Math.floor(Date.now() / 1000)));
      try { localStorage.setItem("rbba-bienvenue", "1"); } catch (e) {}
    } catch (e) {}
  }
  // À appeler directement depuis un toucher (iPhone l'exige)
  function enable(say) {
    say = say || function () {};
    if (!supported) { say("Ce téléphone ne gère pas les notifications."); return Promise.resolve(false); }
    say("Demande en cours…");
    var ask = Notification.permission === "default" ? Notification.requestPermission() : Promise.resolve(Notification.permission);
    return Promise.resolve(ask).then(function (perm) {
      if (perm !== "granted") { notify(); if (perm !== "denied") say("Alertes non activées."); return false; }
      say("Activation…");
      return new Promise(function (res) {
        var tries = 0;
        (function finish() {
          if (OS) { Promise.resolve(OS.User.PushSubscription.optIn()).catch(function () {}).then(function () { setTimeout(function () { notify(); res(true); }, 800); }); return; }
          if (++tries > 20) { notify(); say("Autorisation enregistrée. L'abonnement se finalisera à la prochaine ouverture de l'appli."); res(true); return; }
          setTimeout(finish, 500);
        })();
      });
    }).catch(function () { say("Activation impossible pour le moment. Réessayez dans un instant."); return false; });
  }
  window.OneSignalDeferred = window.OneSignalDeferred || [];
  OneSignalDeferred.push(function (O) { OS = O; notify(); try { O.User.PushSubscription.addEventListener("change", notify); } catch (e) {} });

  // Bloc « Alertes de match » (accueil, page appli)
  function block() {
    var btn = document.getElementById("alerts-btn"); if (!btn) return;
    var status = document.querySelector(".alerts-status"), iosNote = document.querySelector(".alerts-ios");
    function say(t) { if (status) status.textContent = t; }
    if (ios && !standalone) {
      if (iosNote) iosNote.hidden = false;
      btn.textContent = "Installer l'appli d'abord";
      btn.addEventListener("click", function () { var b = document.querySelector(".install-btn"); if (b) b.click(); else location.href = "appli.html"; });
      return;
    }
    if (!supported) { btn.disabled = true; say("Ce navigateur ne gère pas les notifications. Sur iPhone, il faut iOS 16.4 ou plus récent et l'appli installée."); return; }
    function render(st) {
      if (st === "denied") { btn.textContent = "Alertes bloquées"; say("Les notifications sont bloquées pour ce site. Sur iPhone : Réglages > Notifications > RBBA. Sur Android : appui long sur l'appli > Infos > Notifications."); return; }
      btn.textContent = st === "on" ? "Alertes activées" : "Recevoir les alertes";
      btn.setAttribute("aria-pressed", st === "on" ? "true" : "false");
      say(st === "on" ? "C'est bon : vous recevrez les alertes du RBBA." : "");
    }
    listeners.push(render); render(state());
    btn.addEventListener("click", function () {
      if (state() === "on") { say("Pour couper les alertes : réglages de notifications du téléphone."); return; }
      enable(say);
    });
  }

  // Proposition à l'ouverture de l'appli installée : « Ne manquez aucun match »
  function sheet() {
    // À chaque ouverture de l'appli installée, tant que les alertes ne sont pas activées.
    // « Plus tard » ne masque que jusqu'à la prochaine ouverture.
    if (!standalone || !supported) return;
    var KEY = "rbba-alertes-plus-tard";
    try { if (sessionStorage.getItem(KEY)) return; } catch (e) {}
    var denied = Notification.permission === "denied";
    if (Notification.permission === "granted") {
      // Autorisé mais peut-être pas encore abonné : on finalise sans redemander
      var waited = 0;
      (function check() {
        if (OS) {
          if (!optedIn()) Promise.resolve(OS.User.PushSubscription.optIn()).catch(function () {}).then(function () { setTimeout(function () { if (!optedIn()) show(false); notify(); }, 1500); });
          return;
        }
        if ((waited += 500) < 10000) setTimeout(check, 500); else show(false);
      })();
      return;
    }
    show(denied);
    function show(blocked) {
      var el = document.createElement("div");
      el.className = "alert-sheet"; el.setAttribute("role", "dialog"); el.setAttribute("aria-labelledby", "as-title");
      var aide = ios ? "Réglages > Notifications > RBBA, puis activez « Autoriser les notifications »." : "Appui long sur l'icône RBBA > Infos sur l'appli > Notifications, puis activez-les.";
      el.innerHTML = '<div class="as-in"><img src="' + (document.querySelector(".brand img") || {}).src + '" alt="" width="44" height="40">' +
        '<div class="as-tx"><h2 id="as-title">Ne manquez aucun match</h2><p>Le jour du match, le score final et les nouveaux posts du club, directement sur votre écran.</p>' +
        (blocked ? '<p class="as-help">Les notifications sont coupées pour l\'appli. Pour les activer : ' + aide + '</p>' : '') +
        '<p class="as-st" role="status" aria-live="polite"></p></div>' +
        '<div class="as-btns">' + (blocked ? '' : '<button class="btn" type="button" data-as="ok">Activer les alertes</button>') +
        '<button class="btn btn--out" type="button" data-as="later">' + (blocked ? "Compris" : "Plus tard") + '</button></div></div>';
      var st = el.querySelector(".as-st");
      function close() { el.classList.remove("open"); setTimeout(function () { el.remove(); }, 250); }
      el.querySelector('[data-as="later"]').addEventListener("click", function () { try { sessionStorage.setItem(KEY, "1"); } catch (e) {} close(); });
      var ok = el.querySelector('[data-as="ok"]');
      if (ok) ok.addEventListener("click", function () {
        enable(function (t) { st.textContent = t; }).then(function (res) {
          if (res) { st.textContent = "C'est bon, à samedi au gymnase !"; setTimeout(close, 1600); }
          else if (Notification.permission === "denied") { close(); }
        });
      });
      document.body.appendChild(el);
      setTimeout(function () { el.classList.add("open"); el.querySelector("button").focus({ preventScroll: true }); }, 1500);
    }
  }

  function boot() { block(); sheet(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
