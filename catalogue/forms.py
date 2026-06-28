from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Movie, Comment


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['titre', 'realisateur', 'resume', 'annee_sortie',
                  'duree', 'poster_url', 'poster', 'genres']
        widgets = {
            'resume': forms.Textarea(attrs={'rows': 5}),
            'annee_sortie': forms.NumberInput(attrs={'min': 1888, 'max': 2030}),
            'duree': forms.NumberInput(attrs={'min': 1}),
        }

    def clean_titre(self):
        titre = self.cleaned_data.get('titre')
        if titre:
            # Vérifier si un film avec le même titre existe déjà
            existing = Movie.objects.filter(titre__iexact=titre)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                movie = existing.first()
                url = reverse('movie-detail', kwargs={'pk': movie.pk})
                raise forms.ValidationError(
                    mark_safe(
                        f'Un film nommé « <strong>{movie.titre}</strong> » ({movie.annee_sortie}) '
                        f'existe déjà dans le catalogue. '
                        f'<a href="{url}">Voir la fiche →</a>'
                    )
                )
        return titre


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['texte']
        widgets = {
            'texte': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Partagez votre avis sur ce film...',
            }),
        }
