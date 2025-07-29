from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


class TokenRefreshTests(APITestCase):
    """
    Test suite for the token refresh endpoint.

    This class contains tests to verify the functionality of the
    CookieTokenRefreshView, ensuring that access tokens can be
    refreshed correctly using the refresh token stored in an HTTPOnly cookie.
    """

    def setUp(self):
        """
        Set up the test environment for each test case.

        This method creates an active user and performs a login to obtain
        a valid refresh token. This token is stored in an instance variable
        to be used by the individual tests.
        """
        self.user = User.objects.create_user(
            username='refreshtest@example.com',
            email='refreshtest@example.com',
            password='password123'
        )
        self.user.is_active = True
        self.user.save()

        # Perform a login to get valid cookies
        login_url = reverse('token_obtain_pair')
        login_data = {
            "email": "refreshtest@example.com",
            "password": "password123"
        }
        response = self.client.post(login_url, login_data, format='json')

        # Store the valid refresh token and the refresh URL for use in tests
        self.valid_refresh_token = response.cookies.get('refresh_token').value
        self.refresh_url = reverse('token_refresh')

    def test_successful_token_refresh(self):
        """
        Ensure that an access token can be successfully refreshed.

        This test sends a POST request with a valid refresh token cookie
        and asserts that the response is successful (200 OK), contains the
        correct confirmation message, and sets a new `access_token` cookie.
        """
        # Set the valid refresh token in the test client's cookies
        self.client.cookies['refresh_token'] = self.valid_refresh_token

        response = self.client.post(self.refresh_url, format='json')

        # Assert the response is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'access token refreshed')

        # Assert that a new access token cookie has been set in the response
        self.assertIn('access_token', response.cookies)
        self.assertTrue(response.cookies.get('access_token').value)

    def test_refresh_with_missing_token(self):
        """
        Ensure that the refresh endpoint fails if no refresh token is provided.

        This test clears all cookies from the test client and then sends a
        POST request. It asserts that the request fails with a 400 Bad Request
        status and the appropriate error message.
        """
        # Ensure no cookies are sent with the request
        self.client.cookies.clear()

        response = self.client.post(self.refresh_url, format='json')

        # Assert the request fails with the correct status and error detail
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Refresh token not found!')

    def test_refresh_with_invalid_token(self):
        """
        Ensure that the refresh endpoint fails if an invalid refresh token is provided.

        This test sends a POST request with a malformed or invalid refresh
        token cookie. It asserts that the request is unauthorized (401) and
        returns the expected error detail.
        """
        # Set a garbage value for the refresh token cookie
        self.client.cookies['refresh_token'] = 'invalid.token.string'

        response = self.client.post(self.refresh_url, format='json')

        # Assert the request is unauthorized and has the correct error detail
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Refresh token invalid!')
