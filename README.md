# Observatoire de la régularité TGV

Projet portfolio : API SNCF → snapshot JSON → Pandas → PostgreSQL → Streamlit/Plotly.

## Démarrage

Prérequis : Docker avec Compose, connexion Internet.

```bash
cp .env.example .env
# Modifier le mot de passe local dans .env avant le démarrage
 docker compose up --build
```

Ouvrir http://localhost:8501. Le service ETL attend PostgreSQL ; le tableau de bord attend la réussite de l'ETL. La base est conservée dans un volume Docker.

Pour actualiser les données :

```bash
docker compose run --rm etl
```

Le cache de l'interface expire après cinq minutes. Pour charger le snapshot fourni si l'API est indisponible :

```bash
docker compose run --rm etl python pipeline.py --offline
docker compose up dashboard
```

Pour vérifier les données sans PostgreSQL :

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python pipeline.py --offline --validate-only
python -m pytest -q
```

Exécuter les commandes depuis le répertoire de ce README. Pour une installation native, configurer PGHOST, PGPORT, PGDATABASE, PGUSER et PGPASSWORD, lancer `python pipeline.py`, puis `streamlit run app.py`.

## Données et indicateurs

Source officielle : https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-axes/

API : https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/regularite-mensuelle-tgv-axes/exports/json

Snapshot téléchargé le 17 octobre 2026 UTC : 835 lignes, janvier 2015 à septembre 2026. Une valeur manque pour chacun des deux indicateurs ; ces valeurs restent nulles. Aucune donnée synthétique incluse. Consulter la fiche officielle pour la licence, les définitions et les conditions de réutilisation ; conserver l'attribution SNCF lors d'une publication.

La ponctualité origine correspond aux départs avec moins d'une minute de retard. La régularité composite est reprise telle que publiée. Les deux indicateurs ne sont pas interchangeables. Aucun taux national n'est calculé : le jeu ne fournit pas les volumes pour pondérer les axes. Les valeurs sont mensuelles, sans temps réel ni mesure individuelle par train.

## Pipeline et qualité

- Vérification des colonnes, des mois, des axes et des pourcentages entre 0 et 100.
- Suppression des doublons identiques après nettoyage ; rejet des clés mois/axe contradictoires.
- Valeurs manquantes conservées, sans remplacement par zéro.
- Rapport local avec SHA-256, dates couvertes et décompte des valeurs nulles.
- Chargement complet dans une transaction : contraintes SQL, verrou de chargement et clé primaire (date, axe). Un échec de chargement restaure l'état antérieur de la base.
- Journal PostgreSQL `ingestion_runs` enregistré dans la même transaction. Le rapport local est un rapport de validation ; sa présence seule ne prouve pas un chargement réussi.
- Les relances remplacent le snapshot courant sans dupliquer les observations. L'historique des exécutions est conservé, pas les versions historiques de chaque valeur.

## Interface

Filtres axes/période, choix de l'indicateur, évolution temporelle, comparaison au dernier mois sélectionné, table détaillée, export CSV et traçabilité du chargement. Un axe absent du dernier mois ne reçoit pas artificiellement une valeur antérieure.

## Validation réalisée et limites

Le snapshot réel a été nettoyé avec succès et les sept cas de contrôle du nettoyage ont été exécutés : dédoublonnage/espaces, mois invalide, axe vide, taux hors limites, valeur non numérique, conflit de clé et conservation des nulls. Les modules Python ont été compilés. Les mêmes cas sont fournis dans `tests/test_pipeline.py` pour pytest.

Docker, PostgreSQL et Streamlit n'ont pas été exécutés dans l'environnement de création : l'intégration SQL et le rendu du tableau de bord restent à valider avec `docker compose up --build`. Les dépendances sont bornées par version majeure, sans lockfile. Le mot de passe d'exemple doit être changé ; ce Compose vise une démonstration locale.
