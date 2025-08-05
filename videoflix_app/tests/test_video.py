from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Video


class VideoAPITest(APITestCase):

    def setUp(self):
        self.list_url = reverse('video-list')
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
        
        self.detail_url = reverse('video-detail', kwargs={'pk': self.video1.pk})

    def test_unauthenticated_user_cannot_access_video_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_authenticated_user_can_access_video_list_and_data_is_correct(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        
    def test_unauthenticated_user_cannot_access_detail_view(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        

    def test_authenticated_user_can_access_detail_view(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.video1.title)        
        self.assertIn('hls_urls', response.data)
        self.assertIn('720p', response.data['hls_urls'])
        expected_url_part = f'/api/video/{self.video1.pk}/720p/index.m3u8'
        self.assertIn(expected_url_part, response.data['hls_urls']['720p'])


    def test_detail_view_returns_404_for_invalid_id(self):
        self.client.force_authenticate(user=self.user)
        invalid_url = reverse('video-detail', kwargs={'pk': 9999})
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)