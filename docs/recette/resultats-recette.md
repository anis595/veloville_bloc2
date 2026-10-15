# Résultats de recette

## Campagne

15/10/2026, heures de Paris. Version testée : API 0.1.0, commit 06652cb,
avant la finalisation documentaire 1.0.0. Windows, Python 3.14.7, PostgreSQL 18.6.
Le code fonctionnel est resté inchangé de REC-01 à REC-10.

Le [plan fourni](plan-de-recette.md) a été exécuté dans l'ordre. Pour partir
d'un état vide sans modifier les données de travail, les quatre tables ont
été créées dans un schéma PostgreSQL temporaire de la base locale, avec le
script sql/schema.sql, puis les comptes fournis ont été chargés. La connexion
de recette utilisait ce schéma via search_path. Le schéma a été supprimé après
la campagne ; les comptages des tables de travail sont restés inchangés.

Appels HTTP avec requests contre Uvicorn réel, port local 61976 ; contrôles
SQL avec SQLAlchemy. Streamlit a démarré sur le port 62003. Le parcours du
front a été exécuté par AppTest, avec des appels à cette API réelle. Les
serveurs de recette ont été arrêtés après les contrôles. Aucun jeton, hachage
ou mot de passe n'est conservé dans les preuves.

## Relevé d'exécution

| Cas | Date et heure | Version testée | Statut | Preuve : résultat effectivement obtenu | Anomalie |
|---|---|---|---|---|---|
| REC-01 | 15/10/2026 13:39:59 | 06652cb / 0.1.0 | OK | sql/schema.sql rejoué deux fois ; deux exécutions de python scripts/importer.py depuis le schéma vide : 120 stations, 2002 trajets, 177 incidents et deux comptes aux deux passages. | — |
| REC-02 | 15/10/2026 13:39:59 | 06652cb / 0.1.0 | OK | Journal de 192 événements et six colonnes. Stations : 120 = 120 + 0 + 0 ; trajets : 2030 = 2002 + 16 + 12 ; incidents : 180 = 177 + 3 + 0. Comptage des arrivées orphelines : 0. | — |
| REC-03 | 15/10/2026 13:40:00 | 06652cb / 0.1.0 | OK | POST /auth/login pour les deux comptes : 200, access_token présent, token_type bearer, rôle exploitant puis direction. | — |
| REC-04 | 15/10/2026 13:40:01 | 06652cb / 0.1.0 | OK | Mot de passe incorrect et compte inconnu : 401 avec le même corps {"detail":"Identifiants invalides"}. | — |
| REC-05 | 15/10/2026 13:40:01 | 06652cb / 0.1.0 | OK | GET /stations sans jeton puis avec jeton invalide : 401 ; GET /sante : 200, {"statut":"ok"}. | — |
| REC-06 | 15/10/2026 13:40:01 | 06652cb / 0.1.0 | OK | I2026-0002 : direction 403, ouvert inchangé en base ; exploitant 200, en_cours en base ; seconde transition identique 422, {"detail":"Transition de statut non autorisee"}. | — |
| REC-07 | 15/10/2026 13:40:01 | 06652cb / 0.1.0 | OK | Page 1 de 50 : total 120, 50 résultats, premier S001 ; page 3 : 20 résultats ; filtre Lille : 46 ; page 0 et taille 101 : 422. | — |
| REC-08 | 15/10/2026 13:40:01 | 06652cb / 0.1.0 | OK | S001 : 200, Lille - Gare ; S999 : 404, {"detail":"Station introuvable"}. | — |
| REC-09 | 15/10/2026 13:40:01 | 06652cb / 0.1.0 | OK | Du 24 au 30 août : 329, 311, 306, 300, 315, 219 et 222 trajets. Réponse API identique au SQL ligne à ligne ; somme = total de GET /trajets = 2002. | — |
| REC-10 | 15/10/2026 13:40:08 | 06652cb / 0.1.0 | OK | AppTest : page Stations 999, « Aucun résultat pour ces critères. » ; API arrêtée, Stations et Indicateurs affichent « L'API est injoignable. Vérifiez qu'elle est démarrée. » sans exception ; après redémarrage, tableau Stations visible. Santé HTTP du serveur Streamlit : 200. | — |

Extraits des contrôles SQL utilisés :

