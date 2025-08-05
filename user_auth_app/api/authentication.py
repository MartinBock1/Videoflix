from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom authentication class for Django Rest Framework that extends JWTAuthentication.

    This class overrides the default behavior to extract the JSON Web Token (JWT)
    from a secure, HTTP-only cookie named 'access_token', instead of the
    standard 'Authorization' header.

    This approach is commonly used for browser-based clients (e.g., Single Page
    Applications) where storing JWTs in cookies is preferred for security reasons,
    such as mitigating Cross-Site Scripting (XSS) attacks.
    """

    def authenticate(self, request):
        """
        The entry point for the authentication process for each incoming request.

        This method attempts to retrieve the 'access_token' from the request's
        cookies. If the cookie is not present, it returns `None`, signaling that
        this authentication backend cannot handle the request, and allowing other
        authentication methods (if any) to be attempted.

        If a token is found, it is validated using the parent class's logic.
        If the token is invalid (e.g., malformed, expired), the `get_validated_token`
        method will raise an `InvalidToken` exception. This exception is intentionally
        not caught here, allowing DRF's default exception handler to process it and
        generate a standard 401 Unauthorized response with a detailed error code
        (e.g., 'token_not_valid').

        Args:
            request (HttpRequest): The incoming HTTP request object.

        Returns:
            A tuple of (user, validated_token) on successful authentication.
            `None` if no 'access_token' cookie is present in the request.

        Raises:
            rest_framework_simplejwt.exceptions.InvalidToken: If the token is
                found but is invalid, expired, or malformed.
        """
        # Attempt to retrieve the access token from the request's cookies.
        access_token = request.COOKIES.get('access_token')

        # If no access token is found in the cookies, we cannot authenticate.
        # Return None to signal that authentication has not been attempted.
        if not access_token:
            return None

        
        try:
            # If a token is found, use the parent class's method to validate it.
            # This will raise an `InvalidToken` exception if validation fails.
            validated_token = self.get_validated_token(access_token)
            
            # If the token is valid, use the parent class's method to retrieve the
            # user associated with this token.
            user = self.get_user(validated_token)
            
        except (InvalidToken, TokenError) as e:
            # Log the error for debugging.
            # print(f“CookieJWTAuthentication Error: {e}”)
            # Important: Raise the exception so that DRF returns a 401 error
            # with error details (e.g., “token_not_valid”).
            # If you return `None` here, the error will be “swallowed.”
            raise InvalidToken(f"Token is invalid or expired: {e}")
        
        if not user or not user.is_active:
            # No user found or user is inactive.
            return None

        # On success, return the user and the validated token.
        return user, validated_token
