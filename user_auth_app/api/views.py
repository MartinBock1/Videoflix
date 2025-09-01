from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings

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
    created but marked as inactive. An activation email is then sent to the
    user's provided email address.
    """    
    permission_classes = [AllowAny]
        
    def post(self, request):
        """
        Processes the user registration request.

        This method validates the registration data, creates a new user,
        generates an account activation link, and sends it via email.

        Args:
            request (Request): The HTTP request object containing user data
                               (e.g., email, password).

        Returns:
            Response: An HTTP response object. If successful, it returns a 201 CREATED
                      status with the new user's basic data. If validation fails,
                      it returns a 400 BAD REQUEST status with the validation errors.
        """
        
        serializer = RegistrationSerializer(data=request.data)
        data = {}

        if serializer.is_valid():
            saved_account = serializer.save()

            # --- Email Activation Logic ---

            # Generate the activation parameters
            # 'uidb64' is the user's primary key encoded in base64.
            # 'token' is the security token to verify the user's identity.
            uidb64 = urlsafe_base64_encode(force_bytes(saved_account.pk))
            token = account_activation_token.make_token(saved_account)

            # Create direct link to frontend activation page with parameters
            # activation_link = (
            #     "http://127.0.0.1:5500/pages/auth/activate.html"
            #     f"?uid={uidb64}&token={token}"
            # )
            activation_link = (
                "http://localhost:4200/auth/activate.html"
                f"?uid={uidb64}&token={token}"
            )
            mail_subject = 'Activate your Videoflix account.'

            # Create plain text message to avoid HTML escaping
            message = (
                f"Hi {saved_account.username},\n"
                "Please click on the link below to activate your account:\n\n"
                f"{activation_link}\n\n"
                "If you did not request this, please ignore this email."
            )

            to_email = serializer.validated_data.get('email')
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.send()
            # --- End of Email Activation Logic ---

            data = {
                "message": (
                    "User registered successfully. "
                    "Please check your email to activate your account."
                ),
                "user": {"id": saved_account.pk, "email": saved_account.email},
            }
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivationView(APIView):
    """
    Handles the account activation process.

    This view is accessed via API calls from the frontend after the user
    clicks the activation link in their email. It verifies the user ID 
    and token from the URL to activate the account.
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        """
        Processes the GET request to activate a user account.
        This endpoint is called by the frontend after the user clicks the activation link.

        It decodes the user ID from the base64 encoded string and checks
        if the provided token is valid for that user.

        Args:
            request (Request): The HTTP request object.
            uidb64 (str): The user's primary key encoded in base64 (passed as 'uid' in URL).
            token (str): The activation token for the user.

        Returns:
            Response: An HTTP response indicating success or failure of the
                      activation attempt.
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"error": "Invalid activation link!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user is not None and account_activation_token.check_token(user, token):
            if user.is_active:
                return Response(
                    {"message": "Account is already activated!"},
                    status=status.HTTP_200_OK
                )

            user.is_active = True
            user.save()
            return Response(
                {"message": "Account successfully activated!"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Activation link is invalid or has expired!"},
                status=status.HTTP_400_BAD_REQUEST
            )


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    Custom view for obtaining JWT tokens and setting them as HTTPOnly cookies.

    This view extends Simple JWT's TokenObtainPairView to use a custom serializer
    (`CustomTokenObtainPairSerializer`) for email-based authentication. Instead
    of returning tokens in the response body, it sets the access and refresh
    tokens in secure, HTTPOnly cookies. This is a common security best practice
    as it helps prevent token theft via cross-site scripting (XSS) attacks.
    """
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = serializer.validated_data["refresh"]
        access = serializer.validated_data["access"]
        user = serializer.user

        response = Response(
            {
                "detail": "login successful",
                "user": {
                    "id": user.id,
                    "username": user.username
                },
            }
        )

        # Use environment-aware cookie settings from SIMPLE_JWT
        jwt_settings = settings.SIMPLE_JWT
        
        response.set_cookie(
            key=jwt_settings.get('AUTH_COOKIE', 'access_token'),
            value=str(access),
            max_age=int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            httponly=jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            secure=jwt_settings.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
            samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            domain=jwt_settings.get('AUTH_COOKIE_DOMAIN'),
            path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        )

        response.set_cookie(
            key=jwt_settings.get('AUTH_REFRESH_COOKIE', 'refresh_token'),
            value=str(refresh),
            max_age=int(jwt_settings['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            httponly=jwt_settings.get('AUTH_REFRESH_COOKIE_HTTP_ONLY', True),
            secure=jwt_settings.get('AUTH_REFRESH_COOKIE_SECURE', not settings.DEBUG),
            samesite=jwt_settings.get('AUTH_REFRESH_COOKIE_SAMESITE', 'Lax'),
            domain=jwt_settings.get('AUTH_REFRESH_COOKIE_DOMAIN'),
            path=jwt_settings.get('AUTH_REFRESH_COOKIE_PATH', '/'),
        )

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
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token is None:
            return Response(
                {"detail": "Refresh token not found!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except:
            return Response(
                {"detail": "Refresh token invalid!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access_token = serializer.validated_data.get("access")

        response = Response(
            {
                "detail": "Token refreshed",
                "access": "new_access_token"
            }
        )

        # Use SIMPLE_JWT settings for cookie configuration
        jwt_settings = settings.SIMPLE_JWT
        
        response.set_cookie(
            key=jwt_settings.get('AUTH_COOKIE', 'access_token'),
            value=access_token,
            max_age=int(jwt_settings['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            httponly=jwt_settings.get('AUTH_COOKIE_HTTP_ONLY', True),
            secure=jwt_settings.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
            samesite=jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            domain=jwt_settings.get('AUTH_COOKIE_DOMAIN'),
            path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
        )

        return response


class PasswordResetRequestView(APIView):
    """
    Handles the initial request from a user to reset their password.

    This view accepts a POST request with an email address. If the email
    is valid, it initiates the password reset process by sending an email
    containing a unique reset link.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Processes the password reset request.

        Validates the provided email. If a corresponding user exists, a
        password reset token and link are generated and sent via email.
        For security reasons, it always returns a success response, even
        if the email address is not in the database.

        Args:
            request (Request): The HTTP request object containing the email.

        Returns:
            Response: A 200 OK response indicating that the process has
                      been initiated, or a 400 Bad Request with errors.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Create direct link to frontend password reset page with parameters
                # reset_link = (
                #     "http://127.0.0.1:5500/pages/auth/confirm_password.html"
                #     f"?uid={uid}&token={token}"
                # )
                reset_link = (
                    "http://localhost:4200/auth/confirm_password.html"
                    f"?uid={uid}&token={token}"
                )

                mail_subject = 'Reset your password.'
                
                # Create plain text message to avoid HTML escaping
                message = (
                    f"Hello {user.username},\n\n"
                    "You requested a password reset for your account.\n"
                    "Please go to the following link to set a new password:\n\n"
                    f"{reset_link}\n\n"
                    "If you didn't request this, you can safely ignore this email.\n\n"
                    "Thanks,\n"
                    "Martin Bock"
                )

                email_message = EmailMessage(
                    mail_subject, message, to=[email]
                )
                email_message.send()

            except User.DoesNotExist:
                # If the user does not exist, we do nothing ('pass').
                # This prevents an attacker from discovering which emails are
                # registered in the system (email enumeration attack).
                pass

            # Always return a success response, regardless of whether the
            # user was found. This is part of the security measure.
            return Response(
                {"detail": "If an account with this email exists, "
                           "an email has been sent to reset your password."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    Handles the final step of the password reset process.

    This view receives the user ID (uidb64), a token, and the new password
    via a POST request. It validates the token and, if successful, updates
    the user's password.
    """
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token, *args, **kwargs):
        """
        Processes the password reset confirmation.

        Validates the token and user ID from the URL. If they are valid,
        it validates the new password from the request body and saves it.

        Args:
            request (Request): The HTTP request, containing the new password.
            uidb64 (str): The user's primary key encoded in base64.
            token (str): The password reset token.

        Returns:
            Response: A response indicating success or failure.
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            serializer = PasswordResetConfirmSerializer(data=request.data)

            if serializer.is_valid():
                new_password = serializer.validated_data['new_password']
                user.set_password(new_password)
                user.save()

                return Response(
                    {"detail": "Your Password has been successfully reset."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response(
                {"error": "Password reset link is invalid or has expired!"},
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutView(APIView):
    """
    Handles user logout by invalidating the refresh token.

    This view requires the user to be authenticated via a JWT stored in a
    cookie. Upon a successful POST request, it blacklists the refresh
    token (preventing its reuse) and instructs the browser to delete the
    access and refresh token cookies.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Processes the logout request.

        Args:
            request (Request): The HTTP request object.

        Returns:
            Response: An HTTP response confirming logout or reporting an error.
        """
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token is None:
            # This case is unlikely if IsAuthenticated works, but it's good practice.
            return Response(
                {"error": "Refresh token not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            response = Response({
                "detail": "Log-Out successfully! Tokens have been invalidated."
            }, status=status.HTTP_200_OK)

            # Use SIMPLE_JWT settings for cookie deletion
            jwt_settings = settings.SIMPLE_JWT
            
            response.delete_cookie(
                key=jwt_settings.get('AUTH_COOKIE', 'access_token'),
                path=jwt_settings.get('AUTH_COOKIE_PATH', '/'),
                domain=jwt_settings.get('AUTH_COOKIE_DOMAIN')
            )
            response.delete_cookie(
                key=jwt_settings.get('AUTH_REFRESH_COOKIE', 'refresh_token'),
                path=jwt_settings.get('AUTH_REFRESH_COOKIE_PATH', '/'),
                domain=jwt_settings.get('AUTH_REFRESH_COOKIE_DOMAIN')
            )

            return response
        except Exception as e:

            return Response(
                {"error": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )
