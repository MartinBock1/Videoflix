from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView

from .authentication import CookieJWTAuthentication
from .serializers import (
    RegistrationSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .tokens import account_activation_token


class RegistrationView(APIView):
    """
    Handles the creation of new users.

    This view allows any user (authenticated or not) to submit their registration
    details via a POST request. If the data is valid, a new user account is
    created, and their basic information is returned.
    """
    # Set permission to AllowAny, so that unauthenticated users can access this endpoint.
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Processes the user registration request.

        Args:
            request (Request): The HTTP request object containing user data.

        Returns:
            Response: An HTTP response object. If successful, it contains the new
                      user's data. If not, it contains the validation errors.
        """
        # Instantiate the serializer with the data from the request.
        serializer = RegistrationSerializer(data=request.data)

        data = {}
        # Validate the serializer's data.
        if serializer.is_valid():
            # If valid, save the new user to the database.
            saved_account = serializer.save()
            current_site = get_current_site(request)
            mail_subject = 'Activate your Videoflix account.'

            message = render_to_string('acc_active_email.html', {
                'user': saved_account,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(saved_account.pk)),
                'token': account_activation_token.make_token(saved_account),
            })
            to_email = serializer.validated_data.get('email')
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.send()  # E-Mail senden

            # Prepare the data to be sent in the response.
            data = {
                "user": {
                    "id": saved_account.pk,
                    "email": saved_account.email
                },
                # Geben Sie den Token zur Information zurück
                "token": account_activation_token.make_token(saved_account)
            }
            # Return the user data with a 200 OK status.
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            # If the data is invalid, return the errors with a 400 Bad Request status.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        try:
            uid = force_bytes(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"message": "Account successfully activated!"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Activation link is invalid!"}, status=status.HTTP_400_BAD_REQUEST)


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    Custom view for obtaining JWT tokens and setting them as HTTPOnly cookies.

    This view extends Simple JWT's TokenObtainPairView to use a custom serializer
    (`CustomTokenObtainPairSerializer`) for email-based authentication. Instead
    of returning tokens in the response body, it sets the access and refresh
    tokens in secure, HTTPOnly cookies. This is a common security best practice
    as it helps prevent token theft via cross-site scripting (XSS) attacks.
    """
    # Specify the custom serializer to be used for token generation.
    # This serializer handles authentication using email and password.
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """
        Handles the POST request to log in a user and set tokens in cookies.

        This method processes the login request by first validating the user's
        credentials (email and password) using the custom serializer. If the
        credentials are valid, it extracts the generated access and refresh
        tokens. It then creates a response with a success message and attaches
        the tokens as secure, HTTPOnly cookies.

        Args:
            request (Request): The HTTP request object containing user credentials.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: An HTTP response object with a success message and cookies set.
                      If authentication fails, the serializer will raise an
                      exception, resulting in a 401 Unauthorized response.
        """
        # Instantiate the serializer with the data from the request.
        serializer = self.get_serializer(data=request.data)
        # Validate the serializer. If the credentials are invalid, this will
        # raise a serializers.ValidationError, which DRF handles by returning
        # a 401 Unauthorized response.
        serializer.is_valid(raise_exception=True)

        # If validation is successful, extract the refresh and access tokens
        # from the validated data.
        refresh = serializer.validated_data["refresh"]
        access = serializer.validated_data["access"]

        user = serializer.user

        # Create the initial response object with a success message.
        response = Response(
            {
                "detail": "login successful",
                "user": {
                    "id": user.id,
                    "username": user.username
                },
            }
        )

        # Set the access token in a secure, HTTPOnly cookie.
        # httponly=True: Prevents client-side JavaScript from accessing the cookie.
        # secure=True: Ensures the cookie is only sent over an HTTPS connection.
        # samesite='Lax': Provides a balance between security and usability by
        #                 sending the cookie for top-level navigations.
        response.set_cookie(
            key="access_token",
            value=str(access),
            httponly=True,
            secure=True,
            samesite="Lax",
        )

        # Set the refresh token in another secure, HTTPOnly cookie with the same settings.
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Lax",
        )

        # Return the final response to the client.
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """
    Custom view to refresh the access token using a refresh token from a cookie.

    This view extends Simple JWT's TokenRefreshView to read the refresh token
    from an HTTPOnly cookie. If the token is valid, it generates a new access
    token and sets it in a new HTTPOnly cookie.
    """

    def post(self, request, *args, **kwargs):
        """
        Handles the POST request to refresh an access token.

        Args:
            request (Request): The HTTP request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: An HTTP response object with a success message and a new
                      access token cookie, or an error response if the refresh
                      token is missing or invalid.
        """
        # Retrieve the refresh token from the request's cookies.
        refresh_token = request.COOKIES.get("refresh_token")

        # Check if the refresh token exists.
        if refresh_token is None:
            return Response(
                {"detail": "Refresh token not found!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize the serializer with the refresh token from the cookie.
        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            # Validate the refresh token. raise_exception=True will raise an exception
            # for invalid tokens.
            serializer.is_valid(raise_exception=True)
        except:
            # If the token is invalid, return an unauthorized status.
            return Response(
                {"detail": "Refresh token invalid!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Get the new access token from the validated serializer data.
        access_token = serializer.validated_data.get("access")

        # Create a response with a success message.
        response = Response(
            {
                "detail": "Token refreshed",
                "access": "new_access_token"
            }
        )
        # Set the new access token in a secure, HTTPOnly cookie.
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax",
        )

        return response


class PasswordResetRequestView(APIView):
    """
    Handles the request to send a password reset link.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Processes the request to send a password reset email.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)                
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                relative_link = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                reset_link = f"{request.scheme}://{request.get_host()}{relative_link}"

                mail_subject = 'Reset your password.'
                message = render_to_string('password_reset_email.html', {
                    'user': user,
                    'reset_link': reset_link,
                })
                
                email_message = EmailMessage(
                    mail_subject, message, to=[email]
                )
                email_message.send()

            except User.DoesNotExist:
                pass

            return Response(
                {"detail": "An email has been sent to reset your password."}, 
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    Handles the actual password reset.
    """
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token, *args, **kwargs):
        """
        Processes the password reset confirmation.
        """
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
             # Token is valid. Now we validate the new password.
            serializer = PasswordResetConfirmSerializer(data=request.data)
            
            if serializer.is_valid():
                new_password = serializer.validated_data['new_password']
                # Set the new password and save the user.
                # set_password takes care of the correct hashing.
                user.set_password(new_password)
                user.save()
                
                return Response(
                    {"detail": "Your Password has been successfully reset."}, 
                    status=status.HTTP_200_OK
                )
            else:
                # The passwords do not match or are invalid.
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            # The link is invalid or has expired.
            return Response(
                {"error": "Activation link is invalid or has expired!"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutView(APIView):
    """
    Handles user logout by blacklisting the refresh token and deleting session cookies.

    This view requires the user to be authenticated via a valid access token.
    It reads the refresh token from the HTTPOnly cookie, adds it to the blacklist
    to invalidate it, and then instructs the client to delete both the access and
    refresh token cookies.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Processes the logout request.

        Args:
            request (Request): The HTTP request object.

        Returns:
            Response: An HTTP response object confirming logout and instructing
                      the client to delete the authentication cookies.
        """
        # Holen des Refresh-Tokens aus dem Cookie
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token is None:
            return Response(
                {"error": "Refresh token not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Den Token zur Blacklist hinzufügen
            token = RefreshToken(refresh_token)
            token.blacklist()

            # Erfolgsmeldung gemäss API-Doku erstellen
            response = Response({
                "detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."
            }, status=status.HTTP_200_OK)

            # Cookies im Browser des Clients löschen
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")

            return response
        except Exception as e:
            # Falls der Token bereits ungültig oder manipuliert ist
            return Response(
                {"error": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )
