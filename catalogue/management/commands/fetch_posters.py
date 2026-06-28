import json
import os
import time
import urllib.request
import urllib.error
from django.core.management.base import BaseCommand
from catalogue.models import Movie

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "c539211898f81342c906f0504b6bc28b")
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/w500'


class Command(BaseCommand):
    help = 'Recupere les posters TMDB pour les films sans poster_url'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limite le nombre de films a traiter (0 = tout)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.3,
            help='Delai entre chaque requete TMDB (defaut: 0.3s)',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        delay = options['delay']

        # Films avec tmdb_id mais sans poster_url
        movies = Movie.objects.filter(
            tmdb_id__isnull=False,
            poster_url='',
        )

        total = movies.count()

        if limit > 0:
            movies = movies[:limit]
            total = min(total, limit)

        if total == 0:
            self.stdout.write('Tous les films avec tmdb_id ont deja un poster_url.')
            # Verifier aussi ceux sans poster du tout
            no_poster = Movie.objects.exclude(tmdb_id__isnull=True).filter(poster_url='')
            self.stdout.write(f'  Films sans aucun poster : {no_poster.count()}')
            return

        self.stdout.write(f'Recuperation des posters pour {total} films...')
        self.stdout.write(f'  Delai entre requetes : {delay}s')
        self.stdout.write('')

        fetched = 0
        no_poster_tmdb = 0
        errors = 0

        for i, movie in enumerate(movies, 1):
            try:
                url = (
                    f'https://api.themoviedb.org/3/movie/{movie.tmdb_id}'
                    f'?api_key={TMDB_API_KEY}'
                )
                req = urllib.request.Request(url)
                response = urllib.request.urlopen(req, timeout=10)
                data = json.loads(response.read().decode('utf-8'))

                poster_path = data.get('poster_path')
                if poster_path:
                    movie.poster_url = f'{TMDB_IMAGE_BASE}{poster_path}'
                    movie.save(update_fields=['poster_url'])
                    fetched += 1
                else:
                    no_poster_tmdb += 1

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Film non trouve sur TMDB
                    errors += 1
                elif e.code == 429:
                    self.stdout.write(self.style.WARNING(
                        '  Rate limit atteint, pause de 10s...'
                    ))
                    time.sleep(10)
                    # Retry
                    try:
                        req = urllib.request.Request(url)
                        response = urllib.request.urlopen(req, timeout=10)
                        data = json.loads(response.read().decode('utf-8'))
                        poster_path = data.get('poster_path')
                        if poster_path:
                            movie.poster_url = f'{TMDB_IMAGE_BASE}{poster_path}'
                            movie.save(update_fields=['poster_url'])
                            fetched += 1
                        else:
                            no_poster_tmdb += 1
                    except Exception:
                        errors += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

            if i % 50 == 0 or i == total:
                self.stdout.write(
                    f'  [{i}/{total}] '
                    f'✅ Recuperes: {fetched} | '
                    f'❌ Pas de poster TMDB: {no_poster_tmdb} | '
                    f'⚠️ Erreurs: {errors}'
                )

            time.sleep(delay)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== RESULTAT ==='))
        self.stdout.write(f'  ✅  Posters recuperes : {fetched}')
        self.stdout.write(f'  ❌  Aucun poster sur TMDB : {no_poster_tmdb}')
        self.stdout.write(f'  ⚠️   Erreurs : {errors}')
        self.stdout.write(f'  📊  Total traites : {total}')
