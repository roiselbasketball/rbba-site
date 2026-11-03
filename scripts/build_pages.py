"""
Génère les pages statiques lisibles par Google à partir des données FFBB :
  - une page par match (matchs/<id>/index.html),
  - un fichier agenda par match (data/ics/<id>.ics) pour iPhone / Outlook,
  - le plan du site (sitemap.xml).
Appelé automatiquement par ffbb_sync.py après chaque récupération.
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def nice(name: str) -> str:
    name = re.sub(r"\s*\([^)]*\)", "", str(name or ""))
    name = re.sub(r"\s+-\s+(\d+)$", r" \1", name)
    s = re.sub(r"(^|[\s\-'’])(\w)", lambda m: m.group(1) + m.group(2).upper(), str(name or "").lower())
    return re.sub(r"\b(Ca|Us|Uso|Bb|Bc|Es|As|Rbba)\b", lambda m: m.group(0).upper(), s)


def date_fr(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year} à {d.hour:02d}h{d.minute:02d}"


def match_page(m: dict, poule: dict | None, site_url: str) -> str:
    import json, sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_site as B
    e = html.escape
    dom, ext = nice(m["equipeDomicile"]), nice(m["equipeExterieur"])
    d = datetime.fromisoformat(m["coupEnvoi"]) if m.get("coupEnvoi") else None
    quand = date_fr(m["coupEnvoi"]) if d else "date à confirmer"
    jour = f"J{m['journee']}" if m.get("journee") else ""
    titre = f"{dom} – {ext}" + (f", DM2 {jour}" if jour else "") + (f", {d.day} {MOIS[d.month-1]} {d.year}" if d else "")
    joue = m.get("joue") and m.get("scoreDomicile") is not None
    def crest(n, logo=None):
        if "roisel" in n.lower():
            return '<span class="crest" aria-hidden="true"><img src="../../assets/logo.webp" alt=""></span>'
        if logo:
            src = logo if logo.startswith("http") else "../../" + logo
            return f'<span class="crest" aria-hidden="true"><img src="{e(src)}" alt=""></span>'
        w = [x for x in re.sub(r"\b(Basket|Ball|Basketball|Club|Section|De|Du|Des|La|Le|Les|Et)\b", " ", n, flags=re.I).split()] or [n]
        return f'<span class="crest" aria-hidden="true">{e("".join(x[0] for x in w[:3]).upper())}</span>'
    if joue:
        s1, s2 = m["scoreDomicile"], m["scoreExterieur"]
        rb = s1 if m.get("rbbaADomicile") else s2
        adv = s2 if m.get("rbbaADomicile") else s1
        verdict = "Victoire du RBBA" if rb > adv else "Défaite du RBBA"
        mid = f'<div class="mid"><span class="vs">Terminé</span><div class="score-pair"><span class="sb sb--lg{" w" if s1 > s2 else ""}">{s1}</span><span class="sb sb--lg{" w" if s2 > s1 else ""}">{s2}</span></div></div>'
        lieu_court = "à domicile" if m.get("rbbaADomicile") else f"à {ext if 'roisel' in dom.lower() else dom}"
        resume = f"{'Victoire' if rb > adv else 'Défaite'} {rb} à {adv} {lieu_court}"
    else:
        mid = f'<div class="mid"><span class="time">{d.hour:02d}:{d.minute:02d}</span><span class="vs">VS</span></div>' if d else '<div class="mid"><span class="vs">VS</span></div>'
        resume = f"{dom} reçoit {ext}"
    rang = ""
    if poule:
        me = next((r for r in poule.get("lignes", []) if r.get("estRBBA")), None)
        if me and me.get("rang"):
            rang = f"RBBA {me['rang']}{'er' if me['rang'] == 1 else 'e'}, {me.get('points')} pts"
    it = m.get("itineraire") or {}
    route = "".join(f'<a class="btn btn--out-l" href="{e(it[k])}" target="_blank" rel="noopener">{lbl}</a>' for k, lbl in (("google", "Google Maps"), ("apple", "Apple Plans"), ("waze", "Waze")) if it.get(k))
    agenda = "" if joue else f'<a class="btn" href="../../data/ics/{e(m["id"])}.ics">Ajouter à l’agenda</a>'
    ld = {"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{dom} – {ext}", "startDate": m.get("coupEnvoi"), "sport": "Basketball",
          "location": {"@type": "Place", "name": m.get("lieu")}, "homeTeam": {"@type": "SportsTeam", "name": dom}, "awayTeam": {"@type": "SportsTeam", "name": ext}, "url": m.get("page")}
    head = B.head(e(titre) + " – Roisel Basketball", e(resume + (" · " + rang if rang else "")), "../../").replace("</head>", f'<link rel="canonical" href="{e(m.get("page",""))}">\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n</head>')
    return head + f"""<body data-page="match">
{B.header("", "../../")}
<main id="main" tabindex="-1">
  <section class="match-hero"><div class="wrap">
    <p class="next-top"><span><b>{e(m.get('competition',''))}</b>{' · ' + e(jour) if jour else ''}</span><span>{e(quand)}</span></p>
    <h1 class="sr">{e(dom)} contre {e(ext)}</h1>
    <div class="versus"><div class="side">{crest(dom, m.get("logoDomicile"))}<span class="nm">{e(dom)}</span><span class="tg">Domicile</span></div>{mid}<div class="side">{crest(ext, m.get("logoExterieur"))}<span class="nm">{e(ext)}</span><span class="tg">Extérieur</span></div></div>
    <div class="next-bottom"><p class="venue">{e((m.get('lieu') or '').split(',')[0])}<small>{e(','.join((m.get('lieu') or '').split(',')[1:]).strip())}</small></p><div class="btns">{agenda}{route}</div></div>
  </div></section>
  <section class="block wrap"><p class="facts">{''.join(f'<span>{e(x)}</span>' for x in [jour, resume, rang] if x)}</p><p style="margin-top:20px"><a class="more" href="../../matchs.html">Tous les matchs</a></p></section>
</main>
{B.footer("../../")}</body>
</html>
"""


def build(root: Path, data_dir: Path, matches: list[dict], rankings: list[dict], site_url: str, ics_for) -> int:
    poule = rankings[0] if rankings else None
    (data_dir / "ics").mkdir(parents=True, exist_ok=True)
    urls = [f"{site_url}/", f"{site_url}/matchs.html", f"{site_url}/appli.html"]
    n = 0
    for m in matches:
        if not m.get("id") or not m.get("coupEnvoi"):
            continue
        safe = re.sub(r"[^A-Za-z0-9_-]", "", str(m["id"]))
        d = root / "matchs" / safe
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(match_page(m, poule, site_url), encoding="utf-8")
        (data_dir / "ics" / f"{safe}.ics").write_text(ics_for([m]), encoding="utf-8", newline="")
        urls.append(f"{site_url}/matchs/{safe}/")
        n += 1
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls]
    sm.append("</urlset>")
    (root / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    return n
