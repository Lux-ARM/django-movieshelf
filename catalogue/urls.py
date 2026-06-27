from django.urls import path
from . import views

urlpatterns = [
    path('', views.AccueilView.as_view(), name='accueil'),
    path('catalogue/', views.CatalogueView.as_view(), name='catalogue'),
    path('catalogue/<int:pk>/', views.MovieDetailView.as_view(), name='movie-detail'),
    path('catalogue/creer/', views.MovieCreateView.as_view(), name='movie-create'),
    path('catalogue/<int:pk>/modifier/', views.MovieUpdateView.as_view(), name='movie-update'),
    path('catalogue/<int:pk>/supprimer/', views.MovieDeleteView.as_view(), name='movie-delete'),
    path('catalogue/<int:pk>/add-to-shelf/', views.AddToShelfView.as_view(), name='add-to-shelf'),
    path('genres/', views.GenreListView.as_view(), name='genre-list'),
    path('genres/<slug:slug>/', views.GenreDetailView.as_view(), name='genre-detail'),
    # Shelf
    path('shelf/', views.ShelfView.as_view(), name='shelf'),
    path('shelf/<int:pk>/update/', views.UpdateShelfStatusView.as_view(), name='update-shelf-status'),
]
