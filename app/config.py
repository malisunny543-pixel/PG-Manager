import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class _ProductionSecretKeyDescriptor:
    def __get__(self, instance, owner):
        secret = os.environ.get('FLASK_SECRET_KEY') or os.environ.get('SECRET_KEY')
        if not secret:
            raise ValueError("FLASK_SECRET_KEY must be set in production environment.")
        return secret

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', os.environ.get('SECRET_KEY', 'pgms-dev-insecure-secret-key-change-in-prod'))
    
    # Database Settings
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'pg_management')
    DB_TEST_NAME = os.environ.get('DB_TEST_NAME', 'pg_management_test')
    DB_CHARSET = 'utf8mb4'
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 10))
    DB_SSL_CA = os.environ.get('DB_SSL_CA')

    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    DB_NAME = os.environ.get('DB_TEST_NAME', 'pg_management_test')
    SECRET_KEY = 'test-secret-key'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SECRET_KEY = _ProductionSecretKeyDescriptor()

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
