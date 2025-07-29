from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


class LoginTests(APITestCase):

    def setUp(self):
        """
        Erstellt einen aktiven Benutzer für die Login-Tests.
        """
        self.user = User.objects.create_user(
            username='exampleUsername',
            email='example@mail.de',
            password='examplePassword'
        )
        self.user.is_active = True
        self.user.save()

        # Korrekter URL-Name für den Login-Endpunkt
        self.login_url = reverse('token_obtain_pair')

    def test_login_success(self):
        """
        Testet den erfolgreichen Login.
        Sendet die korrekten Felder (email/password) und prüft die korrekte Antwort.
        """
        # KORREKT: Senden Sie 'email', nicht 'username'
        data = {
            "email": "example@mail.de",
            "password": "examplePassword"
        }
        response = self.client.post(self.login_url, data, format='json')

        # 1. Überprüfen, ob die Anfrage erfolgreich war (Status 200 OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. KORREKT: Überprüfen der korrekten Antwortstruktur
        self.assertEqual(response.data['detail'], 'login successful')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['user']['username'], self.user.username)

        # 3. KORREKT: Überprüfen, ob die Cookies gesetzt wurden
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_login_with_inactive_account(self):
        """
        Testet den Login-Versuch eines validen, aber inaktiven Benutzers.
        Dies ist ein kritischer Test für den Registrierungs-Flow.
        """
        # Einen neuen, inaktiven Benutzer erstellen
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

        # Erwartet einen 400er Fehler
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Prüft die spezifische Fehlermeldung aus Ihrem Serializer
        self.assertIn('non_field_errors', response.data)
        expected_error = "Account is not active. Please check your E-Mails for the activation link."
        self.assertEqual(response.data['non_field_errors'][0], expected_error)

    def test_login_bad_credentials(self):
        """
        Testet den Login mit falschem Passwort.
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
        Testet den Login mit einem nicht existierenden Benutzer.
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
        Testet den Login mit fehlenden Feldern.
        """
        data = {
            "email": "",
            "password": ""
        }
        response = self.client.post(self.login_url, data, format='json')

        # Erwartet einen 400 Bad Request wegen Validierungsfehlern
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Spezifisch prüfen, dass für beide Felder Fehler gemeldet werden
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)
        self.assertEqual(response.data['email'][0], 'This field may not be blank.')
        self.assertEqual(response.data['password'][0], 'This field may not be blank.')
