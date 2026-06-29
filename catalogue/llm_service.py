"""Service LLM Agentic v2 — DeepSeek avec Function Calling libre.

Le LLM decide librement de sa strategie selon la requete utilisateur :
  - Recommandation simple → TF-IDF via get_system_recommendations
  - Demande specifique → check_movies_exist + search_db
  - Ajout a la shelf → add_to_shelf
  - Film absent → add_movie_from_tmdb
"""
import json
import os
import urllib.request
import urllib.error
import urllib.parse
from django.db.models import Q
from .models import Movie, Genre, UserMovie

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL = "deepseek-v4-flash"
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

MAX_TOOL_TURNS = 3
TEMPERATURE = 0.3

# ═══════════════════════════════════════════════
#  1. TOOL DEFINITIONS  (OpenAI-compatible JSON
#     Schema pour le Function Calling DeepSeek)
# ═══════════════════════════════════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_db",
            "description": "Recherche des films dans la base de donnees par mots-cles (titre, resume, realisateur), genres, annee et duree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Mots-cles pour chercher dans le titre, resume ou realisateur"
                    },
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Genres pour filtrer (ex: Action, Science Fiction, Thriller)"
                    },
                    "year_min": {"type": "integer", "description": "Annee minimum"},
                    "year_max": {"type": "integer", "description": "Annee maximum"},
                    "duree_min": {"type": "integer", "description": "Duree minimum en minutes"},
                    "duree_max": {"type": "integer", "description": "Duree maximum en minutes"},
                    "limit": {"type": "integer", "description": "Nombre max de resultats", "default": 10}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_movies_exist",
            "description": "Verifie si des films (par titre) existent dans la base de donnees. Utilise d'abord une correspondance exacte, puis approximative. A utiliser pour verifier que les films que tu connais sont bien disponibles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste des titres de films a verifier"
                    }
                },
                "required": ["titles"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_genres",
            "description": "Retourne la liste de tous les genres de films disponibles dans la base de donnees."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_recommendations",
            "description": "Recommandations personnalisees basees sur les favoris de l'utilisateur via l'algorithme TF-IDF. A utiliser quand l'utilisateur demande une recommandation generale sans precision.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Nombre de recommandations souhaitées",
                        "default": 4
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_context",
            "description": "Retourne le contexte de l'utilisateur connecte : ses films favoris, le nombre de films dans sa shelf, ses statistiques (vus, a voir)."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_movie_from_tmdb",
            "description": "Cherche un film sur TMDB et l'ajoute a la base de donnees locale. A utiliser quand un film demande par l'utilisateur n'existe pas encore dans la base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titre": {
                        "type": "string",
                        "description": "Le titre du film a chercher et ajouter via TMDB"
                    }
                },
                "required": ["titre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_shelf",
            "description": "Ajoute un film a la shelf personnelle de l'utilisateur (collection privee). Detecte le statut (vu/a_voir), la note et si c'est un favori a partir de la demande utilisateur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titre": {
                        "type": "string",
                        "description": "Titre du film a ajouter"
                    },
                    "statut": {
                        "type": "string",
                        "enum": ["vu", "a_voir"],
                        "description": "Statut : 'vu' si l'utilisateur l'a deja vu, 'a_voir' sinon",
                        "default": "a_voir"
                    },
                    "note": {
                        "type": "integer",
                        "description": "Note sur 10 (optionnelle)",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "is_favori": {
                        "type": "boolean",
                        "description": "true si l'utilisateur aime ce film",
                        "default": False
                    }
                },
                "required": ["titre"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navigate_to",
            "description": "Redirige l'utilisateur vers une page de la plateforme. A utiliser quand l'utilisateur demande explicitement a voir/aller sur une page (ex: 'montre ma shelf', 'va sur mon profil', 'affiche le film X').",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "enum": ["accueil", "catalogue", "shelf", "profil", "genres", "ajouter_film"],
                        "description": "La page de destination : accueil(/), catalogue, shelf (Ma Bibliotheque), profil, genres, ajouter_film"
                    },
                    "titre_film": {
                        "type": "string",
                        "description": "Titre du film si on veut voir un film specifique (optionnel, utilise search_db pour trouver l'id)"
                    },
                    "genre": {
                        "type": "string",
                        "description": "Nom du genre si on veut voir un genre specifique (optionnel)"
                    }
                },
                "required": ["page"]
            }
        }
    },
]

