from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.test import APITestCase


class PasswordResetConfirmAPITest(APITestCase):
    """
    Test suite for the password reset confirmation endpoint.

    This class verifies the functionality of the view that handles the final
    step of the password reset process. It tests the successful password
    update with valid tokens and various failure scenarios, including invalid
    tokens, invalid user IDs, and password validation errors.
    """

    def setUp(self):
        """
        Set up the test environment before each test method runs.

        This method creates a test user and generates a valid, corresponding
        UID and token for them. It also prepares a valid data payload for
        the new password, making these resources available to all tests.
        """
        self.user = User.objects.create_user(
            username='confirmuser',
            email='confirm@example.com',
            password='oldstrongpassword'
        )
        # Generate the user's ID encoded in base64.
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        # Generate a valid, one-time token for the user.
        self.token = default_token_generator.make_token(self.user)
        # Prepare a valid payload with matching passwords.
        self.valid_password_data = {
            'new_password': 'newsecurepassword123',
            'confirm_password': 'newsecurepassword123'
        }

    def test_password_reset_confirm_success(self):
        """
        Tests the successful confirmation of a password reset.

        This test uses a valid UID, token, and password payload. It asserts
        that the response is 200 OK with the correct success message, and
        most importantly, that the user's password has been updated in the
        database.
        """
        url = reverse('password_reset_confirm',
                      kwargs={'uidb64': self.uidb64, 'token': self.token})

        response = self.client.post(url, self.valid_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'detail': 'Your Password has been successfully reset.'}
        )

        # Verify the password was changed in the database.
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newsecurepassword123'))
        self.assertFalse(self.user.check_password('oldstrongpassword'))

    def test_password_reset_confirm_invalid_token(self):
        """
        Tests that password reset fails if the provided token is invalid.

        This test uses a valid user ID but an incorrect token. It asserts
        that the request fails with a 400 Bad Request status and the
        appropriate error message.
        """
        invalid_token = 'invalid-token'
        url = reverse('password_reset_confirm',
                      kwargs={'uidb64': self.uidb64, 'token': invalid_token}
                      )

        response = self.client.post(url, self.valid_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            response.data, {"error": "Password reset link is invalid or has expired!"})

    def test_password_reset_confirm_invalid_uid(self):
        """
        Tests that password reset fails if the provided user ID is invalid.

        This test uses a malformed UID. It asserts that the request fails
        with a 400 Bad Request status because the user cannot be found,
        resulting in an invalid link error.
        """
        invalid_uidb64 = 'invalid-uid'
        url = reverse('password_reset_confirm',
                      kwargs={'uidb64': invalid_uidb64, 'token': self.token}
                      )

        response = self.client.post(url, self.valid_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {"error": "Password reset link is invalid or has expired!"})

    def test_password_reset_confirm_password_mismatch(self):
        """
        Tests that the request fails validation if the new passwords do not match.

        This test uses a valid UID and token but provides different values for
        'new_password' and 'confirm_password'. It asserts a 400 Bad Request
        and checks for the specific validation error message.
        """
        url = reverse('password_reset_confirm',
                      kwargs={'uidb64': self.uidb64, 'token': self.token}
                      )
        mismatched_password_data = {
            'new_password': 'newsecurepassword123',
            'confirm_password': 'anotherpassword456'
        }

        response = self.client.post(url, mismatched_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('Passwords do not match.', response.data['password'])

    def test_password_reset_confirm_missing_password_fields(self):
        """
        Tests that the request fails validation if password fields are missing.

        This test sends an empty payload and asserts that the request fails
        with a 400 Bad Request status, returning validation errors for both
        required password fields.
        """
        url = reverse('password_reset_confirm',
                      kwargs={'uidb64': self.uidb64, 'token': self.token}
                      )

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('This field is required.', response.data['new_password'][0])
        self.assertIn('This field is required.', response.data['confirm_password'][0])
