from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from .forms import CustomUserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from catalogue.models import Movie


class SignupView(CreateView):
    """Inscription d'un nouvel utilisateur"""
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, 'Compte créé ! Vous pouvez vous connecter.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, ListView):
    """Profil utilisateur avec ses films"""
    model = Movie
    template_name = 'accounts/profile.html'
    context_object_name = 'movies'

    def get_queryset(self):
        return Movie.objects.filter(auteur=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        movies = Movie.objects.filter(auteur=user)
        context['total'] = movies.count()
        context['vus'] = movies.filter(statut='vu').count()
        context['a_voir'] = movies.filter(statut='a_voir').count()
        context['favoris'] = movies.filter(statut='favori').count()
        return context
