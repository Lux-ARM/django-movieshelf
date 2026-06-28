import csv
import os
from django.core.management.base import BaseCommand
from catalogue.models import Movie


class Command(BaseCommand):
    help = (
        'Synchronise les poster_url de la base Django vers le fichier poster.csv. '
        'Ajoute les titres manquants et met a jour les entrees sans poster.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='MovieDB/poster.csv',
            help='Chemin vers le fichier poster.csv (defaut: MovieDB/poster.csv)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait modifie sans ecrire le fichier',
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']

        # 1. Charger le CSV existant dans un dict {titre: poster_url}
        existing = {}  # preserve insertion order on Python 3.7+
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = row.get('title', '').strip()
                    poster = row.get('poster', '').strip()
                    if title:
                        existing[title] = poster
            self.stdout.write(f'Charge {len(existing)} entrees depuis {csv_path}')
        else:
            self.stdout.write(f'{csv_path} introuvable, un nouveau fichier sera cree')

        # 2. Parcourir les films en base qui ont un poster_url
        movies_with_poster = Movie.objects.exclude(poster_url='').only('titre', 'poster_url')

        added = 0
        updated = 0
        skipped = 0

        for movie in movies_with_poster:
            title = movie.titre.strip()
            url = movie.poster_url.strip()

            if not title or not url:
                continue

            if title in existing:
                if existing[title] == '':
                    # Le CSV a une entree vide -> on la remplit
                    existing[title] = url
                    updated += 1
                    self.stdout.write(f'  ✏️  Mise a jour : {title}')
                elif existing[title] != url:
                    # URL differente -> on ecrase avec celle de la base (TMDB plus recent)
                    existing[title] = url
                    updated += 1
                    self.stdout.write(f'  🔄  Remplace : {title}')
                else:
                    skipped += 1
            else:
                # Nouveau titre absent du CSV
                existing[title] = url
                added += 1
                self.stdout.write(f'  ➕  Ajoute  : {title}')

        self.stdout.write('')
        self.stdout.write(f'  ➕  Nouveaux : {added}')
        self.stdout.write(f'  ✏️  Mis a jour : {updated}')
        self.stdout.write(f'  ⏭️  Inchanges : {skipped}')
        self.stdout.write(f'  📊  Total CSV  : {len(existing)}')

        # 3. Ecrire le CSV
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'DRY-RUN : aucune modification ecrite. Relancez sans --dry-run pour appliquer.'
            ))
            return

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['title', 'poster'])
            for title, poster in existing.items():
                writer.writerow([title, poster])

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Fichier {csv_path} mis a jour avec {len(existing)} entrees.'
        ))
