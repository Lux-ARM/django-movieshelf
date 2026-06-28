from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.db.models import Avg, Count
from .forms import CustomUserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from catalogue.models import Movie, UserMovie, Genre


class SignupView(CreateView):
    """Inscription d'un nouvel utilisateur"""
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, 'Compte créé ! Vous pouvez vous connecter.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, ListView):
    """Profil utilisateur avec les stats de sa shelf"""
    model = Movie
    template_name = 'accounts/profile.html'
    context_object_name = 'movies'

    def get_queryset(self):
        return UserMovie.objects.filter(user=self.request.user).select_related('movie')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        shelf = UserMovie.objects.filter(user=user)
        context['total'] = shelf.count()
        context['vus'] = shelf.filter(statut='vu').count()
        context['a_voir'] = shelf.filter(statut='a_voir').count()
        context['favoris'] = shelf.filter(is_favori=True).count()

        # Note moyenne
        avg = shelf.filter(note__isnull=False).aggregate(avg=Avg('note'))
        context['note_moyenne'] = round(avg['avg'], 1) if avg['avg'] else None

        # Genres dominants (top 5)
        context['top_genres'] = Genre.objects.filter(
            movies__shelf_entries__user=user
        ).annotate(total=Count('movies')).order_by('-total')[:5]

        return context
