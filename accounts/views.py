from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, View
from django.db.models import Avg, Count, Q
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import (
    CustomUserCreationForm,
    PasswordResetUsernameForm,
    PasswordResetQuestionForm,
    PasswordResetChangeForm,
)
from .models import UserProfile
from catalogue.models import Movie, UserMovie, Genre


class SignupView(CreateView):
    """Inscription avec question secrete."""
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Creer le profil avec la question secrete
        UserProfile.objects.create(
            user=self.object,
            security_question=form.cleaned_data['security_question'],
        )
        self.object.profile.set_security_answer(
            form.cleaned_data['security_answer']
        )
        self.object.profile.save()
        messages.success(self.request, 'Compte cree ! Vous pouvez vous connecter.')
        return response


class ProfileView(LoginRequiredMixin, ListView):
    """Profil utilisateur avec les stats de sa shelf."""
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

        avg = shelf.filter(note__isnull=False).aggregate(avg=Avg('note'))
        context['note_moyenne'] = round(avg['avg'], 1) if avg['avg'] else None

        context['top_genres'] = Genre.objects.filter(
            movies__shelf_entries__user=user
        ).annotate(
            count=Count('movies', filter=Q(movies__shelf_entries__user=user))
        ).order_by('-count')[:5]

        return context


# ─── Password Reset via Question Secrete ───

class PasswordResetUsernameView(View):
    """Etape 1: Saisir le username."""
    template_name = 'accounts/password_reset.html'

    def get(self, request):
        form = PasswordResetUsernameForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PasswordResetUsernameForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            try:
                user = User.objects.get(username__iexact=username)
                request.session['reset_user_id'] = user.pk
                return redirect('password-reset-question')
            except User.DoesNotExist:
                form.add_error('username', "Aucun utilisateur avec ce nom.")
        return render(request, self.template_name, {'form': form})


class PasswordResetQuestionView(View):
    """Etape 2: Afficher la question et verifier la reponse."""
    template_name = 'accounts/password_reset_question.html'

    def get(self, request):
        user = self._get_user(request)
        if not user:
            messages.error(request, "Session expiree. Veuillez recommencer.")
            return redirect('password-reset')
        try:
            question = user.profile.get_security_question_display()
        except UserProfile.DoesNotExist:
            messages.error(request, "Ce compte n a pas de question secrete. Contactez un administrateur.")
            return redirect('login')
        form = PasswordResetQuestionForm()
        return render(request, self.template_name, {
            'form': form,
            'username': user.username,
            'question': question,
        })

    def post(self, request):
        user = self._get_user(request)
        if not user:
            messages.error(request, "Session expiree. Veuillez recommencer.")
            return redirect('password-reset')
        profile = get_object_or_404(UserProfile, user=user)
        form = PasswordResetQuestionForm(request.POST)
        if form.is_valid():
            if profile.check_security_answer(form.cleaned_data['answer']):
                request.session['reset_verified'] = True
                return redirect('password-reset-change')
            else:
                form.add_error('answer', "Reponse incorrecte.")
        return render(request, self.template_name, {
            'form': form,
            'username': user.username,
            'question': profile.get_security_question_display(),
        })

    def _get_user(self, request):
        uid = request.session.get('reset_user_id')
        if uid:
            try:
                return User.objects.get(pk=uid)
            except User.DoesNotExist:
                pass
        return None


class PasswordResetChangeView(View):
    """Etape 3: Choisir un nouveau mot de passe."""
    template_name = 'accounts/password_reset_change.html'

    def get(self, request):
        user = self._get_user(request)
        if not user:
            messages.error(request, "Session expiree. Veuillez recommencer.")
            return redirect('password-reset')
        form = PasswordResetChangeForm()
        return render(request, self.template_name, {
            'form': form,
            'username': user.username,
        })

    def post(self, request):
        user = self._get_user(request)
        if not user:
            messages.error(request, "Session expiree.")
            return redirect('password-reset')
        form = PasswordResetChangeForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            update_session_auth_hash(request, user)
            # Nettoyer la session
            request.session.pop('reset_user_id', None)
            request.session.pop('reset_verified', None)
            messages.success(request, 'Mot de passe change avec succes ! Vous etes maintenant connecte.')
            return redirect('accueil')
        return render(request, self.template_name, {
            'form': form,
            'username': user.username,
        })

    def _get_user(self, request):
        if not request.session.get('reset_verified'):
            return None
        uid = request.session.get('reset_user_id')
        if uid:
            try:
                return User.objects.get(pk=uid)
            except User.DoesNotExist:
                pass
        return None
