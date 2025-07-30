from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class PasswordResetRequestAPITest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldstrongpassword'
        )
        self.url = reverse('password_reset_request')

    def test_password_reset_request_success(self):
        data = {'email': 'test@example.com'}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data, {'detail': 'An email has been sent to reset your password.'})

        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(mail.outbox[0].to[0], 'test@example.com')
        
        from django.contrib.auth.tokens import default_token_generator
        token = default_token_generator.make_token(self.user)
        self.assertIn(token, mail.outbox[0].body)


    def test_password_reset_request_nonexistent_email(self):
        data = {'email': 'nonexistent@example.com'}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('User with this email does not exist.', response.data['email'])

        self.assertEqual(len(mail.outbox), 0)


    def test_password_reset_request_missing_email_field(self):
        data = {} 

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('This field is required.', response.data['email'][0])

        self.assertEqual(len(mail.outbox), 0)


    def test_password_reset_request_invalid_email_format(self):
        data = {'email': 'not-a-valid-email'}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('Enter a valid email address.', response.data['email'][0])

        self.assertEqual(len(mail.outbox), 0)