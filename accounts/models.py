from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password


class UserProfile(models.Model):
    """Profil etendu avec question secrete pour reset password."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    SECURITY_QUESTIONS = [
        ('pet', 'Quel est le nom de votre premier animal de compagnie ?'),
        ('city', 'Quel est le nom de votre ville natale ?'),
        ('mother', 'Quel est le nom de jeune fille de votre mere ?'),
        ('movie', 'Quel est votre film prefere ?'),
        ('friend', 'Quel est le nom de votre meilleur ami d enfance ?'),
        ('school', 'Quelle est votre matiere preferee a l ecole ?'),
    ]

    security_question = models.CharField(
        max_length=20,
        choices=SECURITY_QUESTIONS,
    )
    security_answer = models.CharField(max_length=128)

    def set_security_answer(self, raw_answer):
        """Hash la reponse secrete."""
        self.security_answer = make_password(raw_answer.strip().lower())

    def check_security_answer(self, raw_answer):
        """Verifie la reponse secrete."""
        return check_password(raw_answer.strip().lower(), self.security_answer)

    def __str__(self):
        return f"Profil de {self.user.username}"
