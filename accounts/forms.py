from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Adresse email")
    security_question = forms.ChoiceField(
        choices=UserProfile.SECURITY_QUESTIONS,
        label="Question secrete",
        help_text="Choisissez une question pour recuperer votre mot de passe."
    )
    security_answer = forms.CharField(
        max_length=128,
        label="Reponse secrete",
        help_text="Cette reponse vous servira si vous oubliez votre mot de passe.",
        widget=forms.TextInput(attrs={'placeholder': 'Votre reponse...'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class PasswordResetUsernameForm(forms.Form):
    """Etape 1: Saisir le username."""
    username = forms.CharField(
        max_length=150,
        label="Nom d utilisateur",
        widget=forms.TextInput(attrs={'placeholder': 'Votre nom d utilisateur...'})
    )


class PasswordResetQuestionForm(forms.Form):
    """Etape 2: Repondre a la question secrete."""
    answer = forms.CharField(
        max_length=128,
        label="Votre reponse",
        widget=forms.TextInput(attrs={'placeholder': 'Votre reponse secrete...'})
    )


class PasswordResetChangeForm(forms.Form):
    """Etape 3: Choisir un nouveau mot de passe."""
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': 'Nouveau mot de passe...'})
    )
    new_password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirmez...'})
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password1')
        p2 = cleaned.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned
