from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


class TokenRefreshTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='refreshtest@example.com',
            email='refreshtest@example.com',
            password='password123'
        )
        self.user.is_active = True
        self.user.save()

        login_url = reverse('token_obtain_pair')
        login_data = {
            "email": "refreshtest@example.com",
            "password": "password123"
        }
        response = self.client.post(login_url, login_data, format='json')

        self.valid_refresh_token = response.cookies.get('refresh_token').value
        self.refresh_url = reverse('token_refresh')

    def test_successful_token_refresh(self):
        self.client.cookies['refresh_token'] = self.valid_refresh_token

        response = self.client.post(self.refresh_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'access token refreshed')

        self.assertIn('access_token', response.cookies)
        self.assertTrue(response.cookies.get('access_token').value)

    def test_refresh_with_missing_token(self):
        self.client.cookies.clear()

        response = self.client.post(self.refresh_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Refresh token not found!')

    def test_refresh_with_invalid_token(self):
        self.client.cookies['refresh_token'] = 'invalid.token.string'

        response = self.client.post(self.refresh_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Refresh token invalid!')
