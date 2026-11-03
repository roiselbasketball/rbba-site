# Site du RBBA – récupération automatique des données FFBB

Ce dossier est la première brique du site de Roisel Basketball. Il récupère seul les matchs, les scores et le classement de l'équipe seniors depuis les données publiques de la FFBB.

## Ce que ça produit (dossier `data/`)

| Fichier | Contenu | Utilisé pour |
| --- | --- | --- |
| `matchs.json` | Calendrier, scores, salle, liens d'itinéraire | Pages Matchs, accueil, pages de match, bouton « On y va » |
| `classement.json` | Classement complet de la poule | Page Matchs, position du RBBA sur l'accueil |
| `live.json` | Score en direct pendant un match | Bandeau « En direct » |
| `agenda-matchs.ics` | Flux d'agenda de la saison | Abonnement Google Agenda, iPhone, Android |
| `status.json` | Dernière mise à jour, source, alerte | Surveillance |
| `manual.json` | Saisie manuelle de secours | Corriger un score si la FFBB ne remonte pas |

## Rythme

Le planificateur lance le script toutes les 5 minutes. Le script récupère les données :
- toutes les 5 minutes pendant un match du RBBA ;
- toutes les 15 minutes le jour d'un match ;
- toutes les heures le reste du temps.

Si la FFBB ne répond pas, les dernières données valides restent affichées. Après 24 h sans données, une alerte est envoyée par e-mail.

## Pages du site

| Fichier | Page |
| --- | --- |
| `index.html` | Accueil : animation d'ouverture, prochain match et compte à rebours, dernier résultat, classement, vitrine des réseaux, accès « On y va », abonnement agenda |
| `matchs.html` | Calendrier, résultats, score en direct, ajout à l'agenda, classement complet |
| `appli.html` | Installation sur iPhone et Android, tutos agenda Gmail / iPhone / Android |
| `mentions-legales.html` | Mentions légales, confidentialité, droit à l'image, accessibilité (à compléter : siège, RNA, hébergeur) |
| `matchs/<id>/` | Une page par match, créée automatiquement (référencement Google) |

## Mise en route (une seule fois)

1. Créer un compte GitHub au nom du club et y déposer ce dossier dans un dépôt.
2. **Settings > Pages** : choisir « GitHub Actions » comme source. Ajouter le nom de domaine (par exemple roisel-basket.fr) dans « Custom domain ».
3. **Settings > Variables** : `RBBA_SITE_URL` = l'adresse du site (par exemple `https://roisel-basket.fr`).
4. Onglet **Actions** : lancer « Données FFBB » à la main une première fois. Le site est mis en ligne à la fin du passage.
5. Vérifier `data/status.json` : la ligne `"source": "ffbb"` confirme que la récupération fonctionne. L'identifiant FFBB du club y apparaît ; le copier dans la variable `RBBA_ORGANISME_ID` pour fiabiliser la recherche.
6. Vitrine des réseaux : coller le code de l'agrégateur (Elfsight, Tagembed…) à l'emplacement `social-wall` de `index.html`.

## Saisir un score à la main

Ouvrir `data/manual.json` sur GitHub, ajouter l'entrée du match (son `id` est dans `matchs.json`), enregistrer. Le site est corrigé au passage suivant. Supprimer l'entrée quand la FFBB est de nouveau à jour.

## Tester sans connexion

```
python3 tests/test_sync.py
```

## Réglages à compléter (scripts/build_site.py)

- `INSTAGRAM` et `FACEBOOK` : liens des comptes du club. La section « Suivez le RBBA » et les liens du pied de page apparaissent dès qu'ils sont renseignés.
- `LAT`, `LON` : position exacte du Gymnase de Roisel sur la carte.
- Puis relancer `python3 scripts/build_site.py` pour régénérer les pages.
