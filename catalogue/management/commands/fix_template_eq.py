"""
Management command: fixe la syntaxe == dans les templates Django 6.

Usage:
    python manage.py fix_template_eq
    python manage.py fix_template_eq --check   (verification seule, sans ecrire)
"""
import re
from pathlib import Path
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ajoute des espaces autour de == dans les {% if %} tags des templates Django.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', action='store_true',
            help='Verifie seulement, sans modifier les fichiers',
        )

    def handle(self, **options):
        check_only = options['check']
        templates_dir = Path('catalogue/templates')
        accounts_dir = Path('accounts/templates')
        files = list(templates_dir.rglob('*.html')) + list(accounts_dir.rglob('*.html'))

        fixed_count = 0
        issue_count = 0

        for fp in files:
            content = fp.read_text(encoding='utf-8')
            # Cherche: {% if VAR==VALUE %} -> {% if VAR == VALUE %}
            new_content = re.sub(
                r'(\{%\s*if\s+\S+?)\s*==\s*(\S)',
                r'\1 == \2',
                content
            )

            if content != new_content:
                issue_count += 1
                # Affiche les lignes problematiques
                for i, line in enumerate(content.split('\n')):
                    before = line
                    after = re.sub(r'(\{%\s*if\s+\S+?)\s*==\s*(\S)', r'\1 == \2', line)
                    if before != after:
                        self.stdout.write(self.style.WARNING(
                            f'  {fp}:{i+1} -> corrige'
                        ))

                if not check_only:
                    fp.write_text(new_content, encoding='utf-8')
                    fixed_count += 1

        if issue_count == 0:
            self.stdout.write(self.style.SUCCESS('Aucun probleme == detecte. Tous les templates sont OK.'))
        elif check_only:
            self.stdout.write(self.style.WARNING(
                f'{issue_count} fichier(s) a corriger. Lancez sans --check pour corriger.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{fixed_count} fichier(s) corrige(s). Redemarrez le serveur si necessaire.'
            ))