# ═══════════════════════════════════════════════
#  2. SYSTEM PROMPT
# ═══════════════════════════════════════════════

SYSTEM_PROMPT = """Tu es MovieBot, assistant IA de MovieShelf.

REGLES STRICTES :
1. ACTIONS (recommander/ajouter/chercher) → EXECUTE DIRECT sans texte.
   Interdit : "voici", "j'ai trouvé", "d'après", "basé sur", "en fonction de", "pour toi".
   Si tu utilises un outil, le resultat parle de lui-meme.
   Reponse max 3 mots si confirmation necessaire (ex: "✅ Ajouté !").

2. QUESTIONS → 1-2 phrases max.
   - "comment voir ma shelf ?" → "Va dans Ma Bibliotheque en haut a droite."
   - "c'est quoi MovieShelf ?" → Explique en 15 mots max.
   - "comment ajouter un film ?" → "Bouton Ajouter en haut a droite."

3. NAVIGATION → Utilise navigate_to. Phrase courte.
   - "montre ma shelf" → navigate_to(page="shelf")
   - "affiche Inception" → navigate_to(page="catalogue", titre_film="Inception")

RECOMMANDER :
- Sans precision → get_system_recommendations
- Specifique → check_movies_exist + search_db

AJOUTER A LA SHELF :
- check_movies_exist → si trouve: add_to_shelf → sinon: add_movie_from_tmdb + add_to_shelf

REGLES ABSOLUES :
- Jamais de phrase d'introduction ou conclusion
- Jamais de commentaire sur ce que tu fais
- Actions = silencieux, outils font le travail
- Questions = 15 mots max
- Verifie TOUJOURS avec un outil avant d'affirmer"""


# ═══════════════════════════════════════════════
#  3. TOOL HANDLERS  (execution Python des tools)
# ═══════════════════════════════════════════════


def _tool_search_db(query="", genres=None, year_min=None, year_max=None,
                    duree_min=None, duree_max=None, limit=10, user=None):
    """Recherche flexible multi-champs dans la DB."""
    qs = Movie.objects.all()

    if query:
        qs = qs.filter(
            Q(titre__icontains=query)
            | Q(resume__icontains=query)
            | Q(realisateur__icontains=query)
        )

    if genres:
        qs = qs.filter(genres__nom__in=genres)

    if year_min:
        qs = qs.filter(annee_sortie__gte=int(year_min))
    if year_max:
        qs = qs.filter(annee_sortie__lte=int(year_max))
    if duree_min:
        qs = qs.filter(duree__gte=int(duree_min))
    if duree_max:
        qs = qs.filter(duree__lte=int(duree_max))

    movies = qs.distinct()[:limit]

    return {
        "results": [
            {
                "id": m.pk,
                "titre": m.titre,
                "annee": m.annee_sortie,
                "realisateur": m.realisateur,
                "duree": m.duree,
                "poster": m.poster_url or "",
                "note_moyenne": m.vote_average,
                "genres": [g.nom for g in m.genres.all()],
                "url": m.get_absolute_url(),
            }
            for m in movies
        ],
        "total": len(movies),
    }


def _tool_check_movies_exist(titles, user=None):
    """Verifie quels films existent en DB (exact puis fuzzy)."""
    found = []
    not_found = []

    for titre in titles:
        movie = Movie.objects.filter(titre__iexact=titre).first()
        if not movie:
            movie = Movie.objects.filter(titre__icontains=titre).first()
        if movie:
            found.append({
                "id": movie.pk,
                "titre": movie.titre,
                "annee": movie.annee_sortie,
                "poster": movie.poster_url or "",
                "url": movie.get_absolute_url(),
                "realisateur": movie.realisateur,
            })
        else:
            not_found.append(titre)

    return {
        "found": found,
        "not_found": not_found,
        "message": f"{len(found)} film(s) trouve(s), {len(not_found)} manquant(s)"
    }


def _tool_get_genres(user=None):
    """Liste tous les genres disponibles."""
    genres = Genre.objects.all()
    return {
        "genres": [
            {"nom": g.nom, "slug": g.slug, "nb_films": g.movies.count()}
            for g in genres
        ]
    }


