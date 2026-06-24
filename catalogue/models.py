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
    """Fiche film/série"""
    STATUS_CHOICES = [
        ('a_voir', 'À voir'),
        ('vu', 'Vu'),
        ('favori', 'Favori'),
    ]

    titre = models.CharField(max_length=255)
    realisateur = models.CharField(max_length=255, blank=True)
    resume = models.TextField(blank=True)
    annee_sortie = models.IntegerField(null=True, blank=True)
    duree = models.IntegerField(null=True, blank=True, help_text="Durée en minutes")
    statut = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_voir')
    poster_url = models.URLField(max_length=500, blank=True)
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
