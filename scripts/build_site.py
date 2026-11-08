"""Génère les pages HTML du site (gabarits communs). Lancer : python3 scripts/build_site.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600;700&display=swap">'
# Coordonnées du Gymnase de Roisel (rue de Cambrai). EXACT = True affiche le repère sur la carte.
LAT, LON = 49.952727, 3.103363
EXACT = True
MARKER = f"&amp;marker={LAT}%2C{LON}" if EXACT else ""
MAPS = "Gymnase%20de%20Roisel%2C%2048%20Rue%20de%20Cambrai%2C%2080240%20Roisel"
GEO = f"{LAT},{LON}"
# Inscriptions en ligne (HelloAsso) : dès qu'il est renseigné, les boutons des licences y mènent
HELLOASSO = "https://www.helloasso.com/associations/roisel-basketball/adhesions/adhesion-au-club"
# Photos : déposer les fichiers dans assets/photos/ puis les lister dans data/photos.json
import json as _json
PHOTOS = _json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8")) if (ROOT / "data" / "photos.json").exists() else {}

# Liens des réseaux du club : la section s'affiche dès qu'au moins un lien est renseigné
INSTAGRAM = "https://www.instagram.com/roiselbasketball/"
FACEBOOK = "https://www.facebook.com/share/18sTYZXxJF/"
# Flux Instagram (Behold) : identifiant du flux
BEHOLD = "quMGqyDE08fF7hLVtnYc"
ONESIGNAL_APP = "7a9ac6d3-6447-4312-8d8b-02bbcdf13915"
IG_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>'
FB_SVG = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 21v-7.5h2.5l.4-3h-2.9V8.6c0-.9.3-1.5 1.5-1.5h1.5V4.4c-.3 0-1.2-.1-2.2-.1-2.2 0-3.7 1.3-3.7 3.8v2.4H8v3h2.6V21h2.9z"/></svg>'


def social():
    links = []
    if INSTAGRAM: links.append(f'<a href="{INSTAGRAM}" target="_blank" rel="noopener">{IG_SVG}<span>Instagram<small>Photos et affiches de match</small></span></a>')
    if FACEBOOK: links.append(f'<a href="{FACEBOOK}" target="_blank" rel="noopener">{FB_SVG}<span>Facebook<small>Résultats et infos du club</small></span></a>')
    if not links and not BEHOLD: return ""
    feed = ""
    if BEHOLD:
        feed = (f'<div class="ig-feed"><behold-widget feed-id="{BEHOLD}"></behold-widget></div>'
                '<script>(()=>{if(window.__bhldScript)return;window.__bhldScript=true;const d=document,s=d.createElement("script");s.type="module";s.src="https://w.behold.so/widget.js";setTimeout(()=>{d.head.append(s);},0);})();</script>')
    return '<section class="block wrap" id="reseaux" aria-labelledby="h-soc"><div class="head"><h2 id="h-soc">Suivez le RBBA</h2>' + (f'<a class="more" href="{INSTAGRAM}" target="_blank" rel="noopener">@roiselbasketball</a>' if INSTAGRAM else "") + '</div>' + feed + '<div class="social-links">' + "".join(links) + "</div></section>"


def onesignal():
    if not ONESIGNAL_APP: return ""
    return ('<script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>'
            '<script>window.OneSignalDeferred=window.OneSignalDeferred||[];OneSignalDeferred.push(async function(OneSignal){'
            f'await OneSignal.init({{appId:"{ONESIGNAL_APP}",safari_web_id:"web.onesignal.auto.458f9dc8-6677-4788-b5a2-9d66a9d7a179",'
            'serviceWorkerPath:"sw.js",serviceWorkerParam:{scope:"/"},notifyButton:{enable:false}});'
            'document.dispatchEvent(new CustomEvent("rbba:onesignal"));});</script>')


def alerts():
    if not ONESIGNAL_APP: return ""
    return '''<section class="block wrap alerts" id="alertes" aria-labelledby="h-al">
  <div class="alerts-box">
    <div><h2 id="h-al">Alertes de match</h2><p>Une notification le jour du match, le score final, et chaque nouveau post Instagram du club. Gratuit, désactivable à tout moment.</p>
    <p class="alerts-ios" hidden>Sur iPhone : installez d'abord l'appli (bouton « Installer l'appli » en haut), ouvrez-la depuis l'écran d'accueil, puis revenez ici.</p></div>
    <div class="alerts-act"><button class="btn" type="button" id="alerts-btn">Recevoir les alertes</button><p class="alerts-status" role="status" aria-live="polite"></p></div>
  </div>
</section>'''


def head(title, desc, p=""):
    return f'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="{desc}">
<meta name="theme-color" content="#121010">
<link rel="manifest" href="{p}manifest.webmanifest">
<link rel="icon" href="{p}assets/icon-192.png">
<link rel="apple-touch-icon" href="{p}assets/apple-touch-icon.png">
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="RBBA">
{FONTS}
<link rel="stylesheet" href="{p}assets/style.css">
<script src="{p}assets/ui.js" defer></script>
<script src="{p}assets/app.js" defer></script>
{onesignal()}
</head>
'''


def header(cur, p=""):
    items = [("matchs.html", "Matchs"), ("matchs.html#classement", "Classement"), ("index.html#licences", "Licences"), ("index.html#gymnase", "Gymnase"), ("#contact", "Contact")]
    links = "".join(f'<a href="{p if not h.startswith("#") else ""}{h}"{" aria-current=\"page\"" if h == cur else ""}>{l}</a>' for h, l in items)
    return f'''<a class="skip" href="#main">Aller au contenu</a>
<div class="topbar"><div class="wrap"><span class="long">Licences 2026-2027 : jeunes 70&nbsp;€ · seniors 90&nbsp;€</span><span class="short">Licences 70&nbsp;€ · 90&nbsp;€</span><a href="{HELLOASSO or p + 'index.html#licences'}"{' target="_blank" rel="noopener"' if HELLOASSO else ''}>S'inscrire</a></div></div>
<header class="hdr">
  <div class="wrap">
    <a class="brand" href="{p}index.html"><img src="{p}assets/logo.webp" alt="" width="52" height="48"><span>Roisel Basketball<small>RBBA · Seniors DM2</small></span></a>
    <nav class="nav" id="nav" aria-label="Navigation principale">{links}</nav>
    <div class="tools">
      <button class="install-btn" type="button" aria-haspopup="dialog" aria-controls="install-help"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M12 7v7M9 11l3 3 3-3"/></svg><span>Installer l'appli</span></button>
      <button class="ibtn a11y-btn" type="button" aria-haspopup="dialog" aria-controls="a11y" aria-expanded="false" aria-label="Accessibilité"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="4.5" r="1.8" fill="currentColor" stroke="none"/><path d="M5 8.5l7 1.5 7-1.5M12 10v4.5M12 14.5l-3.5 6M12 14.5l3.5 6"/></svg></button>
      <button class="ibtn menu-btn" type="button" aria-expanded="false" aria-controls="nav" aria-label="Ouvrir le menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
    </div>
  </div>
</header>
<div class="install-help" id="install-help" role="dialog" aria-labelledby="ih-title" hidden>
  <h2 id="ih-title">Ajouter le RBBA à l'écran d'accueil</h2>
  <ol class="steps ih-ios">
    <li>Touchez le bouton <strong>Partager</strong> <svg class="ih-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 11v9h14v-9"/></svg><span>En bas de l'écran dans Safari</span></li>
    <li>Choisissez <strong>Sur l'écran d'accueil</strong><span>Faites défiler la liste si besoin</span></li>
    <li>Touchez <strong>Ajouter</strong><span>L'icône RBBA apparaît avec vos applis</span></li>
  </ol>
  <ol class="steps ih-android" hidden>
    <li>Touchez le menu <strong>⋮</strong><span>En haut à droite dans Chrome</span></li>
    <li>Choisissez <strong>Ajouter à l'écran d'accueil</strong><span>Ou « Installer l'application »</span></li>
    <li>Touchez <strong>Installer</strong><span>L'icône RBBA apparaît avec vos applis</span></li>
  </ol>
  <button class="btn btn--dark ih-close" type="button">Compris</button>
</div>
<div class="a11y" id="a11y" role="dialog" aria-labelledby="a11y-title" hidden>
  <h2 id="a11y-title">Accessibilité</h2>
  <fieldset><legend>Taille du texte</legend><div class="seg">
    <label><input type="radio" name="a11y-text" id="a11y-t1" value="" checked><span>Normale</span></label>
    <label><input type="radio" name="a11y-text" id="a11y-t2" value="text-lg"><span>Grande</span></label>
    <label><input type="radio" name="a11y-text" id="a11y-t3" value="text-xl"><span>Très grande</span></label></div></fieldset>
  <fieldset><legend>Animations</legend><div class="seg">
    <label><input type="radio" name="a11y-motion" id="a11y-m1" value="" checked><span>Normales</span></label>
    <label><input type="radio" name="a11y-motion" id="a11y-m2" value="reduce-motion"><span>Aucune</span></label></div></fieldset>
  <fieldset><legend>Contraste</legend><div class="seg">
    <label><input type="radio" name="a11y-contrast" id="a11y-c1" value="" checked><span>Normal</span></label>
    <label><input type="radio" name="a11y-contrast" id="a11y-c2" value="contrast"><span>Renforcé</span></label></div></fieldset>
  <button class="btn btn--dark a11y-close" type="button">Fermer</button>
</div>
<div id="banners"></div>
'''


def socials_ftr():
    out = ""
    if INSTAGRAM: out += f'<li><a href="{INSTAGRAM}" target="_blank" rel="noopener">Instagram</a></li>'
    if FACEBOOK: out += f'<li><a href="{FACEBOOK}" target="_blank" rel="noopener">Facebook</a></li>'
    return out


def footer(p=""):
    return f'''<footer class="ftr" id="contact">
  <div class="wrap">
    <div class="ftr-grid">
      <div class="ftr-brand"><img src="{p}assets/logo.webp" alt="Logo Roisel Basketball" width="72" height="66"><b>Roisel<br>Basketball</b></div>
      <div><h2>Contact</h2><ul><li><a class="tel" href="tel:+33616016765">06 16 01 67 65</a></li><li><a href="mailto:roiselbasketball@gmail.com">roiselbasketball@gmail.com</a></li>{socials_ftr()}</ul></div>
      <div><h2>Gymnase</h2><ul><li>Gymnase de Roisel</li><li>48 Rue de Cambrai, 80240 Roisel</li><li><a href="https://www.google.com/maps/dir/?api=1&amp;destination={GEO}" target="_blank" rel="noopener">Itinéraire</a></li></ul></div>
      <div><h2>Le site</h2><ul><li><a href="{p}matchs.html">Matchs</a></li><li><a href="{p}matchs.html#classement">Classement</a></li><li><a href="{p}index.html#licences">Licences</a></li><li><a href="{p}appli.html">L'appli RBBA</a></li></ul></div>
    </div>
    <div class="ftr-bottom"><span>© 2026 Roisel Basketball · Données FFBB</span><span><a href="{p}mentions-legales.html">Mentions légales</a> · <a href="{p}mentions-legales.html#confidentialite">Confidentialité</a> · <a href="{p}mentions-legales.html#accessibilite">Accessibilité</a></span></div>
  </div>
</footer>
'''


def lic_btns(label, cls, subject):
    if HELLOASSO:
        return f'<div class="btns"><a class="btn {cls}" href="{HELLOASSO}" target="_blank" rel="noopener">{label} en ligne</a><a class="btn btn--out" href="tel:+33616016765">Appeler</a></div>'
    return f'<div class="btns"><a class="btn {cls}" href="tel:+33616016765">{label}</a><a class="btn btn--out" href="mailto:roiselbasketball@gmail.com?subject={subject}">Par e-mail</a></div>'


def gallery():
    pics = PHOTOS.get("accueil", [])[:6]
    if not pics:
        return ""
    credit = PHOTOS.get("credit", "")
    items = "".join(f'<figure><img src="{x["fichier"]}" alt="{x.get("legende","Photo de match du RBBA")}" loading="lazy" width="800" height="600"></figure>' for x in pics)
    return f'''  <section class="block wrap" id="photos" aria-labelledby="h-ph">
    <div class="head"><h2 id="h-ph">En images</h2>{f'<span class="credit">Photos : {credit}</span>' if credit else ''}</div>
    <div class="gallery">{items}</div>
  </section>
'''


def hero_style():
    h = PHOTOS.get("bandeau")
    return f' style="--photo:url(\'/{h.lstrip("/")}\')"' if h else ""


def home():
    return head("RBBA – Roisel Basketball | Club de basket à Roisel (Somme)", "Roisel Basketball (RBBA) : prochain match au Gymnase de Roisel, résultats et classement de l'équipe seniors en DM2, licences jeunes 70 € et seniors 90 €.") + f'''<body data-page="home">
{header("index.html")}
<main id="main" tabindex="-1">
  <section class="next{' has-photo' if PHOTOS.get('bandeau') else ''}"{hero_style()} id="next" aria-label="Prochain match" aria-live="polite"><div class="wrap"><p class="next-top"><b>Prochain match</b></p><div class="versus" style="min-height:150px"></div></div></section>

  <div class="block wrap duo">
    <section aria-labelledby="h-res"><div class="head"><h2 id="h-res">Résultats</h2><a class="more" href="matchs.html#resultats"><span class="lg">Tous les résultats</span><span class="sm">Tous</span></a></div><ul class="games" id="results"></ul></section>
    <section aria-labelledby="h-std"><div class="head"><h2 id="h-std">Classement DM2</h2><a class="more" href="matchs.html#classement"><span class="lg">Classement complet</span><span class="sm">Complet</span></a></div><div id="standings"></div></section>
  </div>

  {social()}
  {alerts()}

  <section class="block wrap" id="licences" aria-labelledby="h-lic">
    <div class="head"><h2 id="h-lic">Licences 2026-2027</h2></div>
    <div class="offers">
      <article class="offer"><h3>Licence jeune</h3><p class="who">Enfants de moins de 12 ans</p><p class="price">70&nbsp;€<small>la saison</small></p><ul><li>Licence FFBB 2026-2027</li><li>Entraînements au Gymnase de Roisel</li></ul>{lic_btns("Inscrire mon enfant", "btn--dark", "Licence%20jeune%202026-2027")}</article>
      <article class="offer gold"><h3>Licence senior</h3><p class="price">90&nbsp;€<small>la saison</small></p><ul><li>Licence FFBB 2026-2027</li><li>Équipe seniors en DM2</li></ul>{lic_btns("Prendre ma licence", "", "Licence%20senior%202026-2027")}</article>
    </div>
  </section>

  <section class="block wrap" id="gymnase" aria-labelledby="h-gym">
    <div class="head"><h2 id="h-gym">Le gymnase</h2></div>
    <div class="venue-grid">
      <div class="map">
        <p class="map-fallback">Gymnase de Roisel<br>48 Rue de Cambrai, 80240 Roisel</p>
        <iframe title="Carte : Gymnase de Roisel" loading="lazy" src="https://www.openstreetmap.org/export/embed.html?bbox={LON-0.012}%2C{LAT-0.006}%2C{LON+0.012}%2C{LAT+0.006}&amp;layer=mapnik{MARKER}"></iframe>
      </div>
      <div class="venue-info">
        <h3>Gymnase de Roisel</h3>
        <p class="addr">Complexe sportif<br>48 Rue de Cambrai, 80240 Roisel</p>
        <dl><dt>Matchs à domicile</dt><dd>Le samedi soir · horaires dans le calendrier</dd></dl>
        <div class="btns"><a class="btn btn--dark" href="https://www.google.com/maps/dir/?api=1&amp;destination={GEO}" target="_blank" rel="noopener">Google Maps</a><a class="btn btn--out" href="https://maps.apple.com/?daddr={GEO}&amp;q=Gymnase%20de%20Roisel" target="_blank" rel="noopener">Apple Plans</a><a class="btn btn--out" href="https://waze.com/ul?ll={GEO}&amp;navigate=yes" target="_blank" rel="noopener">Waze</a></div>
        <details class="pick"><summary class="btn btn--out">Ajouter les matchs à mon agenda</summary><div class="menu"><a data-sub="google" href="#" target="_blank" rel="noopener">Google Agenda (Gmail, Android)</a><a data-sub="apple" href="#">iPhone, iPad, Mac</a></div></details>
      </div>
    </div>
  </section>

{gallery()}

  <section class="block wrap" id="partenaires" aria-labelledby="h-sp">
    <div class="head"><h2 id="h-sp">Partenaires</h2></div>
    <div class="partner-cta"><p><strong>Votre entreprise aux côtés du RBBA</strong><br>Logo sur le site, les affiches de match et au gymnase.</p><a class="btn btn--dark" href="tel:+33616016765">06 16 01 67 65</a></div>
  </section>
</main>
{footer()}</body>
</html>
'''


def matchs():
    return head("Matchs et classement – RBBA Roisel Basketball", "Calendrier, résultats, scores en direct et classement DM2 de Roisel Basketball (RBBA), mis à jour automatiquement depuis la FFBB.") + f'''<body data-page="matchs">
{header("matchs.html")}
<main id="main" tabindex="-1">
  <section class="page-head">
    <div class="wrap">
      <h1>Matchs</h1>
      <p id="maj">Seniors · Départementale Masculine 2 · saison 2026-2027</p>
      <div class="btns"><details class="pick"><summary class="btn">Ajouter les matchs à mon agenda</summary><div class="menu"><a data-sub="google" href="#" target="_blank" rel="noopener">Google Agenda (Gmail, Android)</a><a data-sub="apple" href="#">iPhone, iPad, Mac</a></div></details></div>
      <div class="tabs" role="tablist" aria-label="Matchs">
        <button class="tab" role="tab" id="tab-a-venir" aria-controls="a-venir" aria-selected="true">À venir<span class="count" id="c-next"></span></button>
        <button class="tab" role="tab" id="tab-resultats" aria-controls="resultats" aria-selected="false" tabindex="-1">Résultats<span class="count" id="c-played"></span></button>
        <button class="tab" role="tab" id="tab-classement" aria-controls="classement" aria-selected="false" tabindex="-1">Classement</button>
      </div>
    </div>
  </section>
  <div class="wrap">
    <section class="panel" role="tabpanel" id="a-venir" aria-labelledby="tab-a-venir"><ul class="games" id="upcoming"></ul></section>
    <section class="panel" role="tabpanel" id="resultats" aria-labelledby="tab-resultats" hidden><ul class="games" id="results"></ul></section>
    <section class="panel" role="tabpanel" id="classement" aria-labelledby="tab-classement" hidden><p class="std-note" id="std-note"></p><div id="standings"></div></section>
  </div>
</main>
{footer()}</body>
</html>
'''


def appli():
    ios = '''<svg class="phone" viewBox="0 0 200 380" role="img" aria-labelledby="t-ios"><title id="t-ios">iPhone dans Safari : le bouton Partager est en bas, au centre.</title><rect class="ph-bg" width="200" height="380" rx="18"/><rect class="ph-ui" x="12" y="14" width="176" height="22" rx="11"/><text class="ph-tx" x="100" y="29" font-size="10" text-anchor="middle">roiselbasketball.fr</text><rect class="ph-ui" x="12" y="50" width="176" height="90"/><rect class="ph-ui" x="12" y="150" width="120" height="10"/><rect class="ph-ui" x="12" y="168" width="150" height="10"/><rect class="ph-ui" y="330" width="200" height="50"/><path d="M100 342 v14 M94 348 l6 -6 l6 6 M92 352 h-4 v12 h24 v-12 h-4" stroke="#FFF" stroke-width="2" fill="none"/><circle class="hl" cx="100" cy="353" r="18"/></svg>'''
    andr = '''<svg class="phone" viewBox="0 0 200 380" role="img" aria-labelledby="t-and"><title id="t-and">Android dans Chrome : le menu à trois points est en haut à droite.</title><rect class="ph-bg" width="200" height="380" rx="18"/><rect class="ph-ui" x="12" y="14" width="150" height="22" rx="11"/><text class="ph-tx" x="87" y="29" font-size="10" text-anchor="middle">roiselbasketball.fr</text><circle cx="180" cy="19" r="2.4" fill="#FFF"/><circle cx="180" cy="25" r="2.4" fill="#FFF"/><circle cx="180" cy="31" r="2.4" fill="#FFF"/><circle class="hl" cx="180" cy="25" r="14"/><rect class="ph-ui" x="12" y="50" width="176" height="90"/><rect class="ph-ui" x="12" y="150" width="120" height="10"/><rect class="ph-ui" x="12" y="168" width="150" height="10"/></svg>'''
    return head("L'appli RBBA – installer le site sur son téléphone", "Installer l'appli Roisel Basketball sur iPhone ou Android et ajouter les matchs du RBBA à son agenda.") + f'''<body data-page="appli">
{header("appli.html")}
<main id="main" tabindex="-1">
  <section class="page-head" style="padding-bottom:40px"><div class="wrap"><h1>L'appli RBBA</h1><p>Le site s'installe sur votre téléphone comme une appli. Gratuit, sans App Store ni Google Play.</p><div class="btns"><button class="btn" id="install" type="button" hidden>Installer</button></div></div></section>
  <section class="block wrap" aria-labelledby="h-inst">
    <div class="head"><h2 id="h-inst">Installer</h2></div>
    <div class="tuto">
      <div class="tuto-card" id="iphone">{ios}<div><h3>iPhone</h3><ol class="steps"><li>Ouvrir le site dans Safari</li><li>Toucher Partager<span>Le carré avec une flèche, en bas</span></li><li>« Sur l'écran d'accueil »</li><li>« Ajouter »</li></ol></div></div>
      <div class="tuto-card" id="android">{andr}<div><h3>Android</h3><ol class="steps"><li>Ouvrir le site dans Chrome</li><li>Toucher le menu ⋮<span>En haut à droite</span></li><li>« Installer l'application »</li><li>Confirmer</li></ol></div></div>
    </div>
  </section>
{alerts()}
  <section class="block wrap" id="agenda" aria-labelledby="h-ag">
    <div class="head"><h2 id="h-ag">Les matchs dans votre agenda</h2></div>
    <div class="tuto">
      <div class="tuto-card" style="grid-template-columns:1fr"><div><h3>Gmail · Android</h3><ol class="steps"><li>Toucher le bouton</li><li>Confirmer « Ajouter »</li></ol><div class="btns" style="margin-top:16px"><a class="btn btn--dark" data-sub="google" href="#" target="_blank" rel="noopener">Google Agenda</a></div></div></div>
      <div class="tuto-card" style="grid-template-columns:1fr"><div><h3>iPhone</h3><ol class="steps"><li>Toucher le bouton</li><li>Confirmer « S'abonner »</li></ol><div class="btns" style="margin-top:16px"><a class="btn btn--dark" data-sub="apple" href="#">Calendrier iPhone</a></div></div></div>
    </div>
    <p class="offers-note">Les horaires modifiés se mettent à jour seuls. Autre agenda : <code data-feed></code><button class="copy" type="button" data-copy="">Copier</button></p>
  </section>
</main>
{footer()}<script>(function(){{var ev=null,b=document.getElementById('install');addEventListener('beforeinstallprompt',function(e){{e.preventDefault();ev=e;b.hidden=false;}});b.addEventListener('click',function(){{if(!ev)return;ev.prompt();ev.userChoice.then(function(){{b.hidden=true;ev=null;}});}});}})();</script>
</body>
</html>
'''


def legal():
    return head("Mentions légales – RBBA Roisel Basketball", "Mentions légales, confidentialité et accessibilité du site de Roisel Basketball.") + f'''<body data-page="legal">
{header("")}
<main id="main" tabindex="-1">
  <section class="page-head" style="padding-bottom:40px"><div class="wrap"><h1>Mentions légales</h1></div></section>
  <section class="block wrap legal">
    <h2>Éditeur</h2><p>Roisel Basketball (RBBA), association loi 1901. Siège : [adresse], 80240 Roisel. RNA : [à compléter]. Contact : roiselbasketball@gmail.com · 06 16 01 67 65.</p>
    <h2>Directeur de la publication</h2><p>Le président de l'association.</p>
    <h2>Hébergeur</h2><p>[À compléter lors de la mise en ligne.]</p>
    <h2 id="confidentialite">Confidentialité</h2><p>Aucun cookie de suivi. Mesure d'audience anonyme. Les alertes de match passent par le service OneSignal : elles ne sont envoyées qu'aux personnes qui les ont acceptées, et se désactivent dans les réglages du téléphone ou du navigateur. Les données des formulaires servent uniquement à répondre aux demandes. Accès, rectification, suppression : roiselbasketball@gmail.com.</p>
    <h2>Droit à l'image</h2><p>Photos publiées avec l'autorisation écrite des licenciés, et de leurs représentants légaux pour les mineurs. Retrait sur simple demande.</p>
    <h2 id="accessibilite">Accessibilité</h2><p>Objectif : conformité RGAA niveau AA. Le bouton Accessibilité, en haut de chaque page, agrandit le texte, coupe les animations et renforce les contrastes. Signaler un problème : roiselbasketball@gmail.com.</p>
    <h2>Données sportives</h2><p>Calendriers, résultats et classements : données publiques de la FFBB.</p>
  </section>
</main>
{footer()}</body>
</html>
'''


if __name__ == "__main__":
    for name, fn in [("index.html", home), ("matchs.html", matchs), ("appli.html", appli), ("mentions-legales.html", legal)]:
        (ROOT / name).write_text(fn(), encoding="utf-8")
    print("pages générées")
