"""
Alertes de match du RBBA (notifications web via OneSignal).

Lancé à chaque passage du robot (toutes les 5 minutes) :
  - le mercredi (18 h) de chaque semaine de match : « Nos seniors se déplacent à … ce samedi » + adresse ;
  - le jour d'un match, à partir de 10 h : « C'est jour de match … ce soir » + adresse ;
  - quand la FFBB publie le score final : « Victoire du RBBA … » ;
  - quand un nouveau post apparaît sur Instagram (flux Behold).

Chaque alerte n'est envoyée qu'une fois (mémoire dans data/notify_state.json).
Au tout premier passage, le script note l'existant sans rien envoyer.
Sans la clé secrète ONESIGNAL_REST_KEY, il ne fait que tenir sa mémoire à jour.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATE = DATA / "notify_state.json"
PARIS = ZoneInfo("Europe/Paris")
APP_ID = os.environ.get("ONESIGNAL_APP_ID", "7a9ac6d3-6447-4312-8d8b-02bbcdf13915")
KEY = os.environ.get("ONESIGNAL_REST_KEY", "").strip()
SITE = os.environ.get("RBBA_SITE_URL", "https://roiselbasketball.fr").rstrip("/")
BEHOLD = os.environ.get("BEHOLD_FEED", "quMGqyDE08fF7hLVtnYc")
ICON = SITE + "/assets/icon-192.png"
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def nice(name: str) -> str:
    name = re.sub(r"\s*\([^)]*\)", "", str(name or ""))
    name = re.sub(r"\s+-\s+(\d+)$", r" \1", name)
    s = re.sub(r"(^|[\s\-'’])(\w)", lambda m: m.group(1) + m.group(2).upper(), name.lower())
    return re.sub(r"\b(Ca|Us|Uso|Bb|Bc|Es|As|Rbba)\b", lambda m: m.group(0).upper(), s)


def heure(ko: datetime) -> str:
    return f"{ko.hour}h" if ko.minute == 0 else f"{ko.hour}h{ko.minute:02d}"


def phrase(m: dict, ko: datetime, quand: str) -> str:
    """« Nos seniors se déplacent à Bray-sur-Somme ce samedi 14 novembre à 21h … Adresse : … »"""
    dom, ext = nice(m.get("equipeDomicile")), nice(m.get("equipeExterieur"))
    lieu = (m.get("lieu") or "").strip()
    coupe = " en coupe" if "coupe" in (m.get("competition") or "").lower() else ""
    if m.get("rbbaADomicile"):
        txt = f"Nos seniors reçoivent {ext}{coupe} {quand} à {heure(ko)}."
        return txt + (f" Rendez-vous au {lieu}." if lieu else "")
    ville = re.search(r"\d{5}\s+(.+)$", lieu)
    ou = f"à {ville.group(1)}" if ville else f"chez {dom}"
    txt = f"Nos seniors se déplacent {ou}{coupe} {quand} à {heure(ko)} pour affronter {dom}."
    return txt + (f" Adresse : {lieu}." if lieu else "")


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


LOG = DATA / "notify_log.json"


def log(entry: dict) -> None:
    hist = load(LOG, [])
    hist.append({"quand": datetime.now(PARIS).isoformat(timespec="seconds"), **entry})
    LOG.write_text(json.dumps(hist[-30:], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def send(title: str, body: str, url: str, topic: str) -> bool:
    if not KEY:
        print(f"(pas de clé OneSignal) {title} : {body}")
        log({"titre": title, "resultat": "pas de clé ONESIGNAL_REST_KEY"})
        return False
    payload = {
        "app_id": APP_ID,
        "target_channel": "push",
        "included_segments": ["Total Subscriptions"],
        "headings": {"en": title, "fr": title},
        "contents": {"en": body, "fr": body},
        "url": url,
        "chrome_web_icon": ICON,
        "firefox_icon": ICON,
        "web_push_topic": topic,
    }
    req = urllib.request.Request(
        "https://api.onesignal.com/notifications?c=push",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Key {KEY}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            rep = r.read()[:400].decode("utf-8", "replace")
            print("envoyé :", title, "|", r.status, rep)
            log({"titre": title, "resultat": r.status, "reponse": rep})
            return True
    except Exception as e:
        detail = getattr(e, "read", lambda: b"")()[:300]
        print("échec d'envoi :", title, e, detail, file=sys.stderr)
        log({"titre": title, "resultat": f"échec {e}", "reponse": detail.decode("utf-8", "replace") if isinstance(detail, bytes) else str(detail)})
        return False


def instagram_posts() -> list[dict]:
    try:
        req = urllib.request.Request(f"https://feeds.behold.so/{BEHOLD}", headers={"User-Agent": "RBBA site"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except Exception as e:
        print("flux Instagram indisponible :", e, file=sys.stderr)
        return []
    posts = data.get("posts", []) if isinstance(data, dict) else data
    return [p for p in posts if isinstance(p, dict) and p.get("id")]


def main() -> None:
    now = datetime.now(PARIS)
    first = not STATE.exists()
    state = load(STATE, {"envoyes": [], "instagram": []})
    done = set(state.get("envoyes", []))
    seen = set(state.get("instagram", []))

    raw = load(DATA / "matchs.json", [])
    matches = raw.get("matchs", []) if isinstance(raw, dict) else raw

    for m in matches:
        if not m.get("id") or not m.get("coupEnvoi"):
            continue
        ko = datetime.fromisoformat(m["coupEnvoi"])
        ko = ko.replace(tzinfo=PARIS) if ko.tzinfo is None else ko.astimezone(PARIS)
        dom, ext = nice(m.get("equipeDomicile")), nice(m.get("equipeExterieur"))
        url = m.get("page") or f"{SITE}/matchs.html"
        lieu = (m.get("lieu") or "").split(",")[0].strip().title()

        # Match de la semaine : le mercredi à partir de 18 h, pour un match dans les 6 jours
        k = f"semaine:{m['id']}:{ko.date()}"
        jours = (ko.date() - now.date()).days
        if k not in done and not m.get("joue") and 0 < jours <= 6:
            if first:
                done.add(k)
            elif now.weekday() == 2 and now.hour >= 18:
                quand = f"ce {JOURS[ko.weekday()]} {ko.day} {MOIS[ko.month - 1]}"
                send("Match de la semaine", phrase(m, ko, quand), url, f"semaine-{m['id']}")
                done.add(k)

        # Jour de match (à partir de 10 h, jusqu'au coup d'envoi)
        k = f"jour:{m['id']}:{ko.date()}"
        if k not in done and ko.date() == now.date() and not m.get("joue"):
            if first or now >= ko:
                done.add(k)
            elif now.hour >= 10:
                quand = "ce soir" if ko.hour >= 18 else "aujourd'hui"
                send("C'est jour de match", phrase(m, ko, quand), url, f"jour-{m['id']}")
                done.add(k)

        # Score final (dans les 2 jours suivant le match)
        k = f"score:{m['id']}"
        if k not in done and m.get("joue") and m.get("scoreDomicile") is not None:
            if first or now - ko > timedelta(days=2):
                done.add(k)
            else:
                s1, s2 = m["scoreDomicile"], m["scoreExterieur"]
                rb, adv = (s1, s2) if m.get("rbbaADomicile") else (s2, s1)
                titre = "Victoire du RBBA" if rb > adv else ("Match nul" if rb == adv else "Défaite du RBBA")
                txt = f"{dom} {s1}, {ext} {s2}. Le résumé et le classement sur le site."
                send(titre, txt, url, f"score-{m['id']}")
                done.add(k)

    # Envoi de test : data/notify_test.json {"titre": …, "texte": …} puis suppression
    test = DATA / "notify_test.json"
    if test.exists():
        t = load(test, {})
        if send(t.get("titre", "Test RBBA"), t.get("texte", "Les alertes du RBBA fonctionnent."), t.get("url", SITE + "/"), "test") or not KEY:
            test.unlink()

    # Alerte de test ponctuelle (fichier data/alerte_test.json, supprimé après envoi)
    test = DATA / "alerte_test.json"
    if test.exists():
        t = load(test, {})
        if t.get("titre") and t.get("texte"):
            send(t["titre"], t["texte"], t.get("url") or SITE + "/", "test")
        test.unlink()

    # Nouveau post Instagram : une seule alerte, pour le plus récent
    posts = instagram_posts()
    nouveaux = [p for p in posts if str(p["id"]) not in seen]
    if nouveaux and not first and seen:
        p = nouveaux[0]
        legende = re.sub(r"\s+", " ", (p.get("prunedCaption") or p.get("caption") or "")).strip()
        legende = re.sub(r"#\w+", "", legende).strip()
        txt = (legende[:110] + "…") if len(legende) > 110 else (legende or "Nouvelle publication du club.")
        send("Nouveau post Instagram", txt, p.get("permalink") or "https://www.instagram.com/roiselbasketball/", "instagram")
    seen.update(str(p["id"]) for p in posts)

    new_state = {"envoyes": sorted(done)[-400:], "instagram": sorted(seen)[-200:], "maj": now.isoformat(timespec="minutes")}
    old = load(STATE, None)
    if old is None or {k: v for k, v in old.items() if k != "maj"} != {k: v for k, v in new_state.items() if k != "maj"}:
        STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
