# Migration : ajout is_favori (boolean) + suppression 'favori' des status choices

from django.db import migrations, models


def convert_favori_to_boolean(apps, schema_editor):
    """Convertit statut='favori' → statut='vu' + is_favori=True"""
    UserMovie = apps.get_model('catalogue', 'UserMovie')
    UserMovie.objects.filter(statut='favori').update(statut='vu', is_favori=True)


def reverse_convert_favori(apps, schema_editor):
    """Rollback : is_favori=True → statut='favori'"""
    UserMovie = apps.get_model('catalogue', 'UserMovie')
    UserMovie.objects.filter(is_favori=True).update(statut='favori', is_favori=False)


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0002_usermovie_and_poster'),
    ]

    operations = [
        # 1. Ajouter le champ is_favori
        migrations.AddField(
            model_name='usermovie',
            name='is_favori',
            field=models.BooleanField(default=False),
        ),

        # 2. Migrer les donnees : statut='favori' → statut='vu' + is_favori=True
        migrations.RunPython(convert_favori_to_boolean, reverse_convert_favori),

        # 3. Modifier les choix du champ statut (retirer 'favori')
        migrations.AlterField(
            model_name='usermovie',
            name='statut',
            field=models.CharField(
                choices=[('a_voir', 'À voir'), ('vu', 'Vu')],
                default='a_voir',
                max_length=10,
            ),
        ),
    ]
