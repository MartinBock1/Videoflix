from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class LogoutViewTest(APITestCase):
    """
    Test suite for the LogoutView, specifically testing scenarios related
    to cookie-based authentication and token blacklisting.
    """

    def setUp(self):
        """
        Set up the test environment before each test method is run.

        This method creates a standard, active test user and resolves the URLs
        for the login and logout endpoints. These resources are reused across
        multiple tests.
        """
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.user.is_active = True
        self.user.save()

        # Reverse the URL names to get the actual paths for the API endpoints.
        self.login_url = reverse('token_obtain_pair')
        self.logout_url = reverse('logout')

    def _login_and_get_cookies(self):
        """
        A helper method to perform a login and set auth cookies on the test client.

        This simulates a user logging in via the API. The `APITestCase` client
        automatically persists the cookies set in the response, making them
        available for subsequent requests within the same test method.

        Returns:
            Response: The full response object from the login request.
        """
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }, format='json')

        # Assert that the login was successful and cookies were set.
        self.assertTrue('access_token' in self.client.cookies)
        self.assertTrue('refresh_token' in self.client.cookies)

        return response

    def test_successful_logout(self):
        """
        Tests that a successfully authenticated user can log out correctly.

        This test verifies:
        1. The logout endpoint returns a 200 OK status.
        2. The response contains the expected success message.
        3. The server sends instructions to delete the access and refresh token cookies.
        4. The refresh token used for the session is successfully blacklisted.
        """
        # 1. Log in to establish an authenticated session with valid cookies.
        login_response = self._login_and_get_cookies()
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Store the refresh token value to verify it gets blacklisted later.
        refresh_token_value = login_response.cookies.get('refresh_token').value

        # 2. Make the POST request to the logout endpoint. The client sends the cookies.
        logout_response = self.client.post(self.logout_url, {})

        # 3. Assert the response is successful and contains the correct message.
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            logout_response.data['detail'],
            "Log-Out successfully! Tokens have been invalidated."
        )

        # 4. Assert that the server has instructed the client to delete the cookies.
        # A deleted cookie is sent back with a 'max-age' of 0.
        self.assertEqual(logout_response.cookies['access_token']['max-age'], 0)
        self.assertEqual(logout_response.cookies['refresh_token']['max-age'], 0)

        # 5. Assert that the original refresh token is now on the blacklist.
        # Attempting to use or blacklist it again should raise a TokenError.
        with self.assertRaises(TokenError, msg="The refresh token should be invalid but was accepted."):
            RefreshToken(refresh_token_value)

    def test_logout_without_authentication(self):
        """
        Tests that an unauthenticated request to the logout endpoint is rejected.

        This simulates a user trying to log out without being logged in (i.e.,
        without sending any authentication cookies). The expected result is a
        401 Unauthorized error.
        """
        # Make a request to the logout URL without logging in first.
        response = self.client.post(self.logout_url, {})

        # Assert that the request was unauthorized.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], "Authentication credentials were not provided.")

    def test_logout_with_missing_refresh_token_cookie(self):
        """
        Tests that logout fails if the refresh token cookie is missing.

        Even if the user has a valid access token, the logout view requires the
        refresh token to blacklist it. This test ensures the endpoint returns
        a 400 Bad Request if the refresh token is not provided.
        """
        # 1. Log in to get both access and refresh cookies.
        self._login_and_get_cookies()

        # 2. Manually delete the refresh token from the test client's cookies.
        del self.client.cookies['refresh_token']

        # 3. Attempt to log out. The valid access token is still sent.
        response = self.client.post(self.logout_url, {})

        # 4. Assert that the server responds with a bad request error.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Refresh token not found.")

    def test_logout_with_invalid_access_token(self):
        """
        Tests that logout fails if the provided access token is invalid.

        This test confirms that the `CookieJWTAuthentication` class is working correctly.
        An invalid access token should prevent access to the protected logout view,
        resulting in a 401 Unauthorized error with a 'token_not_valid' code.
        """
        # 1. Log in to get valid cookies.
        self._login_and_get_cookies()

        # 2. Manually overwrite the access token with a garbage value.
        self.client.cookies['access_token'] = 'thisisnotavalidtoken'

        # 3. Attempt to log out.
        response = self.client.post(self.logout_url, {})

        # 4. Assert that the request is unauthorized and contains the specific error code.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('token_not_valid', response.data['code'])
