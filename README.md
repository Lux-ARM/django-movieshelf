# 🎬 MovieShelf

**Catalogue personnel de films et séries** — Projet Django 2025-2026

MovieShelf est une application web de catalogage de films avec shelf personnelle, recommandations TF-IDF, et intégration TMDB.

---

## ✨ Fonctionnalités

- 📚 **Catalogue Public** — ~5000 films avec recherche, filtres par genre et statut
- 📥 **Shelf Personnelle** — Ajout en 1 clic, statuts (À voir / Vu), favoris indépendants
- ❤️ **Favoris + Statuts séparés** — Un film peut être "Vu" ET "Favori"
- ⭐ **Notation** — Note personnelle de 1 à 10 par film
- 🎞️ **Affiches** — URL ou upload local, récupération automatique via API TMDB
- 🤖 **Recommandations TF-IDF** — Films similaires basés sur les résumés (scikit-learn)
- 🎯 **Recommandations personnalisées** — Basées sur vos favoris + notes ≥ 6/10
- 🔍 **Filtres** — Genre, statut (À voir/Vu), favoris, recherche textuelle
- 👤 **Authentification** — Inscription, connexion, déconnexion, profil avec stats
- 🛠️ **CRUD Manuel** — Ajout, modification, suppression avec anti-doublon
- 🗃️ **Import CSV** — Import TMDB (Kaggle) + vérification/récupération posters
- 🧪 **Tests** — 30+ tests unitaires (modèles, vues, shelf, CRUD, auth)

---

## 🛠️ Prérequis

- Python 3.12+
- pip
- Git

---

## 🚀 Installation

```bash
# 1. Cloner le dépôt
git clone <URL_DU_DEPOT>
cd MovieShelf

# 2. Créer et activer l'environnement virtuel
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
python manage.py migrate

# 5. Créer un superutilisateur
python manage.py createsuperuser

# 6. Lancer le serveur
python manage.py runserver
```

L'application est accessible sur [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🗃️ Import de films

```bash
# Import depuis les CSV Kaggle (MovieDB/)
python manage.py import_movies --user-id 1 --limit 100

# Récupérer les posters manquants via l'API TMDB
python manage.py fetch_posters

# Vérifier les posters existants (dry-run)
python manage.py check_posters --dry-run
```

---

## 🤖 Recommandations TF-IDF

```bash
# Précalculer la matrice TF-IDF (obligatoire avant les recos)
python manage.py build_tfidf

# Créer des utilisateurs de test avec favoris + notes
python manage.py create_test_users
```

---

## 🧪 Tests

```bash
python manage.py test catalogue accounts
```

---

## 📁 Structure du projet

```
MovieShelf/
├── movieshelf/          # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── catalogue/           # Application principale
│   ├── models.py        # Genre, Movie, UserMovie
│   ├── views.py         # Catalogue + Shelf + CRUD + Recos
│   ├── recommender.py   # TF-IDF + recommandations
│   ├── forms.py         # MovieForm (anti-doublon)
│   ├── urls.py
│   ├── admin.py
│   ├── tests.py
│   ├── templatetags/    # Filtres custom (dict_get)
│   ├── templates/catalogue/
│   │   ├── base.html
│   │   ├── accueil.html
│   │   ├── catalogue.html
│   │   ├── detail.html
│   │   ├── creation.html
│   │   ├── modification.html
│   │   ├── suppression_confirm.html
│   │   ├── shelf.html
│   │   ├── genres.html
│   │   └── genre_detail.html
│   ├── static/catalogue/
│   │   └── style.css
│   └── management/commands/
│       ├── import_movies.py
│       ├── build_tfidf.py
│       ├── check_posters.py
│       ├── fetch_posters.py
│       └── create_test_users.py
├── accounts/            # Authentification
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── tests.py
│   └── templates/accounts/
│       ├── login.html
│       ├── signup.html
│       └── profile.html
├── MovieDB/             # Données CSV (non versionnées)
├── manage.py
├── requirements.txt
└── .gitignore
```

---

## 🔑 Modèles de données

| Modèle | Champs clés |
|--------|-------------|
| **Genre** | `nom`, `slug`, `description` |
| **Movie** | `titre`, `realisateur`, `resume`, `annee_sortie`, `duree`, `poster_url`, `poster`, `genres`, `auteur`, `vote_average`, `vote_count`, `tmdb_id` |
| **UserMovie** | `user`, `movie`, `statut` (a_voir/vu), `is_favori`, `note` (1-10), `date_ajout` |

---

## 🌐 URLs principales

| URL | Page | Accès |
|-----|------|-------|
| `/` | Accueil (recommandations si connecté) | Public |
| `/catalogue/` | Catalogue public | Public |
| `/catalogue/<pk>/` | Fiche détail + similaires + recommandations | Public |
| `/catalogue/creer/` | Ajout manuel | Connecté |
| `/catalogue/<pk>/modifier/` | Modifier (auteur) | Connecté |
| `/catalogue/<pk>/supprimer/` | Supprimer (auteur) | Connecté |
| `/catalogue/<pk>/add-to-shelf/` | Ajouter à sa shelf | Connecté |
| `/shelf/` | Ma Shelf (filtres À voir/Vu/Favoris) | Connecté |
| `/shelf/<pk>/update/` | Modifier statut/note/favori | Connecté |
| `/genres/` | Liste des genres | Public |
| `/genres/<slug>/` | Films par genre | Public |
| `/accounts/signup/` | Inscription | Public |
| `/accounts/login/` | Connexion | Public |
| `/accounts/profile/` | Profil + stats | Connecté |
| `/admin/` | Django Admin | Staff |

---

## 🎨 Design

Thème sombre inspiré de Jellyfin :
- Fond : `#0a0e17`
- Cartes : `#141a29`
- Texte : `#e2e8f0`
- Accent cyan : `#00a4dc`
- Accent rose (favoris) : `#f72585`

---

*Projet réalisé dans le cadre du cours Django — Année universitaire 2025-2026*
