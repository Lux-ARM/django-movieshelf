import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from catalogue.models import Movie, UserMovie


class Command(BaseCommand):
    help = 'Cree 2 utilisateurs de test avec 20 films chacun (favoris + notes)'

    def handle(self, *args, **options):
        movies = list(Movie.objects.all())
        if len(movies) < 40:
            self.stdout.write(self.style.ERROR('Pas assez de films en base.'))
            return

        configs = [
            {
                'username': 'cinephile_jo',
                'email': 'jo@test.com',
                'password': 'TestPass123!',
                'favoris': 8,    # 8 favoris
                'notes': 12,     # 12 films notes 6-10
            },
            {
                'username': 'movie_fan_sam',
                'email': 'sam@test.com',
                'password': 'TestPass123!',
                'favoris': 5,
                'notes': 15,
            },
        ]

        used_movies = set()

        for cfg in configs:
            user, created = User.objects.get_or_create(
                username=cfg['username'],
                defaults={'email': cfg['email']},
            )
            if created:
                user.set_password(cfg['password'])
                user.save()
                self.stdout.write(f'  👤 {cfg["username"]} cree')
            else:
                self.stdout.write(f'  👤 {cfg["username"]} existant')

            # Supprimer les anciennes entrees shelf pour repartir a zero
            UserMovie.objects.filter(user=user).delete()

            # Selectionner des films aleatoires non encore utilises par l'autre user
            available = [m for m in movies if m.id not in used_movies]
            random.shuffle(available)
            picks = available[:cfg['favoris'] + cfg['notes']]

            fav_count = 0
            note_count = 0

            for i, movie in enumerate(picks):
                if i < cfg['favoris']:
                    statut = 'vu'
                    is_favori = True
                    note = random.randint(7, 10)
                    fav_count += 1
                else:
                    statut = 'vu'
                    is_favori = False
                    note = random.randint(6, 10)
                    note_count += 1

                UserMovie.objects.create(
                    user=user,
                    movie=movie,
                    statut=statut,
                    is_favori=is_favori,
                    note=note,
                )
                used_movies.add(movie.id)

            self.stdout.write(
                f'    ❤️ {fav_count} favoris | ⭐ {note_count} notes (6-10) | '
                f'Total: {fav_count + note_count} films'
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Utilisateurs de test prets. Connecte-toi avec :\n'
            '  cinephile_jo / TestPass123!\n'
            '  movie_fan_sam / TestPass123!'
        ))