```sql
SELECT count(*) FROM station;
SELECT count(*) FROM trajet;
SELECT count(*) FROM incident;

SELECT count(*) FROM trajet t
LEFT JOIN station s ON s.station_id = t.station_arrivee
WHERE t.station_arrivee IS NOT NULL AND s.station_id IS NULL;

SELECT depart_horodatage::date AS jour, count(*) AS nb_trajets
FROM trajet
WHERE depart_horodatage::date BETWEEN '2026-08-24' AND '2026-08-30'
GROUP BY jour ORDER BY jour;
```

Les tests de non-régression des contrats se trouvent dans
tests/integration/test_importer.py, test_api.py et test_front.py.

## Synthèse

10 cas prévus, 10 exécutés : 10 OK, 0 KO, 0 NT. Aucune anomalie constatée
pendant cette campagne, aucune fiche ANO créée et aucun correctif de recette
nécessaire. La modification de REC-06 a disparu avec le schéma temporaire.

161 tests automatisés réussis. Couverture mesurée avec
`python -m pytest --cov=api/services --cov-report=term-missing` : 326 instructions
couvertes sur 326, soit 100 %. Ce chiffre ne prouve pas l'absence de tout défaut.

La sauvegarde réelle et son catalogue ont été vérifiés séparément. Le
parcours AppTest et le démarrage de Streamlit ne constituent pas une inspection
visuelle dans un navigateur ou sur tablette. La restauration complète dans
une autre base n'a pas été exécutée.

## Procès-verbal de recette — VéloVille V1

### 1. Identification

Application : VéloVille. État recetté : 06652cb, API 0.1.0, le 15/10/2026.
Environnement : Windows, Python 3.14.7, PostgreSQL 18.6, CSV fournis.
La version 1.0.0 regroupe la documentation et le présent bilan ; les traitements
fonctionnels restent ceux recettés. Exécution technique locale ; identité du
développeur et représentant du commanditaire à renseigner lors de la validation.

### 2. Périmètre recetté

REC-01 à REC-10 : import, audit, connexion, droits, pagination, recherche,
indicateur SQL et états du front. Les essais ont porté sur un schéma dédié
et les volumes fournis. Non testés : tablette réelle, lecteur d'écran,
montée en charge et restauration complète, faute d'environnement dédié.

### 3. Résultats de la campagne

10 cas prévus et exécutés ; 10 OK, 0 KO, 0 NT. Aucune anomalie ouverte,
aucune correction de recette à rejouer. Preuves dans le relevé ci-dessus.

### 4. Réserves bloquantes

Aucune réserve bloquante dans les cas exécutés.

### 5. Réserves non bloquantes

| Contrôle restant | Responsable | Échéance proposée |
|---|---|---|
| Vérifier le parcours visuel, le clavier et la lisibilité à 768 pixels dans un navigateur | Développeur | 16/10/2026, avant démonstration |
| Restaurer l'archive dans une base distincte et contrôler données et comptes | Administrateur technique | 16/10/2026, avant utilisation durable |
| Vérifier les tags et la branche fusionnée demandés par l'énoncé | Développeur | Avant dépôt |

Ces échéances sont des propositions à confirmer avec le commanditaire.

### 6. Décision

Proposition technique : **PRONONCÉE AVEC RÉSERVES**, à confirmer par le
commanditaire. Les dix cas sont conformes ; les contrôles visuels et la
restauration complète restent à réaliser. Ce document ne vaut pas signature
du commanditaire.

### 7. Signatures

Pour le commanditaire : nom, signature et date à renseigner.

Pour le développeur : nom, signature et date à renseigner.

## Axes d'amélioration

1. Vérifier les temps de réponse sur des volumes proches de l'exploitation
   réelle et examiner les plans SQL avant d'ajouter des index : maintenir les
   consultations sous deux secondes sans optimisation prématurée.
2. Tester périodiquement une restauration et planifier les sauvegardes avec
   contrôle des échecs : une archive lisible ne prouve pas une reprise complète.
3. Valider l'accessibilité avec les équipes sur tablette, au clavier et avec
   un lecteur d'écran : les libellés français ne suffisent pas à garantir le confort.
4. Étudier la purge des trajets selon la durée de conservation prévue et la
   révocation des jetons, pour mieux maîtriser les données et les accès.
