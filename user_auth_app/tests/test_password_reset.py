from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class PasswordResetRequestAPITest(APITestCase):
    """
    Test suite for the password reset request endpoint.

    This class contains tests that verify the functionality of the view
    responsible for initiating the password reset process. It covers
    successful requests, security considerations for non-existent users,
    and validation for invalid input.
    """

    def setUp(self):
        """
        Set up the test environment before each test method runs.

        This method creates a standard test user and resolves the URL for the
        password reset request endpoint, making them available to all tests
        in this class.
        """
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldstrongpassword'
        )
        self.url = reverse('password_reset_request')
        self.password_reset_url = reverse('password_reset_request')

    def test_password_reset_request_success(self):
        """
        Tests the successful password reset request for an existing user.

        This test verifies that:
        1. A POST request with a valid, registered email returns a 200 OK status.
        2. The response contains the generic success message.
        3. An email is sent to the user's address.
        4. The email body contains a valid password reset token.
        """
        data = {'email': 'test@example.com'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['detail'],
            'If an account with this email exists, an email has been sent to reset your password.'
        )
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], 'test@example.com')
        
        token = default_token_generator.make_token(self.user)
        self.assertIn(token, mail.outbox[0].body)

    def test_password_reset_request_with_nonexistent_email_returns_200(self):
        """
        Tests that a request with a non-existent email still returns 200 OK.

        This is a critical security test to ensure the endpoint does not
        reveal whether an email address is registered in the system (prevents
        email enumeration attacks). It verifies that the response is the same
        as a successful one, but no email is actually sent.
        """
        data = {'email': 'nonexistent@example.com'}
        response = self.client.post(self.password_reset_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['detail'],
            'If an account with this email exists, an email has been sent to reset your password.'
        )
        
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_missing_email_field(self):
        """
        Tests that the request fails validation if the 'email' field is missing.

        This test verifies that a payload without an email key results in a
        400 Bad Request status and the appropriate validation error.
        """
        data = {}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This field is required.', response.data['email'][0])
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_invalid_email_format(self):
        """
        Tests that the request fails validation if the 'email' field is malformed.

        This test verifies that providing a string that is not a valid email
        format results in a 400 Bad Request status and the correct error message.
        """
        data = {'email': 'not-a-valid-email'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Enter a valid email address.', response.data['email'][0])
        self.assertEqual(len(mail.outbox), 0)
