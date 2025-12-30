import os


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
    
    # Database
    DATABASE_URL = os.getenv(
        'DATABASE_URL', 
        'postgresql://tournament:tournament123@localhost:5432/tournament_db'
    )
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Google Cloud
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '')
    GCP_REGION = os.getenv('GCP_REGION', 'us-central1')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
