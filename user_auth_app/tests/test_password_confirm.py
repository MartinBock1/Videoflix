from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.test import APITestCase


class PasswordResetConfirmAPITest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='confirmuser',
            email='confirm@example.com',
            password='oldstrongpassword'
        )
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)
        self.valid_password_data = {
            'new_password': 'newsecurepassword123',
            'confirm_password': 'newsecurepassword123'
        }

    def test_password_reset_confirm_success(self):
        url = reverse('password_reset_confirm', kwargs={
                      'uidb64': self.uidb64, 'token': self.token})

        response = self.client.post(url, self.valid_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data, {'detail': 'Your Password has been successfully reset.'})

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newsecurepassword123'))
        self.assertFalse(self.user.check_password('oldstrongpassword'))

    def test_password_reset_confirm_invalid_token(self):
        invalid_token = 'invalid-token'
        url = reverse('password_reset_confirm', kwargs={
                      'uidb64': self.uidb64, 'token': invalid_token})

        response = self.client.post(url, self.valid_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(response.data, {"error": "Activation link is invalid or has expired!"})

    def test_password_reset_confirm_invalid_uid(self):
        invalid_uidb64 = 'invalid-uid'
        url = reverse('password_reset_confirm', kwargs={
                      'uidb64': invalid_uidb64, 'token': self.token})

        response = self.client.post(url, self.valid_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(response.data, {"error": "Activation link is invalid or has expired!"})

    def test_password_reset_confirm_password_mismatch(self):
        url = reverse('password_reset_confirm', kwargs={
                      'uidb64': self.uidb64, 'token': self.token})
        mismatched_password_data = {
            'new_password': 'newsecurepassword123',
            'confirm_password': 'anotherpassword456'
        }

        response = self.client.post(url, mismatched_password_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('Passwords do not match.', response.data['password'])

    def test_password_reset_confirm_missing_password_fields(self):
        url = reverse('password_reset_confirm', kwargs={
                      'uidb64': self.uidb64, 'token': self.token})

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('This field is required.', response.data['new_password'][0])
        self.assertIn('This field is required.', response.data['confirm_password'][0])
