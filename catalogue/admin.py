from django.contrib import admin
from .models import Genre, Movie


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'description')
    prepopulated_fields = {'slug': ('nom',)}
    search_fields = ('nom',)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('titre', 'realisateur', 'annee_sortie', 'statut', 'auteur', 'date_creation')
    list_filter = ('statut', 'genres', 'annee_sortie')
    search_fields = ('titre', 'realisateur', 'resume')
    date_hierarchy = 'date_creation'
    filter_horizontal = ('genres',)
