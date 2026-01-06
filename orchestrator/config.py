import os


def build_database_url():
    """Build DATABASE_URL from individual env vars or use DATABASE_URL directly."""
    # If DATABASE_URL is set, use it directly
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')
    
    # Otherwise build from individual components (for Cloud Run with secrets)
    db_user = os.getenv('DB_USER', 'tournament')
    db_pass = os.getenv('DB_PASS', 'nonsense')
    db_name = os.getenv('DB_NAME', 'tournament_db')
    db_host = os.getenv('DB_HOST', 'localhost:5432')
    
    # Cloud SQL uses Unix socket path like /cloudsql/project:region:instance
    if db_host.startswith('/cloudsql/'):
        return f'postgresql://{db_user}:{db_pass}@/{db_name}?host={db_host}'
    else:
        return f'postgresql://{db_user}:{db_pass}@{db_host}/{db_name}'


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'nano-secret-catholic-rook')
    
    # Database
    SQLALCHEMY_DATABASE_URI = build_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Google Cloud
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '')
    GCP_REGION = os.getenv('GCP_REGION', 'us-central1')


class DevelopmentConfig(Config):
    DEBUG = True



class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
