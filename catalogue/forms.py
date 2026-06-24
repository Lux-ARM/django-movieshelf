from django import forms
from .models import Movie


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['titre', 'realisateur', 'resume', 'annee_sortie',
                  'duree', 'statut', 'poster_url', 'genres']
        widgets = {
            'resume': forms.Textarea(attrs={'rows': 5}),
            'annee_sortie': forms.NumberInput(attrs={'min': 1888, 'max': 2030}),
            'duree': forms.NumberInput(attrs={'min': 1}),
        }
