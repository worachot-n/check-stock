import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/supply_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB upload limit
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'client_encoding': 'utf8'}
    }
    DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'
