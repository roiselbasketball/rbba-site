"""
Alertes de match du RBBA (notifications web via OneSignal).

Lancé à chaque passage du robot (toutes les 5 minutes) :
  - le jour d'un match, à partir de 10 h : « Ce soir 20h30 : RBBA contre … » ;
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
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def nice(name: str) -> str:
    name = re.sub(r"\s*\([^)]*\)", "", str(name or ""))
    name = re.sub(r"\s+-\s+(\d+)$", r" \1", name)
    s = re.sub(r"(^|[\s\-'’])(\w)", lambda m: m.group(1) + m.group(2).upper(), name.lower())
    return re.sub(r"\b(Ca|Us|Uso|Bb|Bc|Es|As|Rbba)\b", lambda m: m.group(0).upper(), s)


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def send(title: str, body: str, url: str, topic: str) -> bool:
    if not KEY:
        print(f"(pas de clé OneSignal) {title} : {body}")
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
            print("envoyé :", title, "|", r.status, r.read()[:200])
            return True
    except Exception as e:
        detail = getattr(e, "read", lambda: b"")()[:300]
        print("échec d'envoi :", title, e, detail, file=sys.stderr)
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

        # Jour de match (à partir de 10 h, jusqu'au coup d'envoi)
        k = f"jour:{m['id']}:{ko.date()}"
        if k not in done and ko.date() == now.date() and not m.get("joue"):
            if first or now >= ko:
                done.add(k)
            elif now.hour >= 10:
                heure = f"{ko.hour}h{ko.minute:02d}"
                quand = "ce soir" if ko.hour >= 18 else "aujourd'hui"
                txt = f"{dom} reçoit {ext} {quand} à {heure}" + (f", {lieu}." if lieu else ".")
                send("Jour de match", txt, url, f"jour-{m['id']}")
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
