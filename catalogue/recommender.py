import os
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

_tfidf_cache = None


def _load_tfidf():
    """Charge la matrice TF-IDF en memoire (singleton)."""
    global _tfidf_cache
    if _tfidf_cache is None:
        path = os.path.join(os.path.dirname(__file__), 'tfidf_data.pkl')
        if not os.path.exists(path):
            raise FileNotFoundError(
                'Matrice TF-IDF introuvable. Lancez : python manage.py build_tfidf'
            )
        with open(path, 'rb') as f:
            _tfidf_cache = pickle.load(f)
    return _tfidf_cache


def get_similar_movies(movie_id, top_n=5):
    """Retourne [(movie_id, score), ...] des films les plus similaires."""
    data = _load_tfidf()
    ids = data['ids']
    matrix = data['matrix']

    try:
        idx = ids.index(movie_id)
    except ValueError:
        return []

    movie_vec = matrix[idx]
    similarities = cosine_similarity(movie_vec, matrix).flatten()
    similar_indices = similarities.argsort()[::-1]
    # Ignorer le film lui-meme (idx) et prendre les top_n
    similar_indices = [i for i in similar_indices if i != idx][:top_n]

    return [(ids[i], float(similarities[i])) for i in similar_indices]


def get_recommendations_for_user(user, top_n=4):
    """
    Recommandations personnalisees basees sur les favoris et notes >= 6.
    Retourne [(movie, score_cumulatif), ...].
    """
    from .models import Movie, UserMovie

    # Films favoris ou bien notes (note >= 6)
    favorites = UserMovie.objects.filter(
        user=user,
        is_favori=True,
        movie__resume__isnull=False,
    ).exclude(movie__resume='').select_related('movie')

    high_rated = UserMovie.objects.filter(
        user=user,
        note__gte=6,
        movie__resume__isnull=False,
    ).exclude(movie__resume='').select_related('movie')

    source_ids = set()
    source_ids.update(favorites.values_list('movie_id', flat=True))
    source_ids.update(high_rated.values_list('movie_id', flat=True))

    if not source_ids:
        return []

    # Pour chaque film source, recuperer les similaires et cumuler les scores
    scores = {}
    for movie_id in source_ids:
        for similar_id, score in get_similar_movies(movie_id, top_n=top_n * 2):
            if similar_id not in source_ids:  # Ne pas recommander un favori existant
                scores[similar_id] = scores.get(similar_id, 0) + score

    # Trier par score cumule decroissant
    sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    result = []
    for movie_id, score in sorted_ids:
        try:
            movie = Movie.objects.get(pk=movie_id)
            result.append((movie, round(score * 100)))  # Score en pourcentage
        except Movie.DoesNotExist:
            pass

    return result
