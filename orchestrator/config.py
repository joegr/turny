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
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Tournament Service
    TOURNAMENT_SERVICE_BASE_PORT = int(os.getenv('TOURNAMENT_SERVICE_BASE_PORT', '6001'))
    TOURNAMENT_SERVICE_HOST = os.getenv('TOURNAMENT_SERVICE_HOST', 'localhost')
    MAX_TOURNAMENT_INSTANCES = int(os.getenv('MAX_TOURNAMENT_INSTANCES', '100'))
    
    # Docker settings (for container-based deployment)
    USE_DOCKER = os.getenv('USE_DOCKER', 'false').lower() == 'true'
    DOCKER_NETWORK = os.getenv('DOCKER_NETWORK', 'tournament-network')
    
    # Cloud Run settings
    USE_CLOUD_RUN = os.getenv('USE_CLOUD_RUN', 'false').lower() == 'true'
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '')
    GCP_REGION = os.getenv('GCP_REGION', 'us-central1')
    TOURNAMENT_SERVICE_IMAGE = os.getenv('TOURNAMENT_SERVICE_IMAGE', '')


class DevelopmentConfig(Config):
    DEBUG = True
    USE_DOCKER = False
    USE_CLOUD_RUN = False


class ProductionConfig(Config):
    DEBUG = False
    USE_DOCKER = True
    USE_CLOUD_RUN = False


class CloudRunConfig(Config):
    DEBUG = False
    USE_DOCKER = False
    USE_CLOUD_RUN = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'cloudrun': CloudRunConfig,
    'default': DevelopmentConfig
}
