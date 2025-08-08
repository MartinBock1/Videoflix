from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    This class generates a unique token for account activation.
    It inherits from Django's PasswordResetTokenGenerator and modifies the
    hash value to include the user's primary key, a timestamp, and their active status.
    This ensures that the token is unique and becomes invalid once the user is activated.
    """
    def _make_hash_value(self, user, timestamp):
        """
        This method creates a hash value that will be used to generate the token.

        Args:
            user: The user object for whom the token is being generated.
            timestamp: The current timestamp.

        Returns:
            A string containing the user's primary key, the timestamp, and the user's active
            status.
        """
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.is_active)
        )

account_activation_token = AccountActivationTokenGenerator()
