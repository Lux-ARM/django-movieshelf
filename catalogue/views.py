from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from .models import Movie, Genre
from .forms import MovieForm


class AccueilView(ListView):
    """Page d'accueil avec les derniers films ajoutes"""
    model = Movie
    template_name = 'catalogue/accueil.html'
    context_object_name = 'movies'

    def get_queryset(self):
        return Movie.objects.all().order_by('-date_creation')[:12]


class CatalogueView(ListView):
    """Liste de tous les films avec pagination"""
    model = Movie
    template_name = 'catalogue/catalogue.html'
    context_object_name = 'movies'
    paginate_by = 12


class MovieDetailView(DetailView):
    """Fiche detaillee d'un film"""
    model = Movie
    template_name = 'catalogue/detail.html'
    context_object_name = 'movie'


class MovieCreateView(LoginRequiredMixin, CreateView):
    """Ajout d'un nouveau film"""
    model = Movie
    form_class = MovieForm
    template_name = 'catalogue/creation.html'

    def form_valid(self, form):
        form.instance.auteur = self.request.user
        messages.success(self.request, 'Film ajouté avec succès !')
        return super().form_valid(form)


class MovieUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Modification d'un film (auteur seulement)"""
    model = Movie
    form_class = MovieForm
    template_name = 'catalogue/modification.html'

    def test_func(self):
        movie = self.get_object()
        return self.request.user == movie.auteur

    def form_valid(self, form):
        messages.success(self.request, 'Film modifié avec succès !')
        return super().form_valid(form)


class MovieDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Suppression d'un film (auteur seulement)"""
    model = Movie
    template_name = 'catalogue/suppression_confirm.html'
    success_url = reverse_lazy('catalogue')

    def test_func(self):
        movie = self.get_object()
        return self.request.user == movie.auteur

    def form_valid(self, form):
        messages.success(self.request, 'Film supprimé.')
        return super().form_valid(form)


class GenreListView(ListView):
    """Liste de tous les genres"""
    model = Genre
    template_name = 'catalogue/genres.html'
    context_object_name = 'genres'


class GenreDetailView(ListView):
    """Films d'un genre specifique"""
    model = Movie
    template_name = 'catalogue/genre_detail.html'
    context_object_name = 'movies'

    def get_queryset(self):
        self.genre = get_object_or_404(Genre, slug=self.kwargs['slug'])
        return self.genre.movies.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genre'] = self.genre
        return context
