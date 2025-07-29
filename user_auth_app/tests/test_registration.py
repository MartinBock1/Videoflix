from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase
from user_auth_app.api.tokens import account_activation_token
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


class RegistrationAndActivationTests(APITestCase):

    def setUp(self):
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
        response = self.client.post(
            self.register_url, self.invalid_payload_passwords_mismatch, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertEqual(response.data['password'][0], 'Passwords do not match.')
        self.assertFalse(User.objects.filter(
            email=self.invalid_payload_passwords_mismatch['email']).exists())

    def test_registration_with_missing_password(self):
        """ Testet die Registrierung, wenn das Passwort-Feld fehlt. """
        payload = {
            'email': 'test@example.com',
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertIn('confirmed_password', response.data)

    def test_registration_with_existing_email(self):
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
        payload = {
            'password': 'password123',
            'confirmed_password': 'password123'
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_successful_account_activation(self):
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
        self.assertEqual(response.data['error'], 'Activation link is invalid!')
        user.refresh_from_db()
        self.assertFalse(user.is_active)
