import json
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from .models import Movie, Genre, UserMovie, Comment
from .forms import MovieForm, CommentForm


class AccueilView(ListView):
    """Page d'accueil avec recommandations ou derniers films ajoutes"""
    model = Movie
    template_name = 'catalogue/accueil.html'
    context_object_name = 'movies'
    paginate_by = 5

    def get_queryset(self):
        if self.request.user.is_authenticated:
            try:
                from .recommender import get_recommendations_for_user
                self._recs = get_recommendations_for_user(self.request.user, top_n=24)
                if self._recs:
                    return [m for m, _ in self._recs]
            except (FileNotFoundError, ImportError):
                self._recs = []
        return Movie.objects.all().order_by('-date_creation')[:12]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['user_shelf_ids'] = set(
                UserMovie.objects.filter(user=self.request.user).values_list('movie_id', flat=True)
            )
            context['is_personalized'] = True
            # Scores pour l'affichage dans le template
            if hasattr(self, '_recs') and self._recs:
                score_map = {m.pk: s for m, s in self._recs}
                context['rec_scores'] = score_map
        # Derniers films ajoutes (toujours affiches en bas)
        context['latest_movies'] = Movie.objects.all().order_by('-date_creation')[:12]
        return context


class CatalogueView(ListView):
    """Liste de tous les films avec pagination et filtres"""
    model = Movie
    template_name = 'catalogue/catalogue.html'
    context_object_name = 'movies'
    paginate_by = 12

    def get_queryset(self):
        queryset = Movie.objects.all()

        # Filtre par genre
        genre_slug = self.request.GET.get('genre')
        if genre_slug:
            queryset = queryset.filter(genres__slug=genre_slug)

        # Filtre par annee (min/max)
        annee_min = self.request.GET.get('annee_min')
        annee_max = self.request.GET.get('annee_max')
        if annee_min:
            queryset = queryset.filter(annee_sortie__gte=int(annee_min))
        if annee_max:
            queryset = queryset.filter(annee_sortie__lte=int(annee_max))

        # Filtre par duree (min/max)
        duree_min = self.request.GET.get('duree_min')
        duree_max = self.request.GET.get('duree_max')
        if duree_min:
            queryset = queryset.filter(duree__gte=int(duree_min))
        if duree_max:
            queryset = queryset.filter(duree__lte=int(duree_max))

        # Recherche textuelle
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(titre__icontains=q)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = Genre.objects.all()
        if self.request.user.is_authenticated:
            context['user_shelf_ids'] = set(
                UserMovie.objects.filter(user=self.request.user).values_list('movie_id', flat=True)
            )
        return context


class MovieDetailView(DetailView):
    """Fiche detaillee d'un film"""
    model = Movie
    template_name = 'catalogue/detail.html'
    context_object_name = 'movie'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['shelf_entry'] = UserMovie.objects.filter(
                user=self.request.user, movie=self.object
            ).first()
        # Recommandations TF-IDF
        context['similar_movies'] = self._get_similar_movies()
        context['personal_recommendations'] = self._get_personal_recommendations()
        # Commentaires
        context['comments'] = self.object.comments.all()
        context['comment_form'] = CommentForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.is_authenticated:
            form = CommentForm(request.POST)
            if form.is_valid():
                Comment.objects.create(
                    movie=self.object,
                    user=request.user,
                    texte=form.cleaned_data['texte'],
                )
                messages.success(request, 'Commentaire ajouté !')
        return redirect('movie-detail', pk=self.object.pk)

    def _get_similar_movies(self):
        """Films similaires via TF-IDF (resume)."""
        if not self.object.resume:
            return []
        try:
            from .recommender import get_similar_movies
            similar = get_similar_movies(self.object.pk, top_n=5)
            result = []
            for sid, score in similar:
                try:
                    result.append((Movie.objects.get(pk=sid), int(score * 100)))
                except Movie.DoesNotExist:
                    pass
            return result
        except (FileNotFoundError, ImportError):
            return []

    def _get_personal_recommendations(self):
        """Recommandations personnalisees basees sur les favoris de l'utilisateur."""
        if not self.request.user.is_authenticated:
            return []
        try:
            from .recommender import get_recommendations_for_user
            return get_recommendations_for_user(self.request.user, top_n=4)
        except (FileNotFoundError, ImportError):
            return []


class MovieCreateView(LoginRequiredMixin, CreateView):
    """Ajout d'un nouveau film (manuel)"""
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
        if self.request.user.is_authenticated:
            context['user_shelf_ids'] = set(
                UserMovie.objects.filter(user=self.request.user).values_list('movie_id', flat=True)
            )
        return context


# ─── Shelf (nouveau) ───

class AddToShelfView(LoginRequiredMixin, View):
    """Ajoute un film du catalogue public a la shelf de l'utilisateur"""

    def post(self, request, pk):
        movie = get_object_or_404(Movie, pk=pk)
        statut = request.POST.get('statut', 'a_voir')
        note = request.POST.get('note')

        _, created = UserMovie.objects.get_or_create(
            user=request.user,
            movie=movie,
            defaults={'statut': statut, 'is_favori': False, 'note': note if note else None}
        )
        if created:
            messages.success(request, f'« {movie.titre} » ajouté à votre shelf !')
        else:
            messages.info(request, f'« {movie.titre} » est déjà dans votre shelf.')
        return redirect('movie-detail', pk=pk)


class ShelfView(LoginRequiredMixin, ListView):
    """Shelf personnelle avec filtres par statut"""
    model = UserMovie
    template_name = 'catalogue/shelf.html'
    context_object_name = 'shelf_items'
    paginate_by = 12

    def get_queryset(self):
        qs = UserMovie.objects.filter(user=self.request.user).select_related('movie')
        statut = self.request.GET.get('statut')
        favori = self.request.GET.get('favori')
        if statut:
            qs = qs.filter(statut=statut)
        if favori:
            qs = qs.filter(is_favori=True)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = UserMovie.objects.filter(user=self.request.user)
        context['count_a_voir'] = base_qs.filter(statut='a_voir').count()
        context['count_vu'] = base_qs.filter(statut='vu').count()
        context['count_favori'] = base_qs.filter(is_favori=True).count()
        context['count_total'] = base_qs.count()
        return context


def llm_endpoint(request):
    """Endpoint AJAX pour le Sparkling Button (LLM Agentic)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    query = data.get('query', '').strip()
    if not query:
        return JsonResponse({'error': 'Requete vide'}, status=400)

    from .llm_service import process_query
    result = process_query(
        query,
        user=request.user if request.user.is_authenticated else None,
    )
    return JsonResponse(result)


class UpdateShelfStatusView(LoginRequiredMixin, View):
    """Mise a jour rapide du statut / note depuis la shelf"""

    def post(self, request, pk):
        entry = get_object_or_404(UserMovie, pk=pk, user=request.user)
        entry.statut = request.POST.get('statut', entry.statut)
        entry.is_favori = request.POST.get('is_favori') == 'on'
        note = request.POST.get('note')
        entry.note = int(note) if note else None
        entry.save()
        messages.success(request, f'Statut de « {entry.movie.titre} » mis à jour.')
        return redirect('shelf')
