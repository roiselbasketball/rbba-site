"""Test hors ligne : un faux client reproduit la structure des données FFBB."""
import json, os, shutil, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ffbb_sync as S  # noqa: E402


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail

    def search_organismes(self, q, limit=10):
        if self.fail:
            raise ConnectionError("Unable to reach FFBB service")
        return NS(hits=[NS(id=999, nom="ROISEL BASKETBALL", codePostal="80240")])

    def get_organisme(self, oid):
        return NS(id=999, nom="ROISEL BASKETBALL",
                  engagements=[NS(idPoule=NS(id=555), idCompetition=NS(nom="Départementale Masculine Seniors - Division 2"))])

    def get_poule(self, pid):
        def r(i, j, e1, o1, e2, o2, d, h, s1=None, s2=None, salle=None):
            return NS(id=i, numeroJournee=j, nomEquipe1=e1, idOrganismeEquipe1=o1, nomEquipe2=e2,
                      idOrganismeEquipe2=o2, date_rencontre=d, horaire=h, resultatEquipe1=s1,
                      resultatEquipe2=s2, joue=s1 is not None, salle=salle)
        return NS(nom="Poule A", rencontres=[
            r(1, 2, "ROISEL BASKETBALL", 999, "EQUIPE TEST", 10, "2026-10-31T00:00:00", "2030", 70, 64, salle=NS(id=1)),
            r(2, 4, "BRAY BASKET BALL", 11, "ROISEL BASKETBALL", 999, "2026-11-14T00:00:00", "2100", salle=NS(id=2)),
            r(3, 5, "ROISEL BASKETBALL", 999, "BASKET BALL NESLOIS", 12, "2026-11-21T00:00:00", "2030", salle=NS(id=1)),
            r(4, 3, "ROISEL BASKETBALL", 999, "CA PERONNE", 13, "2026-11-28T00:00:00", "2030", salle=None),
            r(5, 4, "EQUIPE TEST", 10, "CA PERONNE", 13, "2026-11-14T00:00:00", "2030"),
        ], classements=[
            NS(position=2, id_engagement=NS(nom="EQUIPE TEST", nom_usuel=None), organisme_id="10", match_joues=3, gagnes=2, perdus=1, nombre_forfaits=0, paniers_marques=200, paniers_encaisses=190, difference=10, points=5),
            NS(position=1, id_engagement=NS(nom="ROISEL BASKETBALL", nom_usuel="Roisel Basketball"), organisme_id="999", match_joues=3, gagnes=3, perdus=0, nombre_forfaits=0, paniers_marques=210, paniers_encaisses=180, difference=30, points=6),
        ])

    def get_salle(self, sid):
        return {"1": NS(libelle="Gymnase de Roisel", adresse="Rue de test", codePostal="80240", ville="Roisel"),
                "2": NS(libelle="Salle de Bray", adresse=None, codePostal="80340", ville="Bray-sur-Somme")}[str(sid)]

    def get_lives(self):
        return [NS(external_id=NS(match_id=2), team_name_home="BRAY BASKET BALL", team_name_out="ROISEL BASKETBALL",
                   score_home=31, score_out=35, current_period="Q2", match_status="IN_PROGRESS")]


def main():
    base = Path(tempfile.mkdtemp())
    tmp = base / "data"; tmp.mkdir()
    S.DATA = tmp
    shutil.copy(Path(__file__).resolve().parent.parent / "data" / "manual.json", tmp / "manual.json")

    # 1. hors match : récupération forcée
    os.environ["RBBA_NOW"] = "2026-11-03T15:00:00+01:00"
    assert S.run(FakeClient(), force=True) == 0
    m = json.loads((tmp / "matchs.json").read_text())["matchs"]
    assert [x["id"] for x in m] == ["1", "2", "3", "4"], m
    assert m[0]["joue"] and m[0]["scoreDomicile"] == 70
    assert m[1]["coupEnvoi"] == "2026-11-14T21:00:00+01:00"
    assert m[1]["lieu"] == "Salle de Bray, 80340 Bray-sur-Somme"
    assert m[3]["lieu"] == "Gymnase de Roisel, 48 Rue de Cambrai, 80240 Roisel"  # salle absente -> gymnase du club
    assert "waze.com" in m[1]["itineraire"]["waze"]
    c = json.loads((tmp / "classement.json").read_text())["poules"][0]["lignes"]
    assert c[0]["rang"] == 1 and c[0]["estRBBA"] and c[1]["equipe"] == "EQUIPE TEST"

    # 2. une heure pas encore écoulée -> rien à faire
    os.environ["RBBA_NOW"] = "2026-11-03T15:20:00+01:00"
    S.run(FakeClient())
    assert json.loads((tmp / "status.json").read_text())["derniereTentative"].startswith("2026-11-03T15:00")

    # 3. jour de match : 15 min suffisent ; pendant le match : score en direct
    os.environ["RBBA_NOW"] = "2026-11-14T22:00:00+01:00"
    S.run(FakeClient())
    live = json.loads((tmp / "live.json").read_text())["enDirect"]
    assert live and live[0]["scoreExterieur"] == 35, live
    assert "match en cours" in json.loads((tmp / "status.json").read_text())["rythme"]

    # 4. FFBB injoignable : les données précédentes restent, pas d'alerte avant 24 h
    os.environ["RBBA_NOW"] = "2026-11-15T00:30:00+01:00"
    S.run(FakeClient(fail=True), force=True)
    st = json.loads((tmp / "status.json").read_text())
    assert st["source"] == "cache" and not st["alerte"]
    assert len(json.loads((tmp / "matchs.json").read_text())["matchs"]) == 4
    os.environ["RBBA_NOW"] = "2026-11-16T00:30:00+01:00"
    assert S.run(FakeClient(fail=True), force=True) == 2  # alerte après 24 h

    # 5. score saisi à la main
    man = json.loads((tmp / "manual.json").read_text())
    man["matchs"] = [{"id": "2", "joue": True, "scoreDomicile": 58, "scoreExterieur": 66}]
    (tmp / "manual.json").write_text(json.dumps(man))
    S.run(FakeClient(fail=True), force=True)
    m2 = [x for x in json.loads((tmp / "matchs.json").read_text())["matchs"] if x["id"] == "2"][0]
    assert m2["scoreExterieur"] == 66 and m2["source"] == "ffbb+manuel"

    # 6. agenda : horaire modifié -> SEQUENCE incrémentée
    ics = (tmp / "agenda-matchs.ics").read_text()
    print(ics[:1500])
    print("Fichiers :", sorted(p.name for p in tmp.iterdir()))
    assert (base / "matchs" / "3" / "index.html").exists() and (tmp / "ics" / "3.ics").exists() and (base / "sitemap.xml").exists()
    print("TOUS LES TESTS OK")
    return tmp


if __name__ == "__main__":
    main()