def _tool_get_system_recommendations(limit=4, user=None):
    """Recommandations TF-IDF personnalisees."""
    if not user or not user.is_authenticated:
        return {"error": "Utilisateur non connecte", "results": []}

    try:
        from .recommender import get_recommendations_for_user
        recs = get_recommendations_for_user(user, top_n=limit)
        return {
            "results": [
                {
                    "id": m.pk,
                    "titre": m.titre,
                    "annee": m.annee_sortie,
                    "poster": m.poster_url or "",
                    "url": m.get_absolute_url(),
                    "score": s,
                }
                for m, s in recs
            ]
        }
    except (FileNotFoundError, ImportError) as e:
        return {"error": str(e), "results": []}


def _tool_get_user_context(user=None):
    """Contexte de l'utilisateur."""
    if not user or not user.is_authenticated:
        return {"error": "Utilisateur non connecte"}

    shelf = UserMovie.objects.filter(user=user)
    favs = shelf.filter(is_favori=True).select_related('movie')[:5]

    return {
        "nb_films_shelf": shelf.count(),
        "nb_vus": shelf.filter(statut='vu').count(),
        "nb_a_voir": shelf.filter(statut='a_voir').count(),
        "nb_favoris": shelf.filter(is_favori=True).count(),
        "favoris": [
            {"id": f.movie.pk, "titre": f.movie.titre, "annee": f.movie.annee_sortie}
            for f in favs
        ],
    }


