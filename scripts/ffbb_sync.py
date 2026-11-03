#!/usr/bin/env python3
"""
Synchronisation des données FFBB pour le site du RBBA (Roisel Basketball).

Récupère automatiquement, à partir des données publiques de la FFBB
(les mêmes que celles de l'application fédérale) :
  - le calendrier et les résultats de l'équipe seniors,
  - le classement complet de la poule (DM2),
  - les scores en direct pendant les matchs,
  - les adresses des salles (pour le bouton « On y va »).

Fichiers produits dans data/ :
  matchs.json, classement.json, live.json, status.json,
  agenda-matchs.ics (abonnement agenda Google / iPhone / Android)

Fréquence (le planificateur lance ce script toutes les 5 minutes) :
  - pendant un match du RBBA : à chaque lancement (toutes les 5 min)
  - le jour d'un match : toutes les 15 minutes
  - le reste du temps : toutes les heures
Utiliser --force pour ignorer cette règle.

Secours : si la FFBB ne répond pas, les dernières données valides sont
conservées, et data/manual.json permet de saisir un score à la main.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CLUB_SEARCH = os.environ.get("RBBA_CLUB_SEARCH", "Roisel")
CLUB_CP = os.environ.get("RBBA_CLUB_CP", "80240")
CLUB_ID_ENV = os.environ.get("RBBA_ORGANISME_ID")  # facultatif : identifiant FFBB du club
SITE_URL = os.environ.get("RBBA_SITE_URL", "https://roisel-basket.fr")
HOME_HALL = os.environ.get("RBBA_GYMNASE", "Gymnase de Roisel, 48 Rue de Cambrai, 80240 Roisel")
MATCH_DURATION = timedelta(hours=2, minutes=30)


# ---------------------------------------------------------------- utilitaires
def g(obj, *names, default=None):
    """Lit le premier attribut (ou clé) présent parmi plusieurs noms possibles."""
    for n in names:
        if obj is None:
            return default
        v = obj.get(n) if isinstance(obj, dict) else getattr(obj, n, None)
        if v not in (None, ""):
            return v
    return default


def now_paris() -> datetime:
    override = os.environ.get("RBBA_NOW")  # pour les tests
    if override:
        return datetime.fromisoformat(override).astimezone(PARIS)
    return datetime.now(PARIS)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


HOME_GEO = os.environ.get("RBBA_GYMNASE_GEO", "49.952727,3.103363")


def directions(address: str, home: bool = False) -> dict:
    if home and HOME_GEO:
        g_ = HOME_GEO
        return {"google": f"https://www.google.com/maps/dir/?api=1&destination={g_}",
                "apple": f"https://maps.apple.com/?daddr={g_}&q=Gymnase%20de%20Roisel",
                "waze": f"https://waze.com/ul?ll={g_}&navigate=yes"}
    q = quote(address)
    return {
        "google": f"https://www.google.com/maps/dir/?api=1&destination={q}",
        "apple": f"https://maps.apple.com/?daddr={q}",
        "waze": f"https://waze.com/ul?q={q}&navigate=yes",
    }


def parse_kickoff(m) -> datetime | None:
    raw = g(m, "date_rencontre", "date")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s[:19] if "+" not in s[10:] else s)
        except ValueError:
            try:
                dt = datetime.fromisoformat(s[:10])
            except ValueError:
                return None
    if dt.year <= 1970:
        return None
    horaire = str(g(m, "horaire", default="") or "").strip()
    digits = "".join(ch for ch in horaire if ch.isdigit())
    if len(digits) in (3, 4) and digits not in ("000", "0000"):
        digits = digits.zfill(4)
        dt = dt.replace(hour=int(digits[:2]), minute=int(digits[2:]))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARIS)
    return dt.astimezone(PARIS)


def to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ lecture FFBB
def find_club(client):
    if CLUB_ID_ENV:
        return client.get_organisme(int(CLUB_ID_ENV))
    res = client.search_organismes(CLUB_SEARCH, limit=10)
    hits = list(getattr(res, "hits", None) or [])
    best = None
    for h in hits:
        nom = str(g(h, "nom", default="")).upper()
        cp = str(g(h, "codePostal", "code_postal", default=""))
        if "ROISEL" in nom and "BASKET" in nom:
            best = h
            if cp == CLUB_CP:
                break
    if best is None:
        raise RuntimeError(f"Club « {CLUB_SEARCH} » introuvable dans les données FFBB")
    return client.get_organisme(int(g(best, "id")))


def senior_poules(org) -> dict[int, str]:
    """Poules des équipes engagées par le club (toutes, l'équipe seniors en tête)."""
    poules: dict[int, str] = {}
    for eng in g(org, "engagements", default=[]) or []:
        p = g(eng, "idPoule")
        pid = to_int(g(p, "id") if not isinstance(p, (str, int)) else p)
        comp = g(eng, "idCompetition")
        if pid:
            poules[pid] = str(g(comp, "nom", default="") or "")
    return poules


def salle_address(client, salle_ref, cache: dict) -> str | None:
    sid = g(salle_ref, "id") if not isinstance(salle_ref, (str, int)) else salle_ref
    if not sid:
        return None
    if sid in cache:
        return cache[sid]
    addr = None
    try:
        s = client.get_salle(str(sid))
        commune = g(s, "commune")
        parts = [
            g(s, "libelle", "nom"),
            g(s, "adresse"),
            " ".join(x for x in [str(g(s, "codePostal", "cp", default="") or g(commune, "codePostal", "code_postal", default="")),
                                  str(g(s, "ville", default="") or g(commune, "libelle", default=""))] if x).strip(),
        ]
        addr = ", ".join(p for p in parts if p) or None
    except Exception:
        addr = None
    cache[sid] = addr
    return addr


FFBB_ASSETS = "https://api.ffbb.com/assets/"


def logo_path(oid: str, logo_id: str | None, name: str) -> str | None:
    """Logo d'un club : fichier manuel (data/logos.json) sinon logo FFBB téléchargé dans data/logos/."""
    manual = load_json(DATA / "logos.json", {})
    for k, v in manual.items():
        if k.startswith("_"):
            continue
        if k.upper() in (name or "").upper():
            return v
    if not oid or not logo_id:
        return None
    dest = DATA / "logos" / f"{oid}.png"
    if not dest.exists():
        try:
            import urllib.request
            req = urllib.request.Request(FFBB_ASSETS + str(logo_id), headers={"User-Agent": "Mozilla/5.0 (RBBA site)"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            if len(data) > 200:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        except Exception:
            return FFBB_ASSETS + str(logo_id)
    return f"data/logos/{oid}.png" if dest.exists() else None


_club_cache: dict = {}
DIAG: dict = {}


def _brief(o, depth=0):
    """Aperçu des champs d'un objet FFBB (diagnostic, sans données personnelles)."""
    if depth > 2 or o is None: return repr(o)[:80]
    if isinstance(o, (str, int, float, bool)): return o if not isinstance(o, str) else o[:80]
    if isinstance(o, dict): items = o.items()
    elif hasattr(o, "__dict__"): items = vars(o).items()
    else: return repr(o)[:80]
    return {k: _brief(v, depth + 1) for k, v in list(items)[:25] if not str(k).startswith("_") and k not in ("membres", "engagements", "competitions")}


def venue_from_match(client, mid):
    """Salle d'un match, d'après sa fiche détaillée FFBB."""
    try:
        r = client.get_rencontre(mid)
        s = g(r, "salle")
        DIAG.setdefault("rencontre_salle", _brief(s))
        if isinstance(s, (str, int)):
            return salle_address(client, s, {})
        com = g(s, "commune")
        parts = [g(s, "libelle", "nom"), g(s, "adresse"), " ".join(str(x) for x in [g(s, "codePostal", "cp", default="") or g(com, "codePostal", "code_postal", default=""), g(s, "ville", default="") or g(com, "libelle", default="")] if x).strip()]
        return ", ".join(str(x) for x in parts if x) or salle_address(client, g(s, "id"), {})
    except Exception as exc:
        DIAG.setdefault("rencontre_err", str(exc)[:200])
        return None


def club_info(client, oid: str) -> dict:
    """Logo et salle d'un club adverse, d'après sa fiche FFBB (mise en cache)."""
    if not oid or oid in _club_cache:
        return _club_cache.get(oid, {})
    info = {}
    try:
        o = client.get_organisme(int(oid))
        lg = g(o, "logo")
        info["logo_id"] = g(lg, "id") if lg is not None and not isinstance(lg, (str, int)) else lg
        s = g(o, "salle")
        com = g(s, "commune") or g(o, "commune")
        cp = str(g(s, "codePostal", "code_postal", default="") or g(com, "codePostal", "code_postal", default="") or "")
        ville = str(g(s, "ville", default="") or g(com, "libelle", default="") or "")
        parts = [g(s, "libelle", "nom"), g(s, "adresse"), " ".join(x for x in [cp, ville] if x).strip()]
        info["lieu"] = ", ".join(str(x) for x in parts if x) or None
    except Exception as exc:
        DIAG.setdefault("club_err", str(exc)[:200])
    DIAG.setdefault("club_info", info)
    _club_cache[oid] = info
    return info


def build_matches(client, org, poules: dict[int, str]):
    club_id = str(g(org, "id"))
    club_nom = str(g(org, "nom", default="ROISEL")).upper()
    matches, rankings, salle_cache = [], [], {}
    logos: dict[str, str | None] = {}

    for pid, comp_nom in poules.items():
        poule = client.get_poule(pid)
        if not poule:
            continue
        poule_nom = g(poule, "nom", "libelle", default="") or ""

        # Classement complet de la poule
        rows = []
        for r in g(poule, "classements", "classement", default=[]) or []:
            eng = g(r, "id_engagement", "idEngagement")
            nom = g(eng, "nom_usuel", "nom") if not isinstance(eng, str) else None
            nom = nom or g(r, "organisme_nom_simple", "organisme_nom", default="?")
            oid = str(g(r, "organisme_id", default="") or "")
            lid = g(eng, "logo_id") if not isinstance(eng, str) else None
            lid = lid or g(r, "organisme_logo_id")
            logo = logo_path(oid, lid, nom)
            if oid:
                logos[oid] = logo
            logos["name:" + str(nom).upper()] = logo
            rows.append({
                "logo": logo,
                "rang": to_int(g(r, "position")),
                "equipe": nom,
                "estRBBA": str(g(r, "organisme_id", default="")) == club_id or "ROISEL" in str(nom).upper(),
                "joues": to_int(g(r, "match_joues")),
                "victoires": to_int(g(r, "gagnes")),
                "defaites": to_int(g(r, "perdus")),
                "forfaits": to_int(g(r, "nombre_forfaits")),
                "pointsPour": to_int(g(r, "paniers_marques")),
                "pointsContre": to_int(g(r, "paniers_encaisses")),
                "difference": to_int(g(r, "difference")),
                "points": to_int(g(r, "points")),
            })
        rows.sort(key=lambda x: (x["rang"] is None, x["rang"] or 0))
        # Tous les résultats de la poule : servent à recalculer le classement si la FFBB tarde
        results = []
        for m in g(poule, "rencontres", default=[]) or []:
            s1, s2 = to_int(g(m, "resultatEquipe1")), to_int(g(m, "resultatEquipe2"))
            ko = parse_kickoff(m)
            results.append({"e1": str(g(m, "nomEquipe1", default="")), "e2": str(g(m, "nomEquipe2", default="")),
                            "o1": str(g(m, "idOrganismeEquipe1", default="")), "o2": str(g(m, "idOrganismeEquipe2", default="")),
                            "s1": s1, "s2": s2, "date": ko.isoformat() if ko else None,
                            "joue": bool(g(m, "joue", default=False)) or (s1 is not None and s2 is not None and (s1 or s2))})
        rankings.append({"pouleId": pid, "competition": comp_nom, "poule": poule_nom, "lignes": rows, "_resultats": results})

        # Rencontres du club
        for m in g(poule, "rencontres", default=[]) or []:
            e1, e2 = str(g(m, "nomEquipe1", default="")), str(g(m, "nomEquipe2", default=""))
            r1, r2 = g(m, "idOrganismeEquipe1"), g(m, "idOrganismeEquipe2")
            # selon l'API, l'équipe est un identifiant ou un objet {id, logo: {id}}
            ident = lambda r: str(g(r, "id", default="") if r is not None and not isinstance(r, (str, int)) else (r or ""))
            lid = lambda r: g(g(r, "logo"), "id") if r is not None and not isinstance(r, (str, int)) else None
            o1, o2 = ident(r1), ident(r2)
            for oid_, r_, nm_ in ((o1, r1, str(g(m, "nomEquipe1", default=""))), (o2, r2, str(g(m, "nomEquipe2", default="")))):
                if oid_ and not logos.get(oid_) and lid(r_) and "ROISEL" not in nm_.upper():
                    logos[oid_] = logo_path(oid_, lid(r_), nm_)
            home = o1 == club_id or "ROISEL" in e1.upper() or club_nom in e1.upper()
            away = o2 == club_id or "ROISEL" in e2.upper() or club_nom in e2.upper()
            if not (home or away):
                continue
            kickoff = parse_kickoff(m)
            s1, s2 = to_int(g(m, "resultatEquipe1")), to_int(g(m, "resultatEquipe2"))
            played = bool(g(m, "joue", default=False)) or (s1 is not None and s2 is not None and (s1 or s2))
            lieu = salle_address(client, g(m, "salle"), salle_cache)
            if home and not lieu:
                lieu = HOME_HALL
            DIAG.setdefault("poule_salle", _brief(g(m, "salle")))
            DIAG.setdefault("poule_equipe1", _brief(r1))
            if not lieu:
                lieu = venue_from_match(client, str(g(m, "id")))
            if not lieu:
                lieu = club_info(client, o1).get("lieu")
            for oid_, nm_ in ((o1, e1), (o2, e2)):
                if oid_ and not logos.get(oid_) and "ROISEL" not in nm_.upper():
                    ci = club_info(client, oid_)
                    if ci.get("logo_id"):
                        logos[oid_] = logo_path(oid_, ci["logo_id"], nm_)
            mid = str(g(m, "id"))
            matches.append({
                "id": mid,
                "competition": comp_nom,
                "poule": poule_nom,
                "pouleId": pid,
                "journee": to_int(g(m, "numeroJournee", "numero_journee")),
                "equipeDomicile": e1,   # l'équipe à domicile est toujours citée en premier
                "equipeExterieur": e2,
                "rbbaADomicile": home,
                "logoDomicile": logos.get(o1) or logos.get("name:" + e1.upper()) or logo_path("", None, e1),
                "logoExterieur": logos.get(o2) or logos.get("name:" + e2.upper()) or logo_path("", None, e2),
                "coupEnvoi": kickoff.isoformat() if kickoff else None,
                "joue": bool(played),
                "scoreDomicile": s1 if played else None,
                "scoreExterieur": s2 if played else None,
                "lieu": lieu or "Lieu à confirmer",
                "itineraire": directions(lieu, home and "ROISEL" in lieu.upper()) if lieu else None,
                "page": f"{SITE_URL}/matchs/{mid}/",
                "source": "ffbb",
            })
    matches.sort(key=lambda x: x["coupEnvoi"] or "9999")
    by_name = {}
    for m in matches:
        by_name[m["equipeDomicile"].upper()] = m.get("logoDomicile")
        by_name[m["equipeExterieur"].upper()] = m.get("logoExterieur")
    for p in rankings:
        for r in p["lignes"]:
            if not r.get("logo"):
                r["logo"] = by_name.get(str(r["equipe"]).upper()) or by_name.get(str(r["equipe"]).upper() + " - 2")
    return matches, finalize_rankings(rankings, club_id)


def compute_table(results: list[dict], club_id: str) -> list[dict]:
    """Classement recalculé à partir des scores (barème FFBB : victoire 2 pts, défaite 1 pt)."""
    t: dict[str, dict] = {}
    def team(name, oid):
        return t.setdefault(name, {"equipe": name, "estRBBA": oid == club_id or "ROISEL" in name.upper(),
                                   "joues": 0, "victoires": 0, "defaites": 0, "forfaits": 0,
                                   "pointsPour": 0, "pointsContre": 0, "points": 0})
    for r in results:
        a, b = team(r["e1"], r["o1"]), team(r["e2"], r["o2"])
        if not r["joue"] or r["s1"] is None or r["s2"] is None:
            continue
        for x, pf, pc in ((a, r["s1"], r["s2"]), (b, r["s2"], r["s1"])):
            x["joues"] += 1; x["pointsPour"] += pf; x["pointsContre"] += pc
            if pf > pc: x["victoires"] += 1; x["points"] += 2
            else: x["defaites"] += 1; x["points"] += 1
    rows = list(t.values())
    for x in rows:
        x["difference"] = x["pointsPour"] - x["pointsContre"]
    rows.sort(key=lambda x: (-x["points"], -x["difference"], -x["pointsPour"], x["equipe"]))
    for i, x in enumerate(rows, 1):
        x["rang"] = i
    return rows


def finalize_rankings(rankings: list[dict], club_id: str) -> list[dict]:
    previous = {p.get("pouleId"): p for p in load_json(DATA / "classement.json", {}).get("poules", [])}
    for p in rankings:
        results = p.pop("_resultats", [])
        played = sum(1 for r in results if r["joue"])
        ffbb_played = sum((r.get("joues") or 0) for r in p["lignes"]) // 2
        computed = compute_table(results, club_id) if results else []
        # La FFBB met parfois à jour le classement après les scores : on prend la version la plus récente
        names = {str(r.get("equipe", "")).upper(): r.get("logo") for r in p["lignes"]}
        for r in computed:
            r["logo"] = names.get(str(r["equipe"]).upper()) or logo_path("", None, r["equipe"])
        if computed and (not p["lignes"] or played > ffbb_played):
            p["lignes"], p["source"] = computed, "calcule"
        else:
            p["source"] = "ffbb"
        p["journeesJouees"] = played
        last = max((r["date"] for r in results if r["joue"] and r["date"]), default=None)
        p["dernierResultat"] = last
        # évolution du rang par rapport au passage précédent
        before = {r.get("equipe"): r.get("rang") for r in (previous.get(p["pouleId"]) or {}).get("lignes", [])}
        for r in p["lignes"]:
            old = before.get(r["equipe"])
            r["evolution"] = (old - r["rang"]) if (old and r.get("rang")) else 0
    # poule principale : championnat (pas une coupe) où joue le RBBA, avec le résultat le plus récent
    def score(p):
        comp = (p.get("competition") or "").upper()
        return (any(r.get("estRBBA") for r in p["lignes"]), "COUPE" not in comp and "TROPH" not in comp, p.get("dernierResultat") or "")
    rankings.sort(key=score, reverse=True)
    for i, p in enumerate(rankings):
        p["principale"] = i == 0
    return rankings


def fetch_lives(client, matches) -> list[dict]:
    ids = {m["id"] for m in matches}
    out = []
    try:
        lives = client.get_lives() or []
    except Exception:
        return out
    for lv in lives:
        ext = g(lv, "external_id")
        mid = str(g(ext, "match_id", "id", default="") or g(lv, "match_id", default=""))
        home, away = str(g(lv, "team_name_home", default="")), str(g(lv, "team_name_out", default=""))
        if mid in ids or "ROISEL" in home.upper() or "ROISEL" in away.upper():
            out.append({
                "id": mid,
                "equipeDomicile": home,
                "equipeExterieur": away,
                "scoreDomicile": to_int(g(lv, "score_home")),
                "scoreExterieur": to_int(g(lv, "score_out")),
                "periode": g(lv, "current_period"),
                "statut": g(lv, "match_status", "current_status"),
            })
    return out


# --------------------------------------------------------------- secours manuel
def apply_manual(matches: list[dict]) -> list[dict]:
    """data/manual.json : scores ou matchs saisis à la main (prioritaires)."""
    manual = load_json(DATA / "manual.json", {"matchs": []})
    by_id = {m["id"]: m for m in matches}
    for entry in manual.get("matchs", []):
        mid = str(entry.get("id") or "manuel-" + hashlib.sha1(json.dumps(entry, sort_keys=True).encode()).hexdigest()[:8])
        base = by_id.get(mid, {"id": mid, "source": "manuel"})
        base.update({k: v for k, v in entry.items() if k != "id"})
        if base.get("lieu") and not base.get("itineraire"):
            base["itineraire"] = directions(base["lieu"])
        base["source"] = "manuel" if mid not in by_id else "ffbb+manuel"
        by_id[mid] = base
    return sorted(by_id.values(), key=lambda x: x.get("coupEnvoi") or "9999")


# ------------------------------------------------------------------- agenda .ics
def ics_escape(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line: str) -> str:
    out, b = [], line.encode("utf-8")
    while len(b) > 75:
        cut = 75
        while (b[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b" " + b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n".join(out)


VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Paris
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def build_ics(matches: list[dict], stamp: datetime) -> str:
    state = load_json(DATA / ".ics_state.json", {})
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Roisel Basketball//Matchs RBBA//FR",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Matchs RBBA",
             "X-WR-TIMEZONE:Europe/Paris", "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
             "X-PUBLISHED-TTL:PT1H"]
    lines += VTIMEZONE.split("\n")
    dtstamp = stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for m in matches:
        if not m.get("coupEnvoi"):
            continue
        start = datetime.fromisoformat(m["coupEnvoi"]).astimezone(PARIS)
        end = start + timedelta(hours=2)
        titre = f"{m['equipeDomicile']} – {m['equipeExterieur']}"
        if m.get("joue") and m.get("scoreDomicile") is not None:
            titre += f" ({m['scoreDomicile']} à {m['scoreExterieur']})"
        desc = f"{m.get('competition','')} – journée {m.get('journee') or '?'}\nInfos et itinéraire : {m['page']}"
        uid = f"ffbb-{m['id']}@roisel-basketball"
        fingerprint = hashlib.sha1(f"{titre}|{start}|{m['lieu']}".encode()).hexdigest()
        prev = state.get(uid, {"seq": 0, "fp": fingerprint})
        seq = prev["seq"] + (1 if prev["fp"] != fingerprint else 0)
        state[uid] = {"seq": seq, "fp": fingerprint}
        lines += [
            "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{dtstamp}", f"SEQUENCE:{seq}",
            f"DTSTART;TZID=Europe/Paris:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Paris:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{ics_escape(titre)}", f"LOCATION:{ics_escape(m['lieu'])}",
            f"DESCRIPTION:{ics_escape(desc)}", f"URL:{m['page']}",
            "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-P1D", f"DESCRIPTION:{ics_escape('Match demain : ' + titre)}", "END:VALARM",
            "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT2H", f"DESCRIPTION:{ics_escape('Match dans 2 h : ' + titre)}", "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    save_json(DATA / ".ics_state.json", state)
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


# ------------------------------------------------------------- choix du rythme
def due(matches: list[dict], status: dict, now: datetime) -> tuple[bool, str]:
    kicks = [datetime.fromisoformat(m["coupEnvoi"]) for m in matches if m.get("coupEnvoi")]
    last = status.get("derniereTentative")
    elapsed = (now - datetime.fromisoformat(last)).total_seconds() / 60 if last else 1e9
    if any(k - timedelta(minutes=15) <= now <= k + MATCH_DURATION for k in kicks):
        return True, "match en cours (toutes les 5 min)"
    if any(k.date() == now.date() for k in kicks):
        return elapsed >= 14, "jour de match (toutes les 15 min)"
    return elapsed >= 59, "hors match (toutes les heures)"


# ------------------------------------------------------------------------ main
def run(client=None, force=False) -> int:
    now = now_paris()
    status = load_json(DATA / "status.json", {})
    previous = load_json(DATA / "matchs.json", {}).get("matchs", [])
    ok, mode = due(previous, status, now)
    if not (ok or force):
        print(f"Rien à faire : {mode}, dernière tentative {status.get('derniereTentative')}")
        return 0

    status["derniereTentative"] = now.isoformat()
    status["rythme"] = mode
    try:
        if client is None:
            from ffbb_data_client import FFBBDataClient
            client = FFBBDataClient.create()
        org = find_club(client)
        poules = senior_poules(org)
        if not poules:
            raise RuntimeError("Aucune équipe engagée trouvée pour le club")
        matches, rankings = build_matches(client, org, poules)
        if not matches:
            raise RuntimeError("Aucun match trouvé pour le club")
        lives = fetch_lives(client, matches)
        status.update({"club": g(org, "nom"), "organismeId": g(org, "id"), "source": "ffbb",
                       "derniereReussite": now.isoformat(), "erreur": None})
    except Exception as exc:  # secours : on garde les dernières données valides
        print(f"Échec de la récupération FFBB : {exc}", file=sys.stderr)
        status.update({"source": "cache", "erreur": str(exc)})
        matches = previous
        rankings = load_json(DATA / "classement.json", {}).get("poules", [])
        lives = []

    matches = apply_manual(matches)
    maj = now.isoformat()
    save_json(DATA / "matchs.json", {"miseAJour": maj, "matchs": matches})
    save_json(DATA / "classement.json", {"miseAJour": maj, "poules": rankings})
    save_json(DATA / "live.json", {"miseAJour": maj, "enDirect": lives})
    (DATA / "agenda-matchs.ics").write_text(build_ics(matches, now), encoding="utf-8", newline="")
    try:  # pages de match, agenda par match, plan du site
        import build_pages
        nb = build_pages.build(DATA.parent, DATA, matches, rankings, SITE_URL.rstrip("/"), lambda ms: build_ics(ms, now))
        print(f"{nb} pages de match générées")
    except Exception as exc:
        print(f"Pages de match non générées : {exc}", file=sys.stderr)

    last_ok = status.get("derniereReussite")
    if DIAG:
        status["diagnostic"] = DIAG
    status["alerte"] = (not last_ok) or (now - datetime.fromisoformat(last_ok) > timedelta(hours=24))
    save_json(DATA / "status.json", status)
    print(f"OK – {len(matches)} matchs, source {status['source']}, rythme : {mode}")
    return 2 if status["alerte"] else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--force", action="store_true", help="récupérer même si ce n'est pas l'heure")
    sys.exit(run(force=ap.parse_args().force))
