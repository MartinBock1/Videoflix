"""
Global pytest configuration for the Videoflix project.

This conftest.py provides fixtures and configuration that are available
to all tests in the project, following pytest-django best practices.
"""
import os
import shutil
import tempfile
import pytest
from django.db.models.signals import post_save
from videoflix_app.models import Video
from videoflix_app import signals


@pytest.fixture(scope='function')
def temp_media_root():
    """
    Create a temporary media directory for each test.
    
    This fixture creates a unique temporary directory for each test
    and automatically cleans it up after the test completes.
    """
    temp_dir = tempfile.mkdtemp(prefix='videoflix_test_')
    yield temp_dir
    # Cleanup after test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Allow database access for all tests automatically.
    
    This fixture is auto-used for all tests, providing database access
    without needing to mark each test with @pytest.mark.django_db.
    
    Alternative: Remove this fixture and use @pytest.mark.django_db explicitly.
    """
    pass


@pytest.fixture(autouse=True)
def disable_video_signals():
    """
    Disable video-related signals during testing to prevent Redis connections.
    
    This fixture automatically disconnects Django signals that would trigger
    Redis/RQ operations during testing, preventing connection errors.
    """
    post_save.disconnect(signals.video_post_save, sender=Video)
    yield
    post_save.connect(signals.video_post_save, sender=Video)


@pytest.fixture(autouse=True)
def cleanup_test_media():
    """
    Automatically cleanup test media files after each test.
    
    This fixture runs after every test and removes any test media files
    that might have been created during testing.
    """
    yield  # Run the test first
    
    # Cleanup paths that might contain test files
    cleanup_paths = [
        '/app/test_media',
        '/app/media/test_videos',
        '/tmp/videoflix_test_media_*',
        '/tmp/videoflix_test_edge_cases_*'
    ]
    
    for pattern in cleanup_paths:
        if '*' in pattern:
            # Handle glob patterns
            import glob
            for path in glob.glob(pattern):
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
        else:
            # Handle direct paths
            if os.path.exists(pattern):
                shutil.rmtree(pattern, ignore_errors=True)


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for the entire test session.
    
    This fixture runs once per test session and can be used to
    populate the database with initial test data.
    """
    with django_db_blocker.unblock():
        # Add any global test data setup here
        pass


@pytest.fixture
def api_client():
    """
    Provide a DRF APIClient for testing API endpoints.
    
    Returns:
        APIClient: Django REST framework test client
    """
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """
    Create a test user for authentication tests.
    
    Returns:
        User: Django user instance
    """
    from django.contrib.auth.models import User
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123'
    )


@pytest.fixture
def authenticated_client(api_client, authenticated_user):
    """
    Provide an authenticated API client.
    
    Returns:
        APIClient: Authenticated DRF test client
    """
    api_client.force_authenticate(user=authenticated_user)
    return api_client


@pytest.fixture
def sample_video(db, authenticated_user, temp_media_root):
    """
    Create a sample video for testing with automatic cleanup.
    
    Returns:
        Video: Test video instance
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.conf import settings
    
    # Temporarily override MEDIA_ROOT to use temp directory
    original_media_root = settings.MEDIA_ROOT
    settings.MEDIA_ROOT = temp_media_root
    
    fake_video_file = SimpleUploadedFile(
        "test_video.mp4",
        b'fake video content',
        content_type="video/mp4"
    )
    
    video = Video.objects.create(
        title="Test Video",
        description="A test video",
        category="Testing",
        video_file=fake_video_file
    )
    
    yield video
    
    # Restore original MEDIA_ROOT
    settings.MEDIA_ROOT = original_media_root
