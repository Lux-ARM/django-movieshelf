from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Genre, Movie, UserMovie


class GenreModelTest(TestCase):
    """Tests du modele Genre"""

    def test_create_genre(self):
        genre = Genre.objects.create(nom='Action', slug='action', description='Films d\'action')
        self.assertEqual(str(genre), 'Action')
        self.assertEqual(genre.get_absolute_url(), reverse('genre-detail', kwargs={'slug': 'action'}))

    def test_genre_ordering(self):
        Genre.objects.create(nom='Zombie', slug='zombie')
        Genre.objects.create(nom='Action', slug='action')
        self.assertEqual(list(Genre.objects.all().values_list('nom', flat=True)), ['Action', 'Zombie'])


class MovieModelTest(TestCase):
    """Tests du modele Movie"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.genre = Genre.objects.create(nom='Drame', slug='drame')

    def test_create_movie(self):
        movie = Movie.objects.create(
            titre='Inception',
            realisateur='Christopher Nolan',
            annee_sortie=2010,
            duree=148,
            auteur=self.user,
        )
        movie.genres.add(self.genre)
        self.assertEqual(str(movie), 'Inception')
        self.assertEqual(movie.get_absolute_url(), reverse('movie-detail', kwargs={'pk': movie.pk}))

    def test_movie_ordering(self):
        m1 = Movie.objects.create(titre='First', auteur=self.user)
        m2 = Movie.objects.create(titre='Second', auteur=self.user)
        movies = list(Movie.objects.all())
        self.assertEqual(movies[0], m2)  # Plus recent en premier

    def test_movie_poster_url_optional(self):
        movie = Movie.objects.create(titre='No Poster', auteur=self.user)
        self.assertEqual(movie.poster_url, '')
        self.assertFalse(movie.poster)


class UserMovieModelTest(TestCase):
    """Tests du modele UserMovie"""

    def setUp(self):
        self.user = User.objects.create_user(username='shelfuser', password='testpass')
        self.movie = Movie.objects.create(titre='Test Movie', auteur=self.user)

    def test_create_usermovie(self):
        entry = UserMovie.objects.create(user=self.user, movie=self.movie, statut='a_voir')
        self.assertIn('Test Movie', str(entry))
        self.assertIn('À voir', str(entry))

    def test_default_statut(self):
        entry = UserMovie.objects.create(user=self.user, movie=self.movie)
        self.assertEqual(entry.statut, 'a_voir')

    def test_unique_together(self):
        UserMovie.objects.create(user=self.user, movie=self.movie)
        with self.assertRaises(Exception):
            UserMovie.objects.create(user=self.user, movie=self.movie)

    def test_note_optional(self):
        entry = UserMovie.objects.create(user=self.user, movie=self.movie, note=8)
        self.assertEqual(entry.note, 8)
        entry2 = UserMovie.objects.create(user=User.objects.create_user(username='other', password='pass'), movie=self.movie)
        self.assertIsNone(entry2.note)

    def test_ordering(self):
        entry1 = UserMovie.objects.create(user=self.user, movie=self.movie)
        m2 = Movie.objects.create(titre='Second', auteur=self.user)
        entry2 = UserMovie.objects.create(user=self.user, movie=m2)
        entries = list(UserMovie.objects.filter(user=self.user))
        self.assertEqual(entries[0], entry2)  # Plus recent en premier


class PublicPageTests(TestCase):
    """Tests des pages publiques"""

    def setUp(self):
        self.user = User.objects.create_user(username='publicuser', password='testpass')
        self.genre = Genre.objects.create(nom='Comedie', slug='comedie')
        self.movie = Movie.objects.create(
            titre='Public Movie', annee_sortie=2024, auteur=self.user
        )
        self.movie.genres.add(self.genre)

    def test_accueil_status(self):
        response = self.client.get(reverse('accueil'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalogue/accueil.html')

    def test_catalogue_status(self):
        response = self.client.get(reverse('catalogue'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Movie')

    def test_catalogue_search(self):
        response = self.client.get(reverse('catalogue') + '?q=Public')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Movie')

    def test_catalogue_filter_genre(self):
        response = self.client.get(reverse('catalogue') + '?genre=comedie')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Movie')

    def test_movie_detail_status(self):
        response = self.client.get(reverse('movie-detail', kwargs={'pk': self.movie.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Movie')

    def test_genre_list_status(self):
        response = self.client.get(reverse('genre-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comedie')

    def test_genre_detail_status(self):
        response = self.client.get(reverse('genre-detail', kwargs={'slug': 'comedie'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Movie')


class AuthenticatedShelfTests(TestCase):
    """Tests de la shelf (utilisateur connecte)"""

    def setUp(self):
        self.user = User.objects.create_user(username='shelftester', password='testpass')
        self.other_user = User.objects.create_user(username='other', password='testpass')
        self.movie = Movie.objects.create(titre='Shelf Movie', auteur=self.other_user)
        self.client.login(username='shelftester', password='testpass')

    def test_shelf_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('shelf'))
        self.assertEqual(response.status_code, 302)

    def test_shelf_empty(self):
        response = self.client.get(reverse('shelf'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Votre shelf est vide.')

    def test_add_to_shelf(self):
        response = self.client.post(
            reverse('add-to-shelf', kwargs={'pk': self.movie.pk}),
            {'statut': 'vu'}
        )
        self.assertRedirects(response, reverse('movie-detail', kwargs={'pk': self.movie.pk}))
        self.assertTrue(UserMovie.objects.filter(user=self.user, movie=self.movie).exists())
        entry = UserMovie.objects.get(user=self.user, movie=self.movie)
        self.assertEqual(entry.statut, 'vu')

    def test_add_to_shelf_duplicate(self):
        UserMovie.objects.create(user=self.user, movie=self.movie, statut='a_voir')
        response = self.client.post(
            reverse('add-to-shelf', kwargs={'pk': self.movie.pk}),
            {'statut': 'favori'}
        )
        self.assertEqual(response.status_code, 302)
        # Le doublon ne doit pas etre cree, le statut existant est preserve
        self.assertEqual(UserMovie.objects.filter(user=self.user, movie=self.movie).count(), 1)

    def test_shelf_shows_movie(self):
        UserMovie.objects.create(user=self.user, movie=self.movie, statut='favori')
        response = self.client.get(reverse('shelf'))
        self.assertContains(response, 'Shelf Movie')

    def test_shelf_filter_by_statut(self):
        m2 = Movie.objects.create(titre='Vu Movie', auteur=self.other_user)
        m3 = Movie.objects.create(titre='Fav Movie', auteur=self.other_user)
        UserMovie.objects.create(user=self.user, movie=self.movie, statut='a_voir')
        UserMovie.objects.create(user=self.user, movie=m2, statut='vu')
        UserMovie.objects.create(user=self.user, movie=m3, statut='favori')

        response = self.client.get(reverse('shelf') + '?statut=vu')
        self.assertContains(response, 'Vu Movie')
        self.assertNotContains(response, 'Fav Movie')

    def test_update_shelf_status(self):
        entry = UserMovie.objects.create(user=self.user, movie=self.movie, statut='a_voir')
        response = self.client.post(
            reverse('update-shelf-status', kwargs={'pk': entry.pk}),
            {'statut': 'favori', 'note': '9'}
        )
        self.assertRedirects(response, reverse('shelf'))
        entry.refresh_from_db()
        self.assertEqual(entry.statut, 'favori')
        self.assertEqual(entry.note, 9)

    def test_update_shelf_status_other_user_forbidden(self):
        entry = UserMovie.objects.create(user=self.other_user, movie=self.movie, statut='a_voir')
        response = self.client.post(
            reverse('update-shelf-status', kwargs={'pk': entry.pk}),
            {'statut': 'favori'}
        )
        self.assertEqual(response.status_code, 404)


class MovieCRUDTests(TestCase):
    """Tests du parcours CRUD manuel (creation, modification, suppression)"""

    def setUp(self):
        self.user = User.objects.create_user(username='cruduser', password='testpass')
        self.genre = Genre.objects.create(nom='Sci-Fi', slug='sci-fi')
        self.client.login(username='cruduser', password='testpass')

    def test_create_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('movie-create'))
        self.assertEqual(response.status_code, 302)

    def test_create_movie_get(self):
        response = self.client.get(reverse('movie-create'))
        self.assertEqual(response.status_code, 200)

    def test_create_movie_post(self):
        response = self.client.post(reverse('movie-create'), {
            'titre': 'New Movie',
            'realisateur': 'Director',
            'resume': 'A great movie',
            'annee_sortie': 2025,
            'duree': 120,
            'poster_url': 'https://example.com/poster.jpg',
            'genres': [self.genre.pk],
        })
        self.assertEqual(response.status_code, 302)
        movie = Movie.objects.get(titre='New Movie')
        self.assertEqual(movie.auteur, self.user)
        self.assertRedirects(response, movie.get_absolute_url())

    def test_update_movie_author_only(self):
        movie = Movie.objects.create(titre='My Movie', auteur=self.user)
        # Un autre utilisateur ne peut pas modifier
        self.client.logout()
        other = User.objects.create_user(username='hacker', password='testpass')
        self.client.login(username='hacker', password='testpass')
        response = self.client.get(reverse('movie-update', kwargs={'pk': movie.pk}))
        self.assertEqual(response.status_code, 403)

    def test_update_movie_post(self):
        movie = Movie.objects.create(titre='Old Title', auteur=self.user)
        response = self.client.post(reverse('movie-update', kwargs={'pk': movie.pk}), {
            'titre': 'Updated Title',
            'realisateur': 'New Director',
            'resume': 'Updated resume',
            'annee_sortie': 2026,
            'duree': 90,
            'poster_url': '',
            'genres': [self.genre.pk],
        })
        self.assertRedirects(response, movie.get_absolute_url())
        movie.refresh_from_db()
        self.assertEqual(movie.titre, 'Updated Title')

    def test_delete_movie_author_only(self):
        movie = Movie.objects.create(titre='Delete Me', auteur=self.user)
        self.client.logout()
        other = User.objects.create_user(username='destroyer', password='testpass')
        self.client.login(username='destroyer', password='testpass')
        response = self.client.post(reverse('movie-delete', kwargs={'pk': movie.pk}))
        self.assertEqual(response.status_code, 403)

    def test_delete_movie_post(self):
        movie = Movie.objects.create(titre='Delete Me', auteur=self.user)
        response = self.client.post(reverse('movie-delete', kwargs={'pk': movie.pk}))
        self.assertRedirects(response, reverse('catalogue'))
        self.assertFalse(Movie.objects.filter(pk=movie.pk).exists())
