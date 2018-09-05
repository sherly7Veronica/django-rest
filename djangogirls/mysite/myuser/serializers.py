from rest_framework import serializers
from models import GENDER_CHOICES, User


class UserSerializer(serializers.Serializer):
    first_name = serializers.CharField (max_length=100)
    last_name = serializers.CharField (max_length=100)
    email = serializers.EmailField ()
    username = serializers.CharField (max_length=100)
    dob = serializers.DateField ()
    phone = serializers.CharField (max_length=20)
    gender = serializers.CharField (choices=GENDER_CHOICES)
    address = serializers.TextField ()
    password = serializers.CharField (maxlength=255)

    def create(self, validate_data):
        password = validate_data.pop("password")
        user = User.objects.create(**validate_data)

        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validate_data):
        password = validate_data.pop("password")
        instance.__dict__.update(validate_data)

        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "username",
            "dob",
            "phone",
            "gender",
            "address"
        )

