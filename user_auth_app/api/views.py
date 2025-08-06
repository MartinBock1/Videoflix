from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
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
        # Instantiate the serializer with the data received from the request body.
        serializer = RegistrationSerializer(data=request.data)
        # Prepare an empty dictionary to hold the response data.
        data = {}

        # Validate the serializer's data. 'raise_exception=True' could be used here
        # to automatically handle errors, but manual handling is shown.
        if serializer.is_valid():
            # If the data is valid, save the new user to the database.
            # The .save() method of the serializer will call the .create() method.
            saved_account = serializer.save()

            # --- Email Activation Logic ---

            # Generate a relative URL for the account activation endpoint.
            # 'uidb64' is the user's primary key encoded in base64.
            # 'token' is the security token to verify the user's identity.
            relative_link = reverse('activate', kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(saved_account.pk)),
                'token': account_activation_token.make_token(saved_account),
            })

            # Build a full, absolute URL (e.g., http://127.0.0.1:8000/api/activate/...)
            # This is necessary for the link to work when clicked from an email client.
            activation_link = request.build_absolute_uri(relative_link)

            # Define the subject for the activation email.
            mail_subject = 'Activate your Videoflix account.'

            # Render an HTML template into a string to use as the email body.
            # Pass the user object and activation link to the template context.
            message = render_to_string('acc_active_email.html', {
                'user': saved_account,
                'activation_link': activation_link,
            })

            # Get the user's email address from the validated data.
            to_email = serializer.validated_data.get('email')

            # Create an EmailMessage instance with the subject, body, and recipient.
            email = EmailMessage(mail_subject, message, to=[to_email])

            # Send the email.
            email.send()

            # Prepare the success response data, including the new user's ID and email.
            data = {
                "message": ("User registered successfully. \
                    Please check your email to activate your account."),
                "user": {"id": saved_account.pk, "email": saved_account.email},
            }
            # Return a 201 CREATED response with the success data.
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            # If the serializer is not valid, return the dictionary of errors.
            # A 400 BAD REQUEST status indicates a client-side error.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivationView(APIView):
    """
    "Handles the account activation process.

    This view is accessed via the activation link sent to the user's email.
    It verifies the user ID and token from the URL to activate the account.
    """
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        """
        Processes the GET request to activate a user account.

        It decodes the user ID from the base64 encoded string and checks
        if the provided token is valid for that user.

        Args:
            request (Request): The HTTP request object.
            uidb64 (str): The user's primary key encoded in base64.
            token (str): The activation token for the user.

        Returns:
            Response: An HTTP response indicating success or failure of the
                      activation attempt.
        """
        try:
            # Decode the base64 encoded user ID.
            uid = force_str(urlsafe_base64_decode(uidb64))
            # Retrieve the user from the database using the decoded ID.
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            # If any error occurs during decoding or user lookup, set user
            # to None. This handles invalid uidb64 values or non-existent users.
            user = None

        # Check if the user exists and the token is valid for this user.
        if user is not None and account_activation_token.check_token(user, token):
            # If both are valid, activate the user account.
            user.is_active = True
            user.save()
            # Return a success message.
            return Response(
                {"message": "Account successfully activated!"},
                status=status.HTTP_200_OK
            )
        else:
            # If the user or token is invalid, return an error message.
            return Response(
                {"error": "Activation link is invalid!"},
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
        # Instantiate the serializer with the data from the request.
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']

            # This try-except block is a critical security measure.
            # It ensures the logic inside only runs if the user exists,
            # but prevents leaking information about which emails are registered.
            try:
                user = User.objects.get(email=email)

                # Generate a one-time token and a base64 encoded user ID.
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Build the full password reset confirmation link.
                relative_link = reverse(
                    'password_reset_confirm',
                    kwargs={'uidb64': uid, 'token': token}
                )
                reset_link = (
                    f"{request.scheme}://{request.get_host()}{relative_link}"
                )

                # Prepare and send the email.
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
            # If the serializer is invalid (e.g., malformed email),
            # return the validation errors.
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
        # First, try to decode the user ID and find the user.
        try:
            # Decode the base64 string to get the user's primary key.
            # force_str is used to convert the resulting bytes into a string.
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            # If the uidb64 is invalid or the user doesn't exist,
            # treat it as if the user is None.
            user = None

        # Check if the user object is valid and the token is correct for them.
        # The token is time-sensitive and becomes invalid after use.
        if user is not None and default_token_generator.check_token(user, token):
            # If the user and token are valid, proceed to validate the new password.
            serializer = PasswordResetConfirmSerializer(data=request.data)

            if serializer.is_valid():
                # Get the validated new password from the serializer.
                new_password = serializer.validated_data['new_password']
                
                # Use set_password() to ensure the password is correctly hashed.
                # Never assign a password directly (e.g., user.password = ...)!
                user.set_password(new_password)
                user.save()

                return Response(
                    {"detail": "Your Password has been successfully reset."},
                    status=status.HTTP_200_OK
                )
            else:
                # If the new password is not valid (e.g., too short),
                # return the validation errors.
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            # If the user is None or the token is invalid, return an error.
            # This is a security measure to prevent invalid attempts.
            return Response(
                {"error":"Password reset link is invalid or has expired!"},
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
    # Use your custom authentication class to read the JWT from the cookie.
    authentication_classes = [CookieJWTAuthentication]
    # Ensure that only authenticated users can access this endpoint.
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Processes the logout request.

        Args:
            request (Request): The HTTP request object.

        Returns:
            Response: An HTTP response confirming logout or reporting an error.
        """
        # Retrieve the refresh token from the browser's cookies.
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token is None:
            # This case is unlikely if IsAuthenticated works, but it's good practice.
            return Response(
                {"error": "Refresh token not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create a RefreshToken object from the token string.
            token = RefreshToken(refresh_token)
            # Blacklist the token. This adds it to a database table of invalid
            # tokens, rendering it unusable for future authentication.
            token.blacklist()

            # Create a success response object. We must create the response
            # before we can attach cookie deletion instructions to it.
            response = Response({
                "detail": "Log-Out successfully! Tokens have been invalidated."
            }, status=status.HTTP_200_OK)

            # Instruct the browser to delete the cookies by setting an empty
            # value and an expired timestamp.
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")

            return response
        except Exception as e:
            
            # Catching a specific TokenError is better than a generic Exception.
            # This occurs if the token is malformed, expired, or already blacklisted.
            return Response(
                {"error": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )
