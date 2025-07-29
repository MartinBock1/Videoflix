from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


class LoginTests(APITestCase):
    """
    Test suite for the user login endpoint.

    This class verifies all aspects of the `CookieTokenObtainPairView`,
    including successful login, handling of incorrect credentials,
    inactive accounts, and invalid data submissions.
    """

    def setUp(self):
        """
        Set up the test environment for each test case.

        This method creates an active user and defines the login URL to be
        used across multiple tests.
        """
        self.user = User.objects.create_user(
            username='exampleUsername',
            email='example@mail.de',
            password='examplePassword'
        )
        self.user.is_active = True
        self.user.save()

        # Define the correct URL name for the login endpoint
        self.login_url = reverse('token_obtain_pair')

    def test_login_success(self):
        """
        Ensure a user can log in successfully with correct credentials.

        This test sends a POST request with a valid email and password.
        It asserts that the response is successful (200 OK), the response
        body contains the expected user data, and that `access_token` and
        `refresh_token` cookies are correctly set.
        """
        data = {
            "email": "example@mail.de",
            "password": "examplePassword"
        }
        response = self.client.post(self.login_url, data, format='json')

        # 1. Assert that the request was successful (200 OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Assert the correct structure and content of the response body
        self.assertEqual(response.data['detail'], 'login successful')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['user']['username'], self.user.username)

        # 3. Assert that the HTTPOnly cookies have been set
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_login_with_inactive_account(self):
        """
        Ensure that a user with a valid but inactive account cannot log in.

        This is a critical test for the registration-activation flow. It
        asserts that the request fails with a 400 Bad Request status and
        returns the specific error message for inactive accounts.
        """
        # Create a new, inactive user
        inactive_user = User.objects.create_user(
            username='inactive@example.com',
            email='inactive@example.com',
            password='password123'
        )
        inactive_user.is_active = False
        inactive_user.save()

        data = {
            "email": "inactive@example.com",
            "password": "password123"
        }
        response = self.client.post(self.login_url, data, format='json')

        # Assert that the request fails with a 400 error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert the specific error message from the serializer
        self.assertIn('non_field_errors', response.data)
        expected_error = "Account is not active. Please check your E-Mails for the activation link."
        self.assertEqual(response.data['non_field_errors'][0], expected_error)

    def test_login_bad_credentials(self):
        """
        Ensure a login attempt with a correct email but an incorrect password fails.

        This test asserts that the request fails with a 400 Bad Request
        status and that the response contains the expected 'non_field_errors'
        message.
        """
        data = {
            "email": "example@mail.de",
            "password": "wrongPassword"
        }
        response = self.client.post(self.login_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertEqual(response.data['non_field_errors'][0], 'email or password does not exist.')

    def test_login_non_existent_user(self):
        """
        Ensure a login attempt with a non-existent email address fails.

        This test asserts that the request fails with a 400 Bad Request
        status and returns the appropriate 'non_field_errors' message.
        """
        data = {
            "email": "nouser@example.com",
            "password": "somePassword"
        }
        response = self.client.post(self.login_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertEqual(response.data['non_field_errors'][0], 'email or password does not exist.')

    def test_login_missing_fields(self):
        """
        Ensure a login attempt with missing (blank) credentials fails validation.

        This test asserts that the request fails with a 400 Bad Request
        status and that the response contains validation errors for both
        the 'email' and 'password' fields.
        """
        data = {
            "email": "",
            "password": ""
        }
        response = self.client.post(self.login_url, data, format='json')

        # Assert that the request is a bad request due to validation failure
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert that the response contains specific error details for each field
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)
        self.assertEqual(response.data['email'][0], 'This field may not be blank.')
        self.assertEqual(response.data['password'][0], 'This field may not be blank.')
