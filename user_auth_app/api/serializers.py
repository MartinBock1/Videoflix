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
        # 'username' ist hier NICHT mehr aufgeführt!
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
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value

    def save(self):
        email = self.validated_data['email']
        password = self.validated_data['password']

        account = User(
            email=email,
            username=email
        )
        # Wichtig: Setzen Sie das Passwort und markieren Sie den Benutzer als inaktiv.
        account.set_password(password)
        account.is_active = False
        account.save()
        return account


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "username" in self.fields:
            self.fields.pop("username")

    def validate(self, attrs):
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
