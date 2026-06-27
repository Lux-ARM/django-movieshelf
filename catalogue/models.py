from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Genre(models.Model):
    """Genre cinématographique (Action, Comédie, etc.)"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('genre-detail', kwargs={'slug': self.slug})


class Movie(models.Model):
    """Fiche film/série — catalogue public"""

    titre = models.CharField(max_length=255)
    realisateur = models.CharField(max_length=255, blank=True)
    resume = models.TextField(blank=True)
    annee_sortie = models.IntegerField(null=True, blank=True)
    duree = models.IntegerField(null=True, blank=True, help_text="Durée en minutes")
    poster_url = models.URLField(max_length=500, blank=True, help_text="Lien HTTP vers une affiche")
    poster = models.ImageField(upload_to='posters/', blank=True, help_text="Upload local d'une affiche")
    genres = models.ManyToManyField(Genre, related_name='movies')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movies')

    # Champs supplémentaires pour recommandations futures
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.IntegerField(null=True, blank=True)
    tmdb_id = models.IntegerField(null=True, blank=True, unique=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse('movie-detail', kwargs={'pk': self.pk})


class UserMovie(models.Model):
    """Lien entre un utilisateur et un film dans sa shelf personnelle"""

    STATUS_CHOICES = [
        ('a_voir', 'À voir'),
        ('vu', 'Vu'),
        ('favori', 'Favori'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shelf')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shelf_entries')
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_voir')
    note = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Note personnelle sur 10")
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')
        ordering = ['-date_ajout']

    def __str__(self):
        return f"{self.user.username} — {self.movie.titre} ({self.get_statut_display()})"
