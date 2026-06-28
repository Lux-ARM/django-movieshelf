from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # Password Reset via question secrete
    path('password-reset/', views.PasswordResetUsernameView.as_view(), name='password-reset'),
    path('password-reset/question/', views.PasswordResetQuestionView.as_view(), name='password-reset-question'),
    path('password-reset/change/', views.PasswordResetChangeView.as_view(), name='password-reset-change'),
]
