import pickle
import numpy as np
from django.core.management.base import BaseCommand
from sklearn.feature_extraction.text import TfidfVectorizer
from catalogue.models import Movie


class Command(BaseCommand):
    help = 'Calcule la matrice TF-IDF sur les resumes et la sauvegarde'

    def handle(self, *args, **options):
        movies = Movie.objects.exclude(resume='')
        ids = list(movies.values_list('id', flat=True))
        resumes = list(movies.values_list('resume', flat=True))

        if len(resumes) < 2:
            self.stdout.write(self.style.WARNING('Pas assez de films avec resume.'))
            return

        self.stdout.write(f'Vectorisation TF-IDF de {len(resumes)} resumes...')

        vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2),
        )
        tfidf_matrix = vectorizer.fit_transform(resumes)

        with open('catalogue/tfidf_data.pkl', 'wb') as f:
            pickle.dump({
                'ids': ids,
                'vectorizer': vectorizer,
                'matrix': tfidf_matrix,
            }, f)

        self.stdout.write(self.style.SUCCESS(
            f'TF-IDF sauvegarde : {tfidf_matrix.shape[0]} films, '
            f'{tfidf_matrix.shape[1]} features '
            f'({tfidf_matrix.data.nbytes / 1024 / 1024:.1f} MB)'
        ))
