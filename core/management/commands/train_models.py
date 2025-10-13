from django.core.management.base import BaseCommand  # type: ignore
from core.ml_pipeline import train_models, ML_LIBRARIES_AVAILABLE

class Command(BaseCommand):
    help = 'Train and save ML models for predictions'

    def handle(self, *args, **options):
        if not ML_LIBRARIES_AVAILABLE:
            self.stdout.write(
                self.style.ERROR('ML libraries (sklearn, pandas, numpy, joblib) are not available. Please install them first.')
            )
            return

        self.stdout.write('Starting ML model training...')
        
        success = train_models()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('Successfully trained and saved ML models.')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Failed to train ML models. Check logs for details.')
            )