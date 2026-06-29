# 🎬 MovieShelf

**Catalogue personnel de films et séries** — Projet Django 2025-2026

> Dépôt GitHub : [https://github.com/Lux-ARM/django-movieshelf](https://github.com/Lux-ARM/django-movieshelf)

MovieShelf est une application web de catalogage de films avec shelf personnelle, recommandations TF-IDF, assistant IA (LLM), réinitialisation de mot de passe par question secrète, et intégration TMDB.

---

## ✨ Fonctionnalités

- 📚 **Catalogue Public** — ~5000 films avec recherche, filtres par genre, année, durée
- 📥 **Shelf Personnelle** — Ajout en 1 clic, statuts (À voir / Vu), favoris indépendants
- ❤️ **Favoris + Statuts séparés** — Un film peut être "Vu" ET "Favori"
- ⭐ **Notation** — Note personnelle de 1 à 10 par film
- 💬 **Commentaires** — Les utilisateurs peuvent commenter les films
- 🎞️ **Affiches** — URL ou upload local, récupération automatique via API TMDB
- 🤖 **Recommandations TF-IDF** — Films similaires basés sur les résumés (scikit-learn)
- 🎯 **Recommandations personnalisées** — Basées sur vos favoris + notes ≥ 6/10
- ✨ **Assistant IA (LLM)** — Sparkling Button ✨ : recherche en langage naturel et ajout à la shelf via DeepSeek
- 🔐 **Réinitialisation mot de passe** — Via question secrète (3 étapes : username → question → nouveau mot de passe)
- 🔍 **Filtres** — Genre, année (min/max), durée (min/max), recherche textuelle
- 👤 **Authentification** — Inscription avec question secrète, connexion, déconnexion, profil avec stats
- 📊 **Statistiques** — Films vus, à voir, favoris, note moyenne, genres dominants
- 🛠️ **CRUD Manuel** — Ajout, modification, suppression avec anti-doublon
- 🗃️ **Import CSV** — Import TMDB (Kaggle) + récupération automatique des posters
- 🧪 **Tests** — 39 tests unitaires (modèles, vues, shelf, CRUD, auth, password reset)
- 🎨 **Animations UI** — Scroll reveal, ripple effect sur boutons, compteurs animés, auto-dismiss toasts

---

## 🛠️ Prérequis

- Python 3.12+
- pip
- Git
- (Optionnel) Clé API TMDB pour les posters automatiques
- (Optionnel) Clé API DeepSeek pour l'assistant IA

---

## 🚀 Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/Lux-ARM/django-movieshelf.git
cd MovieShelf

# 2. Créer et activer l'environnement virtuel
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API (TMDB, DeepSeek) — voir section Configuration API

# 5. Appliquer les migrations
python manage.py migrate

# 6. Créer un superutilisateur
python manage.py createsuperuser

# 7. Lancer le serveur
python manage.py runserver
```

L'application est accessible sur [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🔑 Configuration API (optionnelle)

Copiez [`.env.example`](.env.example) en `.env` et remplissez les clés :

| Variable | Service | Utilisation | Obligatoire |
|----------|---------|-------------|-------------|
| `TMDB_API_KEY` | [The Movie Database](https://www.themoviedb.org/settings/api) | Récupération des posters et recherche de films | Non |
| `TMDB_ACCESS_TOKEN` | TMDB | Token d'accès API v4 | Non |
| `DEEPSEEK_API_KEY` | [DeepSeek Platform](https://platform.deepseek.com/api_keys) | Assistant IA (Sparkling Button) | Non |

Sans ces clés, l'application fonctionne normalement — seules les fonctions de récupération automatique de posters et l'assistant IA seront désactivées.

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

### Principe

Le systeme de recommandation utilise l'approche **TF-IDF (Term Frequency - Inverse Document Frequency)**
associee a la **similarite cosinus**, implementee via la bibliotheque `scikit-learn` :

1. Les resumes des films sont vectorises en une matrice creuse de **~4800 films x 5000 termes** (unigrammes + bigrammes)
2. Le poids TF-IDF de chaque terme est calcule : plus un mot est frequent dans un resume mais rare dans le corpus, plus il est important
3. La similarite cosinus entre deux vecteurs mesure l'angle qui les separe (plus l'angle est petit, plus les films sont similaires)
4. Les recommandations personnalisees cumulent les scores des films favoris et des notes >= 6/10 de l'utilisateur

### Performance

| Metrique | Valeur |
|----------|--------|
| Films vectorises | ~4800 |
| Features (termes) | 5000 |
| Taille fichier pickle | ~1,4 Mo |
| Stockage memoire | Matrice creuse CSR |
| Temps de chargement | ~100 ms (singleton) |
| N-grammes | (1, 2) |

Le choix du TF-IDF (plutot que Sentence Transformers + base vectorielle FAISS/ChromaDB) a ete motive par
la legerete du modele (1,4 Mo vs 80-400 Mo pour un Transformer), l'absence de dependance a une base
vectorielle externe, et une qualite de recommandation suffisante pour un corpus de 4800 resumes.

```bash
# Précalculer la matrice TF-IDF (obligatoire avant les recommandations)
python manage.py build_tfidf

# Créer des utilisateurs de test avec favoris + notes
python manage.py create_test_users
```

---

## ✨ Assistant IA (Sparkling Button)

Un bouton flottant ✨ est disponible en bas à droite de l'écran pour les utilisateurs connectés. Il permet de :

- **Rechercher** des films en langage naturel : *"un film SF spatial pas trop long"*
- **Ajouter à sa shelf** par la voix : *"ajoute Inception, vu, 9/10, favori"*

L'assistant utilise l'API DeepSeek pour interpréter l'intention et interroger le catalogue ou TMDB.

Nécessite la clé `DEEPSEEK_API_KEY` dans le fichier `.env`.

---

## 🔐 Réinitialisation de mot de passe

Un utilisateur ayant oublié son mot de passe peut le réinitialiser via sa question secrète :

1. **Étape 1** — Saisir son nom d'utilisateur sur `/accounts/password-reset/`
2. **Étape 2** — Répondre à la question secrète choisie lors de l'inscription
3. **Étape 3** — Définir un nouveau mot de passe

Le lien "Mot de passe oublié ?" est accessible depuis la page de connexion.

---

## 🧪 Tests

```bash
python manage.py test catalogue accounts
```

Les tests couvrent :
- ✅ Modèles (Genre, Movie, UserMovie, Comment, UserProfile)
- ✅ Pages publiques (accueil, catalogue, détail, genres)
- ✅ CRUD (création, modification, suppression, permissions auteur)
- ✅ Shelf (ajout, filtres, mise à jour statut/note, anti-doublon)
- ✅ Authentification (inscription avec question secrète, connexion, déconnexion, profil)
- ✅ Inscription — création automatique du UserProfile

---

## 📁 Structure du projet

```
MovieShelf/
├── movieshelf/              # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── catalogue/               # Application principale
│   ├── models.py            # Genre, Movie, UserMovie, Comment
│   ├── views.py             # Catalogue + Shelf + CRUD + Recos + LLM endpoint
│   ├── recommender.py       # TF-IDF + recommandations personnalisées
│   ├── llm_service.py       # Service LLM Agentic (DeepSeek)
│   ├── forms.py             # MovieForm (anti-doublon), CommentForm
│   ├── urls.py
│   ├── admin.py
│   ├── tests.py
│   ├── templatetags/        # Filtres custom (dict_get, etc.)
│   ├── static/catalogue/
│   │   ├── style.css        # 850+ lignes, thème Jellyfin Dark
│   │   └── main.js          # Animations UI (scroll reveal, ripple, counters)
│   ├── templates/catalogue/
│   │   ├── base.html        # Base avec navbar Glassmorphism + LLM widget
│   │   ├── accueil.html
│   │   ├── catalogue.html
│   │   ├── detail.html
│   │   ├── creation.html
│   │   ├── modification.html
│   │   ├── suppression_confirm.html
│   │   ├── shelf.html
│   │   ├── genres.html
│   │   └── genre_detail.html
│   └── management/commands/
│       ├── import_movies.py
│       ├── build_tfidf.py
│       ├── check_posters.py
│       ├── fetch_posters.py
│       ├── create_test_users.py
│       └── fix_template_eq.py    # Utilitaire syntaxe == dans templates
├── accounts/                # Application authentification
│   ├── models.py            # UserProfile (question secrète)
│   ├── views.py             # Signup, Profile, Password Reset (3 étapes)
│   ├── forms.py             # Inscription + Password Reset forms
│   ├── urls.py
│   ├── tests.py
│   ├── admin.py
│   ├── migrations/
│   └── templates/accounts/
│       ├── login.html
│       ├── signup.html
│       ├── profile.html
│       ├── password_reset.html          # Étape 1 : username
│       ├── password_reset_question.html  # Étape 2 : question secrète
│       └── password_reset_change.html   # Étape 3 : nouveau mot de passe
├── MovieDB/                 # Données CSV (non versionnées)
├── .env.example             # Template des variables d'environnement
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🔑 Modèles de données

| Modèle | App | Champs clés |
|--------|-----|-------------|
| **Genre** | catalogue | `nom`, `slug`, `description` |
| **Movie** | catalogue | `titre`, `realisateur`, `resume`, `annee_sortie`, `duree`, `poster_url`, `poster`, `genres` (M2M), `auteur`, `vote_average`, `vote_count`, `tmdb_id` |
| **UserMovie** | catalogue | `user`, `movie`, `statut` (a_voir/vu), `is_favori`, `note` (1-10), `date_ajout` |
| **Comment** | catalogue | `movie`, `user`, `texte`, `date_creation` |
| **UserProfile** | accounts | `user` (OneToOne), `security_question` (choice), `security_answer` (hashé) |

### Note sur le statut et les favoris

Le `statut` (À voir / Vu) et `is_favori` sont deux champs **indépendants** dans `UserMovie`. Cela permet à un film d'être à la fois « Vu » ET « Favori », ce qui est plus flexible que les 3 valeurs figées (`à voir`, `vu`, `favori`) demandées dans le cahier des charges initial.

---

## 🌐 URLs principales

| URL | Page | Accès |
|-----|------|-------|
| `/` | Accueil (recommandations si connecté) | Public |
| `/catalogue/` | Catalogue avec filtres (genre, année, durée) | Public |
| `/catalogue/<pk>/` | Fiche détail + films similaires + commentaires | Public |
| `/catalogue/creer/` | Ajout manuel d'un film | Connecté |
| `/catalogue/<pk>/modifier/` | Modifier (auteur uniquement) | Connecté |
| `/catalogue/<pk>/supprimer/` | Supprimer (auteur uniquement) | Connecté |
| `/catalogue/<pk>/add-to-shelf/` | Ajouter à sa shelf | Connecté |
| `/shelf/` | Ma Shelf (filtres À voir/Vu/Favoris) | Connecté |
| `/shelf/<pk>/update/` | Modifier statut/note/favori | Connecté |
| `/genres/` | Liste des genres | Public |
| `/genres/<slug>/` | Films par genre | Public |
| `/accounts/signup/` | Inscription (avec question secrète) | Public |
| `/accounts/login/` | Connexion | Public |
| `/accounts/logout/` | Déconnexion | Connecté |
| `/accounts/profile/` | Profil + statistiques personnelles | Connecté |
| `/accounts/password-reset/` | Mot de passe oublié — étape 1 | Public |
| `/accounts/password-reset/question/` | Mot de passe oublié — étape 2 | Public |
| `/accounts/password-reset/change/` | Mot de passe oublié — étape 3 | Public |
| `/admin/` | Django Admin | Staff |
| `/api/llm/` | Endpoint AJAX assistant IA | Connecté |

---

## 🎨 Design

Thème sombre inspiré de Jellyfin (CSS Vanilla, ~850 lignes + JS animations) :

| Variable | Couleur | Usage |
|----------|---------|-------|
| `--bg-primary` | `#0a0e17` | Fond principal |
| `--bg-card` | `#141a29` | Cartes, navbar, conteneurs |
| `--text-primary` | `#e2e8f0` | Texte principal |
| `--text-secondary` | `#94a3b8` | Texte secondaire, métadonnées |
| `--accent` | `#00a4dc` | Accent cyan |
| `--accent-alt` | `#7b2cbf` | Accent violet |
| `--accent-rose` | `#f72585` | Favoris, alertes |

### Animations JavaScript ([`main.js`](catalogue/static/catalogue/main.js))
- **Scroll Reveal** — Les cartes apparaissent avec animation au défilement (IntersectionObserver)
- **Ripple Effect** — Effet de vague au clic sur les boutons
- **Compteurs animés** — Les statistiques du profil s'animent au chargement
- **Toast auto-dismiss** — Les messages disparaissent après 5 secondes
- **Auto-resize** — Le textarea du LLM s'adapte à son contenu

---

## ✅ Checklist de validation (cahier des charges)

- [x] Environnement virtuel `.venv` + `requirements.txt`
- [x] Architecture MVT : URLs, vues, modèles, templates, statiques
- [x] Base de données SQLite, migrations, Django Admin
- [x] Template `base.html`, héritage, navigation, CSS
- [x] Formulaires POST avec `{% csrf_token %}`
- [x] Inscription, connexion, déconnexion
- [x] Tests automatisés (39)
- [x] Dépôt GitHub avec commits réguliers
- [x] `README.md`, `.gitignore`, `requirements.txt`
- [x] CRUD complet (création, consultation, modification, suppression)
- [x] Gestion des genres cinématographiques
- [x] Statuts (À voir / Vu) + Favoris
- [x] `python manage.py runserver` démarre sans erreur
- [x] `python manage.py test` s'exécute avec succès

---

*Projet réalisé dans le cadre du cours Django — Année universitaire 2025-2026*
