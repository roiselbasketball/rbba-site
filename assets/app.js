/* RBBA – données des matchs (produites par scripts/ffbb_sync.py dans data/) et rendu des pages. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var SCRIPT = document.currentScript ? document.currentScript.src : location.href;
  var ROOT = new URL("../", new URL(".", SCRIPT));
  var MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  var MOIS_L = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  var JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  var J3 = ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."];

  function get(path) {
    return fetch(new URL(path, ROOT).href + "?t=" + Date.now(), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function nice(name) {
    return String(name || "").replace(/\s*\([^)]*\)/g, "").replace(/\s+-\s+(\d+)$/, " $1").toLowerCase().replace(/(^|[\s\-'’])([a-zàâçéèêëîïôûùüÿñæœ])/g, function (m, a, b) { return a + b.toUpperCase(); })
      .replace(/\b(Ca|Us|Uso|Bb|Bc|Es|As|Rbba)\b/g, function (m) { return m.toUpperCase(); });
  }
  // nom court pour les titres de score : « Basket Ball Neslois » → « Neslois », « Roisel Basketball » → « RBBA »
  function short(name) {
    if (/roisel/i.test(name)) return "RBBA";
    var w = nice(name).replace(/\b(Basket|Ball|Basketball|Club|Section|Sport(s|ive)?|De|Du|Des|La|Le|Les|Et)\b/gi, " ").replace(/\s+/g, " ").trim();
    return w || nice(name);
  }
  function isRbba(n) { return /roisel/i.test(n || ""); }
  function d(iso) { return new Date(iso); }
  function dayLong(iso) { var x = d(iso); return JOURS[x.getDay()] + " " + x.getDate() + " " + MOIS_L[x.getMonth()]; }
  function heure(iso) { var x = d(iso); return String(x.getHours()).padStart(2, "0") + "h" + String(x.getMinutes()).padStart(2, "0"); }
  function stamp(iso) { var x = d(iso); return "le " + x.getDate() + " " + MOIS_L[x.getMonth()] + " à " + heure(iso); }
  function n(v) { return v == null ? "–" : v; }
  function signed(v) { return v == null ? "–" : (v > 0 ? "+" + v : String(v)); }

  /* ---------- agenda et itinéraire ---------- */
  function gcal(m) {
    var s = d(m.coupEnvoi), e = new Date(s.getTime() + 2 * 3600e3);
    var f = function (x) { return x.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); };
    return "https://calendar.google.com/calendar/render?" + new URLSearchParams({ action: "TEMPLATE", text: nice(m.equipeDomicile) + " – " + nice(m.equipeExterieur), dates: f(s) + "/" + f(e), location: m.lieu || "", details: (m.competition || "") + "\n" + (m.page || ""), ctz: "Europe/Paris" }).toString();
  }
  function ics(m) { return new URL("data/ics/" + encodeURIComponent(m.id) + ".ics", ROOT).href; }
  function subs() {
    var https = new URL("data/agenda-matchs.ics", ROOT).href, webcal = https.replace(/^https?:/, "webcal:");
    return { google: "https://calendar.google.com/calendar/r?cid=" + encodeURIComponent(webcal), apple: webcal, url: https };
  }
  function agenda(m, cls) {
    return '<details class="pick"><summary class="btn ' + (cls || "btn--out") + '">Ajouter à l’agenda</summary><div class="menu"><a href="' + esc(gcal(m)) + '" target="_blank" rel="noopener">Google Agenda (Gmail, Android)</a><a href="' + esc(ics(m)) + '">iPhone, iPad, Outlook</a></div></details>';
  }
  function route(m, cls) {
    if (!m.itineraire) return "";
    return '<details class="pick"><summary class="btn ' + (cls || "") + '">Itinéraire</summary><div class="menu"><a href="' + esc(m.itineraire.google) + '" target="_blank" rel="noopener">Google Maps</a><a href="' + esc(m.itineraire.apple) + '" target="_blank" rel="noopener">Plans (Apple)</a><a href="' + esc(m.itineraire.waze) + '" target="_blank" rel="noopener">Waze</a></div></details>';
  }
  document.addEventListener("click", function (e) { document.querySelectorAll("details.pick[open]").forEach(function (x) { if (!x.contains(e.target)) x.removeAttribute("open"); }); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") document.querySelectorAll("details.pick[open]").forEach(function (x) { x.removeAttribute("open"); x.querySelector("summary").focus(); }); });

  /* ---------- logique ---------- */
  function outcome(m) {
    if (!m.joue || m.scoreDomicile == null) return null;
    var rb = m.rbbaADomicile ? m.scoreDomicile : m.scoreExterieur, adv = m.rbbaADomicile ? m.scoreExterieur : m.scoreDomicile;
    return rb > adv ? "win" : "loss";
  }
  function liveFor(L, m) { return (L.enDirect || []).filter(function (l) { return String(l.id) === String(m.id); })[0]; }
  function mainPoule(C) { var ps = C.poules || []; return ps.filter(function (p) { return p.principale; })[0] || ps[0]; }
  var LOGO = new URL("assets/logo.webp", ROOT).href;
  function initials(nm) {
    var w = nice(nm).replace(/\b(Basket|Ball|Basketball|Club|Section|Sport(s|ive)?|De|Du|Des|La|Le|Les|Et|Athletique)\b/gi, " ").trim().split(/\s+/).filter(Boolean);
    return (w.length ? w : [nm]).slice(0, 3).map(function (x) { return x[0]; }).join("").toUpperCase();
  }
  function crest(nm, cls, logo) {
    var src = isRbba(nm) ? LOGO : logo ? (/^https?:/.test(logo) ? logo : new URL(logo, ROOT).href) : "";
    return '<span class="crest' + (cls ? " " + cls : "") + '" aria-hidden="true">' + (src ? '<img src="' + esc(src) + '" alt="" loading="lazy" onerror="this.replaceWith(document.createTextNode(\'' + esc(initials(nm)) + '\'))">' : esc(initials(nm))) + "</span>";
  }
  function sb(v, win, rb, cls) { return '<span class="sb' + (win ? " w" : "") + (rb ? " rb" : "") + (cls ? " " + cls : "") + '">' + v + "</span>"; }
  function dshort(iso) { var x = d(iso); return J3[x.getDay()] + " " + String(x.getDate()).padStart(2, "0") + "/" + String(x.getMonth() + 1).padStart(2, "0"); }
  function comp(m) { return /division 2/i.test(m.competition || "") ? "DM2" : (m.competition || ""); }

  /* ---------- accueil : prochain match ---------- */
  function renderNext(el, matchs, L) {
    var cur = matchs.filter(function (m) { return liveFor(L, m); })[0];
    var m = cur || matchs.filter(function (x) { return !x.joue && d(x.coupEnvoi) > new Date(Date.now() - 3 * 3600e3); })[0];
    if (!m) { el.innerHTML = '<div class="wrap"><p class="next-top"><b>Prochain match</b></p><p style="margin-top:16px">Le calendrier sera publié dès sa programmation par la FFBB.</p></div>'; return; }
    var lv = liveFor(L, m);
    var side = function (nm, tg, lg) { return '<div class="side">' + crest(nm, "", lg) + '<span class="nm">' + esc(nice(nm)) + '</span><span class="tg">' + tg + "</span></div>"; };
    var mid = lv
      ? '<div class="mid"><span class="vs">' + esc(lv.periode || "En direct") + '</span><div class="live-score">' + sb(lv.scoreDomicile, lv.scoreDomicile > lv.scoreExterieur, false, "sb--lg") + sb(lv.scoreExterieur, lv.scoreExterieur > lv.scoreDomicile, false, "sb--lg") + "</div></div>"
      : '<div class="mid"><span class="time">' + heure(m.coupEnvoi) + '</span><span class="vs">VS</span></div>';
    el.innerHTML = '<div class="wrap">' +
      '<p class="next-top"><span><b>' + (lv ? "En direct" : "Prochain match") + "</b> · " + esc(comp(m)) + (m.journee ? " · J" + m.journee : "") + "</span><span>" + dayLong(m.coupEnvoi) + "</span></p>" +
      '<div class="versus">' + side(m.equipeDomicile, "Domicile", m.logoDomicile) + mid + side(m.equipeExterieur, "Extérieur", m.logoExterieur) + "</div>" +
      '<div class="next-bottom"><p class="venue">' + esc((m.lieu || "").split(",")[0]) + "<small>" + esc((m.lieu || "").split(",").slice(1).join(",").trim()) + "</small></p>" +
      (lv ? "" : '<p class="countdown" aria-label="Compte à rebours"><b data-cd="j">–</b>j <b data-cd="h">–</b>h <b data-cd="m">–</b>min</p>') +
      '<div class="btns">' + agenda(m, "btn--out-l") + route(m) + "</div></div></div>";
    if (!lv) {
      var t = d(m.coupEnvoi).getTime();
      var tick = function () {
        var ms = Math.max(0, t - Date.now());
        [["j", Math.floor(ms / 864e5)], ["h", String(Math.floor(ms / 36e5) % 24).padStart(2, "0")], ["m", String(Math.floor(ms / 6e4) % 60).padStart(2, "0")]].forEach(function (p) { var b = el.querySelector('[data-cd="' + p[0] + '"]'); if (b) b.textContent = p[1]; });
      };
      tick(); clearInterval(el._t); el._t = setInterval(tick, 20000);
    }
  }

  /* ---------- une ligne de match (résultats et calendrier) ---------- */
  function game(m, L, withActions) {
    var o = outcome(m), lv = liveFor(L, m), futur = !m.joue && d(m.coupEnvoi) > new Date();
    var s1 = lv ? lv.scoreDomicile : m.scoreDomicile, s2 = lv ? lv.scoreExterieur : m.scoreExterieur;
    var hasScore = s1 != null && s2 != null && (m.joue || lv);
    var row = function (nm, s, other, lg) { return '<div class="g-row' + (isRbba(nm) ? " rb" : "") + '">' + crest(nm, "crest--sm", lg) + '<span class="t">' + esc(nice(nm)) + "</span>" + (hasScore ? sb(s, s > other, isRbba(nm)) : "") + "</div>"; };
    var wl = lv ? '<span class="wl n" title="En direct">•</span>' : o ? '<span class="wl ' + (o === "win" ? "v" : "d") + '" title="' + (o === "win" ? "Victoire" : "Défaite") + '">' + (o === "win" ? "V" : "D") + "</span>" : '<span class="wl n" title="' + (m.rbbaADomicile ? "Domicile" : "Extérieur") + '">' + (m.rbbaADomicile ? "DOM" : "EXT") + "</span>";
    return '<li class="game"><p class="g-date">' + dshort(m.coupEnvoi) + "<small>" + (hasScore ? (lv ? "En direct" : "Terminé") : heure(m.coupEnvoi)) + (m.journee ? " · J" + m.journee : "") + "</small></p>" + wl +
      '<div class="g-teams">' + row(m.equipeDomicile, s1, s2, m.logoDomicile) + row(m.equipeExterieur, s2, s1, m.logoExterieur) + "</div>" +
      '<p class="g-info">' + esc((m.lieu || "").split(",")[0]) + "</p>" +
      '<div class="g-actions">' + (withActions && futur ? agenda(m) + route(m, "btn--dark") : "") + (m.page && !futur ? '<a class="btn btn--out" href="' + esc(m.page) + '">Feuille de match</a>' : "") + "</div></li>";
  }
  function renderResults(el, matchs, L, n0) {
    var list = matchs.filter(function (m) { return m.joue || liveFor(L, m); }).reverse().slice(0, n0 || 99);
    el.innerHTML = list.length ? list.map(function (m) { return game(m, L, false); }).join("") : '<li class="game"><p class="g-info" style="text-align:left;grid-column:1/-1">Aucun match joué pour l’instant.</p></li>';
  }
  function renderUpcoming(el, matchs, L, n0) {
    var list = matchs.filter(function (m) { return !m.joue && !liveFor(L, m) && d(m.coupEnvoi) > new Date(Date.now() - 3 * 3600e3); }).slice(0, n0 || 99);
    el.innerHTML = list.length ? list.map(function (m) { return game(m, L, true); }).join("") : '<li class="game"><p class="g-info" style="text-align:left;grid-column:1/-1">Aucun match programmé.</p></li>';
  }

  /* ---------- classement ---------- */
  function evo(r) { return !r.evolution ? "" : r.evolution > 0 ? '<span class="evo up" title="Gagne ' + r.evolution + ' place(s)">▲' + r.evolution + "</span>" : '<span class="evo down" title="Perd ' + (-r.evolution) + ' place(s)">▼' + (-r.evolution) + "</span>"; }
  function renderStandings(el, p, maj, full) {
    var note = $("#std-note");
    if (!p || !p.lignes || !p.lignes.length) { el.innerHTML = '<p class="std-note">Le classement s’affichera après la première journée.</p>'; if (note) note.textContent = ""; return; }
    if (note) note.innerHTML = '<span class="src">' + (p.source === "calcule" ? "Calculé d’après les scores" : "Officiel FFBB") + "</span>" + esc(p.competition) + (p.poule ? " · " + esc(p.poule) : "") + " · mis à jour " + stamp(maj);
    var head = full ? "<th scope=\"col\">#</th><th scope=\"col\">Équipe</th><th scope=\"col\"><abbr title=\"Matchs joués\">J</abbr></th><th scope=\"col\"><abbr title=\"Victoires\">V</abbr></th><th scope=\"col\"><abbr title=\"Défaites\">D</abbr></th><th scope=\"col\"><abbr title=\"Points marqués\">P+</abbr></th><th scope=\"col\"><abbr title=\"Points encaissés\">P-</abbr></th><th scope=\"col\">+/-</th><th scope=\"col\"><abbr title=\"Points au classement\">Pts</abbr></th>"
      : "<th scope=\"col\">#</th><th scope=\"col\">Équipe</th><th scope=\"col\"><abbr title=\"Matchs joués\">J</abbr></th><th scope=\"col\"><abbr title=\"Victoires\">V</abbr></th><th scope=\"col\"><abbr title=\"Défaites\">D</abbr></th><th scope=\"col\"><abbr title=\"Points au classement\">Pts</abbr></th>";
    el.innerHTML = '<div class="tbl-wrap"><table class="std"><thead><tr>' + head + "</tr></thead><tbody>" + p.lignes.map(function (r) {
      var cells = "<td>" + n(r.rang) + evo(r) + '</td><td><span class="team">' + crest(r.equipe, "crest--sm", r.logo) + esc(nice(r.equipe)) + (r.estRBBA ? ' <span class="sr">(RBBA)</span>' : "") + "</span></td><td>" + n(r.joues) + "</td><td>" + n(r.victoires) + "</td><td>" + n(r.defaites) + "</td>";
      if (full) cells += "<td>" + n(r.pointsPour) + "</td><td>" + n(r.pointsContre) + "</td><td>" + signed(r.difference) + "</td>";
      return "<tr" + (r.estRBBA ? ' class="me"' : "") + ">" + cells + '<td class="pts">' + n(r.points) + "</td></tr>";
    }).join("") + "</tbody>" + (full ? "<caption>" + (p.source === "calcule" ? "Recalculé à partir des scores officiels en attendant la mise à jour FFBB : victoire 2 pts, défaite 1 pt." : "Source : FFBB.") + "</caption>" : "") + "</table></div>";
  }
  function tabs() {
    var list = $('[role="tablist"]'); if (!list) return;
    var btns = [].slice.call(list.querySelectorAll('[role="tab"]'));
    function show(id, focus) {
      btns.forEach(function (b) { var on = b.getAttribute("aria-controls") === id; b.setAttribute("aria-selected", on); b.tabIndex = on ? 0 : -1; document.getElementById(b.getAttribute("aria-controls")).hidden = !on; if (on && focus) b.focus(); });
      try { history.replaceState(null, "", "#" + id); } catch (e) {}
    }
    btns.forEach(function (b, i) {
      b.addEventListener("click", function () { show(b.getAttribute("aria-controls")); });
      b.addEventListener("keydown", function (e) { var k = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (!k) return; e.preventDefault(); show(btns[(i + k + btns.length) % btns.length].getAttribute("aria-controls"), true); });
    });
    var id = location.hash.slice(1); if (btns.some(function (b) { return b.getAttribute("aria-controls") === id; })) show(id);
  }

  /* ---------- bandeaux ---------- */
  function notices(M, L) {
    var top = $("#banners"); if (!top) return;
    var h = M.exemple ? '<div class="notice">Aperçu : calendrier de novembre réel, scores et classement fictifs. En ligne, tout vient de la FFBB.</div>' : "";
    var l = (L.enDirect || [])[0];
    if (l) h += '<div class="notice notice--live" role="status">En direct : ' + esc(nice(l.equipeDomicile)) + " " + l.scoreDomicile + " · " + l.scoreExterieur + " " + esc(nice(l.equipeExterieur)) + ' · <a href="matchs.html">suivre</a></div>';
    top.innerHTML = h;
  }

  /* ---------- démarrage ---------- */
  function boot() {
    var mb = $(".menu-btn"), nav = $(".nav");
    if (mb) {
      var setOpen = function (o) { nav.classList.toggle("open", o); mb.setAttribute("aria-expanded", o); mb.setAttribute("aria-label", o ? "Fermer le menu" : "Ouvrir le menu"); document.body.style.overflow = o ? "hidden" : ""; };
      mb.addEventListener("click", function () { setOpen(!nav.classList.contains("open")); });
      nav.addEventListener("click", function (e) { if (e.target.closest("a")) setOpen(false); });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape" && nav.classList.contains("open")) { setOpen(false); mb.focus(); } });
    }
    document.querySelectorAll("[data-copy]").forEach(function (b) {
      b.addEventListener("click", function () { var t = b.getAttribute("data-copy"); (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () { b.textContent = "Copié"; }, function () { b.textContent = t; }); });
    });
    var s = subs();
    document.querySelectorAll("[data-sub]").forEach(function (a) { a.href = s[a.getAttribute("data-sub")]; });
    document.querySelectorAll("[data-feed]").forEach(function (x) { x.textContent = s.url; var c = x.nextElementSibling; if (c && c.matches("[data-copy]")) c.setAttribute("data-copy", s.url); });
    tabs();

    var page = (document.querySelector("[data-page]") || document.body).getAttribute("data-page");
    if (page !== "home" && page !== "matchs") return;
    var sig = "";
    function render(M, C, L) {
      var k = JSON.stringify([M.miseAJour, C.miseAJour, L.enDirect]);
      if (k === sig) return (L.enDirect || []).length > 0; // rien de neuf : aucun saut à l'écran
      sig = k;
      var matchs = (M.matchs || []).filter(function (m) { return m.coupEnvoi; }), p = mainPoule(C);
      notices(M, L);
      if (page === "home") { renderNext($("#next"), matchs, L); renderResults($("#results"), matchs, L, 3); renderStandings($("#standings"), p, C.miseAJour, false); }
      else { $("#c-next").textContent = matchs.filter(function (m) { return !m.joue; }).length; $("#c-played").textContent = matchs.filter(function (m) { return m.joue; }).length; renderUpcoming($("#upcoming"), matchs, L); renderResults($("#results"), matchs, L); renderStandings($("#standings"), p, C.miseAJour, true); $("#maj").textContent = "Mis à jour " + stamp(M.miseAJour) + " · source FFBB"; }
      document.dispatchEvent(new CustomEvent("rbba:rendered"));
      return (L.enDirect || []).length > 0;
    }
    try { var c = JSON.parse(localStorage.getItem("rbba-data") || "null"); if (c) render(c[0], c[1], c[2]); } catch (e) {}
    function load() {
      return Promise.all([get("data/matchs.json"), get("data/classement.json").catch(function () { return { poules: [] }; }), get("data/live.json").catch(function () { return { enDirect: [] }; })])
        .then(function (r) { try { localStorage.setItem("rbba-data", JSON.stringify(r)); } catch (e) {} return render(r[0], r[1], r[2]); })
        .catch(function () {
          if (sig) return false;
          ["#next", "#upcoming", "#standings"].forEach(function (q) { var el = $(q); if (el) el.innerHTML = '<div class="wrap"><p class="mut">Les données des matchs sont momentanément indisponibles. Réessayez dans quelques minutes.</p></div>'; });
          return false;
        });
    }
    (function loop() { load().then(function (live) { setTimeout(loop, live ? 60e3 : 600e3); }); })();
  }
  if ("serviceWorker" in navigator && location.protocol === "https:" && !/claude|artifact/.test(location.hostname)) navigator.serviceWorker.register(new URL("sw.js", ROOT).href).catch(function () {});
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
