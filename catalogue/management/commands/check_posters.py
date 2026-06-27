import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from catalogue.models import Movie


class Command(BaseCommand):
    help = 'Verifie les poster_url des films et nettoie les liens morts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Verifie sans modifier la base (rapport seul)',
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=10,
            help='Nombre de requetes simultanees (defaut: 10)',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=5,
            help='Timeout par requete en secondes (defaut: 5)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        workers = options['workers']
        timeout = options['timeout']

        movies = Movie.objects.exclude(poster_url='')
        total = movies.count()

        if total == 0:
            self.stdout.write('Aucun film avec poster_url a verifier.')
            return

        self.stdout.write(f'Verification de {total} poster_url...')
        self.stdout.write(f'  Mode : {"DRY-RUN (pas de modif)" if dry_run else "CORRECTION"}')
        self.stdout.write(f'  Workers : {workers}')
        self.stdout.write(f'  Timeout : {timeout}s')
        self.stdout.write('')

        alive = 0
        dead = 0
        errors = 0

        def check_one(movie):
            try:
                req = urllib.request.Request(
                    movie.poster_url,
                    headers={'User-Agent': 'MovieShelf/1.0'},
                    method='HEAD',
                )
                response = urllib.request.urlopen(req, timeout=timeout)
                if response.status == 200:
                    return ('ok', movie)
                elif response.status in (301, 302, 307, 308):
                    return ('redirect', movie)
                else:
                    return ('dead', movie)
            except urllib.error.HTTPError as e:
                return ('dead', movie)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                return ('error', movie)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(check_one, m): m for m in movies}

            for i, future in enumerate(as_completed(futures), 1):
                status, movie = future.result()

                if status == 'ok':
                    alive += 1
                elif status == 'redirect':
                    alive += 1  # On garde les redirections, le navigateur suivra
                elif status == 'dead':
                    dead += 1
                    if not dry_run:
                        movie.poster_url = ''
                        movie.save(update_fields=['poster_url'])
                else:
                    errors += 1
                    if not dry_run:
                        movie.poster_url = ''
                        movie.save(update_fields=['poster_url'])

                if i % 250 == 0 or i == total:
                    self.stdout.write(
                        f'  [{i}/{total}] '
                        f'OK: {alive} | Morts: {dead} | Erreurs: {errors}'
                    )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== RESULTAT ==='))
        self.stdout.write(f'  ✅  Liens valides : {alive}')
        self.stdout.write(f'  💀  Liens morts   : {dead}')
        self.stdout.write(f'  ⚠️   Erreurs reseau: {errors}')
        self.stdout.write(f'  📊  Total verifies : {total}')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'DRY-RUN : aucune modification en base. '
                'Relancez sans --dry-run pour nettoyer les liens morts.'
            ))
        elif dead + errors > 0:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f'{dead + errors} poster_url vides. Les films restent dans le catalogue avec le placeholder 🎞️.'
            ))
