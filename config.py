import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID', '')
    PAYPAL_EMAIL = os.getenv('PAYPAL_EMAIL', 'your-paypal-email@example.com')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database.db')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'production')
    
    if env == 'development':
        return DevelopmentConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return ProductionConfig
