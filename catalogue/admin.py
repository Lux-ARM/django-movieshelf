from django.contrib import admin
from .models import Genre, Movie, UserMovie, Comment


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'description')
    prepopulated_fields = {'slug': ('nom',)}
    search_fields = ('nom',)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('titre', 'realisateur', 'annee_sortie', 'auteur', 'date_creation')
    list_filter = ('genres', 'annee_sortie')
    search_fields = ('titre', 'realisateur', 'resume')
    date_hierarchy = 'date_creation'
    filter_horizontal = ('genres',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'texte_preview', 'date_creation')
    search_fields = ('user__username', 'movie__titre', 'texte')

    @admin.display(description='Texte')
    def texte_preview(self, obj):
        return obj.texte[:80] + ('...' if len(obj.texte) > 80 else '')


@admin.register(UserMovie)
class UserMovieAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'statut', 'is_favori', 'note', 'date_ajout')
    list_filter = ('statut', 'is_favori', 'date_ajout')
    search_fields = ('user__username', 'movie__titre')