def _tool_add_movie_from_tmdb(titre, user=None):
    """Cherche sur TMDB, cree le film dans la DB."""
    if not TMDB_API_KEY:
        return {"error": "Cle API TMDB non configuree"}
    if not user or not user.is_authenticated:
        return {"error": "Connectez-vous pour ajouter un film."}

    # Deja en DB ?
    existing = Movie.objects.filter(titre__iexact=titre).first()
    if existing:
        return {
            "success": True,
            "id": existing.pk,
            "titre": existing.titre,
            "annee": existing.annee_sortie,
            "poster": existing.poster_url or "",
            "url": existing.get_absolute_url(),
            "message": "Ce film est deja dans la base !",
        }

    url = (
        f"https://api.themoviedb.org/3/search/movie"
        f"?api_key={TMDB_API_KEY}&query={urllib.parse.quote(titre)}&language=fr-FR"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("results"):
            return {"error": f"Aucun resultat TMDB pour '{titre}'"}

        r = data["results"][0]
        movie = Movie.objects.create(
            titre=r["title"],
            resume=r.get("overview", ""),
            annee_sortie=int(r["release_date"][:4]) if r.get("release_date") else None,
            poster_url=f"https://image.tmdb.org/t/p/w500{r['poster_path']}" if r.get("poster_path") else "",
            tmdb_id=r["id"],
            vote_average=r.get("vote_average"),
            vote_count=r.get("vote_count"),
            auteur=user,
        )
        return {
            "success": True,
            "id": movie.pk,
            "titre": movie.titre,
            "annee": movie.annee_sortie,
            "poster": movie.poster_url or "",
            "url": movie.get_absolute_url(),
            "message": f"Film '{movie.titre}' ajoute avec succes depuis TMDB !",
        }
    except Exception as e:
        return {"error": f"Erreur TMDB: {str(e)}"}


def _tool_add_to_shelf(titre, statut="a_voir", note=None, is_favori=False, user=None):
    """Ajoute un film a la shelf personnelle de l'utilisateur."""
    if not user or not user.is_authenticated:
        return {"error": "Connectez-vous pour ajouter un film a votre shelf."}

    movie = Movie.objects.filter(titre__iexact=titre).first()
    if not movie:
        movie = Movie.objects.filter(titre__icontains=titre).first()
    if not movie:
        return {"error": f"Film '{titre}' introuvable dans la base. Utilise d'abord add_movie_from_tmdb."}

    entry, created = UserMovie.objects.get_or_create(
        user=user,
        movie=movie,
        defaults={"statut": statut, "is_favori": is_favori, "note": note},
    )
    if not created:
        entry.statut = statut
        entry.is_favori = is_favori
        if note is not None:
            entry.note = note
        entry.save()

    return {
        "__action": "add",
        "success": True,
        "id": movie.pk,
        "titre": movie.titre,
        "annee": movie.annee_sortie,
        "poster_url": movie.poster_url or "",
        "url": movie.get_absolute_url(),
        "message": f"{'Vu' if statut == 'vu' else 'A voir'}{' ❤️' if is_favori else ''}{f' {note}/10' if note else ''}",
        "statut": statut,
        "is_favori": is_favori,
        "created": created,
    }


def _tool_navigate_to(page, titre_film=None, genre=None, user=None):
    """Redirige l'utilisateur vers une page de la plateforme."""
    PAGES = {
        "accueil":     {"url": "/",          "label": "Accueil"},
        "catalogue":   {"url": "/catalogue/", "label": "Catalogue"},
        "shelf":       {"url": "/shelf/",     "label": "Ma Bibliotheque"},
        "profil":      {"url": "/accounts/profile/", "label": "Profil"},
        "genres":      {"url": "/genres/",    "label": "Genres"},
        "ajouter_film": {"url": "/catalogue/creer/", "label": "Ajouter un film"},
    }

    # Film specifique
    if titre_film:
        movie = Movie.objects.filter(titre__iexact=titre_film).first()
        if not movie:
            movie = Movie.objects.filter(titre__icontains=titre_film).first()
        if movie:
            return {
                "__action": "navigate",
                "url": movie.get_absolute_url(),
                "label": f"Film: {movie.titre}",
                "message": f"Redirection vers {movie.titre}...",
            }
        else:
            return {
                "__action": "navigate",
                "url": f"/catalogue/?q={titre_film}",
                "label": f"Recherche: {titre_film}",
                "message": f"Film non trouve. Recherche dans le catalogue...",
            }

    # Genre specifique
    if genre:
        from django.utils.text import slugify
        slug = slugify(genre)
        return {
            "__action": "navigate",
            "url": f"/genres/{slug}/",
            "label": f"Genre: {genre}",
            "message": f"Redirection vers le genre {genre}...",
        }

    # Page standard
    page_info = PAGES.get(page)
    if page_info:
        return {
            "__action": "navigate",
            "url": page_info["url"],
            "label": page_info["label"],
            "message": f"Redirection vers {page_info['label']}...",
        }

    return {"error": f"Page inconnue: {page}"}


# ═══════════════════════════════════════════════
#  4. HANDLER REGISTRY
# ═══════════════════════════════════════════════

TOOL_HANDLERS = {
    "search_db": _tool_search_db,
    "check_movies_exist": _tool_check_movies_exist,
    "get_genres": _tool_get_genres,
    "get_system_recommendations": _tool_get_system_recommendations,
    "get_user_context": _tool_get_user_context,
    "add_movie_from_tmdb": _tool_add_movie_from_tmdb,
    "add_to_shelf": _tool_add_to_shelf,
    "navigate_to": _tool_navigate_to,
}

# ═══════════════════════════════════════════════
#  5. DEEPSEEK API CALL
# ═══════════════════════════════════════════════


def _send_deepseek_request(body):
    """Envoie une requete a l'API DeepSeek et retourne la response parsee."""
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        raise Exception(f"DeepSeek API HTTP {e.code}: {err_body}")
    except urllib.error.URLError as e:
        reason = str(e.reason) if hasattr(e, 'reason') else str(e)
        raise Exception(f"DeepSeek_API_ERR: {reason}")
    except Exception as e:
        raise Exception(f"DeepSeek_API_ERR: {str(e)}")


# ═══════════════════════════════════════════════
#  6. RESPONSE BUILDERS  (pour le frontend)
# ═══════════════════════════════════════════════


def _extract_movies_from_messages(messages):
    """Extrait les films trouves dans les reponses d'outils de la conversation."""
    movies = []
    seen_ids = set()
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        try:
            content = json.loads(msg["content"])
        except (json.JSONDecodeError, TypeError):
            continue

        # check_movies_exist → "found"
        for m in content.get("found", []):
            mid = m.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                movies.append({
                    "id": mid,
                    "titre": m.get("titre", "?"),
                    "annee": m.get("annee"),
                    "poster": m.get("poster", ""),
                    "url": m.get("url", f"/catalogue/{mid}/"),
                })

        # search_db / get_system_recommendations → "results"
        for m in content.get("results", []):
            mid = m.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                movies.append({
                    "id": mid,
                    "titre": m.get("titre", "?"),
                    "annee": m.get("annee"),
                    "poster": m.get("poster", ""),
                    "url": m.get("url", f"/catalogue/{mid}/"),
                })

    return movies[:10]  # max 10 films


def _is_add_action_in_messages(messages):
    """Verifie si la conversation contient une action d'ajout a la shelf."""
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        try:
            content = json.loads(msg["content"])
            if content.get("__action") == "add" and content.get("success"):
                return content
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def _is_navigate_action_in_messages(messages):
    """Verifie si la conversation contient une action de navigation."""
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        try:
            content = json.loads(msg["content"])
            if content.get("__action") == "navigate" and content.get("url"):
                return content
        except (json.JSONDecodeError, TypeError):
            pass
    return None


# ═══════════════════════════════════════════════
#  7. MAIN ENTRY POINT
# ═══════════════════════════════════════════════


def _build_conversation(chat_messages, user):
    """Construit la liste de messages pour l'API LLM a partir de l'historique."""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Contexte utilisateur (favoris recents)
    if user and user.is_authenticated:
        favs = UserMovie.objects.filter(
            user=user, is_favori=True
        ).select_related('movie')[:5]
        if favs:
            fav_titles = ", ".join(f.movie.titre for f in favs)
            msgs.append({
                "role": "system",
                "content": f"[CONTEXTE] Favoris de l'utilisateur : {fav_titles}"
            })

    # Ajouter l'historique de la conversation
    for msg in chat_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        msgs.append({"role": role, "content": content})

    return msgs


def _run_function_calling_loop(messages, user):
    """Boucle principale de Function Calling.

    Prend une liste de messages (deja prets pour l'API), execute les appels
    d'outils si necessaire, et retourne (reponse_finale, messages_avec_tool_calls).
    """
    for turn in range(MAX_TOOL_TURNS):
        body = {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "temperature": TEMPERATURE,
            "max_tokens": 300,
        }

        try:
            response = _send_deepseek_request(body)
        except Exception as e:
            return {"type": "error", "message": str(e)}, messages

        choice = response["choices"][0]
        msg = choice["message"]
        messages.append(msg)

        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if tc.get("type") != "function":
                    continue

                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                handler = TOOL_HANDLERS.get(tool_name)
                if handler:
                    try:
                        result = handler(**tool_args, user=user)
                    except Exception as e:
                        result = {"error": f"Erreur dans {tool_name}: {str(e)}"}
                else:
                    result = {"error": f"Outil inconnu: {tool_name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })
        else:
            # Reponse finale du LLM
            return msg, messages

    # Fallback
    return {
        "type": "error",
        "message": "Je n'ai pas pu traiter votre demande completement. Veuillez reformuler."
    }, messages


# ── Patterns verbaux a supprimer du texte LLM ──
VERBOSE_PATTERNS = [
    r"Voici\s+(donc\s+)?(quelques\s+)?(les\s+)?(recommandations|suggestions|films|resultats|titres|propositions)",
    r"J['eai]+\s+(trouv[eé]|s[eé]lectionn[eé]|pr[ée]par[ée]|vous\s+propose|te\s+propose)",
    r"(D'apr[eè]s|Selon|Sur la base de|En fonction de|Bas[eé](es?)?\s+sur)\s+(tes|vos|ta|ton|mes|les)\s*(favoris|pr[ée]f[ée]rences|go[ûu]ts|choix|films)",
    r"Et\s+voil[àa]\s*!?\s*$",
    r"Voil[àa]\s+!?\s*$",
    r"^\s*Bien s[ûu]r\s*[!.]?\s*",
    r"^\s*Avec plaisir\s*[!.]?\s*",
    r"^\s*Je\s+(peux|vais)\s+(te\s+)?(proposer|recommander|sugg[ée]rer|chercher|trouver)",
    r"N'h[eé]site\s*(pas\s*)?[àa]\s*(me\s+)?(demander|solliciter|poser)",
    r"^\s*Merci\s+(d['e]avoir|pour|de)\s+(fait|votre|ta)",
    r"^\s*(Bonjour|Bonsoir|Salut)\s*[!.]?\s*(.*?)\s*$",
]

def _strip_verbose(text):
    """Supprime les phrases d'introduction/conclusion verboses du texte LLM."""
    import re
    cleaned = text.strip()
    for pattern in VERBOSE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    # Nettoyer les espaces multiples et la ponctuation en trop
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s*([.!?])\s*", r"\1 ", cleaned)
    cleaned = re.sub(r"\s*:\s*", r": ", cleaned)
    return cleaned.strip()


def _build_response(msg, messages):
    """Construit la reponse structuree pour le frontend a partir du message final du LLM."""
    content = _strip_verbose(msg.get("content", "").strip())
    if not content:
        content = ""

    movies = _extract_movies_from_messages(messages)
    add_action = _is_add_action_in_messages(messages)
    navigate_action = _is_navigate_action_in_messages(messages)

    if add_action:
        return {
            "type": "add",
            "success": True,
            "id": add_action.get("id"),
            "titre": add_action["titre"],
            "annee": add_action.get("annee"),
            "poster": add_action.get("poster_url", ""),
            "url": add_action["url"],
            "message": add_action["message"],
            "statut": add_action["statut"],
            "is_favori": add_action.get("is_favori", False),
            "llm_response": content,
        }

    if navigate_action:
        return {
            "type": "navigate",
            "redirect": navigate_action["url"],
            "label": navigate_action.get("label", ""),
            "message": content or navigate_action.get("message", ""),
        }

    return {
        "type": "recommendation",
        "message": content,
        "movies": movies,
    }


# ═══════════════════════════════════════════════
#  8. INTENT ROUTER  (bypass LLM pour cas simples)
# ═══════════════════════════════════════════════

import re as _re

# Patterns de recommandation SIMPLE (sans mot-cle specifique)
# Ne match que les demandes generiques : "propose moi un film"
# Les demandes specifiques comme "propose moi un film marvel" ne matchent PAS
# et passent par le LLM pour faire une recherche dans la base
# Seuls les motifs GENERIQUES passent par TF-IDF direct.
# Si l'utilisateur ajoute un mot-cle (marvel, action, comedie...),
# le $ anchor fait echouer le match → passe au LLM.
_RECOMMEND_PATTERNS = [
    # "propose moi un film" / "propose-moi un truc" / "propose moi des films"
    r"^propose[\s-]moi\s+(?:un|des?|quelques?)\s*(?:film|truc|suggestion|trucs?)\s*$",
    r"^recommande[\s-]moi\s+(?:un|des?|quelques?)\s*(?:film|truc|suggestion|trucs?)\s*$",
    r"^sugg[eè]re[\s-]moi\s+(?:un|des?|quelques?)\s*(?:film|truc|trucs?)\s*$",
    # "propose" / "recommande" seuls
    r"^propose\s*$",
    r"^recommande\s*$",
    r"^sugg[eè]re\s*$",
    # "propose moi" / "recommande moi" seuls
    r"^propose[\s-]moi\s*$",
    r"^recommande[\s-]moi\s*$",
    r"^sugg[eè]re[\s-]moi\s*$",
    # "quoi regarder" / "quoi voir"
    r"quoi\s+(regarder|voir|mater)\s*$",
    # "tu me conseilles quoi" / "tu recommandes quoi"
    r"^(?:tu\s+(?:me\s+)?)?(?:conseilles?|recommandes?|proposes?)\s*(?:quoi|quelquechose|quelque chose)\s*$",
    # "suggestion film"
    r"^suggestion\s*(?:de\s*)?(?:film|s[eé]ance)?\s*$",
    # "donne moi des films"
    r"donne[\s-]moi?\s+des?\s*(?:films?|recommandations?|suggestions?)\s*$",
    # "recommandation"
    r"^recommandation\s*$",
    # "je veux voir un film"
    r"^je\s+(?:veux|voudrais)\s+(?:voir|regarder)\s+un\s+film\s*$",
    # "quel film me conseilles-tu"
    r"^quel\s+film\s+(?:me\s+)?(?:conseilles?[\s-]tu|recommanderais[\s-]tu|proposes?[\s-]tu)\s*$",
]

_ADD_PATTERNS = [
    r"(?:ajoute|ajouter|mets|mettre)\s*(?:dans?\s*(?:ma\s*)?(?:shelf|biblioth[eè]que|liste|collection))?\s*[:\s]*['\u201c\u201d\u2018\u2019]?(.+?)['\u201c\u201d\u2018\u2019]?\s*(?:\d+\s*/\s*10)?\s*$",
    r"(?:j'ai\s+vu|je\s+vient?\s*de\s+voir|je\s+viens?\s*de\s*regarder)\s+['\u201c\u201d\u2018\u2019]?(.+?)['\u201c\u201d\u2018\u2019]?\s*(?:[:]\s*(\d+)\s*/\s*10\s*)?\s*$",
]


def _detect_intent(query):
    """Detecte l'intention simple : 'recommend', 'add', ou None."""
    q = query.strip().lower()
    
    for pat in _RECOMMEND_PATTERNS:
        if _re.search(pat, q):
            return "recommend", None
    
    for pat in _ADD_PATTERNS:
        m = _re.search(pat, q)
        if m:
            titre = m.group(1).strip().strip('"\u201c\u201d\u2018\u2019')
            if titre and len(titre) > 1:
                return "add", titre
    
    return None, None


def _fast_recommend(user, limit=4):
    """Recommandation TF-IDF directe, sans LLM."""
    if not user or not user.is_authenticated:
        return {
            "type": "recommendation",
            "message": "Connecte-toi pour des recommandations personnalisees.",
            "movies": [],
            "assistant_message": {"role": "assistant", "content": ""},
        }
    
    try:
        from .recommender import get_recommendations_for_user
        recs = get_recommendations_for_user(user, top_n=limit)
        movies = []
        for m, s in recs:
            movies.append({
                "id": m.pk,
                "titre": m.titre,
                "annee": m.annee_sortie,
                "poster": m.poster_url or "",
                "url": m.get_absolute_url(),
            })
        return {
            "type": "recommendation",
            "message": "",
            "movies": movies,
            "assistant_message": {"role": "assistant", "content": ""},
        }
    except Exception as e:
        return {
            "type": "recommendation",
            "message": f"Erreur: {str(e)}",
            "movies": [],
            "assistant_message": {"role": "assistant", "content": ""},
        }


def _fast_add(titre, user):
    """Ajout direct d'un film a la shelf, sans LLM."""
    if not user or not user.is_authenticated:
        return {
            "type": "error",
            "message": "Connecte-toi pour ajouter un film a ta shelf.",
        }
    
    from django.db.models import Q
    
    # Chercher le film
    movie = Movie.objects.filter(Q(titre__iexact=titre) | Q(titre__icontains=titre)).first()
    
    if not movie:
        # Essayer TMDB
        result = _tool_add_movie_from_tmdb(titre, user=user)
        if "error" in result:
            return {
                "type": "error",
                "message": f"Film '{titre}' introuvable.",
            }
        movie = Movie.objects.get(pk=result["id"])
    
    # Ajouter a la shelf
    entry, created = UserMovie.objects.get_or_create(
        user=user, movie=movie,
        defaults={"statut": "a_voir", "is_favori": False},
    )
    if not created:
        entry.statut = "a_voir"
        entry.save()
    
    return {
        "type": "add",
        "success": True,
        "id": movie.pk,
        "titre": movie.titre,
        "annee": movie.annee_sortie,
        "poster": movie.poster_url or "",
        "url": movie.get_absolute_url(),
        "message": "✅ Ajouté !",
        "statut": "a_voir",
        "is_favori": False,
        "assistant_message": {"role": "assistant", "content": ""},
    }


def route_request(chat_messages, user=None):
    """Routeur principal : bypass LLM pour cas simples, sinon LLM.
    
    Args:
        chat_messages: liste [{"role": "user"|"assistant", "content": "..."}]
        user: utilisateur Django (optionnel)
    
    Returns:
        dict reponse structuree pour le frontend.
    """
    # Extraire le dernier message utilisateur
    last_user_msg = ""
    for msg in reversed(chat_messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "").strip()
            break
    
    if not last_user_msg:
        return process_chat(chat_messages, user)
    
    # Detection d'intention
    intent, extra = _detect_intent(last_user_msg)
    
    if intent == "recommend":
        return _fast_recommend(user)
    elif intent == "add":
        return _fast_add(extra, user)
    
    # Cas complexe → LLM
    try:
        return process_chat(chat_messages, user)
    except Exception as e:
        err_msg = str(e)
        # DeepSeek injoignable → fallback propre
        if "DeepSeek_API_ERR" in err_msg:
            # Fallback TF-IDF si l'utilisateur voulait des recommandations
            if any(w in last_user_msg for w in ["film", "recommande", "propose", "regarder", "voir"]):
                fallback = _fast_recommend(user)
                fallback["message"] = "🎬 Assistant IA indisponible. Voici des recommandations basees sur tes favoris :"
                return fallback
            return {
                "type": "error",
                "message": "❌ L'assistant IA est momentanement indisponible. Reessaye plus tard.",
            }
        return {
            "type": "error",
            "message": "❌ Une erreur est survenue. Reessaye ou pose une question plus simple.",
        }


def process_query(user_query, user=None):
    """Point d'entree mono-requete (compatible avec l'ancien format)."""
    # Tenter le bypass LLM d'abord
    intent, extra = _detect_intent(user_query)
    if intent == "recommend":
        return _fast_recommend(user)
    elif intent == "add":
        return _fast_add(extra, user)
    
    # Sinon LLM
    msgs = _build_conversation([], user)
    msgs.append({"role": "user", "content": user_query})
    final_msg, full_msgs = _run_function_calling_loop(msgs, user)

    if isinstance(final_msg, dict) and final_msg.get("type") == "error":
        return final_msg

    return _build_response(final_msg, full_msgs)


def process_chat(chat_messages, user=None):
    """Point d'entree pour le chat avec historique.

    Args:
        chat_messages: liste de dicts [{"role": "user"|"assistant", "content": "..."}]
        user: utilisateur Django (optionnel)

    Returns:
        dict avec la reponse + le message assistant a ajouter a l'historique
    """
    # Nettoyer l'historique : on ne garde que les messages user/assistant
    # (le system prompt et les tool_calls sont gerees en interne)
    cleaned = []
    for msg in chat_messages:
        role = msg.get("role", "")
        if role in ("user", "assistant"):
            cleaned.append({"role": role, "content": msg.get("content", "")})

    msgs = _build_conversation(cleaned, user)
    final_msg, full_msgs = _run_function_calling_loop(msgs, user)

    if isinstance(final_msg, dict) and final_msg.get("type") == "error":
        return final_msg

    response = _build_response(final_msg, full_msgs)

    # Ajouter le message assistant dans la reponse pour que le frontend le stocke
    response["assistant_message"] = {
        "role": "assistant",
        "content": final_msg.get("content", "").strip() or response.get("message", ""),
    }

    return response

    # ── Function Calling Loop ──
    for turn in range(MAX_TOOL_TURNS):
        body = {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "temperature": TEMPERATURE,
            "max_tokens": 1500,
        }

        try:
            response = _send_deepseek_request(body)
        except Exception as e:
            return {"type": "error", "message": str(e)}

        choice = response["choices"][0]
        msg = choice["message"]
        messages.append(msg)

        # Le LLM appelle-t-il des outils ?
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if tc.get("type") != "function":
                    continue

                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                handler = TOOL_HANDLERS.get(tool_name)
                if handler:
                    try:
                        result = handler(**tool_args, user=user)
                    except Exception as e:
                        result = {"error": f"Erreur dans {tool_name}: {str(e)}"}
                else:
                    result = {"error": f"Outil inconnu: {tool_name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })
        else:
            # Plus d'appels d'outils → reponse finale du LLM
            content = msg.get("content", "").strip()
            if not content:
                content = "Voici les resultats !"

            movies = _extract_movies_from_messages(messages)
            add_action = _is_add_action_in_messages(messages)
            navigate_action = _is_navigate_action_in_messages(messages)

            if add_action:
                return {
                    "type": "add",
                    "success": True,
                    "titre": add_action["titre"],
                    "url": add_action["url"],
                    "message": add_action["message"],
                    "statut": add_action["statut"],
                    "is_favori": add_action.get("is_favori", False),
                    "llm_response": content,
                }

            if navigate_action:
                return {
                    "type": "navigate",
                    "redirect": navigate_action["url"],
                    "label": navigate_action.get("label", ""),
                    "message": content or navigate_action.get("message", ""),
                }

            return {
                "type": "recommendation",
                "message": content,
                "movies": movies,
            }

    # Fallback apres MAX_TOOL_TURNS sans reponse finale
    return {
        "type": "error",
        "message": "Je n'ai pas pu traiter votre demande completement. Veuillez reformuler.",
    }
