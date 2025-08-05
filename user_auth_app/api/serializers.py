from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    This serializer is used to handle the creation of new user accounts.
    It includes fields for email, password, and a password confirmation field.
    The username is automatically generated from the email address.
    """
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        # 'username' is NO longer listed here!
        fields = ['email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'email': {
                'required': True
            }
        }

    def validate(self, data):
        """
        Checks if the two password entries match.
        """
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def validate_email(self, value):
        """
        Checks if the email already exists in the database.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value

    def save(self):
        """
        Creates a new but inactive user.
        Saves a new user to the database with the given email and password.
        The username is set to the email. The user is initially marked as inactive.
        """
        email = self.validated_data['email']
        password = self.validated_data['password']

        account = User(
            email=email,
            username=email
        )
        # Important: Set the password and mark the user as inactive.
        account.set_password(password)
        account.is_active = False
        account.save()
        return account


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer for obtaining token pairs that uses email instead of username.
    Inherits from TokenObtainPairSerializer and customizes the authentication method to use email.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        """
        Initializes the serializer and removes the 'username' field.
        """
        super().__init__(*args, **kwargs)

        if "username" in self.fields:
            self.fields.pop("username")

    def validate(self, attrs):
        """
        Validates the user's credentials.
        Checks the email and password, ensures the user exists and is active.
        If the credentials are valid, the username is added for token generation.
        """
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("email or password does not exist.")

        if not user.check_password(password):
            raise serializers.ValidationError("email or password does not exist.")

        if not user.is_active:
            raise serializers.ValidationError(
                "Account is not active. Please check your E-Mails for the activation link."
            )

        attrs['username'] = user.username
        data = super().validate(attrs)
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset e-mail.
    Validates that a user with the given email address exists.
    """
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming a password reset.
    Takes a new password and a confirmation and ensures they match.
    """
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        """
        Check that the two password entries match.
        """
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data
