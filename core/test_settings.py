"""Test settings for pytest"""
import os
from .settings import *

# Test database (SQLite for local tests)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Media settings for tests
import tempfile
MEDIA_ROOT = tempfile.mkdtemp(prefix='videoflix_test_media_')

# Auto-cleanup media files after tests
TEST_MEDIA_CLEANUP = True

# Simplify password validation for tests
AUTH_PASSWORD_VALIDATORS = []

# RQ for tests - use Mock/Dummy
RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
        'ASYNC': False,  # Synchronous execution for tests
    }
}

# Explicitly set secret key
SECRET_KEY = 'test-secret-key-only-for-testing-12345'

# DEBUG for tests
DEBUG = True

# Disable Django RQ for tests
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'django_rq']