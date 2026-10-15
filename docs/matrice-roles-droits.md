# Matrice rôles x droits

| Méthode et route | Anonyme | Exploitant | Direction |
|---|---|---|---|
| GET /sante | Autorisé, 200 | Autorisé, 200 | Autorisé, 200 |
| POST /auth/login | Autorisé ; 401 si identifiants invalides | Autorisé | Autorisé |
| GET /stations | 401 | Lecture, 200 | Lecture, 200 |
| GET /stations/{station_id} | 401 | Lecture, 200 | Lecture, 200 |
| GET /trajets | 401 | Lecture, 200 | Lecture, 200 |
| GET /incidents | 401 | Lecture, 200 | Lecture, 200 |
| PUT /incidents/{incident_id}/statut | 401 | Modification, 200 | 403 |
| GET /indicateurs/activite-par-jour | 401 | Lecture, 200 | Lecture, 200 |
| GET /indicateurs/stations-actives | 401 | Lecture, 200 | Lecture, 200 |
| GET /indicateurs/incidents-par-statut | 401 | Lecture, 200 | Lecture, 200 |

Les succès supposent des paramètres valides et une ressource existante.
Un jeton invalide ou expiré entraîne un 401. Une station ou un incident absent
entraîne un 404 ; une validation ou une transition interdite entraîne un 422.
L'API vérifie le compte en base et son rôle, même si le front masque déjà
le formulaire de modification pour le rôle direction.

## Données sensibles

- Mots de passe : hachages bcrypt en base et champ de saisie masqué.
  Les mots de passe ne sont pas enregistrés dans les preuves de recette.
- Jetons : signature HS256, expiration configurable et secret dans
  l'environnement. Le jeton est conservé dans st.session_state, sans affichage
  à l'écran ni passage dans l'URL. La déconnexion vide cette session ; un
  jeton déjà émis reste valide jusqu'à son expiration.
- Pseudonyme usager_ref : donnée indirectement identifiante, contrôlée à
  l'import. Aucun des quatre écrans ne l'affiche. GET /trajets inclut cette
  colonne pour les deux rôles authentifiés, conformément au contrat.
- Configuration : .env ignoré par Git ; .env.example sans clé JWT réelle.
  Les mots de passe de test sont générés ou lus dans TEST_PASSWORD.
- Sauvegardes : données et hachages des comptes, ignorés par Git et à
  conserver dans un emplacement réservé à l'administrateur.

Les requêtes SQL utilisent des paramètres pour les données saisies. Les
comptes sont créés par script SQL, sans interface d'administration en V1.
