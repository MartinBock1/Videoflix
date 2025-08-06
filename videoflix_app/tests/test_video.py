from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Video


class VideoAPITest(APITestCase):
    """
    Test suite for the Video API endpoints.

    This class contains tests for the list and detail views of the Video API,
    covering authentication, data retrieval, and error handling.
    """
    def setUp(self):
        """
        Set up the necessary objects and data for the tests.

        This method runs before each individual test method in this class.
        """
        # Define the URL for the video list endpoint.
        self.list_url = reverse('video-list')

        # Create a test user for authentication purposes.
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123'
        )
        # Instantiate an APIClient to make requests.
        self.client = APIClient()

        # Create two Video instances to populate the test database.
        self.video1 = Video.objects.create(
            title="The rise of TDD",
            description="An epic drama about test-driven development.",
            category="Education"
        )
        self.video2 = Video.objects.create(
            title="The hunt for the green test",
            description="An exciting thriller.",
            category="Thriller"
        )

        # Define the URL for the detail view of the first video.
        self.detail_url = reverse('video-detail', kwargs={'pk': self.video1.pk})

    def test_unauthenticated_user_cannot_access_video_list(self):
        """
        Ensure that unauthenticated users receive a 401 Unauthorized error
        when trying to access the video list.
        """
        # Act: Make a GET request without authenticating.
        response = self.client.get(self.list_url)
        # Assert: Check that the status code is 401 Unauthorized.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_access_video_list_and_data_is_correct(self):
        """
        Ensure that an authenticated user can access the video list and that
        it contains the correct number of items.
        """
        # Arrange: Authenticate the client with the test user.
        self.client.force_authenticate(user=self.user)
        # Act: Make a GET request.
        response = self.client.get(self.list_url)

        # Assert: Check that the request was successful.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assert: Check that the response contains data for both videos.
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_user_cannot_access_detail_view(self):
        """
        Ensure that unauthenticated users receive a 401 Unauthorized error
        when trying to access the video detail view.
        """
        # Act: Make a GET request to the detail URL without authenticating.
        response = self.client.get(self.detail_url)
        # Assert: Check that the status code is 401 Unauthorized.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_access_detail_view(self):
        """
        Ensure that an authenticated user can access the detail view and that
        the serialized data is correct, including custom serializer fields.
        """
        # Arrange: Authenticate the client.
        self.client.force_authenticate(user=self.user)
        # Act: Make a GET request to the detail URL.
        response = self.client.get(self.detail_url)

        # Assert: Check for a successful response.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assert: Check if the title in the response matches the object's title.
        self.assertEqual(response.data['title'], self.video1.title)
        # Assert: Check for the 'hls_urls' key, which is specific to the detail serializer.
        self.assertIn('hls_urls', response.data)
        # Assert: Check for a specific resolution within the HLS URLs.
        self.assertIn('720p', response.data['hls_urls'])
        # Assert: Check if the generated HLS URL has the correct structure.
        expected_url_part = f'/api/video/{self.video1.pk}/720p/index.m3u8'
        self.assertIn(expected_url_part, response.data['hls_urls']['720p'])

    def test_detail_view_returns_404_for_invalid_id(self):
        """
        Ensure that the detail view returns a 404 Not Found error when
        requested with a primary key that does not exist.
        """
        # Arrange: Authenticate the client.
        self.client.force_authenticate(user=self.user)
        # Arrange: Create a URL with a non-existent primary key.
        invalid_url = reverse('video-detail', kwargs={'pk': 9999})
        # Act: Make a GET request to the invalid URL.
        response = self.client.get(invalid_url)
        # Assert: Check that the status code is 404 Not Found.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
