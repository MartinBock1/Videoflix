"""
Example pytest-style tests following pytest-django best practices.

This module demonstrates how to write tests using pytest-django features
instead of Django's unittest-style TestCase classes.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
def test_video_list_requires_authentication(api_client):
    """Test that video list endpoint requires authentication."""
    url = reverse('video-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_authenticated_user_can_access_video_list(authenticated_client, sample_video):
    """Test that authenticated users can access video list."""
    url = reverse('video-list')
    response = authenticated_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['title'] == sample_video.title


@pytest.mark.django_db
def test_video_detail_view(authenticated_client, sample_video):
    """Test video detail view."""
    url = reverse('video-detail', kwargs={'pk': sample_video.pk})
    response = authenticated_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['title'] == sample_video.title
    assert response.data['description'] == sample_video.description


@pytest.mark.django_db
def test_video_detail_not_found(authenticated_client):
    """Test 404 for non-existent video."""
    url = reverse('video-detail', kwargs={'pk': 99999})
    response = authenticated_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_non_database_function():
    """Example of test that doesn't need database access."""
    # This test doesn't have @pytest.mark.django_db
    # and won't have database access
    result = 2 + 2
    assert result == 4


@pytest.mark.django_db(transaction=True)
def test_with_transaction_support():
    """Example test with transaction support."""
    # This test supports database transactions
    from videoflix_app.models import Video
    assert Video.objects.count() == 0


class TestVideoFixtures:
    """Example of pytest-style test class."""
    
    @pytest.mark.django_db
    def test_sample_video_fixture(self, sample_video):
        """Test using the sample_video fixture."""
        assert sample_video.title == "Test Video"
        assert sample_video.description == "A test video"
    
    @pytest.mark.django_db
    def test_authenticated_user_fixture(self, authenticated_user):
        """Test using the authenticated_user fixture."""
        assert authenticated_user.username == "testuser"
        assert authenticated_user.email == "test@example.com"


@pytest.mark.parametrize("title,expected", [
    ("Short", True),
    ("A" * 200, False),  # Too long
    ("", False),  # Empty
])
@pytest.mark.django_db
def test_video_title_validation(title, expected):
    """Example of parametrized test."""
    from videoflix_app.models import Video
    from django.core.exceptions import ValidationError
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    fake_file = SimpleUploadedFile("test.mp4", b"content", content_type="video/mp4")
    video = Video(title=title, description="Test", category="Test", video_file=fake_file)
    
    if expected:
        # Should not raise exception
        video.full_clean()
    else:
        # Should raise ValidationError
        with pytest.raises(ValidationError):
            video.full_clean()


@pytest.mark.slow
@pytest.mark.django_db
def test_slow_operation():
    """Example of marked slow test."""
    # This test is marked as slow and can be skipped with:
    # pytest -m "not slow"
    import time
    time.sleep(0.1)  # Simulate slow operation
    assert True
