import csv
import json
from django.core.management.base import BaseCommand
from catalogue.models import Genre, Movie, UserMovie
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Importe les films depuis les CSV Kaggle (movies.csv, credits.csv, poster.csv)'

    def add_arguments(self, parser):
        parser.add_argument('--movies', type=str, default='MovieDB/movies.csv')
        parser.add_argument('--credits', type=str, default='MovieDB/credits.csv')
        parser.add_argument('--posters', type=str, default='MovieDB/poster.csv')
        parser.add_argument('--user-id', type=int, default=1)
        parser.add_argument('--limit', type=int, default=0, help='Limite le nombre de films a importer (0 = tout)')

    def handle(self, *args, **options):
        # 1. Charger les posters dans un dict {titre: url}
        posters = {}
        self.stdout.write('Chargement des posters...')
        with open(options['posters'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posters[row['title']] = row['poster']
        self.stdout.write(f'  -> {len(posters)} posters charges')

        # 2. Charger les credits dans un dict {movie_id: {cast, crew}}
        credits = {}
        self.stdout.write('Chargement des credits (cast + crew)...')
        with open(options['credits'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    credits[int(row['movie_id'])] = {
                        'cast': json.loads(row['cast']),
                        'crew': json.loads(row['crew']),
                    }
                except json.JSONDecodeError:
                    pass
        self.stdout.write(f'  -> {len(credits)} credits charges')

        # 3. Importer les films
        user = User.objects.get(pk=options['user_id'])
        count = 0
        skipped = 0
        limit = options['limit']

        self.stdout.write('Import des films...')
        with open(options['movies'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Limite optionnelle
                if limit > 0 and count >= limit:
                    break

                # Ne pas re-importer les doublons
                tmdb_id = int(row['id'])
                if Movie.objects.filter(tmdb_id=tmdb_id).exists():
                    skipped += 1
                    continue

                # Extraire le realisateur du crew
                realisateur = ''
                if tmdb_id in credits:
                    crew = credits[tmdb_id]['crew']
                    directors = [c['name'] for c in crew if c.get('job') == 'Director']
                    realisateur = directors[0] if directors else ''

                # Parser la date
                annee = None
                if row['release_date']:
                    try:
                        annee = int(row['release_date'][:4])
                    except (ValueError, IndexError):
                        pass

                # Parser la duree
                duree = None
                if row['runtime']:
                    try:
                        duree_int = int(float(row['runtime']))
                        if duree_int > 0:
                            duree = duree_int
                    except (ValueError, TypeError):
                        pass

                # Parser le vote
                vote_average = None
                if row['vote_average']:
                    try:
                        vote_average = float(row['vote_average'])
                    except (ValueError, TypeError):
                        pass

                vote_count = None
                if row['vote_count']:
                    try:
                        vote_count = int(float(row['vote_count']))
                    except (ValueError, TypeError):
                        pass

                # Creer le film
                poster = posters.get(row['title'], '')

                movie = Movie.objects.create(
                    titre=row['title'],
                    realisateur=realisateur,
                    resume=row['overview'] if row['overview'] else '',
                    annee_sortie=annee,
                    duree=duree,
                    poster_url=poster,
                    vote_average=vote_average,
                    vote_count=vote_count,
                    tmdb_id=tmdb_id,
                    auteur=user,
                )

                # Ajouter les genres
                try:
                    genres_data = json.loads(row['genres'])
                    for g in genres_data:
                        genre, _ = Genre.objects.get_or_create(
                            nom=g['name'],
                            defaults={
                                'slug': g['name'].lower().replace(' ', '-'),
                                'description': '',
                            }
                        )
                        movie.genres.add(genre)
                except (json.JSONDecodeError, KeyError):
                    pass

                # Ajouter automatiquement a la shelf de l'utilisateur
                UserMovie.objects.get_or_create(
                    user=user,
                    movie=movie,
                    defaults={'statut': 'a_voir'}
                )

                count += 1
                if count % 100 == 0:
                    self.stdout.write(f'  {count} films importes...')

        self.stdout.write(self.style.SUCCESS(
            f'\nImport termine : {count} films importes, {skipped} doublons ignores'
        ))
