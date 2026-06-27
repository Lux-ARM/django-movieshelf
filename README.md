# 🎬 MovieShelf

**Catalogue personnel de films et séries** — Projet Django 2025-2026

MovieShelf est une application web permettant de cataloguer des films, suivre ce qui a été vu, est à voir ou est favori, et gérer une "shelf" (étagère) personnelle.

---

## ✨ Fonctionnalités

- 📚 **Catalogue Public** — Parcourir tous les films disponibles avec recherche et filtres par genre
- 📥 **Shelf Personnelle** — Ajouter des films en 1 clic à sa collection personnelle
- 📋 **Statuts** — À voir / Vu / Favori, avec gestion par utilisateur
- ⭐ **Notation** — Attribuer une note personnelle de 1 à 10
- 🎞️ **Affiches** — Support des posters via URL ou upload local
- 🔍 **Filtres** — Par genre, statut, et recherche textuelle
- 👤 **Authentification** — Inscription, connexion, déconnexion, profil
- 🛠️ **CRUD Manuel** — Ajout, modification, suppression de films
- 📊 **Statistiques** — Compteurs par statut sur le profil
- 🗃️ **Import CSV** — Import de films depuis un dataset Kaggle (TMDB)

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

## 🗃️ Import de films (optionnel)

Si vous disposez des fichiers CSV Kaggle (TMDB) dans le dossier `MovieDB/` :

```bash
python manage.py import_movies --user-id 1 --limit 100
```

Options :
- `--user-id` : ID du superutilisateur propriétaire des films importés
- `--limit` : Nombre max de films à importer (0 = tout)
- `--movies` / `--credits` / `--posters` : Chemins personnalisés vers les CSV

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
│   ├── views.py         # Catalogue public + Shelf + CRUD
│   ├── forms.py         # MovieForm
│   ├── urls.py
│   ├── admin.py
│   ├── tests.py
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
│       └── import_movies.py
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
| **UserMovie** | `user`, `movie`, `statut` (a_voir/vu/favori), `note` (1-10), `date_ajout` |

---

## 🌐 URLs principales

| URL | Page | Accès |
|-----|------|-------|
| `/` | Accueil | Public |
| `/catalogue/` | Catalogue public | Public |
| `/catalogue/<pk>/` | Fiche détail | Public |
| `/catalogue/creer/` | Ajout manuel | Connecté |
| `/catalogue/<pk>/modifier/` | Modifier (auteur) | Connecté |
| `/catalogue/<pk>/supprimer/` | Supprimer (auteur) | Connecté |
| `/catalogue/<pk>/add-to-shelf/` | Ajouter à sa shelf | Connecté |
| `/shelf/` | Ma Shelf | Connecté |
| `/shelf/<pk>/update/` | Modifier statut/note | Connecté |
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
