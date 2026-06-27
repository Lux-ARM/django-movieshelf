# Generated migration — refonte shelf
# Ajout UserMovie + poster ImageField + suppression Movie.statut

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def migrate_statut_to_usermovie(apps, schema_editor):
    """Copie chaque Movie.statut vers un UserMovie lié à l'auteur du film."""
    Movie = apps.get_model('catalogue', 'Movie')
    UserMovie = apps.get_model('catalogue', 'UserMovie')

    for movie in Movie.objects.all():
        UserMovie.objects.create(
            user=movie.auteur,
            movie=movie,
            statut=movie.statut,
        )


def reverse_migrate_statut(apps, schema_editor):
    """Rollback : remet le statut sur Movie depuis le premier UserMovie trouvé."""
    UserMovie = apps.get_model('catalogue', 'UserMovie')
    for entry in UserMovie.objects.select_related('movie').all():
        entry.movie.statut = entry.statut
        entry.movie.save(update_fields=['statut'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- 1. Créer la table UserMovie ---
        migrations.CreateModel(
            name='UserMovie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('statut', models.CharField(choices=[('a_voir', 'À voir'), ('vu', 'Vu'), ('favori', 'Favori')], default='a_voir', max_length=10)),
                ('note', models.PositiveSmallIntegerField(blank=True, help_text='Note personnelle sur 10', null=True)),
                ('date_ajout', models.DateTimeField(auto_now_add=True)),
                ('movie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shelf_entries', to='catalogue.movie')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shelf', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date_ajout'],
            },
        ),

        # --- 2. Ajouter le champ poster (ImageField) sur Movie ---
        migrations.AddField(
            model_name='movie',
            name='poster',
            field=models.ImageField(blank=True, help_text="Upload local d'une affiche", upload_to='posters/'),
        ),

        # --- 3. Contrainte unique_together sur UserMovie ---
        migrations.AddConstraint(
            model_name='usermovie',
            constraint=models.UniqueConstraint(fields=('user', 'movie'), name='unique_user_movie'),
        ),

        # --- 4. Migrer les données : Movie.statut → UserMovie ---
        migrations.RunPython(migrate_statut_to_usermovie, reverse_migrate_statut),

        # --- 5. Supprimer le champ statut de Movie ---
        migrations.RemoveField(
            model_name='movie',
            name='statut',
        ),
    ]
