from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase
from user_auth_app.api.tokens import account_activation_token
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


class RegistrationAndActivationTests(APITestCase):
    """
    Test suite for the user registration and account activation process.

    This class covers the complete workflow from a user signing up to
    activating their account via an email link. It tests both successful

    scenarios and various failure cases.
    """

    def setUp(self):
        """
        Set up the test environment for each test case.

        This method initializes common data used across the tests, including
        the registration URL and sample valid/invalid data payloads.
        """
        self.register_url = reverse('register')
        self.valid_payload = {
            'email': 'testuser@example.com',
            'password': 'strong-password123',
            'confirmed_password': 'strong-password123',
        }
        self.invalid_payload_passwords_mismatch = {
            'email': 'anotheruser@example.com',
            'password': 'strong-password123',
            'confirmed_password': 'different-password456',
        }

    def test_successful_registration(self):
        """
        Ensure a new user can be registered successfully.

        This test verifies that a POST request with valid data to the
        registration endpoint results in a 201 Created status. It also
        checks that a new, inactive user is created in the database and
        that an activation email has been sent.
        """
        response = self.client.post(self.register_url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.valid_payload['email']).exists())
        user = User.objects.get(email=self.valid_payload['email'])

        self.assertEqual(user.username, self.valid_payload['email'])
        self.assertFalse(user.is_active)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Activate your Videoflix account.')
        self.assertIn(self.valid_payload['email'], mail.outbox[0].to)

    def test_registration_with_mismatched_passwords(self):
        """
        Ensure registration fails if the provided passwords do not match.

        This test asserts that the request fails with a 400 Bad Request
        status, returns the correct validation error, and that no new
        user is created in the database.
        """
        response = self.client.post(
            self.register_url, self.invalid_payload_passwords_mismatch, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertEqual(response.data['password'][0], 'Passwords do not match.')
        self.assertFalse(User.objects.filter(
            email=self.invalid_payload_passwords_mismatch['email']).exists())

    def test_registration_with_missing_password(self):
        """
        Ensure registration fails if the password and confirmation fields are missing.
        """
        payload = {
            'email': 'test@example.com',
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertIn('confirmed_password', response.data)

    def test_registration_with_existing_email(self):
        """
        Ensure registration fails if the email address is already in use.

        This test first creates a user, then attempts to register a new
        user with the same email. It asserts that the request fails with
        a 400 Bad Request status and the appropriate error message.
        """
        User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='password'
        )

        payload = {
            'email': 'existing@example.com',
            'password': 'password123',
            'confirmed_password': 'password123'
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'][0], 'Email already exists')

    def test_registration_with_missing_email(self):
        """
        Ensure registration fails if the email field is not provided.
        """
        payload = {
            'password': 'password123',
            'confirmed_password': 'password123'
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_successful_account_activation(self):
        """
        Ensure a user account can be activated using a valid link.

        This test creates an inactive user, generates a valid activation
        UID and token, and makes a GET request to the activation URL. It
        asserts that the response is successful (200 OK) and that the
        user's `is_active` status is updated to True.
        """
        user = User.objects.create_user(
            username='to-activate@example.com',
            email='to-activate@example.com',
            password='password'
        )
        user.is_active = False
        user.save()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        activation_url = reverse('activate', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(activation_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Account successfully activated!')
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_invalid_account_activation_link(self):
        """
        Ensure account activation fails if the activation link token is invalid.

        This test uses a valid UID but an invalid token. It asserts that
        the request fails with a 400 Bad Request status, returns the correct
        error message, and that the user's `is_active` status remains False.
        """
        user = User.objects.create_user(
            username='inactive@example.com',
            email='inactive@example.com',
            password='password'
        )
        user.is_active = False
        user.save()

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = 'invalid-token'

        activation_url = reverse('activate', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(activation_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Activation link is invalid or has expired!')
        user.refresh_from_db()
        self.assertFalse(user.is_active)
