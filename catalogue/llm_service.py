"""Service LLM Agentic — DeepSeek V4 Flash comme interprete d'intention."""
import json
import os
import urllib.request
import urllib.error
from django.db.models import Q
from .models import Movie, UserMovie

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL = "deepseek-v4-flash"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

SYSTEM_PROMPT = """Tu es un assistant de catalogue de films. Comprends l'intention de l'utilisateur en langage naturel et retourne UNIQUEMENT un objet JSON valide.

3 actions possibles :

1. "recommend" — L'utilisateur cherche des films a decouvrir (description, ambiance, genre...)
   EXAMPLE: {"action":"recommend","keywords":["thriller","psychologique"],"genres":["Thriller"],"year_min":null,"year_max":null,"duree_min":null,"duree_max":null}

2. "add_to_shelf" — L'utilisateur exprime le souhait d'ajouter un film a sa collection. Detecte les indices dans son langage :
   - "j'ai vu", "j'ai regarde", "je viens de voir" → statut:"vu"
   - "a voir", "je veux voir", "dans ma liste" → statut:"a_voir"
   - "genial", "j'ai adore", "excellent", "chef d'oeuvre", "favori" → is_favori:true
   - "8/10", "je lui mets 7", "note de 9" → extraire la note en entier
   - Les champs non detectes restent null ou false
   EXAMPLE: {"action":"add_to_shelf","titre":"Inception","statut":"vu","note":9,"is_favori":true,"message":"Ajoute en Vu, Favori, 9/10 !"}

3. "clarify" — L'utilisateur veut ajouter un film mais il manque des infos importantes (le titre du film est ambigu, ou il n'a pas precise s'il l'a vu ou non). Pose UNE question courte et naturelle pour clarifier, dans la meme langue que l'utilisateur.
   EXAMPLE: {"action":"clarify","titre":"Inception","message":"Je l'ajoute ! Vous l'avez deja vu ou c'est a voir ?"}

REGLES :
- Sois flexible : comprends "c'etait genial", "un bon 8/10", "je kiffe", "a mater", "dans ma watchlist"...
- Si le titre du film n'est pas clair, utilise "clarify"
- Les genres sont en anglais (ex: "Science Fiction", "Comedy", "Action")
- Pour les durees : "pas trop long"/"court" → duree_max:120, "long"/"epique" → duree_min:150
- Extraire max 5 mots-cles pour "recommend"
- Le champ "message" dans add_to_shelf ou clarify est un resume convivial pour l'utilisateur

Reponds UNIQUEMENT avec l'objet json, pas de texte avant ou apres."""


def _call_deepseek(user_query, user=None):
    """Appelle DeepSeek et retourne le JSON parse."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Contexte utilisateur (favoris recents)
    if user and user.is_authenticated:
        favs = UserMovie.objects.filter(
            user=user, is_favori=True
        ).select_related('movie')[:5]
        if favs:
            fav_titles = ", ".join(f.movie.titre for f in favs)
            messages.append({
                "role": "system",
                "content": f"Films favoris de l'utilisateur (pour contexte) : {fav_titles}"
            })

    messages.append({"role": "user", "content": user_query})

    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": 300,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
    except (json.JSONDecodeError, KeyError) as e:
        return {"action": "error", "message": f"Erreur parsing reponse LLM: {e}"}
    except urllib.error.HTTPError as e:
        return {"action": "error", "message": f"Erreur API DeepSeek: {e.code}"}
    except Exception as e:
        return {"action": "error", "message": str(e)}


def _handle_recommend(params, user):
    """Recherche hybride : ORM keywords + genres."""
    keywords = params.get("keywords", [])
    genres = params.get("genres", [])
    year_min = params.get("year_min")
    year_max = params.get("year_max")
    duree_min = params.get("duree_min")
    duree_max = params.get("duree_max")

    qs = Movie.objects.all()

    # ORM : mots-cles dans titre ou resume
    if keywords:
        q_filter = Q()
        for kw in keywords:
            q_filter |= Q(titre__icontains=kw) | Q(resume__icontains=kw)
        qs = qs.filter(q_filter)

    # Genres
    if genres:
        qs = qs.filter(genres__nom__in=genres)

    # Annee
    if year_min:
        qs = qs.filter(annee_sortie__gte=int(year_min))
    if year_max:
        qs = qs.filter(annee_sortie__lte=int(year_max))

    # Duree
    if duree_min:
        qs = qs.filter(duree__gte=int(duree_min))
    if duree_max:
        qs = qs.filter(duree__lte=int(duree_max))

    movies = qs.distinct()[:5]

    return {
        "type": "recommend",
        "movies": [
            {
                "id": m.pk,
                "titre": m.titre,
                "annee": m.annee_sortie,
                "poster": m.poster_url or "",
                "url": m.get_absolute_url(),
            }
            for m in movies
        ],
    }


def _handle_add_to_shelf(params, user):
    """Ajoute un film a la shelf de l'utilisateur."""
    titre = params.get("titre", "").strip()
    statut = params.get("statut", "a_voir")
    note = params.get("note")
    is_favori = params.get("is_favori", False)

    if not titre:
        return {"type": "error", "message": "Titre du film non specifie."}

    # Chercher dans la base
    movie = Movie.objects.filter(titre__iexact=titre).first()

    if not movie:
        # Chercher via TMDB
        movie = _search_tmdb(titre, user)

    if not movie:
        return {"type": "error", "message": f"Film \"{titre}\" introuvable. Ajoutez-le manuellement."}

    # Ajouter a la shelf
    entry, created = UserMovie.objects.get_or_create(
        user=user,
        movie=movie,
        defaults={"statut": statut, "is_favori": is_favori, "note": note},
    )

    if not created:
        # Mettre a jour l'entree existante
        entry.statut = statut
        entry.is_favori = is_favori
        if note is not None:
            entry.note = note
        entry.save()

    return {
        "type": "add",
        "success": True,
        "titre": movie.titre,
        "url": movie.get_absolute_url(),
        "message": params.get("message", f"{'Vu' if statut == 'vu' else 'À voir'} {'❤️' if is_favori else ''}"),
        "statut": statut,
        "is_favori": is_favori,
        "created": created,
    }


def _search_tmdb(titre, user):
    """Cherche un film via l'API TMDB et le cree dans la base."""
    import urllib.parse
    url = (
        f"https://api.themoviedb.org/3/search/movie"
        f"?api_key={TMDB_API_KEY}&query={urllib.parse.quote(titre)}&language=fr"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("results"):
            r = data["results"][0]
            movie = Movie.objects.create(
                titre=r["title"],
                resume=r.get("overview", ""),
                annee_sortie=int(r["release_date"][:4]) if r.get("release_date") else None,
                poster_url=f"https://image.tmdb.org/t/p/w500{r['poster_path']}" if r.get("poster_path") else "",
                tmdb_id=r["id"],
                auteur=user,
            )
            return movie
    except Exception:
        pass
    return None


def process_query(user_query, user=None):
    """Point d'entree principal."""
    result = _call_deepseek(user_query, user)

    action = result.get("action", "error")

    if action == "recommend":
        return _handle_recommend(result, user)
    elif action == "add_to_shelf":
        if not user or not user.is_authenticated:
            return {"type": "error", "message": "Connectez-vous pour ajouter un film a votre shelf."}
        return _handle_add_to_shelf(result, user)
    elif action == "clarify":
        return {
            "type": "clarify",
            "message": result.get("message", "Pouvez-vous preciser ?"),
        }
    else:
        return {"type": "error", "message": result.get("message", "Action non reconnue.")}
