from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Video


class VideoAPITest(APITestCase):

    def setUp(self):
        self.url = reverse('video-list')
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123'
        )
        self.client = APIClient()

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

    def test_unauthenticated_user_cannot_access_video_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_access_video_list_and_data_is_correct(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)

        expected_keys = ['id', 'created_at', 'title', 'description', 'thumbnail_url', 'category']
        self.assertCountEqual(response.data[0].keys(), expected_keys)

        response_video_data = {item['id']: item for item in response.data}

        retrieved_video1_data = response_video_data.get(self.video1.id)

        self.assertIsNotNone(retrieved_video1_data)
        self.assertEqual(retrieved_video1_data['title'], self.video1.title)
        self.assertEqual(retrieved_video1_data['description'], self.video1.description)
        self.assertEqual(retrieved_video1_data['category'], self.video1.category)
